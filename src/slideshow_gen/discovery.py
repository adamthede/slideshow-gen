"""File discovery, sorting, and duplicate detection."""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import click

from .config import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from .metadata import read_exif, reverse_geocode, get_date_for_item
from .media import get_image_info, get_video_info


@dataclass
class MediaItem:
    path: Path
    media_type: str  # "image" or "video"
    sort_key: str = ""
    width: int = 0
    height: int = 0
    duration: float = 0.0
    display_date: str = ""
    display_location: str = ""
    gps_lat: float | None = None
    gps_lon: float | None = None
    parsed_date: datetime | None = None
    content_hash: str = ""


def scan_directories(
    dirs: list[Path], verbose: bool = False, recursive: bool = False
) -> list[MediaItem]:
    """Scan directories for supported image and video files, enriching with metadata."""
    items = []

    for dir_path in dirs:
        if not dir_path.is_dir():
            click.echo(f"  Warning: {dir_path} is not a directory, skipping.", err=True)
            continue

        iterator = dir_path.rglob("*") if recursive else dir_path.iterdir()
        files = sorted(f for f in iterator if f.is_file())
        for file_path in files:
            ext = file_path.suffix.lower()

            if ext in IMAGE_EXTENSIONS:
                item = MediaItem(path=file_path, media_type="image", sort_key=file_path.name)

                # Read EXIF
                exif = read_exif(file_path)

                # Get dimensions
                info = get_image_info(file_path)
                if info:
                    item.width = info.width
                    item.height = info.height

                # Get date
                item.parsed_date, item.display_date = get_date_for_item(file_path, exif)

                # Get location from GPS
                if exif.gps_lat is not None and exif.gps_lon is not None:
                    item.gps_lat = exif.gps_lat
                    item.gps_lon = exif.gps_lon
                    location = reverse_geocode(exif.gps_lat, exif.gps_lon)
                    if location:
                        item.display_location = location

                items.append(item)

            elif ext in VIDEO_EXTENSIONS:
                item = MediaItem(path=file_path, media_type="video", sort_key=file_path.name)

                # Get video info
                info = get_video_info(file_path)
                if info:
                    item.width = info.width
                    item.height = info.height
                    item.duration = info.duration

                # Get date from filename
                item.parsed_date, item.display_date = get_date_for_item(file_path)

                items.append(item)

    if verbose:
        click.echo(f"  Found {len(items)} media items across {len(dirs)} directories.")

    return items


def sort_items(items: list[MediaItem], random: bool = False) -> list[MediaItem]:
    """Sort items chronologically by filename, or shuffle if random."""
    if random:
        import random as rand_module
        shuffled = list(items)
        rand_module.shuffle(shuffled)
        return shuffled
    return sorted(items, key=lambda item: item.sort_key)


def detect_duplicates(items: list[MediaItem]) -> list[tuple[MediaItem, MediaItem]]:
    """Detect potential duplicates via partial content hash."""
    hash_map: dict[str, MediaItem] = {}
    duplicates = []

    for item in items:
        h = _fast_hash(item.path)
        if not h:
            continue
        item.content_hash = h
        if h in hash_map:
            duplicates.append((hash_map[h], item))
        else:
            hash_map[h] = item

    return duplicates


def _fast_hash(path: Path) -> str:
    """SHA-256 of first 64KB + file size for fast duplicate detection."""
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            chunk = f.read(65536)
        h = hashlib.sha256(chunk)
        h.update(str(size).encode())
        return h.hexdigest()
    except OSError:
        return ""
