"""Image and video dimension/duration helpers."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .ffbin import ffprobe_binary


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
    has_audio: bool = False


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
    """Get video dimensions, duration, and audio presence via ffprobe."""
    try:
        result = subprocess.run(
            [
                ffprobe_binary(), "-v", "error",
                "-show_entries", "stream=width,height,codec_type",
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

        width = 0
        height = 0
        has_audio = False
        
        for s in streams:
            if s.get("codec_type") == "video":
                width = s.get("width", 0)
                height = s.get("height", 0)
            elif s.get("codec_type") == "audio":
                has_audio = True

        duration = float(fmt.get("duration", 0))

        return VideoInfo(width=width, height=height, duration=duration, has_audio=has_audio)
    except Exception:
        return None
