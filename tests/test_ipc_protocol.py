"""Lock the sidecar IPC contract.

Documented in docs/sidecar-protocol.md. Changes to event names, required
fields, or version should require updating both this test and the doc.
"""

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _make_assets(d: Path) -> None:
    for i, color in enumerate(["red", "green", "blue"]):
        Image.new("RGB", (1200, 900), color=color).save(
            d / f"2026-05-23 12-0{i}-00 - test.jpg", quality=85
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
    assert types == [
        "started",
        "phase_started",
        "discovery_complete",
        "estimate",
        "info",
    ]

    # Required common fields on every event
    for e in events:
        assert e["v"] == 1
        assert isinstance(e["t"], (int, float))
        assert isinstance(e["type"], str)

    # discovery_complete shape
    dc = next(e for e in events if e["type"] == "discovery_complete")
    assert dc["images"] == 3
    assert dc["videos"] == 0

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
