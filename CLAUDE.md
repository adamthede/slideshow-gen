# Slideshow Generator

Ken Burns slideshow generator with EXIF-aware metadata overlays. Takes directories of images and video files and produces MP4 video slideshows for playback on digital picture frames and computers.

## Two layers, one repo

- **`slideshow-gen`** — the Python CLI / engine. Package, binary, and module name. Stable, library-callable via `RenderPipeline`, instrumented for IPC via `--ipc` (see `docs/sidecar-protocol.md`).
- **Marquee** — the macOS desktop app (in development) that wraps the engine. Tauri + React + shadcn/ui shell, with the CLI frozen as a signed sidecar binary. Bundle ID `com.thedetech.marquee`, team `U85N54PC5J`. See [ADR-0001](docs/adr/0001-app-stack.md) and `_bmad-output/planning-artifacts/prd.md` for the architecture and roadmap. App scaffolding lives (or will live) under `desktop/`.

## Tech Stack

- **Python 3.11+** with virtual environment at `.venv/`
- **FFmpeg 7.1+** via subprocess (not a binding)
- **Click** for CLI
- **Pillow + pillow-heif** for image handling and HEIC conversion
- **ExifRead** for EXIF metadata extraction
- **reverse_geocoder** for offline GPS-to-city geocoding

## Development

```bash
source .venv/bin/activate
pip install -e .
slideshow-gen render --help
```

## Architecture

Three-phase FFmpeg render pipeline:
1. **Phase 1:** Each image → individual temp clip (Ken Burns + overlay baked in, 4x supersampled)
2. **Phase 2:** Consecutive clips batched into groups of 50 with crossfades
3. **Phase 3:** Batches + video clips composited into final MP4

Key modules:
- `cli.py` — Click entry point
- `config.py` — RenderConfig dataclass (single source of truth)
- `discovery.py` — file scanning, sorting, dedup
- `metadata.py` — EXIF reading, filename parsing, reverse geocoding
- `kenburns.py` — zoompan filter expression generator
- `overlay.py` — drawtext filter strings with fade alpha
- `ffmpeg.py` — subprocess runner, filter scripts, parallel execution
- `pipeline.py` — three-phase orchestrator

## Conventions

- Filter graphs written to script files (`-filter_complex_script`), never inline
- All encodes use `h264_videotoolbox -b:v 20M` (Apple Silicon hardware encoder) — intermediates and final alike. Final output adds `-movflags +faststart` for streaming.
- Progressive temp cleanup after each batch reduction
- HEIC files pre-converted to JPG before FFmpeg processing
