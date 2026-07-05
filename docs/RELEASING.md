# Releasing Marquee

The 5-minute runbook for cutting a public Marquee release. The heavy lifting —
building, signing, notarizing, stapling, and packaging the DMG — is fully
automated by the [Release workflow](../.github/workflows/release.yml). Your job
is to push a tag and publish the draft it produces.

For the mechanics of *what* the workflow does and *why*, see
[docs/release-pipeline.md](release-pipeline.md). This file is just the checklist.

## Prerequisites (one-time, already done)

- Apple **secrets** set in GitHub (Settings → Secrets and variables → Actions):
  `APPLE_CERTIFICATE_P12_BASE64`, `APPLE_CERTIFICATE_PASSWORD`, `APPLE_ID`,
  `APPLE_APP_SPECIFIC_PASSWORD`, `APPLE_TEAM_ID`.
- FFmpeg vendoring **repo variables** set: `FFMPEG_VENDOR_URL`,
  `FFPROBE_VENDOR_URL`, `FFMPEG_VENDOR_SHA256`, `FFPROBE_VENDOR_SHA256`.
- The `.p12` is backed up in 1Password.

If any of those are missing the workflow fails fast with a clear message — you
won't ship a broken build.

## The 5 steps

### 1. Bump the version (if it changed)

The tag you push should match the app version. Set both to the same value:

- `desktop/src-tauri/tauri.conf.json` → `"version"`
- `desktop/package.json` → `"version"`

For the first public release, set both to `1.0.0`. Commit on `main`:

```bash
git commit -am "chore(release): bump Marquee to 1.0.0"
git push origin main
```

> A version bump is optional for re-cut/hotfix tags where the version is already
> correct — but the tag and the config version should never disagree, or the
> DMG filename (`Marquee_<version>_aarch64.dmg`) won't match the release name.

### 2. Push the tag

```bash
git tag v1.0.0
git push origin v1.0.0
```

The tag push triggers the Release workflow. (Tags must match `v*.*.*`.)

### 3. Watch the run

<https://github.com/adamthede/slideshow-gen/actions> → the newest
"Release (sign + notarize)" run. It takes ~6–10 minutes and does, in order:
freeze the Python sidecar → vendor + sign FFmpeg → build + sign the `.app` →
deep-verify signing → notarize + staple the `.app` → bundle + sign the DMG from
the stapled app → notarize + staple the DMG → verify Gatekeeper acceptance →
attach both to a **draft** release.

If it goes green, you have a signed, notarized, stapled build. If it fails,
the failing step names what went wrong; nothing is published on failure.

### 4. Check the draft release

<https://github.com/adamthede/slideshow-gen/releases> → the draft for `v1.0.0`.
It has two attachments:

- **`Marquee_1.0.0_aarch64.dmg`** — the primary user download (drag-to-Applications).
- **`Marquee-stapled.zip`** — the raw stapled `.app`, for anyone who prefers it.

Optionally smoke-test before publishing: download the DMG on a **clean Mac**
(ideally one with no Homebrew FFmpeg), drag Marquee to `/Applications`, open it
(Gatekeeper should accept with no warning), and run a small render.

### 5. Write the notes and publish

- Paste the relevant section of [`CHANGELOG.md`](../CHANGELOG.md) into the
  release body.
- Uncheck "This is a pre-release" if set.
- Click **Publish release**.

Done. The release is public and the DMG is downloadable.

## After publishing

- Move the shipped plan files to `docs/plans-done/` and flip their frontmatter
  (`/shipped <PR_URL>` handles this for PR-backed plans).
- The **thedetech product page** (download link + screenshots) is a separate
  follow-up step, done *after* the release exists so it can link to a real DMG.

## If notarization fails

The workflow fails at the `notarytool submit --wait` step with Apple's reason.
Most common: a nested binary is unsigned or missing the hardened runtime (the
deep-verify gate should catch this earlier), or an entitlement Apple names is
missing. See [docs/release-pipeline.md](release-pipeline.md) →
"Hardened Runtime & Entitlements" for the action path — add **only** what the
notary log explicitly names, never speculatively.

## Not in this release

- **Auto-updater (E5.S5).** No in-app update check yet — updates ship as fresh
  downloads. This is a deliberate post-v1.0 deferral.
