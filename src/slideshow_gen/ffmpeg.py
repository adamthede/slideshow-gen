"""FFmpeg subprocess runner, filter script builder, and parallel execution."""

import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import click

from .config import RenderConfig
from .discovery import MediaItem
from .events import Reporter
from .ffbin import ffmpeg_binary, ffprobe_binary
from .heic import convert_heic_to_jpg, is_heic
from .kenburns import choose_effect, generate_filter_chain
from .memutil import auto_worker_count
from .overlay import generate_overlay_filters


def check_ffmpeg() -> bool:
    """Verify FFmpeg is installed and accessible."""
    try:
        result = subprocess.run(
            [ffmpeg_binary(), "-version"], capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        # OSError (superclass of FileNotFoundError) also covers a bundled
        # binary that exists but isn't executable (PermissionError) or isn't a
        # valid Mach-O (ENOEXEC) — treat any of these as "FFmpeg unavailable"
        # rather than crashing the pre-render check.
        return False


def render_image_to_clip(
    item: MediaItem,
    index: int,
    temp_dir: Path,
    config: RenderConfig,
) -> tuple[Path | None, tuple[str, str | None] | None]:
    """Render a single image to a temp MP4 with Ken Burns effect and overlays.

    Returns ``(output_path, None)`` on success or ``(None, (reason, detail))``
    on failure. The structured failure tuple lets the caller emit a typed
    `item_failed` IPC event (reason is a short string; detail may include the
    last lines of FFmpeg stderr for diagnostics).
    """
    source = item.path

    # Convert HEIC if needed
    if is_heic(source):
        try:
            source = convert_heic_to_jpg(source, temp_dir)
        except Exception as e:
            click.echo(f"  Warning: HEIC conversion failed for {item.path.name}: {e}", err=True)
            return None, ("HEIC conversion failed", str(e))

    # Choose Ken Burns effect
    effect = choose_effect(item.width, item.height, config.output_ratio)

    # Build filter chain
    kb_filter = generate_filter_chain(item.width, item.height, config, effect)

    # Add overlay filters
    overlay_filters = generate_overlay_filters(
        date_str=item.display_date or None,
        location_str=item.display_location or None,
        config=config,
    )

    full_filter = kb_filter
    if overlay_filters:
        full_filter += "," + ",".join(overlay_filters)

    # Output path
    output_path = temp_dir / f"temp-slide-{index:04d}.mp4"

    # Build FFmpeg command — use hardware encoder for intermediates
    # Inject silent audio track so it can be concatenated with video clips later
    # Use -loop 1 to provide continuous frames for zoompan, and -t to hard-stop
    # the encode at the exact slide duration.
    duration = config.slide_duration
    cmd = [
        ffmpeg_binary(), "-y", "-hide_banner",
        "-v", "warning" if not config.verbose else "info",
        "-loop", "1", "-i", str(source),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-vf", full_filter,
        "-map", "0:v",
        "-map", "1:a",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-c:v", "h264_videotoolbox",
        "-b:v", "20M",
        "-c:a", "aac", "-b:a", "192k",
        "-ac", "2", "-ar", "48000",
        str(output_path),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=300,  # 5 min per image should be more than enough
        )
        if result.returncode != 0:
            tail = (result.stderr or "")[-400:]
            click.echo(
                f"  Warning: FFmpeg failed for {item.path.name}: {tail[:200]}",
                err=True,
            )
            return None, ("ffmpeg returned non-zero", tail or None)
        return output_path, None
    except subprocess.TimeoutExpired:
        click.echo(f"  Warning: FFmpeg timed out for {item.path.name}", err=True)
        return None, ("ffmpeg timed out", None)
    except Exception as e:
        click.echo(f"  Warning: Error rendering {item.path.name}: {e}", err=True)
        return None, ("render exception", str(e))


# Standalone function for ProcessPoolExecutor (must be picklable)
def _render_worker(args: tuple) -> tuple[int, str | None, str, tuple[str, str | None] | None]:
    """Worker function for parallel rendering.

    Returns ``(index, output_path_or_none, source_path, error_info)`` where
    ``error_info`` is ``(reason, detail)`` on failure or ``None`` on success.
    The source path is echoed back so the orchestrator can attach it to an
    ``item_failed`` IPC event without re-deriving from the original items list.
    """
    item_data, index, temp_dir_str, config_dict = args

    # Reconstruct objects from serializable data
    config = RenderConfig(**config_dict)
    temp_dir = Path(temp_dir_str)
    item = MediaItem(**item_data)

    path_result, err = render_image_to_clip(item, index, temp_dir, config)
    return (
        index,
        str(path_result) if path_result else None,
        str(item.path.resolve()),
        err,
    )


def parallel_render(
    items: list[MediaItem],
    temp_dir: Path,
    config: RenderConfig,
    reporter: Reporter | None = None,
) -> list[tuple[int, Path]]:
    """Render all image items to temp clips in parallel.

    Returns list of (original_index, temp_clip_path) tuples for successful renders.
    """
    image_items = [(i, item) for i, item in enumerate(items) if item.media_type == "image"]

    if not image_items:
        return []

    # Serialize config and items for multiprocessing
    config_dict = {
        field: getattr(config, field)
        for field in config.__dataclass_fields__
    }

    work = []
    for orig_idx, item in image_items:
        item_data = {
            "path": item.path,
            "media_type": item.media_type,
            "sort_key": item.sort_key,
            "width": item.width,
            "height": item.height,
            "duration": item.duration,
            "display_date": item.display_date,
            "display_location": item.display_location,
            "gps_lat": item.gps_lat,
            "gps_lon": item.gps_lon,
            "parsed_date": item.parsed_date,
            "content_hash": item.content_hash,
        }
        work.append((item_data, orig_idx, str(temp_dir), config_dict))

    results = []
    total = len(work)
    completed = 0

    workers = auto_worker_count(config.workers)
    if reporter is not None:
        reporter.phase_started("images", total=total)
    else:
        click.echo(f"\n  [images] Rendering {total} images with {workers} workers...")

    # Map orig_idx -> source path for failure attribution when the worker
    # crashes outright (no result tuple to inspect).
    idx_to_path: dict[int, str] = {orig_idx: str(item.path.resolve()) for orig_idx, item in image_items}
    skipped = 0

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_render_worker, w): w[1] for w in work}

        for future in as_completed(futures):
            completed += 1
            orig_idx = futures[future]
            try:
                idx, path_str, src_path, err = future.result()
                if path_str:
                    results.append((idx, Path(path_str)))
                else:
                    skipped += 1
                    reason, detail = err if err else ("unknown failure", None)
                    if reporter is not None:
                        reporter.item_failed(
                            phase="images",
                            path=src_path,
                            reason=reason,
                            detail=detail,
                        )
            except Exception as e:
                # Worker itself crashed (pickling error, OOM, etc.) — surface
                # as item_failed so the UI can still account for the skip.
                skipped += 1
                src_path = idx_to_path.get(orig_idx, "")
                if reporter is not None:
                    reporter.item_failed(
                        phase="images",
                        path=src_path,
                        reason="worker crashed",
                        detail=str(e),
                    )
                else:
                    click.echo(
                        f"  Warning: Worker failed for index {orig_idx}: {e}", err=True,
                    )

            # Progress reflects *attempted* total so the bar still completes
            # even when items are skipped — per docs/sidecar-protocol.md.
            if reporter is not None:
                reporter.progress("images", completed, total)
            else:
                pct = completed / total * 100
                click.echo(f"\r  [images] [{completed}/{total}] {pct:.1f}%", nl=False)

    if reporter is not None:
        reporter.phase_complete("images", f"{len(results)}/{total} rendered")
    else:
        click.echo("")  # Newline after progress
        click.echo(f"  [images] {len(results)}/{total} images rendered successfully.")

    return sorted(results, key=lambda x: x[0])


