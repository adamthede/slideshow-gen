---
title: Epic 5.S6 — Release docs, changelog, README install (+ entitlements cleanup)
status: "QA Needed"
linked_pr: ""
impl-model: opus
---

# Epic 5.S6: Release docs + changelog + README + entitlements cleanup

## Goal

Give Marquee everything a first-time downloader and the release-cutter (Adam)
need: a changelog tied to GitHub releases, a 5-minute release runbook, and a
README download/install section with the Gatekeeper first-open note. Fold in
the queued **entitlements cleanup** follow-up flagged in PR #16's review.

## Deliverables

### 1. `CHANGELOG.md` (repo root)

Keep-a-Changelog format, `## [1.0.0]` section with the real v1 feature list
derived from the PRD functional requirements (FR1–FR10) and shipped epics
(E0–E5). An `## [Unreleased]` section records the deliberately-deferred
auto-updater (E5.S5). Version links at the bottom.

### 2. `docs/RELEASING.md`

The 5-minute Adam runbook: bump version (`tauri.conf.json` + `package.json` to
`1.0.0`) → push `v1.0.0` tag → watch the workflow → check the draft release
(DMG + `.app` zip attached) → paste changelog + publish. Includes prerequisites
(secrets/variables already set), a notarization-failure action path, and the
post-publish steps (plan hygiene, thedetech page is separate). Points at
`docs/release-pipeline.md` for the mechanics.

### 3. README download/install section

New "Download Marquee (macOS app)" section near the top of the root README:
release link, DMG drag-to-Applications steps, and the Gatekeeper first-open
note (signed + notarized, right-click→Open fallback, offline). Reframes the
rest of the README as the CLI/engine docs.

### 4. Entitlements cleanup (PR #16 follow-up)

- **Delete** the orphaned `desktop/src-tauri/entitlements.plist` (E5.S3 split it
  into `app-entitlements.plist` + `binary-entitlements.plist`).
- **Fix stale references** that still say the single file is applied to "both
  binaries":
  - `desktop/README.md` (file-tree entry)
  - `docs/architecture-app.md` (security model)
  - `docs/adr/0002-sidecar-packaging.md` (signing-under-hardened-runtime)
  - `docs/release-pipeline.md` (signing-coverage table row for the Tauri shell)

> Note: `docs/release-pipeline.md`'s numbered-list step 8 mention of
> `entitlements.plist` is intentionally left to PR #18 (E5.S4), which rewrites
> that whole step — editing it here too would create a merge conflict on the
> same line.

## What does NOT change

- No workflow logic (that's E5.S4 / PR #18).
- No version bump in this PR — the runbook documents it as Adam's release step.
- No auto-updater (E5.S5, deferred).
- Historical archives (`docs/plans-done/`, `docs/pr-reviews/`) keep their
  point-in-time `entitlements.plist` references.

## Test plan

- `pytest tests/` (scoped) — no Python changed; green.
- Docs render / links sanity-checked.
- `grep` confirms no live (non-archive) `entitlements.plist` reference remains
  except the PR #18-owned step-8 line.
