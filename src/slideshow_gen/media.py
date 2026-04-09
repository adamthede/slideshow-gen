"""Image and video dimension/duration helpers."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass
class ImageInfo:
    width: int
    height: int
    format: str


@dataclass
class VideoInfo:
    width: int
    height: int
    duration: float


def get_image_info(path: Path) -> ImageInfo | None:
    """Get image dimensions (EXIF-rotation applied) and format."""
    try:
        with Image.open(path) as img:
            # Apply EXIF transpose to get actual display dimensions
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
            return ImageInfo(width=img.width, height=img.height, format=img.format or "")
    except Exception:
        return None


def get_video_info(path: Path) -> VideoInfo | None:
    """Get video dimensions and duration via ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-show_entries", "format=duration",
                "-of", "json",
                str(path),
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        fmt = data.get("format", {})

        width = streams[0]["width"] if streams else 0
        height = streams[0]["height"] if streams else 0
        duration = float(fmt.get("duration", 0))

        return VideoInfo(width=width, height=height, duration=duration)
    except Exception:
        return None
