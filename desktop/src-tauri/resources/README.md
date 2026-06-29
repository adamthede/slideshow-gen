# Bundled binary resources

This directory holds third-party executables that ship **inside**
`Marquee.app` as Tauri bundle resources (see `bundle.resources` in
`../tauri.conf.json`). They land in `Marquee.app/Contents/Resources/`.

## `ffmpeg` / `ffprobe` (vendored, never committed)

A license-clean **static** FFmpeg + ffprobe for `aarch64-apple-darwin`,
fetched and signed at build time — **not** committed to the repo (the
binaries are tens of MB and are `.gitignore`d).

- Local: `desktop/scripts/vendor-ffmpeg.sh desktop/src-tauri/resources`
- CI: the "Vendor + sign FFmpeg" step in `.github/workflows/release.yml`

The vendor script enforces the license/feature posture (fails if the build
is GPL/nonfree or is missing `h264_videotoolbox` / `drawtext`). Source,
version, and license are documented in `docs/release-pipeline.md`.

`npm run tauri build` requires these files to exist; run the vendor script
first. `npm run tauri dev` does not bundle resources, so the engine falls
back to FFmpeg on `PATH`.
