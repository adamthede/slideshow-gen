"""EXIF extraction, filename parsing, and reverse geocoding."""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import exifread
import reverse_geocoder as rg

# Matches multiple filename conventions:
#   YYYY-MM-DD HH-MM-SS Photographer - Album (Camera).ext
#   YYYY MM-DD HHMMSS Photographer - Album.ext
#   YYYY-MM-DD HHMMSS ...
FILENAME_PATTERNS = [
    # YYYY-MM-DD HH-MM-SS ...
    re.compile(r"^(\d{4})-(\d{2})-(\d{2})\s+(\d{2})-(\d{2})-(\d{2})\s*(.*)?$"),
    # YYYY MM-DD HHMMSS ... (space-separated date, no separators in time)
    re.compile(r"^(\d{4})\s+(\d{2})-(\d{2})\s+(\d{2})(\d{2})(\d{2})\s*(.*)?$"),
    # YYYY-MM-DD HHMMSS ... (dashed date, no separators in time)
    re.compile(r"^(\d{4})-(\d{2})-(\d{2})\s+(\d{2})(\d{2})(\d{2})\s*(.*)?$"),
    # YYYY MM-DD ... (date only, no time)
    re.compile(r"^(\d{4})\s+(\d{2})-(\d{2})\s*(.*)?$"),
]


@dataclass
class ParsedFilename:
    date: datetime | None = None
    photographer: str = ""
    album: str = ""
    camera: str = ""


@dataclass
class ExifData:
    date: datetime | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None
    orientation: int = 1
    width: int = 0
    height: int = 0


def parse_filename(path: Path) -> ParsedFilename:
    """Extract date and metadata from the filename convention."""
    stem = path.stem

    for pattern in FILENAME_PATTERNS:
        match = pattern.match(stem)
        if match:
            break
    else:
        return ParsedFilename()

    groups = match.groups()
    try:
        year = int(groups[0])
        month = int(groups[1])
        day = int(groups[2])
        # Some patterns have time, some don't
        if len(groups) >= 7:
            hour = int(groups[3])
            minute = int(groups[4])
            second = int(groups[5])
            remainder_idx = 6
        else:
            hour = minute = second = 0
            remainder_idx = 3
        dt = datetime(year, month, day, hour, minute, second)
    except (ValueError, IndexError):
        return ParsedFilename()

    remainder = (groups[remainder_idx] if remainder_idx < len(groups) else "").strip()
    photographer = ""
    album = ""
    camera = ""

    if " - " in remainder:
        parts = remainder.split(" - ", 1)
        photographer = parts[0].strip()
        album_part = parts[1].strip()
        camera_match = re.match(r"^(.*?)\s*\(([^)]+)\)\s*$", album_part)
        if camera_match:
            album = camera_match.group(1).strip()
            camera = camera_match.group(2).strip()
        else:
            album = album_part

    return ParsedFilename(date=dt, photographer=photographer, album=album, camera=camera)


def _convert_gps_to_decimal(values, ref: str) -> float | None:
    """Convert EXIF GPS rational values to decimal degrees."""
    try:
        parts = [float(v.num) / float(v.den) if hasattr(v, 'num') else float(v) for v in values]
        decimal = parts[0] + parts[1] / 60.0 + parts[2] / 3600.0
        if ref in ("S", "W"):
            decimal = -decimal
        return decimal
    except (ValueError, TypeError, IndexError, ZeroDivisionError):
        return None


def read_exif(path: Path) -> ExifData:
    """Read EXIF metadata from an image file."""
    import logging

    result = ExifData()
    try:
        # Suppress ExifRead's noisy warnings (e.g., "PNG file does not have exif data")
        logging.disable(logging.CRITICAL)
        try:
            with open(path, "rb") as f:
                tags = exifread.process_file(f, details=False)
        finally:
            logging.disable(logging.NOTSET)
    except Exception:
        return result

    # Date
    for tag_name in ("EXIF DateTimeOriginal", "EXIF DateTimeDigitized", "Image DateTime"):
        if tag_name in tags:
            try:
                result.date = datetime.strptime(str(tags[tag_name]), "%Y:%m:%d %H:%M:%S")
                break
            except ValueError:
                continue

    # GPS
    lat_tag = tags.get("GPS GPSLatitude")
    lat_ref = tags.get("GPS GPSLatitudeRef")
    lon_tag = tags.get("GPS GPSLongitude")
    lon_ref = tags.get("GPS GPSLongitudeRef")

    if lat_tag and lat_ref and lon_tag and lon_ref:
        result.gps_lat = _convert_gps_to_decimal(lat_tag.values, str(lat_ref))
        result.gps_lon = _convert_gps_to_decimal(lon_tag.values, str(lon_ref))

    # Orientation
    if "Image Orientation" in tags:
        try:
            result.orientation = int(str(tags["Image Orientation"]).split()[0])
        except (ValueError, IndexError):
            pass

    return result


# Module-level geocoder cache to avoid repeated lookups for same coordinates
_geocode_cache: dict[tuple[float, float], str] = {}


def reverse_geocode(lat: float, lon: float) -> str | None:
    """Reverse geocode GPS coordinates to 'City, State' or 'City, Country'."""
    cache_key = (round(lat, 4), round(lon, 4))
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]

    try:
        results = rg.search([(lat, lon)], verbose=False)
        if not results:
            return None

        result = results[0]
        city = result.get("name", "")
        country_code = result.get("cc", "")
        admin1 = result.get("admin1", "")

        if country_code == "US" and admin1:
            location = f"{city}, {admin1}" if city else admin1
        elif city and country_code:
            # Map country codes to names for common ones
            country_names = {
                "GB": "England", "FR": "France", "DE": "Germany",
                "IT": "Italy", "ES": "Spain", "JP": "Japan",
                "AU": "Australia", "CA": "Canada", "MX": "Mexico",
                "IS": "Iceland", "NL": "Netherlands", "SE": "Sweden",
                "NO": "Norway", "DK": "Denmark", "IE": "Ireland",
            }
            country = country_names.get(country_code, country_code)
            location = f"{city}, {country}"
        else:
            location = city or None

        if location:
            _geocode_cache[cache_key] = location
        return location
    except Exception:
        return None


def format_date(dt: datetime) -> str:
    """Format a datetime as human-readable: 'March 15, 2019'."""
    return dt.strftime("%B %-d, %Y")


def get_date_for_item(path: Path, exif_data: ExifData | None = None) -> tuple[datetime | None, str]:
    """Get the best available date for a media item. Returns (datetime, formatted_string).

    Fallback chain: filename -> EXIF -> file mtime.
    """
    # Try filename first
    parsed = parse_filename(path)
    if parsed.date:
        return parsed.date, format_date(parsed.date)

    # Try EXIF
    if exif_data and exif_data.date:
        return exif_data.date, format_date(exif_data.date)

    # Fall back to file modification time
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return mtime, format_date(mtime)
    except OSError:
        return None, ""
