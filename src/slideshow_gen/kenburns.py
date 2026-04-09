"""Ken Burns zoompan filter expression generator.

Ported from kburns2.rb (sargue/kburns). Generates FFmpeg zoompan filter
expressions for smooth zoom/pan effects on still images.

The 4x supersampling trick is used to avoid the jitter/shake bug in FFmpeg's
zoompan filter (https://trac.ffmpeg.org/ticket/4298).
"""

import random
from dataclasses import dataclass
from enum import Enum

from .config import RenderConfig


class Direction(Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    IN = "in"
    OUT = "out"


class ScaleMode(Enum):
    CROP_CENTER = "crop_center"
    PAD = "pad"
    PAN = "pan"


@dataclass
class KenBurnsEffect:
    direction_x: Direction
    direction_y: Direction
    direction_z: Direction
    is_static: bool = False
    scale_mode: ScaleMode = ScaleMode.CROP_CENTER


def choose_effect(width: int, height: int, output_ratio: float) -> KenBurnsEffect:
    """Choose a Ken Burns effect for an image, with smart static detection."""
    ratio = width / height if height > 0 else 1.0

    # Static detection: panoramas or tiny images
    if ratio > 2.5 or ratio < 0.4:
        return KenBurnsEffect(
            direction_x=Direction.CENTER,
            direction_y=Direction.CENTER,
            direction_z=Direction.IN,
            is_static=True,
        )

    long_edge = max(width, height)
    if long_edge < 800:
        return KenBurnsEffect(
            direction_x=Direction.CENTER,
            direction_y=Direction.CENTER,
            direction_z=Direction.IN,
            is_static=True,
        )

    # Randomize directions
    direction_x = random.choice([Direction.LEFT, Direction.CENTER, Direction.RIGHT])
    direction_y = random.choice([Direction.TOP, Direction.CENTER, Direction.BOTTOM])
    direction_z = random.choice([Direction.IN, Direction.OUT])

    # Auto scale mode based on aspect ratio difference from output
    ratio_diff = abs(ratio - output_ratio)
    if ratio_diff > 0.5:
        scale_mode = ScaleMode.PAD
    else:
        scale_mode = ScaleMode.CROP_CENTER

    return KenBurnsEffect(
        direction_x=direction_x,
        direction_y=direction_y,
        direction_z=direction_z,
        scale_mode=scale_mode,
    )


def generate_filter_chain(
    image_w: int,
    image_h: int,
    config: RenderConfig,
    effect: KenBurnsEffect,
) -> str:
    """Generate the full filter chain for a single image.

    Returns a comma-separated FFmpeg filter string including:
    format, crop (even dims), pad (if needed), supersample scale,
    zoompan, and final crop (if crop_center mode).
    """
    if effect.is_static:
        return _generate_static_filter(image_w, image_h, config)

    return _generate_kenburns_filter(image_w, image_h, config, effect)


def _generate_static_filter(image_w: int, image_h: int, config: RenderConfig) -> str:
    """Generate filter chain for a static (non-animated) image."""
    out_w = config.output_width
    out_h = config.output_height
    total_frames = config.total_frames_per_slide

    filters = [
        "format=pix_fmts=yuva420p",
        f"scale=w='min({out_w},iw)':h='min({out_h},ih)':force_original_aspect_ratio=decrease:flags=lanczos",
        f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:color=black",
        f"loop=loop={total_frames - 1}:size=1:start=0",
        f"fps={config.fps}",
        f"setpts=N/{config.fps}/TB",
    ]
    return ",".join(filters)


def _generate_kenburns_filter(
    image_w: int,
    image_h: int,
    config: RenderConfig,
    effect: KenBurnsEffect,
) -> str:
    """Generate the Ken Burns zoompan filter chain."""
    out_w = config.output_width
    out_h = config.output_height
    out_ratio = config.output_ratio
    ratio = image_w / image_h if image_h > 0 else 1.0
    fps = config.fps
    duration = config.slide_duration
    zoom_rate = config.zoom_rate
    ss_w = config.supersample_width
    ss_h = config.supersample_height

    filters = ["format=pix_fmts=yuva420p"]

    # Ensure even dimensions
    cropped_w = 2 * (image_w // 2)
    cropped_h = 2 * (image_h // 2)
    filters.append("crop=w=2*floor(iw/2):h=2*floor(ih/2)")

    # Compute upscale dimensions (replicate force_original_aspect_ratio=increase logic)
    scale_factor = max(out_w / cropped_w, out_h / cropped_h, 1.0)
    scaled_w = 2 * round(cropped_w * scale_factor / 2)
    scaled_h = 2 * round(cropped_h * scale_factor / 2)
    filters.append(f"scale={scaled_w}:{scaled_h}:flags=lanczos")

    # Pad for pad/pan modes — computed from known post-scale dimensions
    if effect.scale_mode in (ScaleMode.PAD, ScaleMode.PAN):
        if ratio > out_ratio:
            # Wider image: pad height to match output ratio
            pad_w = scaled_w
            pad_h = max(scaled_h, 2 * round(scaled_w / out_ratio / 2))
        else:
            # Taller image: pad width to match output ratio
            pad_w = max(scaled_w, 2 * round(scaled_h * out_ratio / 2))
            pad_h = scaled_h
        filters.append(
            f"pad={pad_w}:{pad_h}:(ow-iw)/2:(oh-ih)/2"
        )

    # Zoom calculations
    z_step = zoom_rate / (fps * duration)
    z_rate = zoom_rate
    z_initial = 1.0

    if effect.scale_mode == ScaleMode.PAN:
        if ratio > out_ratio:
            z_initial = ratio / out_ratio
            z_step = z_step * ratio / out_ratio
            z_rate = z_rate * ratio / out_ratio
        else:
            z_initial = out_ratio / ratio
            z_step = z_step * out_ratio / ratio
            z_rate = z_rate * out_ratio / ratio

    # Z expression
    if effect.direction_z == Direction.IN:
        z_expr = f"if(eq(on,1),{z_initial},zoom+{z_step})"
    else:
        z_expr = f"if(eq(on,1),{z_initial + z_rate},zoom-{z_step})"

    # X expression
    x_expr = _calc_x_expr(effect, ratio, out_ratio, fps, duration)

    # Y expression
    y_expr = _calc_y_expr(effect, ratio, out_ratio, fps, duration)

    # Zoompan dimensions
    if effect.scale_mode == ScaleMode.CROP_CENTER:
        if out_ratio > ratio:
            zp_w = out_w
            zp_h = int(out_w / ratio)
        else:
            zp_w = int(out_h * ratio)
            zp_h = out_h
    else:
        zp_w = out_w
        zp_h = out_h

    # 4x supersample then zoompan
    filters.append(f"scale={ss_w}x{ss_h}")
    filters.append(
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}'"
        f":fps={fps}:d={fps * duration}:s={zp_w}x{zp_h}"
    )

    # Final crop for crop_center mode
    if effect.scale_mode == ScaleMode.CROP_CENTER:
        filters.append(
            f"crop=w={out_w}:h={out_h}:x='(iw-ow)/2':y='(ih-oh)/2'"
        )

    # Force consistent pixel format for concat compatibility
    filters.append("format=pix_fmts=yuv420p")

    return ",".join(filters)


def _calc_x_expr(
    effect: KenBurnsEffect, ratio: float, out_ratio: float,
    fps: int, duration: float,
) -> str:
    """Calculate the X pan expression for zoompan."""
    if effect.scale_mode == ScaleMode.PAN:
        if ratio > out_ratio:
            # Wider image: pan horizontally
            is_left = (
                (effect.direction_x == Direction.LEFT and effect.direction_z != Direction.OUT)
                or (effect.direction_x == Direction.RIGHT and effect.direction_z == Direction.OUT)
            )
            is_right = (
                (effect.direction_x == Direction.RIGHT and effect.direction_z != Direction.OUT)
                or (effect.direction_x == Direction.LEFT and effect.direction_z == Direction.OUT)
            )
            if is_left:
                return f"(1-on/({fps}*{duration}))*(iw-iw/zoom)"
            elif is_right:
                return f"(on/({fps}*{duration}))*(iw-iw/zoom)"
            else:
                return "(iw-ow)/2"
        else:
            # Taller image
            x_offset = f"(iw-{ratio}*ih)/2"
            if effect.direction_x == Direction.LEFT:
                return x_offset
            elif effect.direction_x == Direction.CENTER:
                return f"{x_offset}+ih*{ratio}/2-ih*{out_ratio}/zoom/2"
            else:
                return f"{x_offset}+ih*{ratio}-ih*{out_ratio}/zoom"
    else:
        # crop_center or pad
        if effect.direction_x == Direction.LEFT:
            return "0"
        elif effect.direction_x == Direction.CENTER:
            return "iw/2-(iw/zoom/2)"
        else:
            return "iw-iw/zoom"


def _calc_y_expr(
    effect: KenBurnsEffect, ratio: float, out_ratio: float,
    fps: int, duration: float,
) -> str:
    """Calculate the Y pan expression for zoompan."""
    if effect.scale_mode == ScaleMode.PAN:
        if ratio > out_ratio:
            # Wider image
            y_offset = f"(ih-iw/{ratio})/2"
            if effect.direction_y == Direction.TOP:
                return y_offset
            elif effect.direction_y == Direction.CENTER:
                return f"{y_offset}+iw/{ratio}/2-iw/{out_ratio}/zoom/2"
            else:
                return f"{y_offset}+iw/{ratio}-iw/{out_ratio}/zoom"
        else:
            # Taller image: pan vertically
            is_top = (
                (effect.direction_y == Direction.TOP and effect.direction_z != Direction.OUT)
                or (effect.direction_y == Direction.BOTTOM and effect.direction_z == Direction.OUT)
            )
            is_bottom = (
                (effect.direction_y == Direction.BOTTOM and effect.direction_z != Direction.OUT)
                or (effect.direction_y == Direction.TOP and effect.direction_z == Direction.OUT)
            )
            if is_top:
                return f"(1-on/({fps}*{duration}))*(ih-ih/zoom)"
            elif is_bottom:
                return f"(on/({fps}*{duration}))*(ih-ih/zoom)"
            else:
                return "(ih-oh)/2"
    else:
        # crop_center or pad
        if effect.direction_y == Direction.TOP:
            return "0"
        elif effect.direction_y == Direction.CENTER:
            return "ih/2-(ih/zoom/2)"
        else:
            return "ih-ih/zoom"
