# Slideshow Generator

Ken Burns slideshow generator with EXIF-aware metadata overlays. Takes directories of images and video files and produces MP4 video slideshows for playback on digital picture frames and computers.

## Features

- **Ken Burns effect** — smooth pan/zoom animations on still images
- **EXIF metadata overlays** — automatically displays date and location from photo metadata
- **Reverse geocoding** — converts GPS coordinates to city/location names (offline)
- **HEIC support** — Apple HEIC/HEIF images converted on the fly
- **Video clip support** — intermixes video files alongside photos
- **Crossfades** — smooth transitions between slides
- **Chronological or random** ordering
- **Chunked output** — split long slideshows into multiple files
- **Parallel rendering** — multiple FFmpeg workers for faster builds
- **4K and 1080p** output resolutions

## Requirements

- Python 3.11+
- FFmpeg 7.1+ (must be on your `PATH`)

## Installation

```bash
git clone https://github.com/adamthede/slideshow-gen.git
cd slideshow-gen
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
slideshow-gen render --dir /path/to/photos
```

### Multiple source directories

```bash
slideshow-gen render --dir /path/to/photos --dir /path/to/more-photos
```

### Full options

```
slideshow-gen render [OPTIONS]

Options:
  --dir DIRECTORY           Source directory to scan (can be repeated) [required]
  -o, --output PATH         Output file path
                            Default: ~/Desktop/slideshow-{resolution}.mp4
  --resolution [1080p|4k]   Output resolution
  --slide-duration FLOAT    Seconds per image
  --fade-duration FLOAT     Crossfade duration in seconds
  --fps INTEGER             Output framerate
  --zoom-rate FLOAT         Ken Burns zoom intensity
  --static                  Skip Ken Burns — static images with crossfades (much faster)
  --random                  Random order instead of chronological
  --no-overlays             Disable all text overlays
  --no-date                 Disable date overlay
  --no-location             Disable location overlay
  --workers INTEGER         Parallel FFmpeg processes
  --batch-size INTEGER      Images per batch reduction
  --temp-dir DIRECTORY      Directory for temp files (default: system temp)
  --chunk-duration INTEGER  Split output into chunks of N minutes (e.g. 60)
  --dry-run                 Print manifest without rendering
  --keep-temp               Keep temp directory after render for debugging
  --verbose                 Detailed progress output
  --help                    Show this message and exit
```

### Examples

Render a 4K slideshow from two directories:

```bash
slideshow-gen render --dir ~/Photos/vacation --dir ~/Photos/family --resolution 4k
```

Quick static slideshow (no Ken Burns) with no overlays:

```bash
slideshow-gen render --dir ~/Photos/event --static --no-overlays
```

Dry run to preview what will be included:

```bash
slideshow-gen render --dir ~/Photos --dry-run
```

Split a long slideshow into 60-minute chunks:

```bash
slideshow-gen render --dir ~/Photos --chunk-duration 60
```

## Architecture

Three-phase FFmpeg render pipeline:

1. **Phase 1:** Each image rendered to an individual temp clip (Ken Burns + overlay baked in, 4x supersampled)
2. **Phase 2:** Consecutive clips batched into groups with crossfades
3. **Phase 3:** Batches + video clips composited into final MP4

## License

Private — all rights reserved.
