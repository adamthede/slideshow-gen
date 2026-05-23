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

The engine is proven: a Python CLI validated on collections of 4,000+ images across years of use. **Marquee** is the macOS desktop application that wraps this engine — replacing virtual environment management, file path memorization, and command-line flags with drag-and-drop folder selection and a single Render button. The workflow is: select folders, review a pre-render summary, hit render, and walk away.

**App identity:** Marquee · Bundle ID `com.thedetech.marquee` · Team `U85N54PC5J` (Thede Technologies, LLC) · signed with the existing `Developer ID Application` certificate, notarized via the `AC_PASSWORD` notarytool keychain profile.

### What Makes This Special

- **Automatic EXIF metadata overlays.** Dates, GPS-derived locations ("Paris, France", "Yosemite, California"), and camera details are extracted and rendered onto each slide with zero configuration. No other consumer tool does this.
- **Video as the universal playback format.** The core insight: thousands of loose images are unplayable at scale on every device. A single MP4 is a solved problem everywhere. This isn't just a slideshow maker — it's a format converter from "unplayable archive" to "playable video."
- **Offline GPS reverse geocoding.** Raw GPS coordinates become readable place names without contacting any server. Photos and their locations never leave the user's Mac.
- **Scale without compromise.** Engineered for 4,000+ image collections with parallel FFmpeg rendering, virtualized UI, and progressive processing. Works with 50 photos or 10,000.
- **100% offline, privacy-first.** No cloud, no accounts, no telemetry. The entire pipeline runs locally — a meaningful differentiator in a market where Apple Photos and Google Photos require cloud sync for auto-generation.

## Project Classification

- **Project Type:** macOS desktop application (Tauri shell + React/Tailwind/shadcn UI) wrapping the existing Python rendering engine as a frozen sidecar binary. See [ADR-0001](../../docs/adr/0001-app-stack.md).
- **Domain:** Consumer creative tools / media
- **Complexity:** Medium — the Python engine is reused as-is. Complexity now lives in (a) the sidecar IPC contract between the Rust/Tauri shell and the frozen Python CLI, (b) PyInstaller packaging + signing of the sidecar, and (c) Tauri's macOS notarization + auto-update pipeline.
- **Project Context:** Brownfield — proven CLI engine (~1,700 LOC, 11 modules) kept intact and wrapped, not rewritten. The CLI remains a first-class surface alongside the app.

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
The Python CLI remains the canonical engine surface. The app and the CLI share the same code: the app ships the frozen CLI as a sidecar binary and drives it via IPC. CLI improvements (estimates, ducking, future overlay features) automatically benefit the app. See [ADR-0001](../../docs/adr/0001-app-stack.md).

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

Epics are ordered. Each ships independently. Engine-side epics (E0) ship to the CLI immediately. The Tauri app stack is established once in Epic 1 (skeleton + sidecar contract + signing), then UI features stack on top in Epics 2–4. Distribution is hardened in Epic 5. See [ADR-0001](../../docs/adr/0001-app-stack.md) for the stack decision.

### Epic 0 — Engine hardening (CLI, prerequisite)

Goal: lock down the CLI engine so the sidecar that the app embeds has a stable, well-instrumented surface. Everything in this epic ships in the CLI first.

Stories:
- E0.S1 — Pre-render summary in CLI: duration estimate, size estimate (bitrate × duration), GPS coverage %, dupes removed. Add `--estimate-only` to exit before phase 1. *(Shipped: commit `7ac4c0a`.)*
- E0.S2 — Audible-ducking acceptance test: synthetic test that probes peak volume during a known video-segment window and asserts the bg track is attenuated. Locks in the fix from `bb3dbec`.
- E0.S3 — Render-time calibration: time the first N clips of phase 1, extrapolate, log an ETA. Lays groundwork for the app's render-time estimate.
- E0.S4 — App stack decision: ADR capturing Tauri + React + shadcn + Python sidecar. *(Shipped: `docs/adr/0001-app-stack.md`.)*
- E0.S5 — Engine API extraction: `RenderPipeline` is now driven by an injected `Reporter` instead of bare `click.echo`. Same Python, but the engine is fully library-callable with no terminal coupling. *(Shipped.)*
- E0.S6 — Sidecar IPC contract: `--ipc` flag emits versioned JSON-line events on stdout (`started`, `phase_started`, `discovery_complete`, `estimate`, `progress`, `phase_complete`, `info`, `warning`, `error`, `complete`). Schema documented in [`docs/sidecar-protocol.md`](../../docs/sidecar-protocol.md), locked by `tests/test_ipc_protocol.py`. *(Shipped.)*

### Epic 1 — Tauri shell + sidecar foundation

Goal: stand up the Tauri app skeleton, embed the frozen Python CLI as a signed sidecar, prove the full request/event loop end-to-end with a trivial command ("scan and return summary"). No real UI yet — a "Hello, slideshow" build that exercises every layer that matters for distribution.

Stories:
- E1.S1 — Tauri project skeleton: `desktop/` workspace, Vite + React + TypeScript + Tailwind + shadcn/ui baseline, `src-tauri/` Rust shell, app icon placeholder.
- E1.S2 — Freeze the Python CLI as a sidecar binary via PyInstaller (one-file or one-folder per signing tradeoffs). Include FFmpeg binary alongside.
- E1.S3 — Wire Tauri's sidecar configuration to spawn the frozen CLI; pass arguments; capture stdout/stderr.
- E1.S4 — Implement the IPC event loop in Rust: spawn sidecar, stream JSON-line events, forward to frontend via Tauri events.
- E1.S5 — Frontend hook: a React hook that subscribes to sidecar events and exposes typed progress state.
- E1.S6 — End-to-end smoke: clicking "Scan" in a minimal UI runs the sidecar against a fixture folder and renders the summary returned via IPC. Proves every layer.
- E1.S7 — Bundle + sign + notarize a "Hello, slideshow" build, install on the user's Mac, confirm Gatekeeper accepts. *Notarization proven before any real UI work.*

