# Sidecar IPC Protocol

The `slideshow-gen` CLI exposes a JSON-line event stream over stdout when invoked with `--ipc`. This is the contract the macOS app's Tauri shell will speak to the embedded (frozen) CLI sidecar binary. See [ADR-0001](adr/0001-app-stack.md) for the architectural decision behind this design.

## Invocation

```
slideshow-gen render --ipc [usual render flags]
```

Every other CLI flag (`--dir`, `--output`, `--resolution`, `--slide-duration`, `--audio-track`, etc.) is honored exactly as in human-readable mode. `--ipc` only changes how progress is reported.

## Stream shape

- One JSON object per line on **stdout**. Lines are newline-delimited (`\n`).
- Each line is a complete event — never line-split inside an object.
- Embedding processes should `flush()`-tolerantly read line-by-line.
- **stderr** may contain framework-level errors (Python tracebacks, FFmpeg crash dumps) that are NOT part of the protocol. Capture stderr separately for diagnostics; do not parse it.

## Common fields

Every event includes:

| Field | Type | Meaning |
|---|---|---|
| `v` | integer | Protocol version. Current: `1`. Embedders should check this. |
| `t` | float | Seconds since the reporter was constructed (≈ render start). 3-decimal precision. |
| `type` | string | Event type — selects the rest of the schema (see below). |

Additional fields are event-specific.

## Event types

### `started`

Emitted once at the very beginning, before any work.

```json
{"v": 1, "t": 0.0, "type": "started", "config": {
  "output": "/path/to/out.mp4",
  "dirs": ["/path/to/folder"],
  "resolution": "1920x1080",
  "slide_duration": 4.0,
  "fade_duration": 0.5,
  "fps": 30,
  "static": false,
  "audio_track": null
}}
```

`config` is a redacted snapshot of the effective render settings. Suitable for display ("rendering folder X at 1080p"). Not exhaustive — only fields useful to the UI.

### `phase_started`

A long-running phase begins. Phases are named:

| `phase` | Meaning |
|---|---|
| `discovery` | Scanning directories for media |
| `images` | Phase 1 Ken Burns clip rendering (parallel) |
| `static-batching` | Static (no Ken Burns) batch rendering |
| `batching` | Phase 2 batch reduction with crossfades |
| `chunking` | Splitting output into time-based chunks |
| `compositing` | Phase 3 final composite via concat demuxer |

```json
{"v": 1, "t": 0.06, "type": "phase_started", "phase": "images", "total": 4127}
```

`total` is the expected number of progress ticks for this phase (may be `null` if not known up front — e.g. `discovery`).

### `progress`

Progress tick within a phase. Fires on each completed unit (image rendered, batch composited, second of final video encoded).

```json
{"v": 1, "t": 12.4, "type": "progress", "phase": "images", "done": 50, "total": 4127, "message": null}
```

`message` is an optional human-friendly hint (e.g. `"2 clips"` during batching).

For the `discovery` phase, progress is throttled to every 25th item (plus the final tick) and `message` carries the current filename. Embedders should treat progress as throttled regardless of phase — `done` is monotonic but not strictly contiguous.

### `phase_complete`

A phase finished cleanly.

```json
{"v": 1, "t": 215.0, "type": "phase_complete", "phase": "images", "message": "4125/4127 rendered"}
```

`message` is optional and human-friendly. Phase-complete is informational — `complete` is the lifecycle terminator.

### `discovery_complete`

Convenience event emitted at the end of `discovery` with parsed counts and optional metadata. Always fires before the first non-discovery `phase_started`.

```json
{"v": 1, "t": 0.08, "type": "discovery_complete", "images": 4127, "videos": 23,
 "date_range": {"earliest": "2020-01-15", "latest": "2024-05-23"},
 "gps_coverage_percent": 87.3,
 "duplicates_removed": 12}
```

- `date_range`: Object with `earliest` and `latest` ISO date strings. Present only if parsed dates were found during discovery.
- `gps_coverage_percent`: Percentage of items with valid GPS coordinates (0–100). Present only if any items have GPS data.
- `duplicates_removed`: Count of duplicate items detected via content hash. Present only if duplicates were found.

### `estimate`

Pre-render duration + size estimate. Fires once after `discovery_complete`. If `--estimate-only` was passed, this is the last event before `info` + clean exit.

```json
{"v": 1, "t": 0.08, "type": "estimate",
 "duration_s": 14512.3, "size_bytes": 36608000000,
 "image_duration_s": 14422.5, "video_duration_s": 89.8}
```

`duration_s` is the predicted slideshow runtime; `size_bytes` is the predicted output file size. Both are computed deterministically from the manifest and bitrate (see `estimate.py`). Real output is within ±20% on typical inputs.

### `info`

Non-critical human-readable message. Equivalent of a `click.echo` in verbose mode. Embedders can log or ignore.

```json
{"v": 1, "t": 1.0, "type": "info", "message": "Temp directory: /var/folders/..."}
```

### `warning`

Non-fatal problem. Render continues. Per-item failures (HEIC conversion failed, single image render failed, batch failed and fell back to individual clips) emit warnings.

```json
{"v": 1, "t": 95.0, "type": "warning", "message": "Static batch 3 failed, skipping.", "file": null}
```

`file` is optional — set when the warning is associated with a specific source path.

### `error`

Fatal — render is aborting. Embedders should expect the process to exit non-zero shortly after. No `complete` event follows.

```json
{"v": 1, "t": 0.05, "type": "error", "message": "FFmpeg not found. Install via: brew install ffmpeg"}
```

### `complete`

Lifecycle terminator on success. Lists all output files written.

```json
{"v": 1, "t": 21600.0, "type": "complete",
 "outputs": [{"path": "/path/to/out.mp4", "size_bytes": 32145678901}],
 "elapsed_s": 21600.0}
```

For chunked output, multiple entries appear in `outputs`.

## Lifecycle examples

### Happy path

```
started
phase_started(discovery)
discovery_complete
estimate
phase_started(images)
progress(images) × N
phase_complete(images)
progress(batching) × M
phase_started(compositing)
progress(compositing) × K
phase_complete(compositing)
complete
```

### `--estimate-only`

```
started
phase_started(discovery)
discovery_complete
estimate
info("--estimate-only: exiting before render.")
```

Process exits 0. No `complete` event — `estimate-only` is a pre-render snapshot, not a render.

### Fatal failure

```
started
error("...")
```

Process exits non-zero. No `complete`.

### Cancellation (future)

When the embedding process terminates the sidecar (e.g. user clicks Cancel), the sidecar receives SIGTERM. It cleans the temp directory and exits without emitting `complete`. The embedder should treat absence-of-`complete` + non-zero exit + recent `progress` as "cancelled or crashed mid-render."

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Render completed successfully OR `--estimate-only` completed |
| Non-zero | Render aborted — see the last `error` event for the reason, and stderr for stack traces |

## Versioning

Bump `PROTOCOL_VERSION` in `events.py` for any breaking change to field semantics, types, or required fields. Additive changes (new optional fields, new event types the embedder can ignore) do not require a bump.

Embedders should warn-or-fail on `v > PROTOCOL_VERSION_KNOWN` rather than silently mis-parsing.

## Implementation notes

- Reporter implementations live in `src/slideshow_gen/events.py`.
- `JsonReporter` writes directly to `sys.stdout` and flushes after each event. The frozen CLI sidecar will be launched with line-buffered stdout so the embedding process sees events promptly.
- `ConsoleReporter` is the default for human invocations and preserves the pre-IPC output style.
