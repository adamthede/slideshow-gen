"""Three-phase render pipeline orchestrator.

Phase 1: Each image -> individual temp clip (Ken Burns + overlay, parallel)
Phase 2: Consecutive image clips -> batches with crossfades
Phase 3: Batches + video clips -> final composite
"""

import gc
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import click

from .config import RenderConfig
from .discovery import MediaItem, scan_directories, sort_items
from .ffmpeg import (
    check_ffmpeg,
    parallel_render,
    render_batch,
    render_final_concat,
    render_image_to_clip,
    render_static_batch,
)
from .memutil import auto_worker_count, log_memory_status
from .overlay import generate_overlay_filters


class RenderPipeline:
    def __init__(
        self, config: RenderConfig, dirs: list[Path], output: Path,
        temp_base: Path | None = None, chunk_seconds: float | None = None,
        keep_temp: bool = False, recursive: bool = False,
    ):
        self.config = config
        self.dirs = dirs
        self.output = output
        self.temp_base = temp_base
        self.chunk_seconds = chunk_seconds
        self.keep_temp = keep_temp
        self.recursive = recursive
        self.temp_dir: Path | None = None

    def run(self):
        """Execute the full three-phase render pipeline."""
        start_time = time.time()

        # Preflight checks
        if not check_ffmpeg():
            click.echo("Error: FFmpeg not found. Install via: brew install ffmpeg", err=True)
            return

        # Discover media
        click.echo("\n  Scanning directories...")
        items = scan_directories(self.dirs, verbose=self.config.verbose, recursive=self.recursive)
        items = sort_items(items, random=self.config.random_order)

        if not items:
            click.echo("  Error: No supported media files found.", err=True)
            return

        images = [i for i in items if i.media_type == "image"]
        videos = [i for i in items if i.media_type == "video"]
        click.echo(f"  Found {len(images)} images and {len(videos)} videos.")

        # Create temp directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix="slideshow-gen-", dir=self.temp_base))
        click.echo(f"  Temp directory: {self.temp_dir}")

        try:
            if self.config.static:
                batched_segments = self._static_pipeline(items, images, videos)
            else:
                batched_segments = self._kenburns_pipeline(items, images, videos)

            if not batched_segments:
                click.echo("  Error: No segments to composite.", err=True)
                return

            gc.collect()
            log_memory_status("final composite")

            # Log segment summary for debugging
            if self.config.verbose:
                click.echo(f"\n  [segments] {len(batched_segments)} segments for final composite:")
                for si, seg in enumerate(batched_segments):
                    seg_type = seg.get("type", "?")
                    seg_dur = seg.get("duration", 0)
                    seg_path = seg.get("path", "?")
                    click.echo(f"    {si:3d}. [{seg_type:5s}] {seg_dur:8.2f}s  {Path(seg_path).name}")

            # Phase 3: Final composite — chunked or single output
            if self.chunk_seconds:
                outputs = self._chunked_output(batched_segments)
            else:
                outputs = self._single_output(batched_segments)

            if not outputs:
                click.echo("  Error: Final composite failed.", err=True)
                return

            elapsed = time.time() - start_time
            total_size = sum(p.stat().st_size for p in outputs) / (1024 * 1024)
            click.echo(f"\n  Done! {total_size:.1f} MB in {elapsed:.0f}s")
            for p in outputs:
                click.echo(f"  Output: {p}")

        finally:
            # Cleanup temp directory (unless --keep-temp)
            if self.temp_dir and self.temp_dir.exists():
                if self.keep_temp:
                    click.echo(f"  Temp directory preserved: {self.temp_dir}")
                else:
                    shutil.rmtree(self.temp_dir, ignore_errors=True)
                    if self.config.verbose:
                        click.echo(f"  Cleaned up temp directory.")

    def _single_output(self, segments: list[dict]) -> list[Path]:
        """Render all segments into a single output file."""
        segment_paths = [s["path"] for s in segments]

        if len(segment_paths) == 1:
            self._single_segment_output(segment_paths[0], segments[0]["duration"])
            return [self.output] if self.output.exists() else []

        success = render_final_concat(
            segment_paths, self.output, self.config, self.temp_dir,
        )
        return [self.output] if success else []

    def _chunked_output(self, segments: list[dict]) -> list[Path]:
        """Split segments into time-based chunks and render each as a separate file."""
        chunks = []
        current_chunk: list[dict] = []
        current_duration = 0.0

        for seg in segments:
            current_chunk.append(seg)
            current_duration += seg["duration"]

            if current_duration >= self.chunk_seconds:
                chunks.append(current_chunk)
                current_chunk = []
                current_duration = 0.0

        # Flush remaining
        if current_chunk:
            chunks.append(current_chunk)

        if len(chunks) == 1:
            # Fits in one chunk — no numbering needed
            return self._single_output(chunks[0])

        # Generate numbered output paths: name-01.mp4, name-02.mp4, ...
        stem = self.output.stem
        suffix = self.output.suffix
        parent = self.output.parent
        pad = len(str(len(chunks)))

        outputs = []
        for ci, chunk in enumerate(chunks, 1):
            chunk_output = parent / f"{stem}-{ci:0{pad}d}{suffix}"
            chunk_paths = [s["path"] for s in chunk]
            chunk_dur = sum(s["duration"] for s in chunk)
            chunk_mins = chunk_dur / 60

            click.echo(f"\n  [chunk {ci}/{len(chunks)}] {len(chunk_paths)} segments, ~{chunk_mins:.0f} min")

            if len(chunk_paths) == 1:
                self.output = chunk_output
                self._single_segment_output(chunk_paths[0], chunk[0]["duration"])
                if chunk_output.exists():
                    outputs.append(chunk_output)
            else:
                success = render_final_concat(
                    chunk_paths, chunk_output, self.config, self.temp_dir,
                )
                if success:
                    outputs.append(chunk_output)
                else:
                    click.echo(f"  Error: Chunk {ci} failed.", err=True)

        return outputs

    def _kenburns_pipeline(
        self, items: list[MediaItem], images: list[MediaItem], videos: list[MediaItem],
    ) -> list[dict]:
        """Ken Burns pipeline: Phase 1 (parallel clips) → Phase 2 (batch reduce)."""
        rendered_clips = parallel_render(items, self.temp_dir, self.config)

        if not rendered_clips and not videos:
            click.echo("  Error: No images rendered successfully.", err=True)
            return []

        gc.collect()
        log_memory_status("timeline build")

        segments = self._build_timeline(items, rendered_clips, videos)
        if not segments:
            return []

        gc.collect()
        log_memory_status("batch reduction")

        return self._batch_reduce(segments)

    def _static_pipeline(
        self, items: list[MediaItem], images: list[MediaItem], videos: list[MediaItem],
    ) -> list[dict]:
        """Static pipeline: images go directly into batches (no Phase 1)."""
        click.echo(f"\n  [static] Building batches directly from {len(images)} images...")

        # Walk items in order, grouping consecutive images into batches
        # Videos break batch boundaries (same as Ken Burns path)
        batched = []
        current_batch: list[MediaItem] = []
        batch_num = 0

        # Pre-count total batches for progress
        total_batches = 0
        count = 0
        for item in items:
            if item.media_type == "video":
                if count > 0:
                    total_batches += (count + self.config.batch_size - 1) // self.config.batch_size
                count = 0
                total_batches += 1  # video segment
            else:
                count += 1
        if count > 0:
            total_batches += (count + self.config.batch_size - 1) // self.config.batch_size

        for item in items:
            if item.media_type == "video":
                # Flush current image batch
                if current_batch:
                    batched.extend(
                        self._flush_static_batch(current_batch, len(batched), batch_num, total_batches)
                    )
                    batch_num += len(current_batch) // self.config.batch_size + (1 if len(current_batch) % self.config.batch_size else 0)
                    current_batch = []
                # Prepare video
                batch_num += 1
                video_path = self._prepare_video_clip(item)
                if video_path:
                    batched.append({
                        "type": "video",
                        "path": video_path,
                        "duration": item.duration,
                    })
            else:
                current_batch.append(item)

        # Flush remaining
        if current_batch:
            batched.extend(
                self._flush_static_batch(current_batch, len(batched), batch_num, total_batches)
            )

        click.echo(f"  [static] {len(batched)} segments ready.")
        return batched

    def _flush_static_batch(
        self, items: list[MediaItem], batch_offset: int, batch_num: int, total_batches: int,
    ) -> list[dict]:
        """Split items into batch_size groups and render each as a static batch."""
        results = []
        batch_size = self.config.batch_size

        for i in range(0, len(items), batch_size):
            chunk = items[i:i + batch_size]
            batch_num += 1
            click.echo(f"  [static] [{batch_num}/{total_batches}] {len(chunk)} images...")

            batch_idx = batch_offset + len(results)
            result = render_static_batch(chunk, batch_idx, self.temp_dir, self.config)

            if result:
                slide_dur = self.config.slide_duration
                fade_dur = self.config.fade_duration
                batch_dur = len(chunk) * slide_dur - (len(chunk) - 1) * fade_dur
                results.append({"type": "batch", "path": result, "duration": batch_dur})
            else:
                click.echo(f"  Warning: Static batch {batch_idx} failed, skipping.", err=True)

        return results

    def _build_timeline(
        self,
        items: list[MediaItem],
        rendered_clips: list[tuple[int, Path]],
        videos: list[MediaItem],
    ) -> list[dict]:
        """Build timeline segments from rendered clips and video items."""
        clip_map = {idx: path for idx, path in rendered_clips}
        segments = []

        for i, item in enumerate(items):
            if item.media_type == "image" and i in clip_map:
                segments.append({
                    "type": "image",
                    "path": clip_map[i],
                    "duration": self.config.slide_duration,
                    "item": item,
                })
            elif item.media_type == "video":
                # Prepare video clip with overlay
                video_path = self._prepare_video_clip(item)
                if video_path:
                    segments.append({
                        "type": "video",
                        "path": video_path,
                        "duration": item.duration,
                        "item": item,
                    })

        return segments

    def _prepare_video_clip(self, item: MediaItem) -> Path | None:
        """Scale a video clip to output resolution and add overlays."""
        output_path = self.temp_dir / f"temp-video-{item.path.stem}.mp4"

        # Build filter: scale + pad + fps + pixel format normalize + edge fades
        fade_dur = self.config.fade_duration
        filters = [
            f"scale=w={self.config.output_width}:h={self.config.output_height}"
            f":force_original_aspect_ratio=decrease:flags=lanczos",
            f"pad={self.config.output_width}:{self.config.output_height}:(ow-iw)/2:(oh-ih)/2",
            f"fps={self.config.fps}",
            "format=pix_fmts=yuv420p",
        ]

        # Edge fades for concat assembly (skip if video is too short)
        if fade_dur > 0 and item.duration > fade_dur * 2:
            filters.append(f"fade=t=in:st=0:d={fade_dur}")
            filters.append(f"fade=t=out:st={item.duration - fade_dur}:d={fade_dur}")

        overlay_filters = generate_overlay_filters(
            date_str=item.display_date or None,
            location_str=item.display_location or None,
            config=self.config,
            is_video=True,
        )
        filters.extend(overlay_filters)

        cmd = [
            "ffmpeg", "-y", "-hide_banner",
            "-v", "warning" if not self.config.verbose else "info",
            "-i", str(item.path),
            "-vf", ",".join(filters),
            "-pix_fmt", "yuv420p",
            "-c:v", "h264_videotoolbox",
            "-b:v", "20M",
            "-an",
            str(output_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            if result.returncode != 0:
                click.echo(
                    f"  Warning: Video prep failed for {item.path.name}: {result.stderr[:200]}",
                    err=True,
                )
                return None
            return output_path
        except Exception as e:
            click.echo(f"  Warning: Video prep failed for {item.path.name}: {e}", err=True)
            return None

    def _count_batches(self, segments: list[dict]) -> int:
        """Pre-count how many batches will be created for progress display."""
        count = 0
        current_size = 0
        for seg in segments:
            if seg["type"] == "video":
                if current_size > 1:
                    count += 1
                current_size = 0
                count += 1  # video segment
            else:
                current_size += 1
                if current_size >= self.config.batch_size:
                    count += 1
                    current_size = 0
        if current_size > 1:
            count += 1
        elif current_size == 1:
            count += 1
        return count

    def _batch_reduce(self, segments: list[dict]) -> list[dict]:
        """Reduce consecutive image segments into batches."""
        if len(segments) <= 1:
            return segments

        total_batches = self._count_batches(segments)
        batched = []
        current_batch: list[dict] = []
        batch_num = 0

        for seg in segments:
            if seg["type"] == "video":
                # Flush current image batch
                if current_batch:
                    batch_num += 1
                    batched.extend(self._flush_batch(current_batch, len(batched), batch_num, total_batches))
                    current_batch = []
                batch_num += 1
                batched.append(seg)
            else:
                current_batch.append(seg)
                if len(current_batch) >= self.config.batch_size:
                    batch_num += 1
                    batched.extend(self._flush_batch(current_batch, len(batched), batch_num, total_batches))
                    current_batch = []

        # Flush remaining
        if current_batch:
            batch_num += 1
            batched.extend(self._flush_batch(current_batch, len(batched), batch_num, total_batches))

        return batched

    def _flush_batch(self, batch: list[dict], batch_index: int, batch_num: int, total_batches: int) -> list[dict]:
        """Reduce a batch of image clips into a single composited segment."""
        if len(batch) == 1:
            return batch

        clip_paths = [s["path"] for s in batch]
        click.echo(f"  [batching] [{batch_num}/{total_batches}] {len(clip_paths)} clips...")

        result = render_batch(clip_paths, batch_index, self.temp_dir, self.config)

        if result:
            # Calculate batch duration
            slide_dur = self.config.slide_duration
            fade_dur = self.config.fade_duration
            batch_dur = len(clip_paths) * slide_dur - (len(clip_paths) - 1) * fade_dur

            # Progressive cleanup: delete individual clips
            for p in clip_paths:
                try:
                    p.unlink()
                except OSError:
                    pass

            return [{"type": "batch", "path": result, "duration": batch_dur}]
        else:
            # Batch failed — fall back to individual clips
            click.echo(f"  Warning: Batch {batch_index} failed, using individual clips.", err=True)
            return batch

    def _single_segment_output(self, segment_path: Path, duration: float):
        """When there's only one segment, re-encode it as the final output."""
        click.echo(f"\n  [compositing] Single segment — encoding final output...")

        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-v", "warning",
            "-i", str(segment_path),
        ]

        if self.config.audio_track:
            cmd.extend([
                "-stream_loop", "-1",
                "-i", str(self.config.audio_track),
                "-filter_complex", f"[1:a]volume={self.config.audio_volume}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0[a]",
                "-map", "0:v",
                "-map", "[a]"
            ])

        cmd.extend([
            "-c:v", "h264_videotoolbox",
            "-b:v", "20M",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(self.output),
        ])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if result.returncode != 0:
            click.echo(f"  Error: Final encode failed: {result.stderr[:300]}", err=True)
",
            "-movflags", "+faststart",
            "-an",
            str(self.output),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if result.returncode != 0:
            click.echo(f"  Error: Final encode failed: {result.stderr[:300]}", err=True)
