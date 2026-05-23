---
stepsCompleted:
  - "step-01-init"
  - "step-02-discovery"
  - "step-02b-vision"
  - "step-02c-executive-summary"
  - "step-03-classification"
  - "step-04-requirements"
  - "step-05-epics"
classification:
  projectType: "desktop_app"
  domain: "consumer_creative_tools"
  complexity: "medium"
  projectContext: "brownfield"
inputDocuments:
  - "planning-artifacts/product-brief-slideshow-gen.md"
  - "planning-artifacts/product-brief-slideshow-gen-distillate.md"
  - "docs/index.md"
  - "docs/project-overview.md"
  - "docs/architecture.md"
  - "docs/development-guide.md"
  - "docs/source-tree-analysis.md"
documentCounts:
  briefs: 2
  research: 0
  brainstorming: 0
  projectDocs: 5
workflowType: 'prd'
---

# Product Requirements Document - slideshow-gen

**Author:** Adam
**Date:** 2026-04-09

## Executive Summary

People invest enormous time and money capturing photos — phones, cameras, trips, milestones — and then those photos disappear into archives. A folder on a hard drive. An iCloud library. A Flickr account. They are never viewed again. Photos have become a write-only medium.

The devices designed to display photos make the problem worse. Digital picture frames crash when presented with 6,000 images. Computers choke generating thumbnails for large folders. The scale of modern photo libraries has outgrown the infrastructure built to display individual image files.

Slideshow Gen solves this by converting photo archives into video — the one format every screen handles flawlessly. A single MP4 replaces thousands of loose files. A TV loops it all day. A digital picture frame plays it without crashing. The photos that were sitting forgotten in a folder are now on display, automatically enriched with dates and locations extracted from their own EXIF metadata.

The engine is proven: a Python CLI validated on collections of 4,000+ images across years of use. Slideshow Gen for macOS wraps this engine in a native desktop application — replacing virtual environment management, file path memorization, and command-line flags with drag-and-drop folder selection and a single Render button. The workflow is: select folders, review a pre-render summary, hit render, and walk away.

### What Makes This Special

- **Automatic EXIF metadata overlays.** Dates, GPS-derived locations ("Paris, France", "Yosemite, California"), and camera details are extracted and rendered onto each slide with zero configuration. No other consumer tool does this.
- **Video as the universal playback format.** The core insight: thousands of loose images are unplayable at scale on every device. A single MP4 is a solved problem everywhere. This isn't just a slideshow maker — it's a format converter from "unplayable archive" to "playable video."
- **Offline GPS reverse geocoding.** Raw GPS coordinates become readable place names without contacting any server. Photos and their locations never leave the user's Mac.
- **Scale without compromise.** Engineered for 4,000+ image collections with parallel FFmpeg rendering, virtualized UI, and progressive processing. Works with 50 photos or 10,000.
- **100% offline, privacy-first.** No cloud, no accounts, no telemetry. The entire pipeline runs locally — a meaningful differentiator in a market where Apple Photos and Google Photos require cloud sync for auto-generation.

## Project Classification

- **Project Type:** Native macOS desktop application (Swift/SwiftUI)
- **Domain:** Consumer creative tools / media
- **Complexity:** Medium — general domain but technically demanding (Python-to-Swift port of FFmpeg filter graph construction, 4x supersampled Ken Burns math, three-phase render pipeline, macOS platform concerns including notarization and FFmpeg bundling)
- **Project Context:** Brownfield — proven CLI engine (~1,700 LOC, 11 modules) being rewritten as a native macOS application while retaining the same FFmpeg subprocess architecture

## Users

- **Primary:** The author. Personal-tool-first. macOS power user with 4,000+ image archives spanning years, GPS-tagged iPhone photos, mixed HEIC/JPEG/video, and a digital picture frame and TV to feed.
- **Secondary (potential future):** macOS photographers with folder-based archive workflows who want automated, EXIF-aware slideshows without cloud upload and without timeline-editor tedium. Not in scope for v1 distribution decisions but informs API/UX cleanliness.

## Goals

1. Eliminate the CLI's setup friction (venv, `pip install`, path-typing, flag memorization) by replacing it with drag-and-drop folder selection and a single Render button.
2. Match or exceed the Python engine's render performance and output quality. Output must be byte-comparable in feel: same Ken Burns math, same overlay behavior, same encoding profile.
3. Give the user a trustworthy pre-render summary (duration, file size, render time) so a multi-hour render is a conscious choice, never a surprise.
4. Make HEIC and EXIF metadata invisible plumbing — the user never thinks about either.
5. Keep the entire pipeline offline. No accounts, no telemetry, no cloud calls — including reverse geocoding.

## Non-Goals (v1)

- Overlay style customization (font, color, position) in the GUI — handled as a parallel track on the CLI engine.
- Per-image Ken Burns control or timeline-editor curation.
- Watched folders / scheduled renders / preset save-load.
- App Store distribution (direct download + notarization only).
- Apple Photos / Lightroom / PhotoKit integration.
- AI-powered narrative or trip detection.
- Windows or Linux ports.

## Functional Requirements

