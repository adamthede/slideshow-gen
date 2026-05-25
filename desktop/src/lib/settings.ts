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
    const parsed = JSON.parse(raw) as Partial<RenderSettings>;
    return { ...DEFAULT_SETTINGS, ...parsed };
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
