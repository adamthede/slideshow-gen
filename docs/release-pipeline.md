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
3. **Vendors a static FFmpeg + ffprobe** for
   `aarch64-apple-darwin` into `desktop/src-tauri/resources/` via
   `desktop/scripts/vendor-ffmpeg.sh` (E5.S7). The script fetches a static
   build and **fails the build** if it is `--enable-nonfree`
   (non-redistributable) or is missing a capability the engine uses
   (`h264_videotoolbox`, `aac`, `drawtext`, `zoompan`, `sidechaincompress`,
   `overlay`). A **GPL** build is allowed — see "FFmpeg vendoring & license
   posture" below for why. These resources ship inside
   `Marquee.app/Contents/Resources/` and are **not** committed to the repo
   (`.gitignore`d).
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

**Source (pinned).** Martin Riedl's static macOS/arm64 build server
(`https://ffmpeg.martin-riedl.de`). Chosen because it publishes static
`aarch64-apple-darwin` builds of both `ffmpeg` and `ffprobe` behind a stable,
versioned download API. The shipped artifact is **FFmpeg 8.1.1** (build id
`1778761665_8.1.1`), a **GPL** static build (its `configuration:` line shows
`--enable-gpl --enable-libfreetype --enable-libx264`); this server publishes no
LGPL variant. The exact URLs + checksums are pinned via the four repo variables
below (overridable with `FFMPEG_VENDOR_URL` / `FFPROBE_VENDOR_URL` + `*_SHA256`):

| Artifact | URL | sha256 |
| --- | --- | --- |
| `ffmpeg.zip` | `…/download/macos/arm64/1778761665_8.1.1/ffmpeg.zip` | `a05b1a47bb3ac89a95a55eec713f8bbb347051bb07015f3b7d08fb62ed81a21e` |
| `ffprobe.zip` | `…/download/macos/arm64/1778761665_8.1.1/ffprobe.zip` | `135e70d2518beeb568183952dbc4bdeca1628dd49a7376d57e6b27dbc57d209f` |

**Supply-chain: pinned checksums are REQUIRED in CI.** The script downloads a
binary and then *executes* it (to run the license/feature guards), and the
release runner holds the Apple signing secrets — so executing an unverified
binary from a third-party host would be a supply-chain risk. GitHub Actions sets
`CI=true`, and the script **refuses to run** unless both `FFMPEG_VENDOR_SHA256`
and `FFPROBE_VENDOR_SHA256` are set. Before the first real run, set **four
repository variables** (Settings → Secrets and variables → Actions → Variables),
ideally pointing at a *versioned* (not `latest`) URL so releases are reproducible:

| Repo variable | Value |
| --- | --- |
| `FFMPEG_VENDOR_URL` | Pinned, versioned `ffmpeg.zip` URL |
| `FFPROBE_VENDOR_URL` | Pinned, versioned `ffprobe.zip` URL |
| `FFMPEG_VENDOR_SHA256` | `shasum -a 256 ffmpeg.zip` of that build |
| `FFPROBE_VENDOR_SHA256` | `shasum -a 256 ffprobe.zip` of that build |

To compute the checksums once: download the chosen `.zip`s locally, run
`shasum -a 256`, and paste the digests into the variables. Local/dev runs may
skip pinning (`REQUIRE_PINNED_SHA256=0`), which only emits a warning.

> These four variables are **already set** to the pinned FFmpeg 8.1.1 build in
> the "Source (pinned)" table above (versioned URLs + verified `sha256`s).
> Update them in lockstep whenever the bundled FFmpeg version changes.

**License posture — GPLv2 allowed (arm's-length subprocess).** The shipped
FFmpeg is licensed under the **GNU General Public License v2** (it's a GPL
build). That is fine for Marquee because Marquee invokes FFmpeg purely as a
**separate child process** — it shells out to `ffmpeg`/`ffprobe` as standalone
executables (`src/slideshow_gen/ffmpeg.py`, `media.py`) and **never links
`libav*`** into its own code. Under the well-established GPL aggregation / "mere
aggregation and exec" principle, the GPL's copyleft reaches only the ffmpeg
binary itself, not Marquee's own (separately-licensed) code. Two further facts
keep this clean:

- **Free, direct-download distribution.** Marquee is distributed as a free,
  direct-download, notarized `.app` — **not** through the Mac App Store. (GPL is
  incompatible with the App Store's terms; sidestepping the App Store is what
  makes shipping a GPL binary viable here.)
- **We convey GPL compliance.** Because we redistribute a GPLv2 binary, the app
  ships the full **GPLv2 license text** plus an attribution statement and a
  **written offer for the corresponding source** (see "GPL compliance: what
  ships with the app" below).

What the vendor script still refuses: only `--enable-nonfree`, which produces a
**genuinely non-redistributable** binary (e.g. nonfree-licensed codecs) we'd
have no right to ship. It also still fails if the build is missing any
capability the engine actually uses (`h264_videotoolbox`, `aac`, `drawtext`,
`zoompan`, `sidechaincompress`, `overlay`). The exact `configuration:` line and
`-buildconf` are printed into the CI log for an auditable record of the license
+ feature set of the precise binary shipped (and to anchor the GPLv2 obligation
to that exact build).

**Documented future option — a self-built LGPL build.** Marquee encodes with
`h264_videotoolbox` (Apple's hardware H.264 encoder), **not** libx264, and uses
no GPL-only FFmpeg feature. So the GPL bits in the Riedl build
(`--enable-libx264`, `--enable-gpl`) are not actually exercised by Marquee — a
move to a self-built `--disable-gpl --disable-nonfree` **LGPL** build remains
fully open as a future option (no x264 needed):

```
./configure --disable-gpl --disable-nonfree \
  --enable-videotoolbox --enable-audiotoolbox \
  --enable-libfreetype …
```

That would drop the GPLv2 obligation entirely, at the cost of building + signing
FFmpeg from source ourselves rather than fetching a prebuilt artifact. Until/
unless that's worth doing, the pinned GPL build above is the shipped posture.

### GPL compliance: what ships with the app

Because Marquee redistributes a GPLv2 FFmpeg binary, it conveys the GPLv2
obligations with the app. Three artifacts are committed and wired into the Tauri
bundle (`bundle.resources` in `tauri.conf.json`), so they land inside
`Marquee.app/Contents/Resources/THIRD-PARTY/`:

| Shipped file (in repo) | In the bundle | Purpose |
| --- | --- | --- |
| `desktop/src-tauri/resources/THIRD-PARTY/FFmpeg-COPYING.GPLv2.txt` | `Contents/Resources/THIRD-PARTY/FFmpeg-COPYING.GPLv2.txt` | The full, verbatim GNU GPL v2 license text. |
| `desktop/src-tauri/resources/THIRD-PARTY/THIRD-PARTY-LICENSES.txt` | `Contents/Resources/THIRD-PARTY/THIRD-PARTY-LICENSES.txt` | Plain-text attribution + written offer for source, shipped inside the app. |
| `THIRD-PARTY-LICENSES.md` (repo root) | — (repo-facing) | Same attribution + written offer, human-readable in the repo. |

The attribution statement and the **written offer for the corresponding
source** (FFmpeg 8.1.1 from <https://ffmpeg.org/releases/>, and on request) live
in those files; keep them in sync with the pinned build above whenever the
FFmpeg version changes. There is no in-app About panel today, so the bundled
text files are the user-facing compliance surface; if/when an About/credits view
is added to the Tauri frontend, it should link to or display
`THIRD-PARTY/THIRD-PARTY-LICENSES.txt`.

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
