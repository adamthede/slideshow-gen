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
5. **Signs the PyInstaller sidecar** (`codesign --options runtime
   --timestamp --entitlements …`) with the Developer ID identity, so the
   bundler embeds an already-signed, hardened-runtime binary. (E5.S2 — see
   "Signing coverage" below.)
6. Runs `npm run tauri build -- --target aarch64-apple-darwin`. Tauri's
   bundler signs `Marquee.app` using the keychain identity and the
   `entitlements.plist` already wired in `tauri.conf.json`.
7. **Deep-verify gate (pre-notarize):** runs
   `codesign --verify --deep --strict --verbose=2 Marquee.app`. The build
   fails here if any nested code object is unsigned or invalid — before any
   notary submission is spent. (E5.S2.)
8. Zips the `.app` (notarytool requires zip / dmg / pkg) and submits to
   Apple with `xcrun notarytool submit --wait`.
9. Staples the notarization ticket with `xcrun stapler staple`.
10. Verifies the stapled bundle with `codesign --verify --deep --strict`
    and `spctl -a -t exec -vv`.
11. Re-zips the stapled `.app`, uploads it as a workflow artifact, and
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

## Signing coverage (E5.S2)

Every executable code object inside `Marquee.app` must be signed with the
Developer ID Application identity (Team `U85N54PC5J`) and the bundle must pass
`codesign --verify --deep --strict` before notarization. The release workflow
signs inside-out (nested code first, then the bundle) and enforces a deep-verify
gate after the build and before the notary submit.

| Code object | Where it lives | How it's signed | Why it must be signed |
| --- | --- | --- | --- |
| `Marquee` (Tauri shell) | `Contents/MacOS/Marquee` | Tauri 2.x bundler, via `APPLE_SIGNING_IDENTITY` + `macOS.signingIdentity` in `tauri.conf.json`, with hardened runtime + `entitlements.plist` | It's the app's main executable; Gatekeeper checks it first. |
| `slideshow-gen-aarch64-apple-darwin` (PyInstaller sidecar) | `Contents/MacOS/` (Tauri `externalBin`) | Explicit `codesign --options runtime --timestamp --entitlements …` step in `release.yml` **before** the Tauri build; Tauri preserves the embedded signature | Spawned per render via the shell plugin. Unsigned nested executables fail `--deep` verify and notarization. Needs `disable-library-validation` so the bootloader can `dlopen` the Apple-signed `Python.framework` it extracts (see ADR-0002). |
| Bundled Python framework + C-extension dylibs | **Inside** the sidecar's appended PyInstaller PKG archive — not separate on-disk files | Covered by the single sidecar signature above | A `--onefile` build stores them inside the binary, so they are not exposed as on-disk Mach-O objects at sign/verify time; the outer signature seals them. |
| FFmpeg | **Not bundled.** Resolved from `PATH` at runtime by the engine (`slideshow_gen/ffmpeg.py`) | n/a — no on-disk code object inside the bundle | FFmpeg bundling was deferred by ADR-0002 to E5.S1 but has not yet landed; there is currently no embedded FFmpeg binary to sign. See the note below. |

> **FFmpeg is not yet embedded.** The S2 ticket anticipated signing an embedded
> FFmpeg, but the engine still calls `ffmpeg` from `PATH` and E5.S1 shipped
> without bundling it (ADR-0002 "FFmpeg — deferred to E5.S1"). When FFmpeg is
> later bundled into `Contents/Resources/`, it becomes a nested Mach-O that
> **must** be signed (`codesign --options runtime --timestamp --sign …`) before
> the deep-verify gate, and added as a row above. The gate added in S2 will
> automatically catch it if it lands unsigned. Bundling itself remains its own
> story — out of scope here.

### The `--onefile` deep-signing question — resolved

ADR-0002 chose PyInstaller `--onefile`, leaving open whether a self-extracting
`--onefile` binary can satisfy `codesign --deep --strict`. **It can.**

Verified empirically against the signed sidecar
(`desktop/src-tauri/binaries/slideshow-gen-aarch64-apple-darwin`, hardened
runtime, Developer ID):

```
$ codesign --verify --deep --strict --verbose=2 slideshow-gen-aarch64-apple-darwin
…: valid on disk
…: satisfies its Designated Requirement
# exit 0
```

A `--onefile` PyInstaller binary is a single Mach-O whose bundled Python
framework and dependency dylibs are appended as data inside its PKG archive.
They are unpacked to a temp dir (`/var/folders/.../T/_MEI…`) only at runtime,
so at sign/verify time there are **no separate nested code objects on disk** for
`--deep` to recurse into — the one outer signature covers everything. The
self-extraction at launch is gated by `disable-library-validation`, not by the
bundle-time signature.

**Conclusion: `--onefile` does NOT block deep signing. No `--onedir` rewrite is
required.** (The `--onedir` migration remains a possible future change only if
cold-start latency ever becomes a UX problem — unrelated to signing.)

## Known unknowns
- **Entitlements coverage.** `entitlements.plist` currently grants only
  `com.apple.security.cs.disable-library-validation`. That's the
  entitlement PyInstaller-frozen binaries typically need. If notarization
  surfaces a different requirement (e.g. `allow-jit`,
  `allow-unsigned-executable-memory`), add only what the failure log
  names — don't blanket-grant.
- **First run end-to-end.** No part of this pipeline has been exercised
  with real Apple credentials yet. The first tag push is the real test.
