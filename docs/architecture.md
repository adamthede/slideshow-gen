# Architecture — Slideshow Generator

## Executive Summary

slideshow-gen is a CLI tool that converts directories of photos and videos into polished MP4 slideshows with Ken Burns effects and EXIF-derived metadata overlays. The architecture is a straightforward **pipeline pattern**: discover media, enrich with metadata, render individual clips in parallel, batch-composite with transitions, and produce a final output.

## Architecture Pattern

**Pipeline / Batch Processing** — Data flows linearly through discrete phases with no persistent state between runs. There is no server, no database, no event system. Each run is a self-contained transformation from input directories to a single output file.

## Data Flow

```
Input Directories
       │
       ▼
┌─────────────┐
│  discovery   │ Scan files, read EXIF, parse filenames,
│  + metadata  │ reverse geocode GPS, get dimensions
└──────┬──────┘
       │  list[MediaItem]
       ▼
┌─────────────┐
│   Phase 1    │ Per-image: HEIC convert → Ken Burns filter →
│  (parallel)  │ overlay filters → FFmpeg → temp clip
└──────┬──────┘
       │  list[(index, Path)]
       ▼
┌─────────────┐
│   Phase 2    │ Group consecutive image clips into batches,
│  (batching)  │ composite each batch with crossfades
└──────┬──────┘
       │  list[{path, duration}]
       ▼
┌─────────────┐
│   Phase 3    │ Assemble all batches + video clips
│   (final)    │ into single MP4 with crossfades
└──────┬──────┘
       │
       ▼
  Output MP4
```

## Module Responsibilities

### config.py — Configuration

- `RenderConfig` frozen dataclass: single source of truth for all render parameters
- Resolution presets (1080p, 4K), computed properties (supersample dimensions, frame count)
- `IMAGE_EXTENSIONS` and `VIDEO_EXTENSIONS` constants

### cli.py — Entry Point

- Click group with single `render` command
- Maps CLI flags to `RenderConfig` fields
- Lazy imports: `--dry-run` loads only discovery/manifest, full render loads pipeline

### discovery.py — Media Discovery

- `MediaItem` dataclass: path, type, dimensions, metadata, hash
- `scan_directories()`: iterate files, classify by extension, enrich with EXIF/dimensions
- `sort_items()`: chronological sort by filename or random shuffle
- `detect_duplicates()`: SHA-256 of first 64KB + file size

### metadata.py — Metadata Extraction

- `parse_filename()`: 4 regex patterns for structured filename conventions (e.g., `YYYY-MM-DD HH-MM-SS Photographer - Album (Camera).ext`)
- `read_exif()`: ExifRead wrapper for date, GPS, orientation
- `reverse_geocode()`: offline GPS → "City, State/Country" with module-level cache
- `get_date_for_item()`: fallback chain (filename → EXIF → file mtime)
- `format_date()`: human-readable date formatting

### media.py — Image/Video Info

- `get_image_info()`: Pillow with EXIF transpose for actual display dimensions
- `get_video_info()`: ffprobe subprocess for width, height, duration

### heic.py — HEIC Conversion

- Registers pillow-heif opener at import time
- `convert_heic_to_jpg()`: preserves EXIF data, quality 95

### kenburns.py — Ken Burns Effects

- `choose_effect()`: smart detection (panoramas → static, small images → static, otherwise random directions)
- `generate_filter_chain()`: full FFmpeg filter string including format conversion, even-dimension crop, upscaling, padding, 4x supersample, zoompan, and final crop
- Ported from kburns2.rb (sargue/kburns)

### overlay.py — Text Overlays

- `generate_overlay_filters()`: drawtext filter strings for date and location
- Resolution-adaptive font sizing (42/36px at 1080p, 64/54px at 4K)
- Alpha expressions for fade-in → hold → fade-out timing
- Hardcoded macOS font: `/System/Library/Fonts/Helvetica.ttc`

### ffmpeg.py — FFmpeg Execution

- `check_ffmpeg()`: preflight verification
- `render_image_to_clip()`: single image → temp MP4 with full filter chain
- `parallel_render()`: ProcessPoolExecutor with serializable worker args
- `render_batch()`: composite N clips with crossfade overlay stack, filter script files
- `render_final_composite()`: assemble segments into final MP4

### pipeline.py — Orchestrator

- `RenderPipeline` class: manages temp directory lifecycle
- `_build_timeline()`: interleave rendered image clips and processed video clips
- `_batch_reduce()`: group consecutive image clips, flush batches at size limit
- `_flush_batch()`: composite + progressive cleanup of individual clips
- `_prepare_video_clip()`: scale/pad video + overlays

### manifest.py — Dry Run

- `print_manifest()`: formatted summary with item counts, estimated duration/file size, first/last items

## Key Technical Details

### Parallelism Strategy

Phase 1 uses `ProcessPoolExecutor` (not threads) because FFmpeg subprocesses are CPU-bound during filter graph evaluation. Worker count is configurable (default 8). Each worker receives serialized `MediaItem` and `RenderConfig` dicts to avoid pickling issues with dataclass instances.

### Filter Script Pattern

Complex filter graphs are written to temp files and referenced via `-filter_complex_script` rather than passed inline. This avoids:
- Shell escaping nightmares with nested quotes in drawtext
- Command-line length limits on batch composites with many inputs
- Debugging difficulty (scripts can be inspected)

### Batch Compositing

The overlay-stack approach for batch compositing:
1. Create a black canvas of the total batch duration
2. Each clip gets fade-in/fade-out alpha + time offset via `setpts`
3. Clips are overlaid sequentially: `[black][v0]overlay[ov0]; [ov0][v1]overlay[ov1]; ...`

This avoids FFmpeg's `xfade` filter (which has quirks with many inputs) in favor of explicit alpha-based compositing.

### Memory Management

No media content is held in Python memory. Pillow opens images only briefly for dimensions. All heavy lifting happens in FFmpeg subprocesses. The `_fast_hash` function reads only the first 64KB per file for duplicate detection.

## Platform Dependencies

- **macOS-specific:** Font path hardcoded to `/System/Library/Fonts/Helvetica.ttc`
- **FFmpeg required:** Not bundled, must be system-installed
- **Python 3.11+:** Uses `X | None` union syntax, dataclass features

## Known Limitations / Technical Debt

1. **No progress persistence** — if rendering is interrupted, all temp work is lost
2. **No video metadata overlays** — videos get date from filename only (no EXIF equivalent)

*(Note: Previous limitations regarding tests, macOS-only fonts, and lack of audio support were resolved in v0.2.0).*

## GUI Architecture Transition (Phase 3)

The project is currently evolving toward a native macOS GUI application. The planned architecture involves:

1. **Engine Decoupling:** The core logic (`RenderPipeline`, FFmpeg wrappers, config) remains pure Python and fully decoupled from the `click` CLI.
2. **Progress Events:** The pipeline will be refactored to emit progress events (callbacks or observables) rather than printing directly to `stdout`, allowing a GUI controller to update progress bars.
3. **GUI Framework:** Evaluated approaches include a SwiftUI native app wrapping the Python engine via `Process` execution, or a pure Python GUI (PyQt6/PySide6) bundled via `py2app`.
