---
title: "Product Brief: Slideshow Gen for macOS"
status: "draft"
created: "2026-04-06T01:49:59Z"
updated: "2026-04-06T01:58:00Z"
inputs:
  - docs/project-overview.md
  - docs/architecture.md
  - docs/development-guide.md
  - docs/source-tree-analysis.md
  - _bmad-output/brainstorming/brainstorming-session-2026-04-03-01.md
---

# Product Brief: Slideshow Gen for macOS

## Executive Summary

Slideshow Gen is a proven Ken Burns slideshow engine that transforms directories of photos and videos into polished MP4 slideshows with automatic EXIF metadata overlays — dates, locations from GPS coordinates, and camera details rendered directly onto each slide. Today it exists as a Python CLI tool. It works. The engine is validated across collections of 4,000+ images.

But using it means activating a virtual environment, remembering file paths, and juggling command-line flags every single time. That friction turns a powerful creative tool into a chore. Slideshow Gen for macOS wraps this proven engine in a native desktop application — bringing the full power of automated slideshow generation to a clean, intuitive interface designed for regular use.

No other application on the market combines automatic EXIF metadata overlays, GPS-to-location geocoding, and zero-configuration batch processing. This is the app for photographers and families who want their photos to tell their own story — with dates, places, and context overlaid automatically — without touching a timeline editor or configuring a single slide.

## The Problem

Creating a Ken Burns slideshow from a large photo collection is either **manual and tedious** or **automatic and featureless**. There is no middle ground.

**Manual tools** (FotoMagico at $99, iMovie, Final Cut Pro) give you full creative control — but demand per-slide configuration. Dragging 4,000 photos onto a timeline and setting Ken Burns parameters for each one is not a workflow, it's a punishment. None of them read EXIF data to overlay dates or locations automatically. None of them support a "point at a folder and go" workflow.

**Automatic tools** (Apple Photos slideshows, cheap App Store apps) require zero effort — but offer zero control, no metadata overlays, limited resolution, and no optimization for digital picture frame playback.

**The current CLI** solves the creative problem beautifully: full Ken Burns control, automatic EXIF overlays with GPS reverse geocoding, 4K output, crossfade transitions, and batch processing of thousands of images. But it creates an operational problem: virtual environment management, manual file paths, memorizing flags, and no visual feedback until the render completes hours later.

## The Solution

A native macOS application that makes the full power of the slideshow-gen engine accessible through a thoughtfully designed interface.

**The core workflow is three steps:**

1. **Select folders** — drag and drop or use a native file picker
2. **Review the pre-render summary** — image/video counts, date range, GPS coverage, duplicates removed, estimated slideshow length, estimated file size, and estimated render time
3. **Hit Render** — monitor real-time progress, then preview the result in-app

**Optional curation:** A virtualized image grid lets you browse the collection and exclude specific images before rendering. Designed for scale — lazy-loaded thumbnails and async metadata population ensure smooth performance at 4,000+ images without memory pressure.

**Settings panel** surfaces all current engine capabilities through intuitive controls: resolution (1080p/4K), slide duration, fade timing, zoom rate, FPS, and output location.

The app is a meaningful GUI for a mature engine — not a rebuild. The render pipeline stays intact. The interface removes every point of friction between "I have photos" and "I have a slideshow."

## What Makes This Different

1. **Automatic EXIF metadata overlays** — No other app does this. Dates, GPS-derived locations ("Paris, France", "Yosemite, California"), and camera details are extracted and overlaid on each slide without any manual text placement. Zero configuration.

2. **Offline GPS reverse geocoding** — Turns raw GPS coordinates into readable place names without ever contacting a server. No network required, no privacy compromise. Your photos and their locations never leave your Mac.

3. **Zero-config batch processing** — Folder in, video out. No timeline, no per-slide setup, no library import. Works with 50 images or 5,000.

4. **Performance at scale** — Engineered for collections of 4,000+ images. Virtualized UI, progressive loading, parallel FFmpeg rendering across CPU cores.

5. **Digital picture frame optimized** — Output tuned for looping playback on TVs, monitors, and USB-equipped frames: proper encoding flags, streaming-ready MP4, appropriate quality settings.

