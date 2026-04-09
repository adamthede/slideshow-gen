# Development Guide

## Prerequisites

- **Python 3.11+** (3.14 observed in current venv)
- **FFmpeg 7.1+** with libx264 encoder
- **macOS** (font path hardcoded; may work on other platforms without overlays)

## Setup

```bash
# Clone / navigate to project
cd slideshow-gen

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .

# Verify installation
slideshow-gen --version
slideshow-gen render --help
```

## Dependencies

Managed via `pyproject.toml` using Hatchling build system:

```
click>=8.1          # CLI framework
Pillow>=10.0        # Image processing
pillow-heif>=0.18   # HEIC/HEIF support
exifread>=3.0       # EXIF metadata reading
reverse_geocoder>=1.5  # Offline GPS geocoding
```

System dependency:
```bash
brew install ffmpeg  # macOS
```

## Usage

### Basic render
```bash
slideshow-gen render --dir /path/to/photos
```

### Multiple directories
```bash
slideshow-gen render --dir /photos/vacation --dir /photos/birthday
```

### Full options
```bash
slideshow-gen render \
  --dir /photos \
  --output ~/Desktop/slideshow.mp4 \
  --resolution 4k \
  --slide-duration 5.0 \
  --fade-duration 0.8 \
  --fps 30 \
  --zoom-rate 0.15 \
  --workers 12 \
  --batch-size 50 \
  --verbose
```

### Dry run (manifest only)
```bash
slideshow-gen render --dir /photos --dry-run
```

### Disable overlays
```bash
slideshow-gen render --dir /photos --no-overlays
slideshow-gen render --dir /photos --no-date      # location only
slideshow-gen render --dir /photos --no-location   # date only
```

### Random order
```bash
slideshow-gen render --dir /photos --random
```

## Project Structure

```
src/slideshow_gen/
├── cli.py        # Click entry point
├── config.py     # RenderConfig dataclass
├── discovery.py  # File scanning, sorting, dedup
├── metadata.py   # EXIF, filename parsing, geocoding
├── media.py      # Image/video info helpers
├── heic.py       # HEIC-to-JPG conversion
├── kenburns.py   # Ken Burns filter expressions
├── overlay.py    # Drawtext overlay filters
├── ffmpeg.py     # FFmpeg subprocess execution
├── pipeline.py   # Three-phase orchestrator
└── manifest.py   # Dry-run output
```

## Filename Convention

The tool recognizes structured filenames for date extraction:

```
YYYY-MM-DD HH-MM-SS Photographer - Album (Camera).ext
YYYY MM-DD HHMMSS Photographer - Album.ext
YYYY-MM-DD HHMMSS ....ext
YYYY MM-DD ....ext
```

Examples:
- `2019-03-15 14-30-00 Jane - Iceland Trip (iPhone 12).jpg`
- `2023 07-04 153022 John - Birthday.heic`

## Testing

No tests exist yet. The `tests/` directory is present but empty. Testing would benefit from:
- Unit tests for `metadata.py` (filename parsing, EXIF extraction)
- Unit tests for `kenburns.py` (filter expression correctness)
- Unit tests for `overlay.py` (drawtext filter generation)
- Integration tests with sample images and FFmpeg
- Snapshot tests for filter chain output

## Common Development Tasks

### Adding a new resolution preset
Edit `RESOLUTIONS` dict in `config.py`:
```python
RESOLUTIONS = {
    "1080p": (1920, 1080),
    "4k": (3840, 2160),
    "720p": (1280, 720),  # new
}
```

### Adding a new image format
Add extension to `IMAGE_EXTENSIONS` in `config.py`.

### Adding a new filename pattern
Add a compiled regex to `FILENAME_PATTERNS` in `metadata.py`.

### Modifying overlay appearance
Edit `overlay.py` — font sizes, positions, alpha timing, and font path are all in that file.
