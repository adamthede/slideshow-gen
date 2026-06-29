# Bundled binary resources

This directory holds third-party executables that ship **inside**
`Marquee.app` as Tauri bundle resources (see `bundle.resources` in
`../tauri.conf.json`). They land in `Marquee.app/Contents/Resources/`.

## `ffmpeg` / `ffprobe` (vendored, never committed)

A **static** FFmpeg + ffprobe for `aarch64-apple-darwin` (currently a GPLv2
build — see below), fetched and signed at build time — **not** committed to the
repo (the binaries are tens of MB and are `.gitignore`d).

- Local: `desktop/scripts/vendor-ffmpeg.sh desktop/src-tauri/resources`
- CI: the "Vendor static FFmpeg" step in `.github/workflows/release.yml`

The vendor script enforces the license/feature posture: a GPL build is allowed
(FFmpeg is invoked arm's-length as a separate child process), but it fails if the
build is `--enable-nonfree` (non-redistributable) or is missing
`h264_videotoolbox` / `drawtext`. Source, version, and license — plus the GPLv2
text + attribution + written source offer shipped under `THIRD-PARTY/` — are
documented in `docs/release-pipeline.md`.

## `THIRD-PARTY/` (committed, GPL compliance)

Because the bundled FFmpeg is GPLv2, the app ships its license text +
attribution + a written offer for the corresponding source. These files are
committed and wired into `bundle.resources`, so they land in
`Marquee.app/Contents/Resources/THIRD-PARTY/`:

- `THIRD-PARTY/FFmpeg-COPYING.GPLv2.txt` — full GNU GPL v2 text.
- `THIRD-PARTY/THIRD-PARTY-LICENSES.txt` — attribution + written source offer.

See also `THIRD-PARTY-LICENSES.md` at the repo root (repo-facing copy).

`npm run tauri build` requires these files to exist; run the vendor script
first. `npm run tauri dev` does not bundle resources, so the engine falls
back to FFmpeg on `PATH`.
