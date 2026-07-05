# Changelog

All notable changes to **Marquee** (and the underlying `slideshow-gen` engine)
are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions map to GitHub releases (a `v*.*.*` tag triggers a signed, notarized
build — see [docs/RELEASING.md](docs/RELEASING.md)).

## [Unreleased]

_Deliberately deferred past v1.0:_

- **Auto-updater (E5.S5).** No in-app "Check for Updates" yet. Until it lands,
  a new version ships as a fresh download from the GitHub Releases page.

## [1.0.0] - 2026-07

First public release of **Marquee** — the macOS desktop app that turns folders
of photos and videos into MP4 slideshows, wrapping the proven `slideshow-gen`
Python engine as a signed sidecar. Direct download, notarized, 100% offline.

### The app

- **Drag-and-drop or pick folders.** Point Marquee at one or more source
  folders; optional recursive scanning. (FR1)
- **Pre-render summary before you commit.** Image/video counts, duplicates
  removed, date range, GPS coverage, and estimates for slideshow duration and
  output file size — so a long render is a conscious choice. (FR2, FR4)
- **Render settings.** Output resolution (1080p / 4K), slide duration, fade
  duration, FPS, output destination, background audio track + volume, recursive
  scan, batch size. Defaults match the CLI. (FR4)
- **Live render progress + cancel.** Phase indicator (discovery → image clips →
  batching → composite), current item, percentage, and a per-phase ETA the app
  derives from the engine's streamed progress. Cancel cleans up partial temp
  output. (FR5)
- **Per-item failure tolerance.** A single unreadable photo is skipped with a
  logged warning instead of aborting the whole render. (FR5, NFR5)
- **In-app result view.** The finished MP4 previews inside the app; "Reveal in
  Finder" and "Open in QuickTime"; re-render with the same settings. (FR6)

### The slideshows

- **Ken Burns motion.** Smooth pan/zoom on every still, 4x supersampled for
  clean edges.
- **Automatic EXIF overlays.** Date and GPS-derived location ("Paris, France")
  rendered onto each slide with zero configuration. Date fallback chain:
  filename → EXIF `DateTimeOriginal` → file mtime. (FR8)
- **Offline reverse geocoding.** GPS coordinates become readable place names
  from a bundled dataset — no network, no server. (FR8, NFR4)
- **HEIC support.** Apple HEIC/HEIF images are converted transparently before
  encoding — no setting, no user action. (FR7)
- **Mixed photos + video.** Video clips are composited alongside stills; their
  source audio is preserved and background music ducks under it automatically
  (sidechain compression). (FR9)
- **Crossfades** between slides and a consistent
  `h264_videotoolbox -b:v 20M` + `+faststart` encode (Apple Silicon hardware
  encoder). (NFR7)

### Privacy

- **100% offline.** No accounts, no telemetry, no cloud calls — including
  geocoding. Photos and their locations never leave your Mac. (NFR4)

### Distribution & signing

- **Notarized direct download.** Ships as a signed, notarized, stapled
  `Marquee.app` and a drag-to-Applications **DMG**, built by a GitHub Actions
  release pipeline. Opens past Gatekeeper without an unidentified-developer
  warning. (E5.S1, E5.S4)
- **Hardened runtime, least-privilege entitlements.** Every nested binary
  (Tauri shell, PyInstaller sidecar, bundled FFmpeg) is signed with the
  hardened runtime; only the sidecar/FFmpeg carry
  `disable-library-validation`, and the Tauri shell carries none. (E5.S2, E5.S3)
- **Bundled FFmpeg.** A signed static `ffmpeg` + `ffprobe` ship inside the app,
  so a clean Mac with nothing on `PATH` can still render. GPLv3 compliance text
  and a written offer for source ship in the bundle. (E5.S7)

### Engine (`slideshow-gen` CLI)

The CLI remains the canonical engine surface; the app drives it as a sidecar
over a versioned JSON-line IPC contract. Engine work that shipped for v1:

- Pre-render summary + `--estimate-only` (E0.S1)
- Library-callable `RenderPipeline` driven by an injected `Reporter` (E0.S5)
- `--ipc` versioned event stream, schema-locked by tests (E0.S6)

[Unreleased]: https://github.com/adamthede/slideshow-gen/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/adamthede/slideshow-gen/releases/tag/v1.0.0
