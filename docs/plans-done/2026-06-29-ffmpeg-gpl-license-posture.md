---
title: FFmpeg GPL license posture — relax vendor guard + GPLv3 attribution/source-offer
status: "Done"
completed: 2026-06-29
linked_pr: "https://github.com/adamthede/slideshow-gen/pull/15"
impl-model: opus
---

# FFmpeg GPL license posture + attribution

Follow-on to E5.S7 (FFmpeg bundling, PR #14, Done). The pinned static FFmpeg
source — Martin Riedl's macOS/arm64 server — only publishes a **GPL** build
(`--enable-gpl --enable-libfreetype --enable-libx264`); it offers no LGPL
variant. The current `vendor-ffmpeg.sh` license guard fails closed on
`--enable-gpl`, so it would reject this build and break CI.

## Decision (Adam)

Switch the project's license posture from "LGPL-only" to "**GPL allowed**":
FFmpeg is invoked **arm's-length as a separate child process** (subprocess via
`src/slideshow_gen/ffmpeg.py` / `media.py`; `libav*` is never linked into
Marquee's code), so its copyleft reaches only the ffmpeg binary, not Marquee's
own code — the well-established GPL aggregation/exec principle. Distribution is
free, direct-download, notarized `.app` (NOT the Mac App Store, where GPL would
be incompatible). `--enable-nonfree` stays **blocked** (genuinely
non-redistributable).

Pinned artifact: FFmpeg **8.1.1**, build id `1778761665_8.1.1`.

Documented future option: Marquee encodes with `h264_videotoolbox` (Apple HW),
NOT libx264, and uses no GPL-only feature — so a future move to a self-built
`--disable-gpl` LGPL build (no x264 needed) remains open.

## Scope

1. **Relax the license guard** in `desktop/scripts/vendor-ffmpeg.sh`: drop the
   `--enable-gpl` fail-closed block; KEEP the `--enable-nonfree` block. Rewrite
   the header LICENSE POSTURE comment + inline guard comments to the new
   posture (GPL allowed for arm's-length subprocess distribution; nonfree still
   refused; cite the exec/aggregation rationale).
2. **Update `docs/release-pipeline.md`** FFmpeg license-posture section: source
   = Martin Riedl GPL static build, FFmpeg 8.1.1, license = GPLv3, why
   GPL-via-subprocess is acceptable for this free direct-download (non-App-
   Store) product, plus the documented future self-built LGPL option.
3. **GPL attribution pass** (Marquee now distributes a GPLv3 binary):
   - Ship the **full GPLv3 license text** inside `Marquee.app` (Tauri bundle
     resource).
   - Ship a third-party attribution surface (`THIRD-PARTY-LICENSES.md` at repo
     root + a shipped copy in the bundle) with the required FFmpeg attribution
     statement.
   - Include a **written offer for corresponding source** (FFmpeg 8.1.1 from
     ffmpeg.org/releases/, and on request).

## Out of scope (ops, not in this PR)

- The four repo VARIABLES (`FFMPEG_VENDOR_URL`, `FFPROBE_VENDOR_URL`,
  `FFMPEG_VENDOR_SHA256`, `FFPROBE_VENDOR_SHA256`) — set via `gh variable set`,
  repo config, not a file change.

## Success criteria

- Running `vendor-ffmpeg.sh` against the pinned GPL build (CI-style, with the
  four env vars) prints "License guard passed" and "Feature guards passed" and
  ends OK — proving the GPL build now PASSES the relaxed guard.
- The full test suite passes (no regressions vs. baseline).
- GPLv3 text + attribution + written source offer ship inside `Marquee.app`
  (wired into `tauri.conf.json` `bundle.resources`).
