/**
 * Render settings the user can override before scanning. Mirrors the
 * `ScanSettings` struct on the Rust side (`src-tauri/src/lib.rs`).
 *
 * Each field is optional — when unset, the CLI's default applies.
 */

import { useEffect, useState } from "react";

export type Resolution = "1080p" | "4k";

export interface RenderSettings {
  resolution: Resolution;
  slideDuration: number;
  fadeDuration: number;
  fps: number;
  recursive: boolean;
  /** Absolute path to a background audio file, or null for no audio. */
  audioTrack: string | null;
  /** 0.0 silent → 1.0 source level. Ignored when audioTrack is null. */
  audioVolume: number;
  /** Skip Ken Burns motion — static images with crossfades. */
  staticMode: boolean;
  /** Shuffle order instead of chronological. */
  randomOrder: boolean;
  /** Disable all text overlays (supersedes the per-overlay flags). */
  noOverlays: boolean;
  noDate: boolean;
  noLocation: boolean;
}

export const DEFAULT_SETTINGS: RenderSettings = {
  resolution: "1080p",
  slideDuration: 4.0,
  fadeDuration: 0.5,
  fps: 30,
  recursive: false,
  audioTrack: null,
  audioVolume: 1.0,
  staticMode: false,
  randomOrder: false,
  noOverlays: false,
  noDate: false,
  noLocation: false,
};

const STORAGE_KEY = "marquee.renderSettings.v1";

function loadSettings(): RenderSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    // Trust boundary: localStorage can be corrupted across versions or by
    // a different process writing the same key. Coerce each field with a
    // per-field type guard so a stray string in `audioVolume` can't make
    // downstream `audioVolume.toFixed(2)` throw and break the whole UI.
    return {
      resolution:
        parsed.resolution === "4k" || parsed.resolution === "1080p"
          ? parsed.resolution
          : DEFAULT_SETTINGS.resolution,
      slideDuration:
        typeof parsed.slideDuration === "number" && Number.isFinite(parsed.slideDuration)
          ? parsed.slideDuration
          : DEFAULT_SETTINGS.slideDuration,
      fadeDuration:
        typeof parsed.fadeDuration === "number" && Number.isFinite(parsed.fadeDuration)
          ? parsed.fadeDuration
          : DEFAULT_SETTINGS.fadeDuration,
      fps:
        typeof parsed.fps === "number" && Number.isFinite(parsed.fps)
          ? parsed.fps
          : DEFAULT_SETTINGS.fps,
      recursive:
        typeof parsed.recursive === "boolean"
          ? parsed.recursive
          : DEFAULT_SETTINGS.recursive,
      audioTrack:
        typeof parsed.audioTrack === "string" && parsed.audioTrack.length > 0
          ? parsed.audioTrack
          : DEFAULT_SETTINGS.audioTrack,
      audioVolume:
        typeof parsed.audioVolume === "number" && Number.isFinite(parsed.audioVolume)
          ? parsed.audioVolume
          : DEFAULT_SETTINGS.audioVolume,
      staticMode:
        typeof parsed.staticMode === "boolean"
          ? parsed.staticMode
          : DEFAULT_SETTINGS.staticMode,
      randomOrder:
        typeof parsed.randomOrder === "boolean"
          ? parsed.randomOrder
          : DEFAULT_SETTINGS.randomOrder,
      noOverlays:
        typeof parsed.noOverlays === "boolean"
          ? parsed.noOverlays
          : DEFAULT_SETTINGS.noOverlays,
      noDate:
        typeof parsed.noDate === "boolean"
          ? parsed.noDate
          : DEFAULT_SETTINGS.noDate,
      noLocation:
        typeof parsed.noLocation === "boolean"
          ? parsed.noLocation
          : DEFAULT_SETTINGS.noLocation,
    };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function useSettings() {
  const [settings, setSettings] = useState<RenderSettings>(loadSettings);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch {
      // Best-effort persistence — quota/privacy errors are non-fatal.
    }
  }, [settings]);

  return [settings, setSettings] as const;
}
