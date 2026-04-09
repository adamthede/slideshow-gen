"""System memory monitoring for resource-aware rendering."""

import os
import subprocess

import click


def get_available_memory_gb() -> float | None:
    """Get available system memory in GB. Returns None if unavailable."""
    try:
        # macOS: use vm_stat to get free + inactive pages
        result = subprocess.run(
            ["vm_stat"], capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None

        pages = {}
        for line in result.stdout.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                val = val.strip().rstrip(".")
                try:
                    pages[key.strip()] = int(val)
                except ValueError:
                    pass

        page_size = 16384  # Apple Silicon default
        free = pages.get("Pages free", 0)
        inactive = pages.get("Pages inactive", 0)
        available_bytes = (free + inactive) * page_size
        return available_bytes / (1024 ** 3)
    except Exception:
        return None


def auto_worker_count(requested: int) -> int:
    """Scale worker count based on available memory.

    - >= 16 GB available: use requested count (up to 4)
    - 8-16 GB: max 3
    - 4-8 GB: max 2
    - < 4 GB: 1
    """
    available = get_available_memory_gb()
    if available is None:
        return min(requested, 4)

    if available >= 16:
        cap = min(requested, 4)
    elif available >= 8:
        cap = min(requested, 3)
    elif available >= 4:
        cap = min(requested, 2)
    else:
        cap = 1

    if cap < requested:
        click.echo(
            f"  [memory] {available:.1f} GB available — "
            f"scaling workers from {requested} to {cap}",
        )

    return cap


def check_memory_pressure() -> str:
    """Check current memory pressure level.

    Returns 'normal', 'warning', or 'critical'.
    """
    available = get_available_memory_gb()
    if available is None:
        return "normal"

    if available < 2:
        return "critical"
    elif available < 4:
        return "warning"
    return "normal"


def log_memory_status(phase: str):
    """Log memory status between pipeline phases."""
    available = get_available_memory_gb()
    if available is not None:
        level = check_memory_pressure()
        if level == "critical":
            click.echo(
                f"  [memory] WARNING: Only {available:.1f} GB free before {phase}. "
                f"System may become unstable.",
                err=True,
            )
        elif level == "warning":
            click.echo(f"  [memory] {available:.1f} GB free before {phase}.")
