"""Lock the sidecar IPC contract.

Documented in docs/sidecar-protocol.md. Changes to event names, required
fields, or version should require updating both this test and the doc.
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _make_assets(d: Path, count: int = 3) -> None:
    colors = ["red", "green", "blue", "yellow", "purple", "orange", "cyan", "magenta"]
    for i in range(count):
        Image.new("RGB", (1200, 900), color=colors[i % len(colors)]).save(
            d / f"2026-05-23 12-{i:02d}-00 - test.jpg", quality=85
        )


def _run_ipc(args: list[str], cwd: Path) -> tuple[int, list[dict], str]:
    result = subprocess.run(
        ["slideshow-gen", "render", "--ipc", *args],
        capture_output=True, text=True, timeout=180, cwd=cwd,
    )
    events = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        events.append(json.loads(line))  # raises on malformed JSON
    return result.returncode, events, result.stderr


def test_ipc_estimate_only_lifecycle(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _make_assets(src)
    out = tmp_path / "out.mp4"

    rc, events, _ = _run_ipc(
        [
            "--dir", str(src),
            "-o", str(out),
            "--slide-duration", "1",
            "--fade-duration", "0.2",
            "--fps", "24",
            "--workers", "1",
            "--estimate-only",
        ],
        cwd=tmp_path,
    )

    assert rc == 0
    types = [e["type"] for e in events]
    # Lifecycle ordering, ignoring throttled `progress` ticks and the
    # deduplication phase_started/phase_complete pair that sits between
    # discovery and discovery_complete.
    def idx(t: str) -> int:
        return next(i for i, e in enumerate(events) if e["type"] == t)
    assert types[0] == "started"
    # First phase_started is always discovery.
    first_phase = next(e for e in events if e["type"] == "phase_started")
    assert first_phase["phase"] == "discovery"
    # Deduplication phase fires between discovery and discovery_complete.
    dedup_started = [e for e in events if e["type"] == "phase_started" and e.get("phase") == "deduplication"]
    dedup_complete = [e for e in events if e["type"] == "phase_complete" and e.get("phase") == "deduplication"]
    assert len(dedup_started) == 1 and len(dedup_complete) == 1
    assert idx("phase_started") < idx("discovery_complete") < idx("estimate") < idx("info")
    # Any discovery progress events must sit between phase_started and
    # discovery_complete, reference the discovery phase, and have monotonic
    # `done` values.
    phase_started_idx = next(i for i, e in enumerate(events) if e["type"] == "phase_started")
    discovery_complete_idx = next(
        i for i, e in enumerate(events) if e["type"] == "discovery_complete"
    )
    last_done = 0
    for i, e in enumerate(events):
        if e["type"] != "progress":
            continue
        assert phase_started_idx < i < discovery_complete_idx, (
            f"progress at idx {i} not between phase_started ({phase_started_idx}) "
            f"and discovery_complete ({discovery_complete_idx})"
        )
        assert e["phase"] == "discovery"
        assert 0 < e["done"] <= e["total"]
        assert e["done"] >= last_done, "discovery progress.done must be monotonic"
        last_done = e["done"]

    # Required common fields on every event
    for e in events:
        assert e["v"] == 1
        assert isinstance(e["t"], (int, float))
        assert isinstance(e["type"], str)

    # discovery_complete shape — counts plus the metadata fields documented
    # in docs/sidecar-protocol.md.
    dc = next(e for e in events if e["type"] == "discovery_complete")
    assert dc["images"] == 3
    assert dc["videos"] == 0
    # date_range present, date-only (no time component) per protocol doc.
    # Fixture filenames are "2026-05-23 12-0{i}-00 - test.jpg" → all same date.
    assert "date_range" in dc
    assert dc["date_range"] == {"earliest": "2026-05-23", "latest": "2026-05-23"}
    # gps_coverage_percent always present after items found; PIL-generated
    # fixtures have no EXIF GPS, so 0.0 is correct.
    assert dc["gps_coverage_percent"] == 0.0
    # duplicates_detected always present after items found; distinct synthetic
    # images → 0.
    assert dc["duplicates_detected"] == 0
    # date_histogram present when date_range is — month-bucketed counts
    # covering every month from earliest to latest (zero-filled).
    assert "date_histogram" in dc
    assert dc["date_histogram"] == [{"month": "2026-05", "count": 3}]

    # estimate shape
    est = next(e for e in events if e["type"] == "estimate")
    for field in ("duration_s", "size_bytes", "image_duration_s", "video_duration_s"):
        assert field in est, f"estimate missing {field}"
    assert est["duration_s"] > 0
    assert est["size_bytes"] > 0

    # No complete on estimate-only
    assert "complete" not in types


def test_ipc_full_render_lifecycle(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _make_assets(src)
    out = tmp_path / "out.mp4"

    rc, events, _ = _run_ipc(
        [
            "--dir", str(src),
            "-o", str(out),
            "--slide-duration", "1",
            "--fade-duration", "0.2",
            "--fps", "24",
            "--batch-size", "2",
            "--workers", "1",
        ],
        cwd=tmp_path,
    )

    assert rc == 0
    types = [e["type"] for e in events]

    # Lifecycle: started first, complete last
    assert types[0] == "started"
    assert types[-1] == "complete"

    # Pre-render events present in order
    assert types.index("phase_started") < types.index("discovery_complete")
    assert types.index("discovery_complete") < types.index("estimate")

    # At least one image-phase progress event
    img_progress = [e for e in events if e["type"] == "progress" and e["phase"] == "images"]
    assert len(img_progress) >= 1
    # Progress monotonic non-decreasing
    dones = [e["done"] for e in img_progress]
    assert dones == sorted(dones)

    # complete event lists the output
    done = events[-1]
    assert done["type"] == "complete"
    assert len(done["outputs"]) == 1
    assert done["outputs"][0]["path"] == str(out)
    assert done["outputs"][0]["size_bytes"] > 0
    assert out.exists()


def test_ipc_per_item_failure_completes_with_skip(tmp_path):
    """A deliberately bad input file is skipped; render still completes; an
    `item_failed` event fires and `complete.items_skipped` reflects the count.

    Locks the S4 contract: per-item failures are non-fatal and surface
    passively in IPC. The render proceeds with the remaining valid items.
    """
    src = tmp_path / "src"
    src.mkdir()
    _make_assets(src, count=3)
    # Corrupt fixture: a .heic by extension (so discovery picks it up as an
    # image), but the bytes are not a valid HEIC container. HEIC pre-conversion
    # fails fast in PIL with a clean exception — that exception path is exactly
    # the per-item failure we want to assert on. (A truncated/garbage .jpg
    # would risk FFmpeg hanging on `-loop 1` waiting for image bytes; the HEIC
    # route fails before FFmpeg is invoked at all.)
    bad = src / "2026-05-23 12-99-00 - corrupt.heic"
    bad.write_bytes(b"this is not a heic container" * 32)
    out = tmp_path / "out.mp4"

    rc, events, _ = _run_ipc(
        [
            "--dir", str(src),
            "-o", str(out),
            "--slide-duration", "1",
            "--fade-duration", "0.2",
            "--fps", "24",
            "--batch-size", "2",
            "--workers", "1",
        ],
        cwd=tmp_path,
    )

    # The render completes despite the bad file.
    assert rc == 0, f"render should complete (rc=0) despite bad input, got {rc}"
    types = [e["type"] for e in events]
    assert types[-1] == "complete", f"expected complete last, got {types[-5:]}"

    # At least one item_failed event with the documented shape.
    failures = [e for e in events if e["type"] == "item_failed"]
    assert failures, "expected at least one item_failed event for the corrupt input"
    f = failures[0]
    for field in ("v", "t", "type", "phase", "path", "reason"):
        assert field in f, f"item_failed missing {field}: {f}"
    assert f["v"] == 1
    # The phase should be one of the documented per-item phases (currently
    # only "images" emits item_failed).
    assert f["phase"] == "images"
    assert isinstance(f["path"], str) and f["path"]
    assert isinstance(f["reason"], str) and f["reason"]
    # `detail` is optional but, when present, should be a string.
    if "detail" in f:
        assert isinstance(f["detail"], str)

    # The complete event reports the skip count, and it matches the number of
    # item_failed events emitted (canonical summary vs. per-item stream).
    done = events[-1]
    assert "items_skipped" in done, "complete must carry items_skipped (S4 contract)"
    assert done["items_skipped"] >= 1
    assert done["items_skipped"] == len(failures), (
        f"items_skipped ({done['items_skipped']}) should equal item_failed count "
        f"({len(failures)})"
    )

    # The output file still exists — the render produced a valid slideshow
    # from the remaining good inputs.
    assert out.exists(), "render should produce output even when items are skipped"
    assert done["outputs"][0]["size_bytes"] > 0


def _list_ffmpeg_pids() -> set[int]:
    """PIDs of currently-running ffmpeg processes (for orphan detection)."""
    out = subprocess.run(["pgrep", "-x", "ffmpeg"], capture_output=True, text=True)
    return {int(p) for p in out.stdout.split() if p.strip()}


def test_ipc_cancel_cleans_up_and_emits_cancelled(tmp_path):
    """SIGTERM mid-render → `cancelled` event, temp removed, no `complete`,
    no output file, no orphaned ffmpeg children, non-zero exit.

    Exercises the engine teardown (setpgrp + killpg + temp cleanup) against the
    installed CLI entry point. The PyInstaller-bootloader signal *forwarding* is
    verified separately in manual QA against the frozen sidecar (story 4.3)."""
    src = tmp_path / "src"
    src.mkdir()
    # Enough images (Ken Burns, not --static) that phase 1 runs long enough to
    # interrupt deterministically.
    _make_assets(src, count=8)
    out = tmp_path / "out.mp4"
    temp_root = tmp_path / "temp"
    temp_root.mkdir()

    ffmpeg_before = _list_ffmpeg_pids()

    proc = subprocess.Popen(
        [
            "slideshow-gen", "render", "--ipc",
            "--dir", str(src),
            "-o", str(out),
            "--slide-duration", "2",
            "--fade-duration", "0.5",
            "--fps", "24",
            "--workers", "2",
            "--temp-dir", str(temp_root),
        ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )

    # Read events until phase 1 ("images") is underway, so the temp dir exists
    # and ffmpeg children are spawned when we signal.
    saw_images_phase = False
    deadline = time.time() + 60
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        if evt.get("type") == "phase_started" and evt.get("phase") == "images":
            saw_images_phase = True
            break
        if evt.get("type") in ("progress",) and evt.get("phase") == "images":
            saw_images_phase = True
            break
        if time.time() > deadline:
            break
    assert saw_images_phase, "render never reached the images phase before timeout"

    # A temp dir should now exist under our temp root.
    time.sleep(0.5)
    temp_dirs_during = list(temp_root.glob("slideshow-gen-*"))
    assert temp_dirs_during, "expected a slideshow-gen-* temp dir during render"

    # Cancel: SIGTERM to the CLI process (mimics Rust sending SIGTERM to the
    # sidecar pid). Collect the rest of stdout.
    proc.send_signal(signal.SIGTERM)
    remaining = proc.stdout.read()
    rc = proc.wait(timeout=30)

    tail_events = []
    for line in remaining.strip().split("\n"):
        if line.strip():
            try:
                tail_events.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    # Non-zero exit (cancel is a failure to the embedder).
    assert rc != 0, f"expected non-zero exit on cancel, got {rc}"
    # `cancelled` event emitted; `complete` never emitted.
    types = [e.get("type") for e in tail_events]
    assert "cancelled" in types, f"no cancelled event; tail types={types}"
    assert "complete" not in types
    # Temp dir cleaned up (no --keep-temp).
    leftover = list(temp_root.glob("slideshow-gen-*"))
    assert not leftover, f"temp dir not cleaned on cancel: {leftover}"
    # No output file written.
    assert not out.exists(), "cancelled render must not leave an output file"
    # No orphaned ffmpeg processes from this render. Allow a brief grace for
    # the OS to reap, and only count PIDs that weren't running before.
    time.sleep(1.0)
    orphans = _list_ffmpeg_pids() - ffmpeg_before
    assert not orphans, f"orphaned ffmpeg processes after cancel: {orphans}"
