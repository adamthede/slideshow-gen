---
title: "Product Brief Distillate: Slideshow Gen for macOS"
type: llm-distillate
source: "product-brief-slideshow-gen.md"
created: "2026-04-06T02:05:00Z"
purpose: "Token-efficient context for downstream PRD creation"
---

## Scope Signals — MVP In/Out/Maybe

### Confirmed In (MVP)
- Native macOS app in Swift/SwiftUI — full engine rewrite from Python, not a wrapper
- Folder selection via drag-and-drop and native file picker
- Pre-render summary dashboard: image/video counts, date range, GPS coverage %, duplicates removed, estimated slideshow length, estimated file size, estimated render time
- Virtualized image browse/exclude grid — optional step, not required before rendering
- Settings panel mapping all current CLI parameters (resolution, slide duration, fade timing, zoom rate, FPS, output location)
- Render progress with real-time status updates
- Output preview via AVFoundation (play result in-app)
- Seamless HEIC support (no user action needed)
- Bundled FFmpeg as separate binary within app bundle (Handbrake model)
- Direct download with Apple notarization (not App Store for v1)
- CLI retained alongside GUI — dual interface, one engine

### Confirmed Out (MVP)
- Overlay style customization (font, color, position) — parallel track on the CLI engine, not blocked by app development
- Per-image Ken Burns control
- Audio/music tracks
- Watched folders / scheduled renders
- Preset system (save/load render configurations)
- Batch multi-folder export
- Share extensions
- App Store distribution
- Apple Photos / Lightroom integration (future iteration)
- AI-powered trip detection (long-term vision)

### Open / Needs PRD Decision
- How the browse/exclude grid communicates exclusions — transient per-session or saved to a sidecar file?
- Whether pre-render estimates improve over time (calibration from prior renders) or are static formulas
- ~~Minimum macOS version target~~ — **Resolved: macOS 26 (Tahoe).** User builds for latest OS only. Rationale: access to latest SwiftUI improvements (grid virtualization fixes), Apple Intelligence APIs for future AI features, audio transcription APIs, no legacy compromises. Personal-tool-first means no user base to alienate.
- Whether the CLI and GUI share a common Swift library or the CLI remains Python
- App icon, name finalization ("Slideshow Gen" vs. something more consumer-friendly)

## Requirements Hints

- **Performance is a hard requirement, not aspirational.** The Swift rewrite must match or exceed the Python engine's render performance. User has 4,000+ image collections and will benchmark against the CLI.
- **Memory discipline.** The GUI must not hog memory or cause crashes at scale. Virtualized grid must lazy-load thumbnails and populate metadata asynchronously. Only 50-100 thumbnails in memory at any time regardless of collection size.
- **The default path must be fast.** Folder > summary > render in under 60 seconds. The browse/exclude grid is optional — never forced.
- **Pre-render estimates are important.** User wants a gut check ("do I really want a 6-hour render of a 4-hour slideshow?") before committing. Three estimates: slideshow duration (high accuracy — deterministic math), file size (within ~15-20% via CRF average), render time (calibrate by timing first few clips and extrapolating).
- **No regression in output quality.** Rendered output must be identical to current CLI engine. Same FFmpeg filter graphs, same CRF settings, same encoding flags.
- **HEIC handling must be invisible.** User has HEIC files from iPhone. Conversion to JPG before FFmpeg must happen silently with no user action.

## Technical Context

