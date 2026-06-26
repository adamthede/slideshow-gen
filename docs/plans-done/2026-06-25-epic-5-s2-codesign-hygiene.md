---
title: Epic 5.S2 — Code-signing hygiene (sign all nested binaries, deep-verify gate)
status: "Done"
completed: 2026-06-26
linked_pr: "https://github.com/adamthede/slideshow-gen/pull/13"
---

# Epic 5.S2: Code-signing hygiene

## Goal

Ensure **every** executable, framework, and dylib inside `Marquee.app` is signed with the Developer ID Application identity, and that the bundle passes `codesign --verify --deep --strict`. This closes the signing-coverage gaps that would otherwise cause Apple to reject the bundle at notarization — **de-risking the unproven notarization step (E5.S6 / the first real `v*.*.*` tag push) before Adam spends a real submission on it.**

Per PRD `_bmad-output/planning-artifacts/prd.md` (Epic 5, story E5.S2) and the "Known unknowns" section of `docs/release-pipeline.md`. E5.S1 (the build/sign/notarize workflow) already exists and shipped (`docs/plans-done/2026-05-28-epic-5-s1-build-sign-notarize.md`); this story hardens the *signing coverage* inside that workflow. Notarization itself is the next, deliberately human-gated step — NOT part of this story.

## Scope

### In scope (Agent owns end-to-end)

1. **Enumerate every code object inside the built bundle.** After a `npm run tauri build -- --target aarch64-apple-darwin`, walk `Marquee.app` and list every Mach-O binary, framework, and `.dylib`/`.so` — including the PyInstaller-frozen sidecar (`slideshow-gen-aarch64-apple-darwin`), the embedded **FFmpeg** binary, and any auxiliary shared libs the sidecar or Tauri shell carry. Document the inventory in the PR.
2. **Ensure each is signed with the Developer ID Application identity.** Tauri's bundler signs the `.app` shell; verify it also signs (or add explicit signing for) the `externalBin` sidecar, FFmpeg, and nested dylibs. Sign inside-out (nested code first, then the bundle) so a `--deep` verify passes. Use the same identity the E5.S1 workflow imports (Team `U85N54PC5J`).
3. **Investigate the PyInstaller `--onefile` signing question.** A `--onefile` binary is a self-extracting archive; its internal libs are unpacked at runtime and may not be individually signable at bundle time. Determine whether `--onefile` signing is sufficient for `codesign --deep --strict`, or whether nested binaries need signing. **Document the finding.** If `--onefile` provably blocks deep signing and the only fix is `--onedir` (a larger bundle rewire, out of scope per the "Known unknowns" section of `release-pipeline.md`), **STOP and escalate to Adam as a separate decision** — do not undertake the `--onedir` rewrite in this story.
4. **Add a deep-verify gate to the release workflow.** In `.github/workflows/release.yml`, after the Tauri build / signing step and **before** the notarization submit, add `codesign --verify --deep --strict --verbose=2 Marquee.app` (fail the build on any unsigned/invalid nested code).
5. **Document signing coverage.** Update `docs/release-pipeline.md` with a short table: each signed code object and why it must be signed.

### Out of scope

- **Notarization itself** — the `notarytool submit` run is the deliberate, Adam-in-the-loop step (needs the Apple secrets in the "Required GitHub secrets" section of `release-pipeline.md`). Do not trigger a real notarization.
- **Hardened runtime / entitlements changes** (that's E5.S3 in the PRD). Leave `entitlements.plist` as-is; only flag if a signing failure *names* a missing entitlement.
- **DMG packaging** (E5.S4), **auto-updater** (E5.S5), **release docs** (E5.S6).
- **Switching PyInstaller `--onefile` → `--onedir`** — only if step 3 proves it's required, and then as an escalation to Adam, not a build.

## Files expected to change

- `.github/workflows/release.yml` — add the `codesign --verify --deep --strict --verbose=2` gate after build/sign, before notarize; add explicit nested-binary signing steps if Tauri doesn't already cover the sidecar/FFmpeg.
- `desktop/src-tauri/tauri.conf.json` — possibly signing/`externalBin` config so the bundler signs the sidecar and resources.
- `docs/release-pipeline.md` — signing-coverage table + the `--onefile` finding.
- Possibly a helper script (e.g. `desktop/scripts/sign-nested.sh`) if nested signing needs explicit steps beyond Tauri's bundler.

## Success criteria

- `codesign --verify --deep --strict --verbose=2 Marquee.app` **passes** on a locally built artifact, referencing the Developer ID Application identity for the shell, the sidecar, and FFmpeg.
- The release workflow includes the deep-verify gate and fails on any unsigned nested code.
- `docs/release-pipeline.md` enumerates every signed code object and why.
- The `--onefile` vs `--onedir` question is answered in writing (resolved, or escalated to Adam with the evidence).
- **No notarization required to land this story** — signing + local/CI `codesign` verify only.

## Constraints

- **Verifiable without Apple notarization secrets.** `codesign` signing/verification needs the Developer ID Application identity present — available in CI via the existing `APPLE_CERTIFICATE_P12_BASE64` keychain import (E5.S1), and on Adam's machine if the identity is in his login Keychain. The agent can implement and CI-verify; if the agent's local environment lacks the identity, it verifies the *logic and gate wiring* and defers the signed-artifact proof to a CI `workflow_dispatch` run (no release created).
- macOS-only (PRD NFR6). Apple Silicon (`aarch64-apple-darwin`) is the only target.
- Additive to the shipped E5.S1 workflow — do not break the existing notarize/staple steps.
- Do not expand entitlements (E5.S3 owns that).
- `kburns/` (sibling dir) and the CLI engine are out of scope.
