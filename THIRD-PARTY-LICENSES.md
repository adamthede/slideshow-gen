# Third-Party Licenses — Marquee

Marquee (by Thede Technologies, LLC) distributes third-party software with the
app. This document records that software and the license obligations Marquee
conveys with it. A plain-text copy of this attribution, plus the full license
text, also ships **inside** `Marquee.app` at
`Contents/Resources/THIRD-PARTY/` (wired in via `bundle.resources` in
`desktop/src-tauri/tauri.conf.json`).

## FFmpeg

Marquee uses FFmpeg (<https://ffmpeg.org>), licensed under the GNU General
Public License v3. Bundled build: FFmpeg 8.1.1, static macOS/arm64, from
ffmpeg.martin-riedl.de — built with `--enable-gpl --enable-version3`, which
makes the effective license GPL v3. The exact configure flags are reported by
`ffmpeg -version`.

The full text of the GNU General Public License, version 3, is included as
[`desktop/src-tauri/resources/THIRD-PARTY/FFmpeg-COPYING.GPLv3.txt`](desktop/src-tauri/resources/THIRD-PARTY/FFmpeg-COPYING.GPLv3.txt)
and ships in the app at `Contents/Resources/THIRD-PARTY/FFmpeg-COPYING.GPLv3.txt`.

Marquee invokes FFmpeg only as a **separate command-line program** (a child
process) via the engine (`src/slideshow_gen/ffmpeg.py`, `media.py`); it does
**not** link the FFmpeg libraries (`libav*`) into its own code. Under the GPL's
aggregation / "mere exec" principle, the GPL's copyleft therefore reaches only
the FFmpeg binary, not Marquee's own (separately-licensed) code. See
[`docs/release-pipeline.md`](docs/release-pipeline.md) ("FFmpeg vendoring &
license posture") for the full rationale.

### Written offer for corresponding source

The complete corresponding source code for the bundled FFmpeg build is the
FFmpeg 8.1.1 source release, available from:

- <https://ffmpeg.org/releases/> (file: `ffmpeg-8.1.1.tar.xz`)

This is the upstream source from which the distributed static macOS/arm64 binary
is built.

In addition, for a period of at least three years, Thede Technologies, LLC will
provide, on request and for no more than the cost of physically performing
source distribution, a complete machine-readable copy of the corresponding
source code for the version of FFmpeg distributed with a given copy of Marquee,
matching the exact build shipped (as reported by `ffmpeg -version`). To make
such a request, contact **athede@gmail.com**.
