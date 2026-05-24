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
}

export const DEFAULT_SETTINGS: RenderSettings = {
  resolution: "1080p",
  slideDuration: 4.0,
  fadeDuration: 0.5,
  fps: 30,
  recursive: false,
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
