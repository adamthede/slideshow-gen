"""Resolution-order tests for the ffmpeg/ffprobe binary resolver (E5.S7).

Locks the contract the Marquee desktop shell relies on:
  - When the bundled-binary env var is set to a real file, that path wins.
  - When it is unset, the bare name is returned so subprocess uses ``PATH``
    (the standalone CLI's unchanged behavior).
  - A set-but-missing override falls back to ``PATH`` rather than hard-failing.
"""

import pytest

from slideshow_gen.ffbin import (
    FFMPEG_ENV_VAR,
    FFPROBE_ENV_VAR,
    ffmpeg_binary,
    ffprobe_binary,
)


@pytest.fixture
def bundled_ffmpeg(tmp_path):
    """A real, executable stand-in for a bundled ffmpeg binary."""
    binary = tmp_path / "ffmpeg"
    binary.write_text("#!/bin/sh\n")
    binary.chmod(0o755)
    return binary


@pytest.fixture
def bundled_ffprobe(tmp_path):
    binary = tmp_path / "ffprobe"
    binary.write_text("#!/bin/sh\n")
    binary.chmod(0o755)
    return binary


def test_ffmpeg_env_override_wins_when_file_exists(monkeypatch, bundled_ffmpeg):
    monkeypatch.setenv(FFMPEG_ENV_VAR, str(bundled_ffmpeg))
    assert ffmpeg_binary() == str(bundled_ffmpeg)


def test_ffprobe_env_override_wins_when_file_exists(monkeypatch, bundled_ffprobe):
    monkeypatch.setenv(FFPROBE_ENV_VAR, str(bundled_ffprobe))
    assert ffprobe_binary() == str(bundled_ffprobe)


def test_ffmpeg_falls_back_to_path_when_unset(monkeypatch):
    monkeypatch.delenv(FFMPEG_ENV_VAR, raising=False)
    assert ffmpeg_binary() == "ffmpeg"


def test_ffprobe_falls_back_to_path_when_unset(monkeypatch):
    monkeypatch.delenv(FFPROBE_ENV_VAR, raising=False)
    assert ffprobe_binary() == "ffprobe"


def test_ffmpeg_falls_back_to_path_when_override_missing(monkeypatch, tmp_path):
    # A stale / mistyped override must not brick the install.
    monkeypatch.setenv(FFMPEG_ENV_VAR, str(tmp_path / "does-not-exist"))
    assert ffmpeg_binary() == "ffmpeg"


def test_ffmpeg_falls_back_to_path_when_override_empty(monkeypatch):
    monkeypatch.setenv(FFMPEG_ENV_VAR, "")
    assert ffmpeg_binary() == "ffmpeg"


def test_tilde_in_override_is_expanded(monkeypatch, bundled_ffmpeg):
    # Sanity: ``~`` expansion shouldn't defeat the existence check.
    monkeypatch.setenv(FFMPEG_ENV_VAR, str(bundled_ffmpeg))
    resolved = ffmpeg_binary()
    assert resolved == str(bundled_ffmpeg)
    assert "~" not in resolved
