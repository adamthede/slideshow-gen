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
3. **Vendors a license-clean static FFmpeg + ffprobe** for
   `aarch64-apple-darwin` into `desktop/src-tauri/resources/` via
   `desktop/scripts/vendor-ffmpeg.sh` (E5.S7). The script fetches a static
   build and **fails the build** if it is GPL/nonfree or is missing a
   capability the engine uses (`h264_videotoolbox`, `aac`, `drawtext`,
   `zoompan`, `sidechaincompress`, `overlay`). These resources ship inside
   `Marquee.app/Contents/Resources/` and are **not** committed to the repo
   (`.gitignore`d). See "FFmpeg vendoring & license posture" below.
4. Installs Node 20, Rust stable with the `aarch64-apple-darwin` target,
   and `npm ci` in `desktop/`.
5. Creates a fresh temporary keychain and imports the Developer ID
   Application `.p12` from `APPLE_CERTIFICATE_P12_BASE64`.
6. **Signs the PyInstaller sidecar** (`codesign --options runtime
   --timestamp --entitlements …`) with the Developer ID identity, so the
   bundler embeds an already-signed, hardened-runtime binary. (E5.S2 — see
   "Signing coverage" below.)
7. **Signs the vendored `ffmpeg` + `ffprobe`** with the same Developer ID
   identity, hardened runtime, timestamp, and entitlements — inside-out,
   before the bundle, so the deep-verify gate exercises them. (E5.S7.)
8. Runs `npm run tauri build -- --target aarch64-apple-darwin`. Tauri's
   bundler copies the signed FFmpeg resources into `Contents/Resources/`
   (preserving their signatures) and signs `Marquee.app` using the keychain
   identity and the `entitlements.plist` already wired in `tauri.conf.json`.
9. **Deep-verify gate (pre-notarize):** runs
   `codesign --verify --deep --strict --verbose=2 Marquee.app`. The build
   fails here if any nested code object is unsigned or invalid — before any
   notary submission is spent. (E5.S2; now also covers the bundled FFmpeg.)
10. Zips the `.app` (notarytool requires zip / dmg / pkg) and submits to
    Apple with `xcrun notarytool submit --wait`.
11. Staples the notarization ticket with `xcrun stapler staple`.
12. Verifies the stapled bundle with `codesign --verify --deep --strict`
    and `spctl -a -t exec -vv`.
13. Re-zips the stapled `.app`, uploads it as a workflow artifact, and
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
| `slideshow-gen-aarch64-apple-darwin` (PyInstaller sidecar) | inside `Contents/` (Tauri `externalBin` — `Resources/` on current Tauri v2; the deep-verify gate scans all of `Contents/`) | Explicit `codesign --options runtime --timestamp --entitlements …` step in `release.yml` **before** the Tauri build; Tauri preserves the embedded signature | Spawned per render via the shell plugin. Unsigned nested executables fail `--deep` verify and notarization. Needs `disable-library-validation` so the bootloader can `dlopen` the Apple-signed `Python.framework` it extracts (see ADR-0002). |
| Bundled Python framework + C-extension dylibs | **Inside** the sidecar's appended PyInstaller PKG archive — not separate on-disk files | Covered by the single sidecar signature above | A `--onefile` build stores them inside the binary, so they are not exposed as on-disk Mach-O objects at sign/verify time; the outer signature seals them. |
| `ffmpeg` + `ffprobe` (vendored static build) | `Contents/Resources/ffmpeg`, `Contents/Resources/ffprobe` (Tauri `bundle.resources` map in `tauri.conf.json`) | Explicit `codesign --options runtime --timestamp --entitlements …` step in `release.yml` **before** the Tauri build; Tauri copies the resources into the bundle preserving their signatures | Nested Mach-O executables spawned per render by the engine. Unsigned nested executables fail `--deep` verify and notarization. (E5.S7.) |

