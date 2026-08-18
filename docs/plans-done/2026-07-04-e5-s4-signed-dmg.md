---
title: Epic 5.S4 — Signed, notarized, stapled DMG with drag-to-Applications
status: "Done"
completed: 2026-07-05
linked_pr: "https://github.com/adamthede/slideshow-gen/pull/18"
impl-model: opus
---

# Epic 5.S4: Signed + notarized + stapled DMG

## Goal

Produce a **downloadable `Marquee_<version>_aarch64.dmg`** with the standard
drag-to-Applications layout, signed with the Developer ID Application identity,
notarized by Apple, and stapled — attached to the draft GitHub release on a
`v*.*.*` tag push. This is the last remaining engineering blocker for a public
download (the `.app`-only path is already proven live, 2026-06-30).

## Background — what the proven run actually did

The 2026-06-30 `workflow_dispatch` run (run `28450150115`) proved the pipeline
end-to-end, but only for the **`.app`**:

- Tauri built **two** bundles: `Marquee.app` and
  `Marquee_0.1.0_aarch64.dmg` (Tauri's DMG bundler already emits the
  drag-to-Applications window — the app icon + `/Applications` alias).
- Tauri **signed** both the `.app` and the `.dmg` with the Developer ID
  identity (`Signing …/Marquee_0.1.0_aarch64.dmg` appears in the log).
- Tauri did **not** notarize or staple anything (no `notariz`/`staple` lines in
  the bundler output, despite the notarization env vars being present in that
  step). Notarization + stapling was done by the **manual** steps afterward —
  and those operate on the **`.app` only**.

Net: the DMG that Tauri produced in the proven run wrapped an **un-stapled**
`.app` and was itself **un-notarized / un-stapled**. Shipping it as-is would
give users a DMG Gatekeeper rejects offline.

## Design (lowest-risk, mirrors the proven `.app` path)

Do **not** rely on Tauri's auto-notarization (it demonstrably did not fire in
the proven run). Instead, extend the existing manual notarize/staple discipline
to the DMG, and build the DMG **from the already-stapled `.app`** so the DMG
wraps a stapled app:

1. **Build only the `.app`** in the main Tauri build step
   (`tauri build … --bundles app`), not the DMG. Everything up to and including
   the deep-verify gate is unchanged, operating on the `.app`.
2. **Notarize + staple the `.app`** — unchanged from the proven run.
3. **Bundle the DMG from the stapled `.app`**: `tauri bundle --bundles dmg`
   re-uses the already-built (now stapled) `.app` and produces + signs
   `Marquee_<version>_aarch64.dmg` with the drag-to-Applications layout. No
   recompile.
4. **Notarize + staple the DMG** with the same `notarytool submit --wait` +
   `stapler staple` pattern proven for the `.app`.
5. **Verify** the DMG: `spctl -a -t open --context context:primary-signature`
   (DMGs assess as `open`, not `exec`) + `stapler validate`.
6. **Attach the DMG** (in addition to the stapled `.app` zip) to the draft
   release and upload it as a workflow artifact.

## Files expected to change

- `.github/workflows/release.yml` — split app/DMG bundling; add DMG
  notarize + staple + verify + attach steps.
- `desktop/src-tauri/tauri.conf.json` — add `bundle.macOS.dmg` icon positions
  (explicit drag-to-Applications layout coordinates) for a deliberate window;
  Tauri already defaults to this layout, so this is polish, not a functional
  gate.
- `docs/release-pipeline.md` — document the DMG stage: what it produces, the
  build-from-stapled-app ordering, and the verify command.
- `docs/plans-to-do/` → `docs/plans-done/` on `/shipped`.

## What CI (the tag run) will prove vs. what is verified locally

Full end-to-end DMG notarization needs the Apple secrets, which are **CI-only**.
Locally (no secrets) this PR verifies:

- `release.yml` is valid YAML and the step graph is coherent
  (`python -c yaml.safe_load` / `actionlint` if available).
- `tauri.conf.json` still parses and the DMG bundle config is well-formed.
- The engine test suite (`pytest tests/` scoped) is unaffected (no Python
  changed).
- The DMG layout logic: a **local unsigned** `tauri bundle --bundles dmg` dry
  run (if a sidecar + ffmpeg are stubbed) confirms the DMG is produced with the
  drag-to-Applications window — OR, if the local toolchain can't produce the
  sidecar, the proven-run log already demonstrates Tauri emits the DMG.

The **tag run** will prove: the DMG is notarized (`notarytool` accepts it),
stapled (`stapler validate` passes), Gatekeeper-accepted offline
(`spctl` accepts), and attached to the draft release.

## Success criteria

- A `v*.*.*` tag push produces a draft GitHub release with **both** a stapled
  `Marquee.app` zip and a notarized+stapled `Marquee_<version>_aarch64.dmg`.
- The DMG opens to a window with the app icon and an `/Applications` alias
  (drag-to-install).
- `spctl` + `stapler validate` accept the DMG.
- The proven `.app` path is unchanged — no regression to the 2026-06-30 result.

## Constraints

- macOS / Apple Silicon only (NFR6).
- Additive to the E5.S1/S2/S3/S7 workflow — must not break the proven `.app`
  path.
- Excludes the notarization run itself as a gating human step only in the sense
  that the first tag push is Adam's call; the workflow is fully automated.