### FR1 — Folder ingestion
The app accepts one or more source folders via drag-and-drop onto the window or via the native file picker. Recursive scanning is opt-in (matches CLI `--recursive`). Security-scoped bookmarks persist folder access across launches.

### FR2 — Pre-render summary
After scanning, the app presents a summary card before any render starts. Fields:
- Image count, video count, duplicate-removed count
- Date range (earliest → latest)
- GPS coverage percentage
- Estimated slideshow duration (deterministic from slide_duration, fade_duration, video durations)
- Estimated output file size (from bitrate × duration, within ±20%)
- Estimated render time (calibrated from a 10–20 clip warm-up pass, extrapolated)

### FR3 — Optional browse / exclude grid
A virtualized image grid lets the user browse the scan and exclude specific items before rendering. Capped at ~100 thumbnails resident in memory regardless of collection size. The grid is optional — Render is always available from the summary card without entering the grid.

### FR4 — Render settings
A settings surface exposes the CLI's user-relevant parameters: output resolution (1080p / 4K / custom), slide duration, fade duration, FPS, output destination, audio track + volume, recursive scanning, batch size. Sensible defaults match current CLI defaults.

### FR5 — Render execution and progress
Render runs in-process via bundled FFmpeg (subprocess). Progress UI shows phase (discovery / image clips / batching / composite), current item, percentage, ETA. User can cancel; partial temp output is cleaned up.

### FR6 — In-app preview
On render completion, the finished MP4 plays inside the app via AVKit / AVFoundation. "Reveal in Finder" and "Open in QuickTime" available from the result view.

### FR7 — HEIC support
HEIC files are detected and converted to JPG transparently before FFmpeg sees them. No user action required, no setting to toggle.

### FR8 — EXIF overlays
Date and location overlays render on every slide that has them. Date fallback chain: filename convention → EXIF DateTimeOriginal → file mtime. GPS coordinates resolve to "City, Region" via a bundled offline geocoding dataset.

### FR9 — Audio support
Optional background music track + per-render volume. Video segments preserve their source audio. Background music ducks under video-segment audio automatically (sidechain compression). (Engine: shipped in commit `bb3dbec`.)

### FR10 — CLI parity
The Python CLI remains supported and continues to share the rendering algorithm definition. Either: (a) CLI stays Python and is treated as a reference implementation, or (b) CLI is rewritten as a Swift executable sharing the app's render core. Decision in Epic 0.

## Non-Functional Requirements

### NFR1 — Performance
Render time on a 4,000-image collection must be ≤ Python CLI baseline on the same Mac, measured wall-clock. No regression in encode bitrate or visible quality.

### NFR2 — Memory
Peak resident memory while scanning + browsing a 4,000-image collection: < 1 GB. Thumbnail grid keeps ≤ 100 images in memory; rest are lazy-loaded.

### NFR3 — Time-to-Render
From cold-launch to "render started" on a previously-rendered folder: ≤ 60 seconds for the default path (folder → summary → Render).

### NFR4 — Privacy
Zero network calls during normal operation. Reverse geocoding uses bundled data. App is notarized but does not require an Apple ID at runtime. No telemetry.

### NFR5 — Stability at scale
No crashes on collections up to 10,000 images. Single-image render failure must not abort the run — failed items are skipped with a logged warning, same as CLI today.

### NFR6 — macOS integration
Targets macOS 26 (Tahoe). Native menu bar, keyboard shortcuts, dark mode, security-scoped bookmarks, sandbox-compatible (even if shipped outside the sandbox for v1).

### NFR7 — Output fidelity
Output MP4 must remain identical-feeling to the current CLI output: same Ken Burns supersampling, same crossfade timing, same overlay rendering, same `h264_videotoolbox -b:v 20M` + `+faststart` final encode.

## Epics

Epics are ordered. Each ships independently. Engine-side epics (E0, E1, E5) feed both the current CLI and the future macOS app.

### Epic 0 — Engine hardening for parity (CLI, prerequisite)

Goal: lock down the CLI engine so the Swift port has a stable target. Anything fixed here ships in the CLI immediately.

Stories:
- E0.S1 — Pre-render summary in CLI: print duration estimate, size estimate (bitrate × duration), GPS coverage %, dupes removed. Add `--estimate-only` to exit before phase 1.
- E0.S2 — Audible-ducking acceptance test: synthetic test that probes peak volume during a known video-segment window and asserts the bg track is attenuated. Locks in the fix from `bb3dbec`.
- E0.S3 — Render-time calibration: time the first N clips of phase 1, extrapolate, log an ETA. Lays groundwork for the app's render-time estimate.
- E0.S4 — CLI vs. Swift decision: short ADR in `docs/` choosing whether the CLI remains Python (reference) or is rewritten in Swift atop the app's render core. Block on this before Epic 4.
- E0.S5 — Engine API extraction: refactor `pipeline.py` so the orchestration is callable as a library (not just from `cli.py`). Same Python today; clarifies the surface that the Swift port has to match.

### Epic 1 — Swift render core (macOS, foundational)

Goal: port the algorithm-defining pieces of the engine into Swift as a library, no UI. Validate parity against CLI on a fixture corpus.