> **FFmpeg is bundled as of E5.S7.** The engine (`slideshow_gen/ffbin.py`)
> resolves `ffmpeg`/`ffprobe` from the `FFMPEG_BINARY`/`FFPROBE_BINARY` env
> vars first, then `PATH`. Inside `Marquee.app` the Tauri shell
> (`desktop/src-tauri/src/sidecar.rs`) sets those env vars to the signed copies
> it ships in `Contents/Resources/`, so a clean Mac with nothing on `PATH` can
> still render. The standalone CLI sets no env var and keeps using `PATH`.

## FFmpeg vendoring & license posture (E5.S7)

`Marquee.app` ships its own `ffmpeg` + `ffprobe` so a clean Mac with no FFmpeg
on `PATH` can render. They are fetched and signed at build time by
`desktop/scripts/vendor-ffmpeg.sh` (called from `release.yml`) and **never
committed** (each is tens of MB; `.gitignore`d under
`desktop/src-tauri/resources/`).

**Source (default, overridable).** Martin Riedl's static macOS/arm64 build
server (`https://ffmpeg.martin-riedl.de/redirect/latest/macos/arm64/release/{ffmpeg,ffprobe}.zip`).
Chosen because it publishes static `aarch64-apple-darwin` builds of both
`ffmpeg` and `ffprobe` behind a stable download API. Override with
`FFMPEG_VENDOR_URL` / `FFPROBE_VENDOR_URL` (+ optional `*_SHA256`).

**License posture — LGPL/non-GPL preferred.** Marquee invokes FFmpeg purely as
a **separate child process** (subprocess; it never links `libav*`), so FFmpeg's
license does not "infect" Marquee's own code. Even so, for a distributed
product we prefer a clean LGPL / non-GPL build and avoid GPL-encumbered builds.
The vendor script **fails the build** (fail-closed) if the fetched binary
advertises `--enable-gpl` or `--enable-nonfree`, and also if it is missing any
capability the engine actually uses (`h264_videotoolbox`, `aac`, `drawtext`,
`zoompan`, `sidechaincompress`, `overlay`). The exact `configuration:` line and
`-buildconf` are printed into the CI log for an auditable record of the license
+ feature set of the precise binary shipped.

> **⚠️ Human-gated, flagged for Adam.** A *prebuilt, verified LGPL* static
> macOS/arm64 FFmpeg that also includes `drawtext` (libfreetype) is not a
> settled, universally-available artifact. The default source above is a strong
> candidate, but its license/feature posture is only *proven* when the
> fail-closed guards run on a real `workflow_dispatch` build. **Confirm the
> first signed build's vendor-step log** shows the guards passing (no
> `--enable-gpl`, all features present). If the default source ever serves a
> GPL build, the build fails loudly — point `FFMPEG_VENDOR_URL`/
> `FFPROBE_VENDOR_URL` at a confirmed LGPL build, or wire a from-source LGPL
> build (`./configure --disable-gpl --disable-nonfree --enable-videotoolbox
> --enable-audiotoolbox --enable-libfreetype …`) as the fallback. Once a source
> is locked, pin a versioned URL + `*_SHA256` for reproducible, notarizable
> releases.

**Bundle-size delta.** A static `ffmpeg` + `ffprobe` adds roughly 80–120 MB to
the `.app` (two ~40–70 MB static Mach-O binaries; exact size depends on the
chosen build). Confirm the delta from the first CI artifact.

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
- **Bundled FFmpeg deep-verify + notarization (E5.S7).** The signed FFmpeg
  path has not been exercised with real Apple credentials. The first
  `workflow_dispatch` build must confirm: (a) the vendor-step license/feature
  guards pass, (b) `codesign --verify --deep --strict` accepts the bundled,
  signed `ffmpeg`/`ffprobe`, and (c) notarization does not name an extra
  entitlement for the FFmpeg child process. A static `ffmpeg` calling Apple's
  VideoToolbox should need nothing beyond the current entitlements, but the
  notary log is the source of truth — add only what it names.
- **Clean-Mac render.** The end goal — opening the notarized `Marquee.app` on
  a Mac with **no `ffmpeg` on `PATH`** and completing a small render — can only
  be verified on a clean machine after a real signed build. Until then the
  resolution order is covered by `tests/test_ffbin.py`, not an end-to-end run.
