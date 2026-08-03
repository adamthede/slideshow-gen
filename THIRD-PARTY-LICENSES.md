# Third-Party Licenses — Marquee

Marquee (by Thede Technologies, LLC) distributes third-party software with the
app, and this repository's git history additionally contains a third-party
development framework. This document records that software and the license
obligations conveyed with it.

Marquee's own code is licensed under the MIT License - see [`LICENSE`](LICENSE)
at the repository root. That license covers only the code authored by Thede
Technologies, LLC. It does **not** apply to, and makes no claim over, any
third-party component listed below; each of those remains under its own license,
held by its own copyright holder.

Two separate distribution channels carry obligations, and they do not overlap:

| Channel | Third-party component | Where the notice lives |
|---|---|---|
| `Marquee.app` / DMG | Bundled FFmpeg binary | `Contents/Resources/THIRD-PARTY/` inside the app bundle, wired in via `bundle.resources` in `desktop/src-tauri/tauri.conf.json` |
| This repository's git history | BMAD METHOD framework, vendored until 2026-08-03 | The BMAD section below, which reproduces the license in full |

The BMAD framework was **never** shipped in the app bundle - it is
development-time tooling, and as of 2026-08-03 it is no longer in the tracked
tree either. The FFmpeg binary is **not** stored in this repository - it is
downloaded and vendored at build time by `desktop/scripts/vendor-ffmpeg.sh`.

Only one component therefore reaches anyone who installs Marquee: FFmpeg. The
BMAD section is retained for the historical copies that remain reachable in git
history.

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
such a request, contact **adam@thedetech.com**.

## BMAD METHOD

This repository vendored the BMAD METHOD framework
(<https://github.com/bmad-code-org/BMAD-METHOD>) as development-time tooling -
agent scaffolding used while building Marquee, never part of the Marquee
application and never shipped in the app bundle or the DMG.

**Removed from the tracked tree on 2026-08-03.** The `_bmad/` and
`.claude/skills/` trees were untracked (`git rm --cached`) and added to
`.gitignore`: dev tooling does not belong in the product repository. They
remain on the developer's own disk, and - because the removal does not rewrite
history - the vendored copies stay reachable in this repository's git history.
Anyone cloning the repo still receives those objects, so the attribution below
is retained rather than deleted. The two in-tree `LICENSE` files
(`_bmad/LICENSE` and `.claude/skills/LICENSE`) went untracked along with their
trees, which is why the full license text is reproduced inline here.

Trees and installed versions as vendored (from `_bmad/_config/manifest.yaml`):

| Tree | Module | Version | Upstream |
|---|---|---|---|
| `_bmad/core` | core | 6.2.2 | built-in to BMAD METHOD |
| `_bmad/bmm` | bmm | 6.2.2 | built-in to BMAD METHOD |
| `_bmad/bmb` | bmb | 1.1.0 | [bmad-builder](https://github.com/bmad-code-org/bmad-builder) |
| `_bmad/tea` | tea | 1.7.2 | [bmad-method-test-architecture-enterprise](https://github.com/bmad-code-org/bmad-method-test-architecture-enterprise) |
| `_bmad/wds` | wds | 0.3.1 | [bmad-method-wds-expansion](https://github.com/bmad-code-org/bmad-method-wds-expansion) |
| `.claude/skills/` | 69 generated skill directories (57 `bmad-*`, 12 `wds-*`) | generated from the modules above | emitted by the BMAD installer |

BMAD METHOD is licensed under the MIT License, Copyright (c) 2025 BMad Code,
LLC, with an accompanying trademark notice. The license text as published
upstream is reproduced verbatim below, satisfying the requirement that the
copyright notice and permission notice be included in all copies or substantial
portions of the software. The upstream `CONTRIBUTORS.md` and `TRADEMARK.md`
files referenced within it were not vendored; both are available in the upstream
repository.

```
MIT License

Copyright (c) 2025 BMad Code, LLC

This project incorporates contributions from the open source community.
See [CONTRIBUTORS.md](CONTRIBUTORS.md) for contributor attribution.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

TRADEMARK NOTICE:
BMad™, BMad Method™, and BMad Core™ are trademarks of BMad Code, LLC, covering all
casings and variations (including BMAD, bmad, BMadMethod, BMAD-METHOD, etc.). The use of
these trademarks in this software does not grant any rights to use the trademarks
for any other purpose. See [TRADEMARK.md](TRADEMARK.md) for detailed guidelines.
```

**Trademark.** BMad™, BMad Method™, and BMad Core™ are trademarks of BMad Code,
LLC, covering all casings and variations. The `bmad-*` directory names that
appear in this repository's history are installer-generated paths that identify
the upstream framework; their presence does not imply endorsement of Marquee by
BMad Code, LLC, and no rights to the trademarks are claimed.