Stories:
- E1.S1 — Project skeleton: SwiftPM workspace, app target + render-core library target, FFmpeg bundled as a separate executable in `Resources/`, code signing config.
- E1.S2 — Port `discovery.swift`: directory scan, supported-format filter, duplicate detection by partial content hash, sort by date.
- E1.S3 — Port `metadata.swift`: filename date parser, EXIF read via ImageIO/CGImageSource, GPS extraction, bundled reverse-geocoder lookup.
- E1.S4 — Port `kenburns.swift`: 4x supersampling math, effect chooser, zoompan filter expression generation. Unit tests cross-check Python output for the same inputs.
- E1.S5 — Port `overlay.swift`: drawtext filter string generation, font resolution.
- E1.S6 — Port `ffmpeg.swift`: subprocess runner, filter-script writer, parallel worker pool. Reuses the bundled FFmpeg binary.
- E1.S7 — Port `pipeline.swift`: three-phase orchestrator with progress callbacks.
- E1.S8 — HEIC handling: CoreImage / ImageIO-based HEIC → JPEG conversion to replace pillow-heif.
- E1.S9 — Parity harness: render a fixture set with both Python CLI and Swift core, compare output (duration, dimensions, peak SSIM/PSNR against the Python output, audio waveform RMS).

### Epic 2 — App shell and folder ingestion (macOS)

Goal: SwiftUI app that lets the user point at a folder and see the scan results. No render yet.

Stories:
- E2.S1 — App skeleton: SwiftUI scene, app icon, menu bar, About window.
- E2.S2 — Folder drop zone: drag-and-drop + file picker, security-scoped bookmarks, recent folders.
- E2.S3 — Scan orchestration: trigger discovery + metadata on a background queue, with progress.
- E2.S4 — Summary card: image/video count, date range, GPS coverage, duplicates removed.
- E2.S5 — Estimates: duration, size, render-time (consumes E0.S1 / E0.S3 formulas).
- E2.S6 — Settings panel: resolution, slide duration, fade, FPS, output destination, audio track, audio volume, recursive, batch size.

### Epic 3 — Browse / exclude grid (macOS)

Goal: virtualized thumbnail grid that the user can optionally enter to exclude items before rendering. Memory-bounded.

Stories:
- E3.S1 — Lazy thumbnail loader: ImageIO downsampling, on-demand decode, LRU cache capped at 100 items.
- E3.S2 — Virtualized grid: `LazyVGrid` / `NSCollectionView` with cell recycling; only visible thumbnails are decoded.
- E3.S3 — Exclude/include toggle per item; running excluded-count badge.
- E3.S4 — Exclusion model: transient per-session for v1 (sidecar file deferred to a later iteration).
- E3.S5 — Summary card live-updates duration/size estimates when exclusions change.

### Epic 4 — Render execution and result (macOS)

Goal: actually render from the app, show progress, preview the result.

Stories:
- E4.S1 — Render kickoff: hand the scan result + settings to the Swift render core; track lifecycle on a background actor.
- E4.S2 — Progress UI: phase indicator (discovery / clips / batching / composite), per-phase progress bar, ETA, cancel button.
- E4.S3 — Cancellation: terminate FFmpeg subprocesses, clean temp directory, preserve `--keep-temp` parity.
- E4.S4 — Per-item failure handling: continue on single-item failure, log to an in-app warnings panel; mirrors CLI behavior.
- E4.S5 — Result view: AVKit player, Reveal in Finder, Open in QuickTime, render-again-with-same-settings shortcut.

### Epic 5 — Distribution (macOS)

Goal: ship the app as a notarized direct download.

Stories:
- E5.S1 — FFmpeg bundling: separate executable in `Resources/`, version pinned (FFmpeg 7.1+), signed with the app's identity.
- E5.S2 — Hardened runtime + entitlements minimal set; verify subprocess spawn works under hardened runtime.
- E5.S3 — Code signing pipeline (Developer ID Application).
- E5.S4 — Notarization automation (`notarytool` in a build script).
- E5.S5 — DMG/zip packaging + download landing page.
- E5.S6 — Auto-update mechanism (Sparkle or hand-rolled) — optional for v1, decide late.

## Open Questions

- Exclusion persistence: transient (v1 default) vs. sidecar JSON next to the folder (later)?
- CLI fate: Python reference (less work, two codebases) vs. Swift rewrite sharing the app's render core (more work, single codebase). Capture as ADR in E0.S4.
- App name and bundle ID before E5.
- Render-time estimate calibration strategy: per-machine cache vs. per-run warm-up. Default to per-run warm-up; cache later if it earns its complexity.

## Success Criteria

- A 4,000-image archive renders end-to-end from the app on the user's primary Mac with no crashes, with output indistinguishable from the CLI's output, in render time ≤ CLI baseline.
- The user, on their primary Mac, can go folder → summary → Render in under 60 seconds for a previously-scanned folder.
- Pre-render estimates land within ±20% of actuals on a representative test corpus.
- No network traffic generated during a full render (verified with a packet capture).
- App passes Apple notarization on first submission of the v1 build.