### Epic 2 — Ingestion and pre-render summary UI

Goal: real folder selection, real scan, real summary card with estimates. The user can point the app at a folder and see what would happen if they hit Render.

Stories:
- E2.S1 — Drop zone + file picker: drag-and-drop with visual affordance, native file picker, security-scoped bookmarks for persistence, recent folders.
- E2.S2 — Scan orchestration: dispatch `scan` to the sidecar, stream progress (file count, current path).
- E2.S3 — Summary card: image/video count, date range, GPS coverage, dupes removed — designed with shadcn/Card primitives.
- E2.S4 — Estimates panel: duration, output size, render-time. Sources its numbers from the sidecar (`estimate_output`).
- E2.S5 — Settings drawer: resolution, slide duration, fade, FPS, output destination, audio track + volume, recursive, batch size. Form state persists per-folder via security-scoped bookmark + localStorage.
- E2.S6 — Visual polish pass: dark mode, motion/easing on summary card appearance, typography scale, app icon — first deliberate design pass.

### Epic 3 — Browse / exclude grid

Goal: optional, virtualized thumbnail grid for excluding items before rendering. Memory-bounded.

Stories:
- E3.S1 — Thumbnail generation: sidecar command that emits resized JPEG thumbnails for a folder on demand, cached in the app's `appData` directory keyed by content hash.
- E3.S2 — Virtualized grid: `@tanstack/react-virtual` (or similar) so only visible cells decode/hold image bytes; cap at ~100 in-memory.
- E3.S3 — Per-item exclude/include toggle; running excluded-count badge.
- E3.S4 — Exclusion model: transient per-session for v1 (sidecar file deferred). Exclusions are passed to the render command as an explicit exclude list.
- E3.S5 — Estimates panel live-updates duration/size when exclusions change.

### Epic 4 — Render execution and result

Goal: render from the app, show progress, preview the result.

Stories:
- E4.S1 — Render kickoff: dispatch the `render` command to the sidecar with the full settings payload.
- E4.S2 — Progress UI: phase indicator (discovery / clips / batching / composite), per-phase progress bar, ETA, cancel button. Streams from the sidecar's IPC events.
- E4.S3 — Cancellation: terminate the sidecar process, which propagates SIGTERM to in-flight FFmpeg children; sidecar cleans temp directory before exit. `--keep-temp` parity exposed as a setting.
- E4.S4 — Per-item failure handling: warnings stream into an in-app panel; render does not abort on single-item failure (mirrors CLI behavior).
- E4.S5 — Result view: in-app preview via an HTML5 `<video>` element pointed at the output file; Reveal in Finder; Open in QuickTime; "render again with same settings" shortcut.

### Epic 5 — Distribution and updates

Goal: ship the app as a notarized direct download from GitHub releases, with auto-update.

Stories:
- E5.S1 — Build pipeline: GitHub Actions workflow that builds the React frontend, freezes the Python sidecar, assembles the Tauri bundle, signs (Developer ID Application), and notarizes via `notarytool`.
- E5.S2 — Code signing hygiene: sign the Tauri shell, the sidecar binary, the embedded FFmpeg, and any auxiliary dylibs/.so files. Verify with `codesign --verify --deep`.
- E5.S3 — Hardened runtime + minimal entitlements: ensure sidecar process spawn and FFmpeg child spawn both work; document why each entitlement is needed.
- E5.S4 — DMG packaging with drag-to-Applications layout, signed and stapled.
- E5.S5 — Tauri auto-updater: signed update manifest hosted via GitHub releases, version pinning, rollback discipline. "Check for updates" menu item.
- E5.S6 — Release docs: README install section, troubleshooting (Gatekeeper, first-launch), changelog discipline tied to GitHub releases.

## Open Questions

- Exclusion persistence: transient (v1 default) vs. sidecar JSON next to the folder (later)?
- ~~CLI fate~~ — **Resolved by [ADR-0001](../../docs/adr/0001-app-stack.md):** Python CLI is the engine surface, frozen as a sidecar and embedded in a Tauri shell. No engine rewrite.
- ~~App name and bundle ID before E5~~ — **Resolved:** Marquee, `com.thedetech.marquee`.
- Render-time estimate calibration strategy: per-machine cache vs. per-run warm-up. Default to per-run warm-up; cache later if it earns its complexity.
- Sidecar packaging tradeoffs: PyInstaller one-file (simpler signing, slower cold start) vs. one-folder (faster start, every nested dylib needs signing). Decide in E1.S2.

## Success Criteria

- A 4,000-image archive renders end-to-end from the app on the user's primary Mac with no crashes, with output indistinguishable from the CLI's output, in render time ≤ CLI baseline.
- The user, on their primary Mac, can go folder → summary → Render in under 60 seconds for a previously-scanned folder.
- Pre-render estimates land within ±20% of actuals on a representative test corpus.
- No network traffic generated during a full render (verified with a packet capture).
- App passes Apple notarization on first submission of the v1 build.

