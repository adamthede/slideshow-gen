"""Reporter abstraction for pipeline events.

Two implementations:

- ConsoleReporter: human-readable text via click.echo (the historical behavior).
- JsonReporter: one JSON object per line on stdout, designed for an embedding
  process (the macOS app sidecar) to parse.

Pipeline code calls semantic methods (phase_started, progress, warning, ...)
and the reporter decides how to render them. New events should be added here
and documented in docs/sidecar-protocol.md.
"""

from __future__ import annotations

import json
import sys
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import click


PROTOCOL_VERSION = 1


class Reporter(ABC):
    """Interface for emitting pipeline events."""

    @abstractmethod
    def started(self, config: dict[str, Any]) -> None: ...

    @abstractmethod
    def discovery_complete(
        self,
        images: int,
        videos: int,
        date_range: tuple[str, str] | None = None,
        gps_coverage_percent: float | None = None,
        duplicates_detected: int | None = None,
        date_histogram: list[dict[str, Any]] | None = None,
    ) -> None: ...

    @abstractmethod
    def estimate(
        self,
        duration_s: float,
        size_bytes: int,
        image_duration_s: float,
        video_duration_s: float,
    ) -> None: ...

    @abstractmethod
    def phase_started(self, phase: str, total: int | None = None) -> None: ...

    @abstractmethod
    def progress(
        self, phase: str, done: int, total: int, message: str | None = None
    ) -> None: ...

    @abstractmethod
    def phase_complete(self, phase: str, message: str | None = None) -> None: ...

    @abstractmethod
    def info(self, message: str) -> None: ...

    @abstractmethod
    def warning(self, message: str, file: str | None = None) -> None: ...

    @abstractmethod
    def error(self, message: str) -> None: ...

    @abstractmethod
    def item_failed(
        self,
        phase: str,
        path: str,
        reason: str,
        detail: str | None = None,
    ) -> None: ...

    @abstractmethod
    def complete(
        self,
        outputs: list[Path],
        elapsed_s: float,
        items_skipped: int = 0,
    ) -> None: ...

    @abstractmethod
    def cancelled(self, message: str | None = None) -> None: ...


