---
title: "Epic 5.S1: GitHub Actions build + sign + notarize pipeline"
status: "Done"
created: 2026-05-28
completed: 2026-05-28
linked_pr: "https://github.com/adamthede/slideshow-gen/pull/7"
---

## Goal

A GitHub Actions workflow producing a signed, notarized `Marquee.app` on tag
push, using Developer ID Application cert (Team `U85N54PC5J`) and Apple
`notarytool`. End state: pushing a `v*` tag yields a Gatekeeper-clean artifact
attached to a draft GitHub release.

## Scope (do)

- New workflow `.github/workflows/release.yml` triggered on `push` of `v*.*.*`
  tags and via `workflow_dispatch`, running on `macos-14` (Apple Silicon).
- Steps: checkout, Python 3.11 + PyInstaller install, freeze sidecar as
  `slideshow-gen-aarch64-apple-darwin` into `desktop/src-tauri/binaries/`,
  Node + npm install, Rust toolchain with `aarch64-apple-darwin` target,
  import Developer ID Application cert into a temporary keychain, run
  `npm run tauri build`, zip the produced `.app`, notarize with
  `xcrun notarytool submit --wait`, staple, verify with `codesign` and
  `spctl`, upload artifact, attach to draft GitHub release.
- Tauri config: thread `signingIdentity` through env var
  (`APPLE_SIGNING_IDENTITY`) so the workflow injects it and local dev can
  override with `-` (ad-hoc).
- Entitlements: already include `com.apple.security.cs.disable-library-validation`
  which covers the PyInstaller-frozen sidecar; no changes needed.
- New `docs/release-pipeline.md` documenting required secrets and the manual
  runbook.

## Out of scope (don't)

- DMG layout polish — E5.S4.
- Auto-updater manifest signing — E5.S5.
- Release notes automation — E5.S6.
- Any engine, UI, Rust source, or sidecar-protocol changes.
- Adding the secrets to the repo (Adam will do that out of band).

## Files expected to touch

- `.github/workflows/release.yml` (new)
- `desktop/src-tauri/tauri.conf.json` (env-driven `signingIdentity`)
- `desktop/src-tauri/entitlements.plist` (verify only; expected unchanged)
- `docs/release-pipeline.md` (new)
- `.gitignore` (add PyInstaller `*.spec` + `desktop/src-tauri/binaries/`)

## Success criteria

- Workflow YAML parses cleanly (`python -c "import yaml; yaml.safe_load(...)"`).
- Sidecar binary name in workflow matches Tauri's `externalBin` expectation
  (`slideshow-gen` → `slideshow-gen-aarch64-apple-darwin`).
- All required secrets are documented with purpose.
- PR mergeable into `main` with no conflicts.
- Adam can add the secrets and run the workflow successfully without
  further code changes.

## Known unknowns

- PyInstaller `--onefile` sometimes fails notarization due to embedded
  archives; defaulting to `--onedir` and pointing Tauri at the main
  executable inside `dist/slideshow-gen/`.
- Whether the existing single `disable-library-validation` entitlement is
  enough once notarytool inspects the bundled PyInstaller payload. Leaving
  the entitlement set as-is for this PR; expand only if notarization
  surfaces a specific failure.
- Whether Tauri 2.x honors `APPLE_SIGNING_IDENTITY` env override when the
  config field is also set. Spec-compliant per Tauri docs, but worth
  smoke-testing on first real run.
