"""Render configuration dataclass — single source of truth for all parameters."""

from dataclasses import dataclass
from pathlib import Path


RESOLUTIONS = {
    "1080p": (1920, 1080),
    "4k": (3840, 2160),
}

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".heic", ".heif", ".png",
    ".tiff", ".tif", ".dng", ".bmp", ".gif",
}

VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".avi", ".mkv", ".m4v", ".mts", ".m2ts",
}


@dataclass(frozen=True)
class RenderConfig:
    output_width: int = 1920
    output_height: int = 1080
    slide_duration: float = 4.0
    fade_duration: float = 0.5
    fps: int = 30
    zoom_rate: float = 0.1
    random_order: bool = False
    show_date: bool = True
    show_location: bool = True
    workers: int = 4
    batch_size: int = 20
    static: bool = False
    verbose: bool = False
    supersample_factor: int = 4
    intermediate_crf: int = 17
    final_crf: int = 18

    @property
    def output_ratio(self) -> float:
        return self.output_width / self.output_height

    @property
    def supersample_width(self) -> int:
        return self.output_width * self.supersample_factor

    @property
    def supersample_height(self) -> int:
        return self.output_height * self.supersample_factor

    @property
    def total_frames_per_slide(self) -> int:
        return int(self.fps * self.slide_duration)

    @classmethod
    def from_resolution(cls, resolution: str, **kwargs) -> "RenderConfig":
        width, height = RESOLUTIONS[resolution]
        return cls(output_width=width, output_height=height, **kwargs)
