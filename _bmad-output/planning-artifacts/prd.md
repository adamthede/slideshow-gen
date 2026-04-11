---
stepsCompleted:
  - "step-01-init"
  - "step-02-discovery"
  - "step-02b-vision"
  - "step-02c-executive-summary"
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