### Architecture Decision: Swift Rewrite
- The Python engine is ~1,500 lines across 11 modules. Core IP is in FFmpeg filter graph construction (Ken Burns zoompan expressions, overlay drawtext filters, crossfade compositing) and the three-phase pipeline design.
- These are algorithm-portable — they generate FFmpeg command lines and filter scripts, not Python-specific logic.
- Swift calls FFmpeg via `Process` (same subprocess pattern as Python). Filter graphs written to temp script files via `-filter_complex_script`.
- Key modules to port: `kenburns.py` (296 lines, high complexity — 4x supersampling logic), `ffmpeg.py` (365 lines, high complexity — parallel execution, filter scripts), `pipeline.py` (256 lines — three-phase orchestrator), `metadata.py` (218 lines — EXIF reading, filename parsing, reverse geocoding), `overlay.py` (93 lines), `discovery.py` (129 lines), `config.py` (60 lines).
- Python dependencies to replace in Swift: Pillow/pillow-heif (use CoreImage/ImageIO), exifread (use CGImageSource/ImageIO), reverse_geocoder (need Swift equivalent or bundle the dataset), Click (SwiftUI replaces this).

### FFmpeg Distribution
- Bundle FFmpeg as a separate executable within the app bundle — the Handbrake approach.
- Sidesteps GPL licensing concerns (separate binary, not linked).
- Eliminates "install FFmpeg first" friction for end users.
- Ensures version consistency (no surprises from user's system FFmpeg).
- FFmpeg 7.1+ required for current filter graph compatibility.

### macOS Platform Constraints
- App Sandbox restricts subprocess execution and filesystem access. Direct download with notarization avoids these constraints for v1.
- Security-scoped bookmarks needed for persistent folder access across sessions.
- App Store distribution deferred — sandboxing constraints around FFmpeg subprocess spawning need investigation.
- Notarization requires proper code signing of both the app and the bundled FFmpeg binary.

### Current Engine Characteristics
- Three-phase pipeline: (1) each image to individual temp clip in parallel, (2) batch consecutive clips with crossfades in groups of 50, (3) final composite of all batches + video clips.
- Intermediate files use `-crf 0 -preset ultrafast` (lossless, fast). Final output uses `-crf 18 -preset medium -movflags +faststart`.
- Ken Burns filter uses 4x supersampling to avoid FFmpeg zoompan jitter bug.
- Parallel rendering via worker pool (default 8 workers, CPU-bound FFmpeg subprocesses).
- Date fallback chain: filename convention > EXIF DateTimeOriginal > file mtime.
- Offline reverse geocoding via bundled dataset (no network needed).
- Duplicate detection via partial content hash.
- Panoramas and small images render static (no Ken Burns — smart detection).
- No persistent state — each run is self-contained. No database.
- No audio support currently (all outputs are `-an`).

## Detailed User Scenarios

- **Primary weekly workflow:** User has a folder of 4,000+ family photos spanning years. Opens app, drags folder in, reviews the summary dashboard ("4,127 images, 23 videos, date range 2019-2024, 312 have GPS, 45 dupes removed, ~4h slideshow, ~12GB, ~6h render"). Optionally browses grid to exclude a few bad shots. Adjusts resolution to 4K. Hits render. Walks away. Comes back, previews in-app, copies to USB for TV playback.
- **Quick event slideshow:** User just got back from a trip with 200 photos in a folder. Drags folder, glances at summary, hits render. Done in 20 minutes. Plays on TV for family that evening.
- **Iterative refinement:** User renders a slideshow, notices some images have wrong dates (filename parsing missed). Excludes those images in the grid, re-renders. Summary estimates help decide if the shorter slideshow is still worth it.

## Competitive Intelligence

### Direct Competitors (None Match Full Feature Set)
- **Apple Photos:** Free, basic Ken Burns, no EXIF overlays, no batch workflow, no 4K export, requires library import. Gap: everything we do.
- **FotoMagico ($99):** Professional timeline editor, full Ken Burns keyframes, but manual per-slide setup. No auto EXIF, no batch workflow. Overkill and too expensive for the use case. Gap: automation and EXIF.
- **iMovie (Free):** Ken Burns with manual crop control per image. Full video editor. Tedious at scale, no EXIF, no batch. Gap: automation at scale.
- **Movavi ($50):** Cross-platform, not native Mac feel. Basic pan/zoom. No EXIF, no automation. Gap: native experience, EXIF, automation.
- **Final Cut Pro ($300):** Professional video editor. Massive overkill. No EXIF, no batch. Gap: purpose-built simplicity.

### Key Differentiator Matrix
| Capability | Photos | FotoMagico | iMovie | Slideshow Gen |
|---|---|---|---|---|
| Auto EXIF overlays | No | Manual | No | Yes |
| GPS reverse geocoding | No | No | No | Yes (offline) |
| Folder-in, video-out | No | No | No | Yes |
| 4K output | No | Yes | Yes | Yes |
| Digital frame optimized | No | No | No | Yes |
| Works at 4,000+ images | N/A | Slow | Tedious | Yes |
| Privacy (100% offline) | No (cloud) | Yes | Yes | Yes |

### Positioning
- "The automatic slideshow generator for photographers who want their photos to tell their own story"
- Sits between free/featureless (Photos) and expensive/manual (FotoMagico) at a potential $29-49 price point
- Category-defining: no one owns "automated slideshow generation" the way Handbrake owns video transcoding
- Privacy-first angle resonates with photographer audience skeptical of cloud lock-in

## Rejected Ideas (With Rationale)

- **Python TUI (e.g., Textual) as intermediate step** — Rejected. The goal is a polished native macOS experience, not incremental CLI improvement. A TUI still requires venv management and doesn't solve the core friction.
- **Wrapping the Python engine from Swift** — Rejected. Embedding Python or shelling out to a venv creates the exact dependency friction we're eliminating. Clean Swift rewrite preferred. Performance parity is a hard requirement.
- **Apple Photos integration in MVP** — Deferred to future iteration. Most users who would use this tool have folder-based workflows. PhotoKit integration adds scope without solving the primary user's problem.
- **Full curation mode (reorder, group into chapters, per-image Ken Burns)** — Deferred. MVP sweet spot is scan summary + optional browse/exclude. Full curation approaches timeline-editor territory and overbuilds the MVP.
- **Scan summary only (no grid)** — Rejected as too minimal. The ability to browse and exclude specific images adds meaningful value without heavy implementation cost. The grid is optional, not forced.
- **App Store for v1** — Deferred. Sandboxing constraints around FFmpeg subprocess execution and filesystem access need investigation. Direct download with notarization is the pragmatic first step.

## Opportunity Reviewer Insights (For Future Consideration)

- **AI-powered narrative generation from EXIF clusters** — Auto-detect trips via timestamp/GPS clustering, generate chapter titles. Added to long-term vision. Could be a defining feature.
- **Apple Photos / Lightroom integration** — PhotoKit for library access without folder export. Added to medium-term vision.
- **Embeddable render engine** — The three-phase FFmpeg pipeline could be packaged as a headless render service for funeral homes, wedding platforms, real estate. Second business model hiding inside a consumer app.
- **Digital picture frame manufacturer partnerships** — Aura, Nixplay, Meural sell hardware with weak content software. Bundled slideshow creator solves their content pipeline problem.
- **Preset sharing community** — Users export/share render configs and overlay styles. Lightweight community loop and re-engagement mechanism.
- **Output as acquisition** — Optional credit frame ("Made with Slideshow Gen") turns every TV screening into word-of-mouth.

## Skeptic Reviewer Flags (For PRD to Address)

- **Competitive claims need validation.** "No other app does this" for EXIF overlays should be verified with a structured audit before going to market. True as of research date but could change.
- **FFmpeg GPL licensing.** Bundling as separate binary (Handbrake model) is the standard approach but should be reviewed by someone with licensing expertise before commercial distribution.
- **Render time expectations.** Multi-hour renders for large collections may feel "broken" to users accustomed to instant consumer apps. Progress UI and time estimates are critical for managing expectations.
- **Dual interface maintenance.** CLI + GUI doubles surface area for bugs and feature parity drift. PRD should clarify whether CLI remains Python (maintained separately) or is also rewritten in Swift (shared codebase).
