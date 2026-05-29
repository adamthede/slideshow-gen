# Release Pipeline (Epic 5.S1)

GitHub Actions workflow that builds, signs, and notarizes `Marquee.app` for
direct-download distribution. Defined in
[`.github/workflows/release.yml`](../.github/workflows/release.yml).

## What it does

1. Checks out the repo on a `macos-14` runner (Apple Silicon, the only
   target Marquee supports today).
2. Installs Python 3.11, then `pip install -e .` and `pyinstaller`, and
   freezes the `slideshow-gen` CLI into a single executable named
   `slideshow-gen-aarch64-apple-darwin` placed in
   `desktop/src-tauri/binaries/` — the path Tauri's `externalBin` config
   expects.
3. Installs Node 20, Rust stable with the `aarch64-apple-darwin` target,
   and `npm ci` in `desktop/`.
4. Creates a fresh temporary keychain and imports the Developer ID
   Application `.p12` from `APPLE_CERTIFICATE_P12_BASE64`.
5. Runs `npm run tauri build -- --target aarch64-apple-darwin`. Tauri's
   bundler signs `Marquee.app` using the keychain identity and the
   `entitlements.plist` already wired in `tauri.conf.json`.
6. Zips the `.app` (notarytool requires zip / dmg / pkg) and submits to
   Apple with `xcrun notarytool submit --wait`.
7. Staples the notarization ticket with `xcrun stapler staple`.
8. Verifies with `codesign --verify --deep --strict` and
   `spctl -a -t exec -vv`.
9. Re-zips the stapled `.app`, uploads it as a workflow artifact, and
   attaches it to a **draft** GitHub release for the tag (tag-triggered
   runs only).

## Triggers

- `push` of a tag matching `v*.*.*` — builds the tag and creates a draft
  release with the artifact attached.
- `workflow_dispatch` — manual runs from the Actions tab, no release
  created. Useful for smoke-testing the pipeline.

## Required GitHub secrets

Set these under **Settings → Secrets and variables → Actions** before
running the workflow.

| Secret | Purpose |
| --- | --- |
| `APPLE_CERTIFICATE_P12_BASE64` | Base64-encoded `.p12` export of the Developer ID Application certificate (Team `U85N54PC5J`). |
| `APPLE_CERTIFICATE_PASSWORD` | Password protecting the `.p12` file. |
| `APPLE_ID` | Apple ID email used for notarization (`athede@gmail.com` or the team's distribution Apple ID). |
| `APPLE_APP_SPECIFIC_PASSWORD` | App-specific password generated at <https://appleid.apple.com> — used by `notarytool`. **Not** the Apple ID password. |
| `APPLE_TEAM_ID` | `U85N54PC5J` (Thede Technologies, LLC). |

### How to produce `APPLE_CERTIFICATE_P12_BASE64`

```bash
# Export the cert from Keychain Access first (right-click → Export → .p12),
# then:
base64 -i DeveloperID.p12 | pbcopy
# Paste into the GitHub secret value field.
```

## Manual runbook

### Trigger via tag

```bash
git tag v0.1.0
git push origin v0.1.0
```

Watch the run at <https://github.com/{owner}/slideshow-gen/actions>. On
success a draft release appears at `Releases` with `Marquee-stapled.zip`
attached. Edit and publish the release when ready.

### Trigger manually (no release)

1. Go to **Actions → Release (sign + notarize) → Run workflow**.
2. Pick the branch and run. The signed `.app` will be uploaded as an
   artifact named `Marquee-aarch64-apple-darwin`.

### Verify locally

After downloading the zip artifact:

```bash
unzip Marquee-stapled.zip
codesign --verify --deep --strict --verbose=2 Marquee.app
spctl -a -t exec -vv Marquee.app
xcrun stapler validate Marquee.app
```

All four should report success and reference the Developer ID identity.

### Smoke-test the bundled app

1. Drag `Marquee.app` to `/Applications`.
2. Open it. Gatekeeper should accept without an unidentified-developer
   warning. (First launch may pause briefly while macOS verifies the
   ticket.)
3. Trigger a small render to confirm the embedded `slideshow-gen` sidecar
   spawns and exits cleanly.

## Known unknowns

- **PyInstaller `--onefile` vs `--onedir`.** The workflow uses `--onefile`
  because Tauri's `externalBin` config points at a single file. If
  notarization rejects the bundle because Apple can't inspect the
  self-extracting archive, switch to `--onedir` and rewire the bundle to
  carry the `dist/slideshow-gen/` directory as bundle resources (a larger
  change — out of scope for this PR).
- **Entitlements coverage.** `entitlements.plist` currently grants only
  `com.apple.security.cs.disable-library-validation`. That's the
  entitlement PyInstaller-frozen binaries typically need. If notarization
  surfaces a different requirement (e.g. `allow-jit`,
  `allow-unsigned-executable-memory`), add only what the failure log
  names — don't blanket-grant.
- **First run end-to-end.** No part of this pipeline has been exercised
  with real Apple credentials yet. The first tag push is the real test.
