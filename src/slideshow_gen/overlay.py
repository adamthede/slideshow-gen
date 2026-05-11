"""Text overlay filter string generation for FFmpeg drawtext.

Generates drawtext filters with fade-in/fade-out alpha expressions
for date and location overlays on slideshow images and video clips.
"""

import os
import platform
from .config import RenderConfig

def get_font_path() -> str:
    system = platform.system()
    if system == "Darwin":
        paths = ["/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf"]
    elif system == "Windows":
        paths = ["C:\\Windows\\Fonts\\arial.ttf", "C:\\Windows\\Fonts\\segui.ttf"]
    else:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
        ]
    
    for p in paths:
        if os.path.exists(p):
            return p
    return ""  # FFmpeg might fail if it strictly requires a font path

FONT_PATH = get_font_path()


def generate_overlay_filters(
    date_str: str | None,
    location_str: str | None,
    config: RenderConfig,
    is_video: bool = False,
) -> list[str]:
    """Generate drawtext filter strings for date and location overlays.

    Returns a list of FFmpeg filter strings (0-2 items).

    For images: fade in 0-0.5s, hold 0.5-1.5s, fade out 1.5-2.0s
    For videos: fade in 0-0.5s, hold 0.5-2.0s, fade out 2.0-2.5s
    """
    if not config.show_date and not config.show_location:
        return []

    filters = []

    # Scale font size to resolution
    base_size = 42 if config.output_width <= 1920 else 64
    small_size = 36 if config.output_width <= 1920 else 54

    # Alpha expression: fade in, hold, fade out
    if is_video:
        alpha = _alpha_expr(fade_in_end=0.5, hold_end=2.0, fade_out_end=2.5)
    else:
        alpha = _alpha_expr(fade_in_end=0.5, hold_end=1.5, fade_out_end=2.0)

    # Position: date bottom-left, location bottom-right
    margin = 40 if config.output_width <= 1920 else 60
    y_pos = f"h-{80 if config.output_width <= 1920 else 120}"

    if config.show_date and date_str:
        filters.append(_drawtext(
            text=date_str,
            fontsize=base_size,
            x=str(margin),
            y=y_pos,
            alpha=alpha,
        ))

    if config.show_location and location_str:
        filters.append(_drawtext(
            text=location_str,
            fontsize=small_size,
            x=f"w-text_w-{margin}",
            y=y_pos,
            alpha=alpha,
        ))

    return filters


def _drawtext(text: str, fontsize: int, x: str, y: str, alpha: str) -> str:
    """Build a single drawtext filter string."""
    # Escape special characters for FFmpeg drawtext
    escaped = text.replace("'", "'\\\\\\''").replace(":", "\\:")
    return (
        f"drawtext=text='{escaped}'"
        f":fontfile={FONT_PATH}"
        f":fontsize={fontsize}"
        f":fontcolor=white"
        f":x={x}"
        f":y={y}"
        f":alpha='{alpha}'"
        f":box=1:boxcolor=black@0.4:boxborderw=10"
    )


def _alpha_expr(fade_in_end: float, hold_end: float, fade_out_end: float) -> str:
    """Generate an alpha expression for fade-in, hold, fade-out.

    Example: fade in 0-0.5s, hold 0.5-1.5s, fade out 1.5-2.0s
    """
    fade_out_dur = fade_out_end - hold_end
    return (
        f"if(lt(t,{fade_in_end}),t/{fade_in_end},"
        f"if(lt(t,{hold_end}),1,"
        f"max(0,1-(t-{hold_end})/{fade_out_dur})))"
    )
