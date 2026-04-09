# Source Tree Analysis

## Project Structure

```
slideshow-gen/
├── pyproject.toml            # Package config, dependencies, entry point
├── CLAUDE.md                 # AI assistant project context
├── src/
│   └── slideshow_gen/        # Main package
│       ├── __init__.py       # Version string ("0.1.0")
│       ├── cli.py            # Click entry point — `render` command with all CLI options
│       ├── config.py         # RenderConfig dataclass — single source of truth for parameters
│       ├── discovery.py      # MediaItem dataclass, directory scanning, sorting, dedup
│       ├── metadata.py       # EXIF reading, filename parsing, reverse geocoding
│       ├── media.py          # Image/video dimension + duration helpers (Pillow, ffprobe)
│       ├── heic.py           # HEIC-to-JPG conversion via pillow-heif
│       ├── kenburns.py       # Ken Burns zoompan filter expression generator
│       ├── overlay.py        # Drawtext overlay filter strings with fade alpha
│       ├── ffmpeg.py         # FFmpeg subprocess runner, filter scripts, parallel execution
│       ├── pipeline.py       # Three-phase render orchestrator (RenderPipeline class)
│       └── manifest.py       # Dry-run manifest output (print_manifest)
├── tests/                    # Test directory (empty — no tests yet)
├── docs/                     # Generated project documentation (this folder)
├── design-artifacts/         # BMad design artifacts (empty)
├── _bmad/                    # BMad module configuration
└── _bmad-output/             # BMad workflow outputs
```

## Module Dependency Graph

```
cli.py
├── config.py          (RenderConfig, RESOLUTIONS)
└── [lazy imports]
    ├── discovery.py   (scan_directories, sort_items)
    │   ├── config.py  (IMAGE_EXTENSIONS, VIDEO_EXTENSIONS)
    │   ├── metadata.py (read_exif, reverse_geocode, get_date_for_item)
    │   └── media.py   (get_image_info, get_video_info)
    ├── manifest.py    (print_manifest)
    └── pipeline.py    (RenderPipeline)
        ├── config.py
        ├── discovery.py
        ├── ffmpeg.py
        │   ├── config.py
        │   ├── discovery.py (MediaItem)
        │   ├── heic.py     (is_heic, convert_heic_to_jpg)
        │   ├── kenburns.py (choose_effect, generate_filter_chain)
        │   └── overlay.py  (generate_overlay_filters)
        └── overlay.py
```

## Critical Files

| File | Lines | Role | Complexity |
|---|---|---|---|
| `pipeline.py` | 256 | Orchestrator — ties all phases together | High — manages temp files, batching, cleanup |
| `ffmpeg.py` | 365 | All FFmpeg subprocess execution | High — parallel workers, filter scripts, error handling |
| `kenburns.py` | 296 | Zoompan math and filter expressions | High — complex FFmpeg filter algebra |
| `metadata.py` | 218 | EXIF + filename parsing + geocoding | Medium — regex patterns, GPS conversion |
| `overlay.py` | 93 | Drawtext filter generation | Low — straightforward filter strings |
| `discovery.py` | 129 | File scanning and sorting | Low — directory iteration, hash dedup |
| `config.py` | 60 | Configuration dataclass | Low — pure data |
| `media.py` | 65 | Image/video info extraction | Low — Pillow + ffprobe wrappers |
| `heic.py` | 44 | HEIC conversion | Low — single conversion function |
| `manifest.py` | 79 | Dry-run output | Low — formatted text output |
| `cli.py` | 104 | CLI definition | Low — Click decorators + dispatch |

## External Dependencies (System)

- **FFmpeg 7.1+** — must be installed and on PATH (`brew install ffmpeg`)
- **ffprobe** — bundled with FFmpeg, used for video metadata
- **macOS system fonts** — overlay.py hardcodes `/System/Library/Fonts/Helvetica.ttc`
