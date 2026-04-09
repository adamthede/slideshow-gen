# Slideshow Generator — Documentation Index

## Project Overview

- **Type:** CLI Tool (monolith)
- **Primary Language:** Python 3.11+
- **Architecture:** Three-phase FFmpeg render pipeline
- **Tech Stack:** Click + Pillow + ExifRead + reverse_geocoder + FFmpeg (subprocess)
- **Entry Point:** `slideshow_gen.cli:cli` (`slideshow-gen render`)
- **Version:** 0.1.0
- **Future Direction:** Native macOS application

## Quick Reference

| Parameter | Value |
|---|---|
| Package name | `slideshow-gen` |
| Source root | `src/slideshow_gen/` |
| Modules | 11 Python files (~1,700 LOC) |
| Dependencies | 5 Python packages + FFmpeg system dep |
| Resolutions | 1080p (1920x1080), 4K (3840x2160) |
| Image formats | JPG, JPEG, HEIC, HEIF, PNG, TIFF, DNG, BMP, GIF |
| Video formats | MP4, MOV, AVI, MKV, M4V, MTS, M2TS |
| Test coverage | None (tests/ dir is empty) |
| CI/CD | None |

## Generated Documentation

- [Project Overview](./project-overview.md) — Purpose, tech stack, capabilities, future direction
- [Architecture](./architecture.md) — Pipeline design, module responsibilities, technical details
- [Source Tree Analysis](./source-tree-analysis.md) — Annotated directory structure, dependency graph, critical files
- [Development Guide](./development-guide.md) — Setup, usage, filename conventions, common tasks

## Existing Documentation

- [CLAUDE.md](../CLAUDE.md) — AI assistant project context and conventions

## Getting Started

```bash
source .venv/bin/activate
pip install -e .
slideshow-gen render --dir /path/to/photos --dry-run   # preview
slideshow-gen render --dir /path/to/photos              # render
```
