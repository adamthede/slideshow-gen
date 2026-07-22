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

## Roadmap (lane view)

The lanes below follow the Command Center roadmap convention (`Now / Next / Later / Shipped`) so the portfolio dashboard renders real lanes for this project. They restate the "current state" and "ordered remaining path" this doc has always tracked; the mission, drive-recipe, and pointers sections around them are unchanged. **Status: ~99% through the roadmap** — all engineering for v1.0 is done or in a merge-ready PR; both open PRs are self-reviewed (bots degraded).

## Now

- **E5.S4 · Signed/notarized/stapled DMG** → PR #18 (`feat/e5-s4-signed-dmg`) — Merge-ready (open, self-reviewed, awaiting Adam). The last engineering blocker; extends the proven workflow: builds the `.app` only, notarizes+staples it, then bundles the DMG from the stapled app, notarizes+staples the DMG, and attaches both to the draft release.
- **E5.S6 · Release docs (CHANGELOG, RELEASING.md, README install) + entitlements cleanup** → PR #19 (`feat/e5-s6-release-docs`) — Merge-ready (open, self-reviewed, awaiting Adam). Deletes the orphaned `entitlements.plist`, fixes stale doc refs. Edits a different region of `release-pipeline.md` than #18 — no conflict, merge in either order (#18 first is marginally cleaner since the docs reference the DMG).

## Next

- **`v1.0.0` tag push** — Adam, ~5 min. Bump `tauri.conf.json` + `package.json` to `1.0.0` first (see `docs/RELEASING.md`), tag `v1.0.0`, push → the workflow builds + notarizes + attaches the DMG to a **draft** GitHub release → publish it.
- **thedetech product page** — download link + screenshots; Marquee becomes a published Thede Technologies product. Separate step, after the release exists.

## Later

- **E5.S5 · Tauri auto-updater** — DEFERRED past v1.0 (by design). With no updater, updates ship as fresh downloads; it does not gate the first release.
- **Epic 3 · Browse/exclude grid** — Out of scope; PRD marks optional; recommend cut. (`kburns/` sibling dir = historical prior art, ignore.)

## Shipped

- **Notarization proven end-to-end** — 2026-06-30. A `workflow_dispatch` run of "Release (sign + notarize)" passed every stage: import Developer-ID cert → sign sidecar + vendored FFmpeg → signed Tauri bundle → deep-verify → notarytool → staple → Gatekeeper accepted → artifact uploaded ([run 28450150115](https://github.com/adamthede/slideshow-gen/actions/runs/28450150115)). `--onefile` deep-signing resolved (no `--onedir` rewrite). Detail in "The wall is CLEARED" above.
- **Engine (E0)** — Done; the proven Python `slideshow-gen` engine Marquee wraps.
- **Epics 1, 2, 4** — Shipped.
- **E5.S1 · Build/sign/notarize workflow** — Shipped and proven live.
- **E5.S2 · Code-signing hygiene** — PR #13 (2026-06-26).
- **E5.S7 · Bundled signed FFmpeg** — PR #14 (2026-06-29).
- **CI Developer-ID G2 intermediate** — PR #17 (2026-06-30).
- **E5.S3 · Hardened runtime + minimal entitlements** — PR #16 (2026-07-04).

## Pointers
- PRD/ADRs/stories: `_bmad-output/planning-artifacts/` · Release pipeline: `docs/release-pipeline.md` · Plan files: `docs/plans-to-do/` & `docs/plans-done/`
