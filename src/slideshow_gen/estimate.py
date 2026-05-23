"""Pre-render duration and file-size estimation.

Output is essentially CBR: h264_videotoolbox -b:v 20M + AAC 192k.
Size ≈ bitrate × duration / 8.
"""

from dataclasses import dataclass

from .config import RenderConfig
from .discovery import MediaItem


VIDEO_BITRATE_BPS = 20_000_000  # h264_videotoolbox -b:v 20M
AUDIO_BITRATE_BPS = 192_000     # aac -b:a 192k
TOTAL_BITRATE_BPS = VIDEO_BITRATE_BPS + AUDIO_BITRATE_BPS


@dataclass(frozen=True)
class Estimate:
    image_count: int
    video_count: int
    image_duration_s: float
    video_duration_s: float
    total_duration_s: float
    size_bytes: int


def estimate_output(items: list[MediaItem], config: RenderConfig) -> Estimate:
    """Compute deterministic duration + size estimate from the discovered manifest.

    Treats all images as one batch for duration math; the per-batch concat boundary
    overhead is < 1% on typical inputs and not worth modeling here.
    """
    images = [i for i in items if i.media_type == "image"]
    videos = [i for i in items if i.media_type == "video"]

    n_img = len(images)
    img_dur = (
        n_img * config.slide_duration - max(0, n_img - 1) * config.fade_duration
        if n_img > 0
        else 0.0
    )
    vid_dur = sum(v.duration for v in videos)
    total = img_dur + vid_dur

    size = int(total * TOTAL_BITRATE_BPS / 8)

    return Estimate(
        image_count=n_img,
        video_count=len(videos),
        image_duration_s=img_dur,
        video_duration_s=vid_dur,
        total_duration_s=total,
        size_bytes=size,
    )


def format_duration(seconds: float) -> str:
    s = int(seconds)
    if s >= 3600:
        return f"{s // 3600}h {(s % 3600) // 60:02d}m {s % 60:02d}s"
    if s >= 60:
        return f"{s // 60}m {s % 60:02d}s"
    return f"{s}s"


def format_size(size_bytes: int) -> str:
    mb = size_bytes / (1024 * 1024)
    if mb >= 1024:
        return f"{mb / 1024:.2f} GB"
    return f"{mb:.0f} MB"


def format_estimate(est: Estimate) -> str:
    lines = [
        f"  [estimate] Duration: {format_duration(est.total_duration_s)} "
        f"(images {format_duration(est.image_duration_s)} + "
        f"videos {format_duration(est.video_duration_s)})",
        f"  [estimate] Output size: ~{format_size(est.size_bytes)} "
        f"(at {TOTAL_BITRATE_BPS / 1_000_000:.1f} Mbps, ±20%)",
    ]
    return "\n".join(lines)
