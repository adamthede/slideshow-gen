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
| `deduplication` | Hashing items to detect duplicates (sits between `discovery` and `discovery_complete`) |
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

Convenience event emitted at the end of `discovery` with parsed counts and metadata. Always fires before the first non-discovery `phase_started`.

```json
{"v": 1, "t": 0.08, "type": "discovery_complete", "images": 4127, "videos": 23,
 "date_range": {"earliest": "2020-01-15", "latest": "2024-05-23"},
 "gps_coverage_percent": 87.3,
 "duplicates_detected": 12}
```

- `images`, `videos`: Always present. Counts of each media type after discovery.
- `date_range`: Object with `earliest` and `latest` ISO date strings. **Omitted** when no parsed dates were found during discovery — embedders must handle absence.
- `gps_coverage_percent`: Percentage of items with valid GPS coordinates (0–100). **Always present** when items were discovered; `0.0` means no GPS data, not "field missing".
- `duplicates_detected`: Count of duplicate items detected via content hash. **Always present** when items were discovered; `0` means no duplicates found. *Note:* the engine reports duplicates but does not currently remove them from the render — the field name reflects detection, not removal.

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

### `item_failed`

A single input item could not be processed and was skipped. The render continues; this is a **non-fatal** per-item failure (e.g. one corrupt JPEG out of thousands). The UI should surface these passively — no modal, no required action.

```json
{"v": 1, "t": 95.0, "type": "item_failed",
 "phase": "images",
 "path": "/abs/path/to/corrupt.jpg",
 "reason": "ffmpeg returned non-zero",
 "detail": "...last lines of stderr..."}
```

Fields:

- `phase`: which pipeline phase the failure occurred in. Currently always `"images"` (Phase 1 Ken Burns clip render, and item-scoped Phase 1 video prep). Future phases may emit per-item failures too.
- `path`: absolute path of the offending source file.
- `reason`: short human-readable string (e.g. `"ffmpeg returned non-zero"`, `"HEIC conversion failed"`, `"video prep failed"`, `"worker crashed"`).
- `detail`: optional longer string with diagnostic context (last lines of FFmpeg stderr, exception message). Omitted when there's nothing useful to add.

Skipped items are counted in the terminating `complete` event's `items_skipped` field. Progress counts continue to use the *attempted* total so the bar still completes.

`item_failed` events are distinct from `warning` events: warnings are general non-fatal messages (e.g. "batch fell back to individual clips"); `item_failed` is specifically about a single input item being dropped from the render.

### `complete`

Lifecycle terminator on success. Lists all output files written.

```json
{"v": 1, "t": 21600.0, "type": "complete",
 "outputs": [{"path": "/path/to/out.mp4", "size_bytes": 32145678901}],
 "elapsed_s": 21600.0,
 "items_skipped": 0}
```

For chunked output, multiple entries appear in `outputs`.

`items_skipped` is the count of source files that failed to process and were dropped (see `item_failed`). `0` when every input rendered cleanly. The number is monotonic with the count of `item_failed` events the embedder has seen — embedders that need per-item detail should accumulate `item_failed` events; `items_skipped` is the canonical summary number.

### `cancelled`

Lifecycle terminator when the render is cancelled (the embedder sent SIGTERM — see [Cancellation](#cancellation)). Emitted *instead of* `complete`, immediately before the process exits with code `130`. No output file is written.

```json
{"v": 1, "t": 42.3, "type": "cancelled", "message": null}
```

`message` is optional. This event is the **primary, unambiguous** cancel signal — prefer it over the exit-code heuristic below.

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

### Cancellation

```
started
phase_started(images)
progress(images) × N
cancelled
```

Process exits `130`. No `complete`, no output file.

When the embedder wants to cancel (user clicks Cancel), it sends **SIGTERM** to the sidecar process. On the `--ipc` path the engine has, at render start, isolated itself and all its FFmpeg children into their own process group; on SIGTERM it reaps that whole group (no orphaned FFmpeg), removes the temp directory (honoring `--keep-temp`), emits `cancelled`, and exits `130`.

The embedder must **not** use `CommandChild::kill()` / SIGKILL for a normal cancel — SIGKILL is uncatchable, so the engine cannot clean up (orphaned FFmpeg, leaked temp). SIGKILL is appropriate only as an escalation if the process has not exited within a grace period after SIGTERM.

Detecting cancellation, in priority order:
1. **The `cancelled` event** (primary, unambiguous).
2. *Fallback only* (e.g. after a SIGKILL escalation where `cancelled` never made it out): absence-of-`complete` + non-zero exit + a recent `progress` — indistinguishable from a mid-render crash, so use only when no `cancelled` event was seen.

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
