import pytest
from pathlib import Path
from slideshow_gen.discovery import MediaItem, scan_directories
from slideshow_gen.media import VideoInfo

def test_media_item_creation():
    item = MediaItem(path=Path("dummy.mp4"), media_type="video")
    assert item.media_type == "video"
    assert item.has_audio is False

def test_scan_directories_empty(tmp_path):
    items = scan_directories([tmp_path])
    assert len(items) == 0

def test_scan_directories_ignores_non_dirs():
    # Provide a file instead of a dir
    items = scan_directories([Path("nonexistent_dir")])
    assert len(items) == 0
