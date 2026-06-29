"""Resolve the ``ffmpeg`` / ``ffprobe`` executables.

Resolution order (per Epic 5.S7):

1. An explicit ``FFMPEG_BINARY`` / ``FFPROBE_BINARY`` environment variable
   pointing at a real file. The Marquee desktop shell sets these to the
   signed, bundled binaries it ships inside ``Marquee.app`` so a clean Mac
   with no FFmpeg on ``PATH`` can still render.
2. Otherwise the bare name (``ffmpeg`` / ``ffprobe``), which ``subprocess``
   looks up on ``PATH`` — the standalone CLI's behavior, unchanged.

Kept dependency-free (only ``os`` + ``pathlib``) on purpose: ``ffmpeg.py``,
``pipeline.py``, and ``media.py`` all import it, and ``ffmpeg.py`` already
sits in an import chain (``ffmpeg -> discovery -> media``) that a resolver
living in ``ffmpeg.py`` would turn into a cycle.

A set env var that does **not** point at a real file is treated as
"not configured" and we fall back to ``PATH`` rather than hard-failing, so a
stale or mistyped override can never brick an otherwise-working install.
"""

import os
from pathlib import Path

FFMPEG_ENV_VAR = "FFMPEG_BINARY"
FFPROBE_ENV_VAR = "FFPROBE_BINARY"


def _resolve(env_var: str, default: str) -> str:
    override = os.environ.get(env_var)
    if override:
        candidate = Path(override).expanduser()
        if candidate.is_file():
            return str(candidate)
    return default


def ffmpeg_binary() -> str:
    """Path to the ffmpeg executable to invoke (env override → ``PATH``)."""
    return _resolve(FFMPEG_ENV_VAR, "ffmpeg")


def ffprobe_binary() -> str:
    """Path to the ffprobe executable to invoke (env override → ``PATH``)."""
    return _resolve(FFPROBE_ENV_VAR, "ffprobe")
