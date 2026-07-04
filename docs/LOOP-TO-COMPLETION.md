# Marquee (Slideshow Generator) — Loop to Completion

> **Open a fresh chat thread in this directory and read this file first.** Source of truth for driving Marquee to a shippable release via agentic loops. (Written 2026-06-26.)

## The mission (definition of done)

A **notarized, downloadable `Marquee.app`** a user can drag to `/Applications`, open past Gatekeeper, and render a real slideshow with - per the PRD success criteria (`_bmad-output/planning-artifacts/prd.md`). "Marquee" is the macOS app; `slideshow-gen` is the proven Python engine it wraps (engine is effectively done).

## How to drive it
- Open a thread **in this repo** (`.../slideshow-gen`); agent reads `CLAUDE.md` + the PRD/ADRs in `_bmad-output/`.
- **Loop recipe:** implement one story → `/verify` (run `pytest tests/` *scoped* - bare `pytest` fails on a vendored BMAD self-test) → open PR (request+verify Copilot; Gemini/CodeRabbit auto) → `/review-cycle` to convergence → **stop at the human merge gate.**
- **Optional `/goal`:** e.g. `Epic 5 stories S3–S6 shipped as merge-ready PRs, or 20 turns` - note this **excludes the notarization run itself** (see wall).

## ✅ The wall is CLEARED (2026-06-30)
- **Notarization is proven end-to-end.** Apple secrets are set in GitHub, the .p12 is in 1Password, and a `workflow_dispatch` run of "Release (sign + notarize)" passed every stage on 2026-06-30: import Developer-ID cert → sign sidecar + vendored FFmpeg → signed Tauri bundle → deep-verify → **notarytool → staple → Gatekeeper accepted** → artifact uploaded. Run: https://github.com/adamthede/slideshow-gen/actions/runs/28450150115 (wrap-up doc on main).
- The only remaining human release step: **push a `v*.*.*` tag** — the same workflow runs and attaches the notarized app to a draft GitHub release.
- `--onefile` deep-signing: resolved (passes; no `--onedir` rewrite needed).

## Current state (2026-07-04, corrected)
- ~90–95% through the roadmap. **Engine (E0) done.** Epics 1, 2, 4 shipped. **E5.S1** (build/sign/notarize workflow) shipped and **proven live**.
- **Shipped:** **E5.S2** code-signing hygiene (PR #13, 06-26); **E5.S7** bundled signed FFmpeg (**PR #14, 06-29**); **CI Developer-ID G2 intermediate** (PR #17, 06-30); **E5.S3** hardened runtime + minimal entitlements (PR #16, 07-04).

## Ordered remaining path
1. **E5.S4 - signed/stapled DMG, drag-to-Applications.** ← the only remaining engineering blocker for a public download.
2. **E5.S6 - release docs / changelog.**
3. **E5.S5 - Tauri auto-updater** — *consider deferring past v1.0*: with no updater, updates ship as fresh downloads; don't let it gate the first release.
4. **`v1.0.0` tag push** (Adam, ~5 min) → draft GitHub release with the notarized app.
5. **thedetech product page** — download link + screenshots; Marquee becomes a published Thede Technologies product.
- *Queued small follow-up: delete orphaned `desktop/src-tauri/entitlements.plist` + update stale doc refs (README, architecture-app.md, ADR-0002, release-pipeline.md).*
- *Out of scope: Epic 3 (browse/exclude grid) - PRD marks optional; recommend cut. `kburns/` sibling dir = historical prior art, ignore.*

## Queued small tasks
- **Delete the orphaned `desktop/src-tauri/entitlements.plist`** — E5.S3 (#16) split entitlements into `app-entitlements.plist` + `binary-entitlements.plist`; the old single `entitlements.plist` is now orphaned. Delete it and update the references in `desktop/README.md`, `docs/architecture-app.md`, `docs/adr/0002-sidecar-packaging.md`, and `docs/release-pipeline.md`. Small, do it before S4's DMG work so the DMG doesn't pick up a stale file.

## Pointers
- PRD/ADRs/stories: `_bmad-output/planning-artifacts/` · Release pipeline: `docs/release-pipeline.md` · Plan files: `docs/plans-to-do/` & `docs/plans-done/`