6. **100% offline, privacy-first** — No cloud uploads, no accounts, no telemetry. The entire pipeline runs locally. In a market where Google Photos and Apple Photos require cloud sync for auto-generation, this is a meaningful differentiator.

7. **Dual interface potential** — Native GUI for daily use, CLI retained for automation and scripting. Power users can script nightly regeneration or integrate with photo import workflows. One engine, two access patterns.

## Who This Serves

**Primary user:** The creator — a photographer or photo enthusiast who regularly builds slideshows for display on TVs and digital picture frames. They have large collections (thousands of images) organized in folders, value having dates and locations displayed on their slides, and want a polished tool they reach for weekly, not a CLI they wrestle with. This is a personal tool built to product-grade quality.

**Secondary users:** Families creating memorial slideshows, event recaps, or travel compilations. Anyone who has a folder of photos and wants a polished video without learning video editing. The product-quality design means it's ready to share beyond the primary user from day one.

## Success Criteria

- **Core metric:** Time from "I want a slideshow" to render started is under 60 seconds
- **Performance:** Smooth UI interaction at 4,000+ images with no memory spikes or crashes
- **Adoption signal:** Replaces CLI usage entirely for the primary user's regular workflow
- **Quality parity:** Output identical to current CLI engine — no regression in render quality
- **Stability:** Zero data loss, graceful handling of interrupted renders

## Scope

**MVP (v1.0) — In:**
- Native macOS app (Swift/SwiftUI)
- Folder selection via drag-and-drop and file picker
- Pre-render summary dashboard (counts, date range, GPS coverage, estimated length/size/render time)
- Virtualized image browse/exclude grid with metadata display
- Settings panel for all current CLI parameters
- Render progress with real-time status
- Output preview via AVFoundation
- HEIC support (seamless, no user action needed)
- Bundled FFmpeg (distributed as a separate binary within the app bundle)
- Direct download with notarization (not App Store for v1)

**MVP — Out:**
- Overlay style customization (font, color, position) — parallel track
- Per-image Ken Burns control
- Audio/music tracks
- Watched folders / scheduled renders
- Preset system
- Batch multi-folder export
- Share extensions
- App Store distribution (direct download first)

## Technical Approach

The MVP must resolve a key architectural question: how the Swift/SwiftUI app drives the existing Python render engine.

**Approach:** Reimplement the pipeline orchestration and metadata logic in Swift, calling FFmpeg directly via `Process` (the same subprocess pattern the Python CLI uses). The core IP is in the FFmpeg filter graph construction and the three-phase pipeline design — both are algorithm-portable, not Python-dependent. This avoids embedding Python, eliminates the venv dependency entirely, and produces a truly native app. The Swift implementation must achieve performance parity or better with the existing Python engine — this is a hard requirement, not aspirational.

**FFmpeg distribution:** Bundle FFmpeg as a separate executable within the app bundle (the Handbrake model). This sidesteps GPL concerns (separate binary, not linked), eliminates the "install FFmpeg first" friction, and ensures version consistency.

**Platform considerations:** Distribute via direct download with Apple notarization for v1. App Store sandboxing constraints around subprocess execution and filesystem access make it a better fit for a later release once the app model is proven.

## Vision

Slideshow Gen for macOS starts as the missing app for photographers who want their photos to speak for themselves. But the architecture is built to grow.

**Near-term iterations:** Overlay style editor (fonts, colors, positioning), per-image Ken Burns preview with smart defaults, and a preset system for saving render configurations.

**Medium-term:** Audio track support with beat-synced slide timing, watched folders that auto-regenerate slideshows when new photos arrive, batch export for managing multiple slideshow projects, and Apple Photos / Lightroom library integration via PhotoKit — bringing the folder-free experience to users whose photos live in managed libraries rather than directories.

**Long-term:** AI-powered trip detection that uses EXIF timestamp and GPS coordinate clusters to auto-detect trips, group photos into chapters, and generate narrative titles ("Summer in Provence, June 2024"). This moves the product from automated tool to intelligent storyteller — a slideshow that understands the journey, not just the images.

The architecture is built to grow from a personal power tool into a creative platform that bridges the gap between "automatic and featureless" and "manual and tedious" — giving users the control of a timeline editor with the speed of automation, wherever they want to be on that spectrum.
