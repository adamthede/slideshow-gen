---
title: Epic 5.S7 — Bundle a signed FFmpeg into Marquee.app (distribution blocker)
status: "QA Needed"
linked_pr: "https://github.com/adamthede/slideshow-gen/pull/14"
---

# Epic 5.S7: Bundle FFmpeg into Marquee.app

## Goal

Make `Marquee.app` render on a **clean Mac with no FFmpeg on `PATH`**. Today the engine resolves `ffmpeg` from `PATH` (`src/slideshow_gen/ffmpeg.py`), and the FFmpeg bundling that ADR-0002 deferred to E5.S1 **never actually landed**. A user who downloads the notarized app and has never installed FFmpeg will hit "FFmpeg not found" on their first render. This is a latent **distribution blocker** that surfaced during E5.S2 (see `docs/release-pipeline.md` signing-coverage note and PR #13).

## Scope

### In scope (Agent owns end-to-end)
1. **Choose and vendor a license-clean static FFmpeg** for `aarch64-apple-darwin`. Decide and document the license posture (prefer an LGPL/clean build; avoid GPL-encumbered builds unless the licensing is acceptable for a distributed product). Record the source, version, and license in `docs/release-pipeline.md`.
2. **Carry it as a Tauri bundle resource** (alongside the frozen sidecar) so it ships inside `Marquee.app`.
3. **Make the engine prefer the bundled binary when running inside the app.** Update `src/slideshow_gen/ffmpeg.py` so resolution order is: explicit `FFMPEG_BINARY` (or equivalent) env var / bundled path → then `PATH`. The Tauri shell sets the env var (or passes the path) to the sidecar so the app uses the bundled FFmpeg; the **standalone CLI keeps using `PATH`** (do not break CLI behavior).
4. **Sign the bundled FFmpeg** with the Developer ID Application identity as part of the build (the E5.S2 `codesign --verify --deep --strict` gate will now exercise it — it must pass). Add the FFmpeg row to the signing-coverage table.

### Out of scope
- The actual **notarization run** (deliberate, Adam-in-the-loop step; needs Apple secrets).
- Entitlements changes (E5.S3) beyond what a child-process FFmpeg spawn requires — flag if the notary log names one.
- `kburns/` and any CLI-only behavior change.
- Auto-updater (E5.S5), DMG (E5.S4).

## Files expected to change
- `src/slideshow_gen/ffmpeg.py` — bundled-binary-first resolution with `PATH` fallback.
- `desktop/src-tauri/tauri.conf.json` — add FFmpeg as a bundled resource (and externalBin/resource signing as needed).
- `desktop/src-tauri/src/*` — set the env var / pass the bundled FFmpeg path to the sidecar spawn.
- `.github/workflows/release.yml` — fetch/vendor + sign the FFmpeg binary before the bundle + deep-verify.
- `docs/release-pipeline.md` — FFmpeg source/version/license + signing row.
- `tests/` — a unit test asserting the resolution order (bundled path wins when set; PATH used otherwise).

## Success criteria
- On a Mac with **no `ffmpeg` on `PATH`**, opening `Marquee.app` and running a small render succeeds end-to-end.
- `codesign --verify --deep --strict --verbose=2 Marquee.app` still passes with the bundled FFmpeg signed.
- The standalone CLI still resolves FFmpeg from `PATH` (no regression).
- License posture documented and acceptable for a distributed product.

## Constraints
- macOS / Apple Silicon only (NFR6). 
- Additive to the E5.S1 workflow + E5.S2 signing gate — don't break them.
- Mind bundle size (a static FFmpeg is tens of MB); note the delta in the PR.
- Depends conceptually on E5.S2 (signing gate) being merged first so the signed-FFmpeg requirement is enforced.
