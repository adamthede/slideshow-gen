"""Click CLI entry point for slideshow-gen."""

from pathlib import Path

import click

from .config import RESOLUTIONS, RenderConfig


@click.group()
@click.version_option()
def cli():
    """Slideshow Generator — Ken Burns slideshows with metadata overlays."""
    pass


@cli.command()
@click.option(
    "--dir", "dirs",
    multiple=True,
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Source directory to scan (can be repeated).",
)
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path. Default: ~/Desktop/slideshow-{resolution}.mp4",
)
@click.option(
    "--resolution",
    type=click.Choice(list(RESOLUTIONS.keys())),
    default="1080p",
    help="Output resolution.",
)
@click.option("--slide-duration", type=float, default=4.0, help="Seconds per image.")
@click.option("--fade-duration", type=float, default=0.5, help="Crossfade duration in seconds.")
@click.option("--fps", type=int, default=30, help="Output framerate.")
@click.option("--zoom-rate", type=float, default=0.1, help="Ken Burns zoom intensity.")
@click.option("--static", is_flag=True, help="Skip Ken Burns — static images with crossfades (much faster).")
@click.option("--random", "random_order", is_flag=True, help="Random order instead of chronological.")
@click.option("--no-overlays", is_flag=True, help="Disable all text overlays.")
@click.option("--no-date", is_flag=True, help="Disable date overlay.")
@click.option("--no-location", is_flag=True, help="Disable location overlay.")
@click.option("--workers", type=int, default=4, help="Parallel FFmpeg processes.")
@click.option("--batch-size", type=int, default=20, help="Images per batch reduction.")
@click.option(
    "--temp-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Directory for temp files. Default: system temp. Use for large renders.",
)
@click.option("--chunk-duration", type=int, default=None, help="Split output into chunks of N minutes (e.g. 60).")
@click.option("--recursive", "-r", is_flag=True, help="Recursively scan subdirectories for media files.")
@click.option("--dry-run", is_flag=True, help="Print manifest without rendering.")
@click.option("--keep-temp", is_flag=True, help="Keep temp directory after render for debugging.")
@click.option("--verbose", is_flag=True, help="Detailed progress output.")
def render(
    dirs,
    output,
    resolution,
    slide_duration,
    fade_duration,
    fps,
    zoom_rate,
    static,
    random_order,
    no_overlays,
    no_date,
    no_location,
    workers,
    batch_size,
    temp_dir,
    chunk_duration,
    recursive,
    dry_run,
    keep_temp,
    verbose,
):
    """Render a slideshow from one or more image/video directories."""
    if output is None:
        output = Path.home() / "Desktop" / f"slideshow-{resolution}.mp4"

    show_date = not no_overlays and not no_date
    show_location = not no_overlays and not no_location

    config = RenderConfig.from_resolution(
        resolution,
        slide_duration=slide_duration,
        fade_duration=fade_duration,
        fps=fps,
        zoom_rate=zoom_rate,
        static=static,
        random_order=random_order,
        show_date=show_date,
        show_location=show_location,
        workers=workers,
        batch_size=batch_size,
        verbose=verbose,
    )

    if verbose:
        click.echo(f"Config: {config}")
        click.echo(f"Directories: {[str(d) for d in dirs]}")
        click.echo(f"Output: {output}")

    if dry_run:
        from .discovery import scan_directories, sort_items
        from .manifest import print_manifest

        items = scan_directories(list(dirs), recursive=recursive)
        items = sort_items(items, random=config.random_order)
        print_manifest(items, config, output)
    else:
        from .pipeline import RenderPipeline

        # Convert chunk duration from minutes to seconds
        chunk_secs = chunk_duration * 60 if chunk_duration else None

        pipeline = RenderPipeline(
            config=config, dirs=list(dirs), output=output,
            temp_base=temp_dir, chunk_seconds=chunk_secs,
            keep_temp=keep_temp, recursive=recursive,
        )
        pipeline.run()
