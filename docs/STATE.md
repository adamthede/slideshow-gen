---
name: Marquee (Slideshow Generator)
slug: slideshow-gen
generated: 2026-07-05
sources:
  - git log (Project - Slideshow Generator/slideshow-gen, branch main)
  - gh pr/issue list (adamthede/slideshow-gen)
  - docs/LOOP-TO-COMPLETION.md
---

### What it is

Marquee is a notarized macOS app that wraps a proven Python slideshow/timelapse engine (`slideshow-gen`). It renders programmatic slideshows and timelapse videos from photo archives. Internally called "Marquee"; `slideshow-gen` is the engine repo name. Part of the Thede Technologies portfolio as a publishable standalone product.

### Current state

- Last commit: 2026-07-05 (`fix(release): remove double-hyphen from entitlements XML comment`)
- Version tag: `v1.0.0` (tagged on main; present in `tauri.conf.json` + `package.json`)
- No CI beyond the GitHub Actions release pipeline (no unit-test CI on PRs; no CodeRabbit/Copilot auto-review wired). `pytest tests/` (scoped) passes 19 tests; bare `pytest` fails on vendored `_bmad/` self-tests.
- Notarization end-to-end proven live: GitHub Actions run https://github.com/adamthede/slideshow-gen/actions/runs/28450150115 (2026-06-30) completed import cert → sign → notarize → staple → Gatekeeper. (Source: `docs/LOOP-TO-COMPLETION.md`)
- FFmpeg is bundled and signed inside Marquee.app. (Note: `docs/architecture*.md` may still say FFmpeg is not bundled - flagged in 2026-07-05 audit as stale, not yet corrected.)
- No thedetech product page yet - Marquee has no public download URL.
- Phase: engineering complete at v1.0.0; awaiting `v1.0.0` tag push to trigger the release workflow and produce the downloadable DMG artifact.

### Shipped recently

(Since 2026-06-05, from git log and merged PRs)

- 2026-06-26 - PR #13 merged: E5.S2 - code-signing hygiene (sign sidecar + deep-verify gate)
- 2026-06-26 - PR #14 merged: E5.S7 - bundle signed FFmpeg into Marquee.app
- 2026-06-29 - PR #15 merged: FFmpeg GPL license posture (GPLv2 attribution + written source offer)
- 2026-06-29 - PR #16 merged: E5.S3 - hardened runtime + minimal entitlements
- 2026-06-30 - PR #17 merged: CI Developer ID G2 intermediate (codesign full chain)
- 2026-07-05 - PR #18 merged: E5.S4 - signed, notarized, stapled DMG (drag-to-Applications) [mergedAt: 2026-07-05T15:58:17Z]
- 2026-07-05 - PR #19 merged: E5.S6 - release docs, changelog, README install + entitlements cleanup [mergedAt: 2026-07-05T16:58:11Z]
- 2026-07-05 - PR #20 merged: docs(loop) - E5.S4 + E5.S6 open as merge-ready PRs (loop doc update)
- Version bumped to `1.0.0` in tauri.conf.json + package.json (committed to main 2026-07-05)

### In flight now

- PR #21 - `docs(claude-md): add scoped-pytest verify command + readiness rule to slideshow-gen` (`docs/claude-md-refresh-2026-07`) - OPEN as of 2026-07-05 (CLAUDE.md docs-only refresh from the 2026-07-05 audit batch).

No engineering PRs are open. Both E5.S4 and E5.S6 merged on 2026-07-05.

Note: the audit doc (2026-07-03) described PR #16 as "parked at review gate." This has been resolved - PR #16 merged 2026-06-29 and all subsequent E5 stories (#18, #19) also merged by 2026-07-05.

### Known outstanding

From `docs/LOOP-TO-COMPLETION.md` (2026-07-04, updated post-S4+S6 merge):

1. **`v1.0.0` tag push** - Adam, ~5 min. Bump confirmed already done (tauri.conf.json + package.json at 1.0.0). The `v1.0.0` tag exists on main. Pushing the tag triggers the release workflow which builds + notarizes + attaches the DMG to a draft GitHub release, then Adam publishes it.
2. **thedetech product page** - download link + screenshots after the release exists. Separate step; not in this repo.
3. **E5.S5 (Tauri auto-updater)** - explicitly deferred past v1.0 by design. Updates ship as fresh downloads until this is built.
4. **Epic 3 (browse/exclude grid)** - PRD marks optional; LOOP doc recommends cutting.
5. `docs/plans-to-do/2026-07-04-e5-s4-signed-dmg.md` and `docs/plans-to-do/2026-07-04-e5-s6-release-docs.md` both show `status: "QA Needed"` - stale, both PRs merged 2026-07-05; these files need /shipped to move them to plans-done.

### Distance to done

Per `docs/LOOP-TO-COMPLETION.md` definition of done: "a notarized, downloadable Marquee.app a user can drag to /Applications, open past Gatekeeper, and render a real slideshow."

- Engineering: **100% complete.** All Epics 0, 1, 2, 4, and 5 shipped. E5.S5 (auto-updater) deferred by design.
- Remaining gate: Adam pushes the `v1.0.0` tag (~5 min) → workflow produces draft release → Adam publishes it.
- Product visibility: thedetech product page (separate work item, ~1 day).

### DIRECTION (DRAFT - Adam edits this section)

Marquee is engineering-done at v1.0.0 - the only remaining step is the tag push that triggers the automated release workflow. The highest-leverage next action is not more code but publishing: tag push + thedetech product page turns months of build work into a public Thede Technologies product. The auto-updater (E5.S5) is a quality-of-life addition for later; the first release works fine as a manual download. If `docs/architecture*.md` still describes FFmpeg as unbundled, that should be corrected in a quick docs sweep after the release lands.

### Links

- Roadmap: `_bmad-output/planning-artifacts/prd.md`
- LOOP doc: `docs/LOOP-TO-COMPLETION.md`
- Key plans: `docs/plans-to-do/2026-07-04-e5-s4-signed-dmg.md`, `docs/plans-to-do/2026-07-04-e5-s6-release-docs.md`
- Release pipeline: `docs/release-pipeline.md`
- Dashboard / live URL: None (no thedetech product page yet)
- GitHub: https://github.com/adamthede/slideshow-gen