class ConsoleReporter(Reporter):
    """Human-readable output via click.echo. Preserves the original CLI feel."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose

    def started(self, config: dict[str, Any]) -> None:
        if self.verbose:
            click.echo(f"  [pipeline] starting render with config: {config}")

    def discovery_complete(
        self,
        images: int,
        videos: int,
        date_range: tuple[str, str] | None = None,
        gps_coverage_percent: float | None = None,
        duplicates_detected: int | None = None,
        date_histogram: list[dict[str, Any]] | None = None,
    ) -> None:
        msg = f"  Found {images} images and {videos} videos."
        if date_range:
            msg += f" (dates: {date_range[0]} to {date_range[1]})"
        if gps_coverage_percent is not None:
            msg += f" ({gps_coverage_percent:.1f}% with GPS)"
        if duplicates_detected is not None and duplicates_detected > 0:
            msg += f" ({duplicates_detected} duplicates detected)"
        click.echo(msg)

    def estimate(
        self,
        duration_s: float,
        size_bytes: int,
        image_duration_s: float,
        video_duration_s: float,
    ) -> None:
        from .estimate import format_duration, format_size, TOTAL_BITRATE_BPS

        click.echo(
            f"  [estimate] Duration: {format_duration(duration_s)} "
            f"(images {format_duration(image_duration_s)} + "
            f"videos {format_duration(video_duration_s)})"
        )
        click.echo(
            f"  [estimate] Output size: ~{format_size(size_bytes)} "
            f"(at {TOTAL_BITRATE_BPS / 1_000_000:.1f} Mbps, ±20%)"
        )

    def phase_started(self, phase: str, total: int | None = None) -> None:
        suffix = f" ({total} items)" if total is not None else ""
        click.echo(f"\n  [{phase}] starting{suffix}...")

    def progress(
        self, phase: str, done: int, total: int, message: str | None = None
    ) -> None:
        if total <= 0:
            return
        pct = done / total * 100
        tail = f" {message}" if message else ""
        click.echo(f"\r  [{phase}] [{done}/{total}] {pct:.1f}%{tail}", nl=False)
        if done == total:
            click.echo("")  # newline at end

    def phase_complete(self, phase: str, message: str | None = None) -> None:
        tail = f" — {message}" if message else ""
        click.echo(f"  [{phase}] complete{tail}.")

    def info(self, message: str) -> None:
        click.echo(f"  {message}")

    def warning(self, message: str, file: str | None = None) -> None:
        prefix = f"  Warning: " if file is None else f"  Warning ({file}): "
        click.echo(f"{prefix}{message}", err=True)

    def error(self, message: str) -> None:
        click.echo(f"  Error: {message}", err=True)

    def item_failed(
        self,
        phase: str,
        path: str,
        reason: str,
        detail: str | None = None,
    ) -> None:
        # Mirror the existing warning style so console users still see skipped
        # items. The IPC event carries the richer structured payload.
        name = Path(path).name if path else "<unknown>"
        click.echo(f"  Skipped ({phase}): {name} — {reason}", err=True)

    def complete(
        self,
        outputs: list[Path],
        elapsed_s: float,
        items_skipped: int = 0,
    ) -> None:
        total_size = sum(p.stat().st_size for p in outputs if p.exists()) / (1024 * 1024)
        skipped_suffix = f" ({items_skipped} skipped)" if items_skipped else ""
        click.echo(f"\n  Done! {total_size:.1f} MB in {elapsed_s:.0f}s{skipped_suffix}")
        for p in outputs:
            click.echo(f"  Output: {p}")

    def cancelled(self, message: str | None = None) -> None:
        tail = f" — {message}" if message else ""
        click.echo(f"\n  Cancelled{tail}.", err=True)


class JsonReporter(Reporter):
    """One JSON object per line on stdout. Designed for sidecar IPC.

    Warnings and errors also flow on stdout (as events), not stderr, so the
    embedding process only needs to parse one stream. The underlying CLI may
    still print framework-level text to stderr in failure modes; the
    embedding process should capture stderr separately for diagnostics.
    """

    def __init__(self) -> None:
        self._t0 = time.time()

    def _emit(self, event_type: str, **fields: Any) -> None:
        payload = {
            "v": PROTOCOL_VERSION,
            "t": round(time.time() - self._t0, 3),
            "type": event_type,
            **fields,
        }
        # Stringify Path values for JSON safety.
        for k, v in list(payload.items()):
            if isinstance(v, Path):
                payload[k] = str(v)
            elif isinstance(v, list):
                payload[k] = [str(x) if isinstance(x, Path) else x for x in v]
        sys.stdout.write(json.dumps(payload) + "\n")
        sys.stdout.flush()

    def started(self, config: dict[str, Any]) -> None:
        safe_config = {
            k: (str(v) if isinstance(v, Path) else v) for k, v in config.items()
        }
        self._emit("started", config=safe_config)

    def discovery_complete(
        self,
        images: int,
        videos: int,
        date_range: tuple[str, str] | None = None,
        gps_coverage_percent: float | None = None,
        duplicates_detected: int | None = None,
        date_histogram: list[dict[str, Any]] | None = None,
    ) -> None:
        payload: dict[str, Any] = {"images": images, "videos": videos}
        if date_range:
            payload["date_range"] = {"earliest": date_range[0], "latest": date_range[1]}
        if gps_coverage_percent is not None:
            payload["gps_coverage_percent"] = round(gps_coverage_percent, 1)
        if duplicates_detected is not None:
            payload["duplicates_detected"] = duplicates_detected
        if date_histogram:
            payload["date_histogram"] = date_histogram
        self._emit("discovery_complete", **payload)

    def estimate(
        self,
        duration_s: float,
        size_bytes: int,
        image_duration_s: float,
        video_duration_s: float,
    ) -> None:
        self._emit(
            "estimate",
            duration_s=round(duration_s, 3),
            size_bytes=size_bytes,
            image_duration_s=round(image_duration_s, 3),
            video_duration_s=round(video_duration_s, 3),
        )

    def phase_started(self, phase: str, total: int | None = None) -> None:
        self._emit("phase_started", phase=phase, total=total)

    def progress(
        self, phase: str, done: int, total: int, message: str | None = None
    ) -> None:
        self._emit("progress", phase=phase, done=done, total=total, message=message)

    def phase_complete(self, phase: str, message: str | None = None) -> None:
        self._emit("phase_complete", phase=phase, message=message)

    def info(self, message: str) -> None:
        self._emit("info", message=message)

    def warning(self, message: str, file: str | None = None) -> None:
        self._emit("warning", message=message, file=file)

    def error(self, message: str) -> None:
        self._emit("error", message=message)

    def item_failed(
        self,
        phase: str,
        path: str,
        reason: str,
        detail: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "phase": phase,
            "path": path,
            "reason": reason,
        }
        if detail is not None:
            payload["detail"] = detail
        self._emit("item_failed", **payload)

    def complete(
        self,
        outputs: list[Path],
        elapsed_s: float,
        items_skipped: int = 0,
    ) -> None:
        out_records = []
        for p in outputs:
            size = p.stat().st_size if p.exists() else 0
            out_records.append({"path": str(p), "size_bytes": size})
        self._emit(
            "complete",
            outputs=out_records,
            elapsed_s=round(elapsed_s, 3),
            items_skipped=items_skipped,
        )

    def cancelled(self, message: str | None = None) -> None:
        self._emit("cancelled", message=message)
