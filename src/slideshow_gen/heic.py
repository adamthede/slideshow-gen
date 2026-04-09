"""HEIC-to-JPG conversion via pillow-heif."""

from pathlib import Path

from PIL import Image

# Register HEIF/HEIC support with Pillow at import time
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False

HEIC_EXTENSIONS = {".heic", ".heif"}


def is_heic(path: Path) -> bool:
    """Check if a file is HEIC/HEIF format."""
    return path.suffix.lower() in HEIC_EXTENSIONS


def convert_heic_to_jpg(source: Path, temp_dir: Path) -> Path:
    """Convert a HEIC/HEIF file to JPG, preserving EXIF metadata.

    Returns the path to the converted JPG file.
    """
    if not HEIC_SUPPORTED:
        raise RuntimeError(
            "HEIC support not available. Install pillow-heif: pip install pillow-heif"
        )

    output_path = temp_dir / f"{source.stem}.jpg"

    with Image.open(source) as img:
        # Preserve EXIF data
        exif_data = img.info.get("exif")
        save_kwargs = {"quality": 95, "optimize": True}
        if exif_data:
            save_kwargs["exif"] = exif_data
        img.save(output_path, "JPEG", **save_kwargs)

    return output_path