def render_batch(
    clip_paths: list[Path],
    batch_index: int,
    temp_dir: Path,
    config: RenderConfig,
    offsets: list[float] | None = None,
) -> Path | None:
    """Composite a batch of clips with crossfade transitions.

    Returns the path to the batch output file, or None on failure.
    """
    if not clip_paths:
        return None

    slide_dur = config.slide_duration
    fade_dur = config.fade_duration

    # Calculate offsets if not provided
    if offsets is None:
        offsets = [i * (slide_dur - fade_dur) for i in range(len(clip_paths))]

    batch_duration = offsets[-1] + slide_dur
    n = len(clip_paths)

    # Build filter chains
    chains = []

    # Base black canvas
    chains.append(
        f"color=c=black:r={config.fps}"
        f":size={config.output_width}x{config.output_height}"
        f":d={batch_duration}[black]"
    )

    # Per-clip: fade + time offset
    # Edge fades (first clip fade-in, last clip fade-out) enable concat assembly
    for i in range(n):
        filters = []
        if fade_dur > 0:
            filters.append(f"fade=t=in:st=0:d={fade_dur}:alpha=1")
            filters.append(f"fade=t=out:st={slide_dur - fade_dur}:d={fade_dur}:alpha=1")
        filters.append(f"setpts=PTS-STARTPTS+{offsets[i]}/TB")
        chains.append(f"[{i}:v]" + ",".join(filters) + f"[v{i}]")

    # Overlay stack
    for i in range(n):
        inp1 = f"ov{i - 1}" if i > 0 else "black"
        inp2 = f"v{i}"
        out = "ov_final" if i == n - 1 else f"ov{i}"
        overlay = "overlay=format=yuv420" if i == n - 1 else "overlay"
        chains.append(f"[{inp1}][{inp2}]{overlay}[{out}]")

    # Force consistent pixel format for concat compatibility
    chains.append("[ov_final]format=pix_fmts=yuv420p[out]")

    # Silent audio sized to match the video timeline exactly.
    # Mixing the per-clip silent tracks via amix would produce only
    # slide_duration of audio (all inputs start at t=0 with duration=longest),
    # leaving the batch with video ≫ audio. Concat re-encoding then drifts
    # the audio earlier and earlier across the timeline, which makes later
    # video-segment audio play before its frames render.
    chains.append(
        f"anullsrc=channel_layout=stereo:sample_rate=48000"
        f":d={batch_duration}[a_out]"
    )

    # Write filter script
    script_path = temp_dir / f"temp-batch-script-{batch_index:04d}.txt"
    script_path.write_text(";\n".join(chains))

    # Output path
    output_path = temp_dir / f"temp-batch-{batch_index:04d}.mp4"

    cmd = [
        ffmpeg_binary(), "-y", "-hide_banner",
        "-v", "warning" if not config.verbose else "info",
        *[arg for p in clip_paths for arg in ["-i", str(p)]],
        "-filter_complex_script", str(script_path),
        "-t", str(batch_duration),
        "-map", "[out]",
        "-map", "[a_out]",
        "-pix_fmt", "yuv420p",
        "-c:v", "h264_videotoolbox",
        "-b:v", "20M",
        "-c:a", "aac", "-b:a", "192k",
        "-ac", "2", "-ar", "48000",
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if result.returncode != 0:
            click.echo(
                f"  Error: Batch {batch_index} failed: {result.stderr[:300]}",
                err=True,
            )
            return None
        return output_path
    except Exception as e:
        click.echo(f"  Error: Batch {batch_index} failed: {e}", err=True)
        return None


def render_static_batch(
    items: list[MediaItem],
    batch_index: int,
    temp_dir: Path,
    config: RenderConfig,
) -> Path | None:
    """Render a batch of images as static slides with crossfades (no Ken Burns).

    Takes raw images, scales/pads to output resolution, loops for slide_duration,
    adds overlays, and composites with crossfade transitions. Returns the batch
    output path, or None on failure.
    """
    if not items:
        return None

    slide_dur = config.slide_duration
    fade_dur = config.fade_duration
    out_w = config.output_width
    out_h = config.output_height
    total_frames = int(config.fps * slide_dur)

    # Pre-resolve sources (convert HEIC if needed)
    sources: list[tuple[Path, MediaItem]] = []
    for item in items:
        source = item.path
        if is_heic(source):
            try:
                source = convert_heic_to_jpg(source, temp_dir)
            except Exception as e:
                click.echo(f"  Warning: HEIC conversion failed for {item.path.name}: {e}", err=True)
                continue
        sources.append((source, item))

    if not sources:
        return None

    n = len(sources)
    offsets = [i * (slide_dur - fade_dur) for i in range(n)]
    batch_duration = offsets[-1] + slide_dur

    chains = []

    # Base black canvas
    chains.append(
        f"color=c=black:r={config.fps}"
        f":size={out_w}x{out_h}"
        f":d={batch_duration}[black]"
    )

    # Per-image: scale, pad, loop, overlay, fade, time offset
    for i, (source, item) in enumerate(sources):
        filters = []
        filters.append("format=pix_fmts=yuva420p")
        filters.append(
            f"scale=w={out_w}:h={out_h}"
            f":force_original_aspect_ratio=decrease:flags=lanczos"
        )
        filters.append(f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:color=black")
        filters.append(f"loop=loop={total_frames - 1}:size=1:start=0")
        filters.append(f"fps={config.fps}")
        filters.append(f"setpts=N/{config.fps}/TB")

        # Overlays
        overlay_filters = generate_overlay_filters(
            date_str=item.display_date or None,
            location_str=item.display_location or None,
            config=config,
        )
        filters.extend(overlay_filters)

        # Edge fades for all clips
        if fade_dur > 0:
            filters.append(f"fade=t=in:st=0:d={fade_dur}:alpha=1")
            filters.append(f"fade=t=out:st={slide_dur - fade_dur}:d={fade_dur}:alpha=1")

        filters.append(f"setpts=PTS-STARTPTS+{offsets[i]}/TB")
        chains.append(f"[{i}:v]" + ",".join(filters) + f"[v{i}]")

    # Overlay stack
    for i in range(n):
        inp1 = f"ov{i - 1}" if i > 0 else "black"
        inp2 = f"v{i}"
        out = "ov_final" if i == n - 1 else f"ov{i}"
        overlay = "overlay=format=yuv420" if i == n - 1 else "overlay"
        chains.append(f"[{inp1}][{inp2}]{overlay}[{out}]")

    # Force consistent pixel format for concat compatibility
    chains.append("[ov_final]format=pix_fmts=yuv420p[out]")

    # Write filter script
    script_path = temp_dir / f"temp-static-batch-script-{batch_index:04d}.txt"
    script_path.write_text(";\n".join(chains))

    output_path = temp_dir / f"temp-batch-{batch_index:04d}.mp4"

    cmd = [
        ffmpeg_binary(), "-y", "-hide_banner",
        "-v", "warning" if not config.verbose else "info",
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        *[arg for source, _ in sources for arg in ["-i", str(source)]],
        "-filter_complex_script", str(script_path),
        "-t", str(batch_duration + fade_dur),
        "-map", "[out]",
        "-map", "0:a",
        "-pix_fmt", "yuv420p",
        "-c:v", "h264_videotoolbox",
        "-b:v", "20M",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if result.returncode != 0:
            click.echo(
                f"  Error: Static batch {batch_index} failed: {result.stderr[:300]}",
                err=True,
            )
            return None
        return output_path
    except Exception as e:
        click.echo(f"  Error: Static batch {batch_index} failed: {e}", err=True)
        return None


def render_final_concat(
    segment_paths: list[Path],
    output: Path,
    config: RenderConfig,
    temp_dir: Path,
    reporter: Reporter | None = None,
) -> bool:
    """Assemble segments into final MP4 using concat demuxer.

    All segments must already have edge fades baked in. Re-encodes via
    h264_videotoolbox to match the hardware-encoded intermediates, which
    is ~15× faster on Apple Silicon than software libx264 at comparable
    quality for slideshow content. Returns True on success.
    """
    if not segment_paths:
        return False

    # Write concat file
    concat_path = temp_dir / "concat.txt"
    lines = []
    for p in segment_paths:
        # Escape single quotes in paths for FFmpeg concat format
        escaped = str(p).replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    concat_path.write_text("\n".join(lines))

    # Estimate total duration for progress display and timeout
    total_duration = sum(_get_duration(p) for p in segment_paths)

    cmd = [
        ffmpeg_binary(), "-y", "-hide_banner",
        "-v", "warning" if not config.verbose else "info",
        "-progress", "pipe:1",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_path),
    ]

    if config.audio_track:
        cmd.extend([
            "-stream_loop", "-1",
            "-i", str(config.audio_track),
            "-filter_complex", 
            f"[1:a]volume={config.audio_volume}[bg_vol];"
            f"[bg_vol][0:a]sidechaincompress=threshold=0.08:ratio=4:attack=50:release=1000[bg_ducked];"
            f"[0:a][bg_ducked]amix=inputs=2:duration=first:dropout_transition=0[a]",
            "-map", "0:v",
            "-map", "[a]"
        ])

    cmd.extend([
        "-c:v", "h264_videotoolbox",
        "-b:v", "20M",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(output),
    ])

    total_str = _format_duration(total_duration)
    if reporter is not None:
        reporter.phase_started("compositing", total=int(total_duration))
    else:
        click.echo(
            f"\n  [compositing] Concatenating {len(segment_paths)} segments "
            f"({total_str}) into final video..."
        )

    # Use a temp file for stderr to avoid pipe buffer deadlock
    stderr_path = temp_dir / "ffmpeg-concat-stderr.log"

    try:
        timeout = max(3600, int(600 + total_duration * 5))

        with open(stderr_path, "w") as stderr_file:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=stderr_file, text=True,
            )

            # Parse -progress output for real-time percentage
            last_pct = -1
            try:
                for line in proc.stdout:
                    line = line.strip()
                    if line.startswith("out_time_us="):
                        try:
                            us = int(line.split("=", 1)[1])
                            elapsed_s = us / 1_000_000
                            if total_duration > 0:
                                pct = min(elapsed_s / total_duration * 100, 100)
                                pct_int = int(pct)
                                if pct_int > last_pct:
                                    last_pct = pct_int
                                    if reporter is not None:
                                        reporter.progress(
                                            "compositing",
                                            int(elapsed_s),
                                            int(total_duration),
                                        )
                                    else:
                                        elapsed_str = _format_duration(elapsed_s)
                                        click.echo(
                                            f"\r  [compositing] {elapsed_str}/{total_str} "
                                            f"({pct:.0f}%)",
                                            nl=False,
                                        )
                        except (ValueError, ZeroDivisionError):
                            pass
            except Exception:
                pass

            proc.wait(timeout=timeout)
            if reporter is None:
                click.echo("")  # newline after progress

        if proc.returncode != 0:
            stderr_output = stderr_path.read_text()[-500:] if stderr_path.exists() else ""
            msg = f"Final concat failed: {stderr_output}"
            if reporter is not None:
                reporter.error(msg)
            else:
                click.echo(f"  Error: {msg}", err=True)
            return False
        if reporter is not None:
            reporter.phase_complete("compositing")
        return True
    except subprocess.TimeoutExpired:
        proc.kill()
        msg = f"Final concat timed out after {timeout}s"
        if reporter is not None:
            reporter.error(msg)
        else:
            click.echo(f"\n  Error: {msg}", err=True)
        return False
    except Exception as e:
        msg = f"Final concat failed: {e}"
        if reporter is not None:
            reporter.error(msg)
        else:
            click.echo(f"\n  Error: {msg}", err=True)
        return False


def _format_duration(seconds: float) -> str:
    """Format seconds as MM:SS or H:MM:SS."""
    s = int(seconds)
    if s >= 3600:
        return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    return f"{s // 60}:{s % 60:02d}"


def _get_duration(path: Path) -> float:
    """Get video duration via ffprobe. Returns 0.0 on failure."""
    try:
        result = subprocess.run(
            [ffprobe_binary(), "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip())
    except (ValueError, subprocess.TimeoutExpired, Exception):
        return 0.0
