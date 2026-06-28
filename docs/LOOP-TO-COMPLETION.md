# Marquee (Slideshow Generator) — Loop to Completion

> **Open a fresh chat thread in this directory and read this file first.** Source of truth for driving Marquee to a shippable release via agentic loops. (Written 2026-06-26.)

## The mission (definition of done)

A **notarized, downloadable `Marquee.app`** a user can drag to `/Applications`, open past Gatekeeper, and render a real slideshow with - per the PRD success criteria (`_bmad-output/planning-artifacts/prd.md`). "Marquee" is the macOS app; `slideshow-gen` is the proven Python engine it wraps (engine is effectively done).

## How to drive it
- Open a thread **in this repo** (`.../slideshow-gen`); agent reads `CLAUDE.md` + the PRD/ADRs in `_bmad-output/`.
- **Loop recipe:** implement one story → `/verify` (run `pytest tests/` *scoped* - bare `pytest` fails on a vendored BMAD self-test) → open PR (request+verify Copilot; Gemini/CodeRabbit auto) → `/review-cycle` to convergence → **stop at the human merge gate.**
- **Optional `/goal`:** e.g. `Epic 5 stories S3–S6 shipped as merge-ready PRs, or 20 turns` - note this **excludes the notarization run itself** (see wall).

## ⚠️ The wall (human-only)
- **Notarization needs Adam's Apple secrets** in GitHub (5 secrets - `APPLE_CERTIFICATE_P12_BASE64`, etc.; see `docs/release-pipeline.md`). The first real `v*.*.*` tag push **is the test** - it has never been run. Treat notarization as a **deliberate Adam-in-the-loop step**, not autonomous.
- The signing gate (E5.S2) is wired but **unproven against a real bundle** - run a `workflow_dispatch` CI run (no release) with the Apple cert once, to exercise it end-to-end.
- `--onefile` deep-signing: **resolved** (passes; no `--onedir` rewrite needed).

## Current state (2026-06-26)
- ~80–85% through the roadmap. **Engine (E0) done.** Epics 1, 2, 4 shipped. **E5.S1** (build/sign/notarize workflow) shipped.
- **At merge gate (ready):** PR #13 - **E5.S2 code-signing hygiene** (signs the sidecar + adds a `codesign --deep --strict` gate). Copilot caught a real secret leak here.
- **Drafted, loop-ready:** **E5.S7 - bundle a signed FFmpeg** (`docs/plans-to-do/2026-06-26-e5-s7-bundle-ffmpeg.md`).

## Ordered remaining path
1. **Merge PR #13** (E5.S2) - unblocks everything that touches the release workflow.
2. **E5.S7 - bundle FFmpeg** *(real distribution blocker: the app resolves ffmpeg from `PATH` and doesn't bundle it, so a clean Mac render fails "FFmpeg not found").* Loop off updated master so it builds on #13's signing gate.
3. **E5.S3** - hardened runtime + minimal entitlements (only add what the notary log names).
4. **E5.S4** - signed/stapled DMG, drag-to-Applications.
5. **E5.S5** - Tauri auto-updater (signed manifest).
6. **E5.S6** - release docs / changelog.
7. **Notarization run** - Adam-in-the-loop; set the Apple secrets, push a tag, fix whatever the notary log names.
- *Out of scope: Epic 3 (browse/exclude grid) - PRD marks optional; recommend cut. `kburns/` sibling dir = historical prior art, ignore.*

## Pointers
- PRD/ADRs/stories: `_bmad-output/planning-artifacts/` · Release pipeline: `docs/release-pipeline.md` · Plan files: `docs/plans-to-do/` & `docs/plans-done/`
