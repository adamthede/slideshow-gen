"""Dry-run manifest output."""

from pathlib import Path

import click

from .config import RenderConfig
from .discovery import MediaItem


def print_manifest(items: list[MediaItem], config: RenderConfig, output: Path):
    """Print a summary of discovered media and estimated output."""
    images = [i for i in items if i.media_type == "image"]
    videos = [i for i in items if i.media_type == "video"]

    image_duration = len(images) * config.slide_duration
    if len(images) > 1:
        image_duration -= (len(images) - 1) * config.fade_duration

    video_duration = sum(v.duration for v in videos)
    total_duration = image_duration + video_duration
    hours = int(total_duration // 3600)
    minutes = int((total_duration % 3600) // 60)
    seconds = int(total_duration % 60)

    # Rough file size estimate: ~5 MB/min at 1080p, ~15 MB/min at 4K
    mb_per_min = 15.0 if config.output_width > 1920 else 5.0
    est_size_mb = (total_duration / 60) * mb_per_min
    if est_size_mb > 1024:
        size_str = f"{est_size_mb / 1024:.1f} GB"
    else:
        size_str = f"{est_size_mb:.0f} MB"

    source_dirs = sorted(set(str(i.path.parent) for i in items))
    locations_found = sum(1 for i in items if i.display_location)
    dates_found = sum(1 for i in items if i.display_date)

    click.echo("")
    click.echo("=" * 64)
    click.echo("  SLIDESHOW MANIFEST")
    click.echo("=" * 64)
    click.echo("")
    click.echo(f"  Source directories:    {len(source_dirs)}")
    for d in source_dirs:
        click.echo(f"    {d}")
    click.echo("")
    click.echo(f"  Total items:          {len(items)}")
    click.echo(f"    Images:             {len(images)}")
    click.echo(f"    Videos:             {len(videos)}")
    click.echo(f"    With dates:         {dates_found}")
    click.echo(f"    With GPS location:  {locations_found}")
    click.echo("")
    click.echo(f"  Resolution:           {config.output_width}x{config.output_height}")
    click.echo(f"  Slide duration:       {config.slide_duration}s")
    click.echo(f"  Fade duration:        {config.fade_duration}s")
    click.echo(f"  FPS:                  {config.fps}")
    click.echo("")
    click.echo(f"  Estimated duration:   {hours}h {minutes:02d}m {seconds:02d}s")
    click.echo(f"  Estimated file size:  ~{size_str}")
    click.echo(f"  Output:               {output}")
    click.echo("")

    if items:
        first = items[0]
        last = items[-1]
        click.echo(f"  First: {first.path.name}")
        if first.display_date:
            click.echo(f"         {first.display_date}")
        if first.display_location:
            click.echo(f"         {first.display_location}")
        click.echo(f"  Last:  {last.path.name}")
        if last.display_date:
            click.echo(f"         {last.display_date}")
        if last.display_location:
            click.echo(f"         {last.display_location}")

    click.echo("")
    click.echo("=" * 64)
