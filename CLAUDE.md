# Slideshow Generator

Ken Burns slideshow generator with EXIF-aware metadata overlays. Takes directories of images and video files and produces MP4 video slideshows for playback on digital picture frames and computers.

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
- Intermediate files use `-crf 0 -preset ultrafast` (lossless, fast)
- Final output uses `-crf 18 -preset medium -movflags +faststart`
- Progressive temp cleanup after each batch reduction
- HEIC files pre-converted to JPG before FFmpeg processing
