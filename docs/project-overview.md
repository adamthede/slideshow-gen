# Slideshow Generator — Project Overview

## Purpose

Ken Burns slideshow generator with EXIF-aware metadata overlays. Takes directories of images and video files and produces MP4 video slideshows for playback on digital picture frames and computers.

## Project Classification

| Attribute | Value |
|---|---|
| **Type** | CLI Tool (monolith) |
| **Language** | Python 3.11+ |
| **CLI Framework** | Click 8.1+ |
| **Build System** | Hatchling |
| **Video Engine** | FFmpeg 7.1+ (subprocess) |
| **Version** | 0.1.0 |
| **Tests** | None yet |
| **CI/CD** | None |
| **License** | Not specified |

## Technology Stack

| Category | Technology | Version | Role |
|---|---|---|---|
| Language | Python | >=3.11 | Core runtime |
| CLI | Click | >=8.1 | Command-line interface |
| Image Processing | Pillow | >=10.0 | Image dimension/format detection, EXIF transpose |
| HEIC Support | pillow-heif | >=0.18 | HEIC/HEIF to JPG conversion |
| EXIF Reading | ExifRead | >=3.0 | GPS, date, orientation extraction |
| Geocoding | reverse_geocoder | >=1.5 | Offline GPS-to-city resolution |
| Video Processing | FFmpeg | 7.1+ (system) | All video rendering and compositing |
| Build | Hatchling | (build-system) | Package building |

## Architecture Summary

Three-phase FFmpeg render pipeline:

1. **Phase 1 — Individual Clips:** Each image is rendered to a temp MP4 with Ken Burns zoom/pan effect and text overlays. Parallelized across N workers via `ProcessPoolExecutor`.
2. **Phase 2 — Batch Reduction:** Consecutive image clips are composited in groups (default 50) with crossfade transitions. Progressive cleanup removes individual clips after batching.
3. **Phase 3 — Final Composite:** All batch segments and video clips are assembled into the final MP4 with crossfades between segments.

### Key Design Decisions

- **4x supersampling** in Ken Burns filter to avoid FFmpeg zoompan jitter bug (trac.ffmpeg.org/ticket/4298)
- **Filter scripts** written to temp files (`-filter_complex_script`) instead of inline — prevents shell escaping issues and command-line length limits
- **Intermediate clips** use `-crf 0 -preset ultrafast` (lossless, fast encoding)
- **Final output** uses `-crf 18 -preset medium -movflags +faststart` (quality-optimized, streaming-ready)
- **HEIC pre-conversion** — HEIC files are converted to JPG before FFmpeg processing since FFmpeg lacks native HEIC support
- **Offline geocoding** — no network required; uses `reverse_geocoder` local database
- **Date fallback chain** — filename convention -> EXIF DateTimeOriginal -> file mtime

## Entry Point

```
slideshow-gen = "slideshow_gen.cli:cli"
```

Installed via `pip install -e .`, invoked as `slideshow-gen render --dir <path>`.

## Current Capabilities

- Scan directories for images (JPG, JPEG, HEIC, HEIF, PNG, TIFF, DNG, BMP, GIF) and videos (MP4, MOV, AVI, MKV, M4V, MTS, M2TS)
- Extract EXIF metadata (date, GPS coordinates, orientation)
- Parse dates from structured filenames (multiple conventions)
- Reverse geocode GPS to "City, State/Country"
- Apply Ken Burns zoom/pan effects with smart static detection (panoramas, tiny images)
- Render text overlays (date + location) with fade-in/hold/fade-out alpha
- Parallel rendering with configurable worker count
- Batch compositing with crossfade transitions
- Duplicate detection via partial content hash
- Dry-run manifest mode (`--dry-run`)
- 1080p and 4K output resolution support

## Future Direction

The project is planned to evolve into a **native macOS application**, transitioning from CLI-only to a GUI experience while retaining the FFmpeg render pipeline as the core engine.
