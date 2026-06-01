/**
 * Typed mirror of the sidecar IPC protocol defined in
 * `docs/sidecar-protocol.md`. Keep in sync with the doc and with
 * `src/slideshow_gen/events.py`.
 */

export const PROTOCOL_VERSION = 1;

export type Phase =
  | "discovery"
  | "deduplication"
  | "images"
  | "static-batching"
  | "batching"
  | "chunking"
  | "compositing";

export interface BaseEvent {
  v: number;
  t: number;
}

export interface StartedEvent extends BaseEvent {
  type: "started";
  config: {
    output?: string;
    dirs?: string[];
    resolution?: string;
    slide_duration?: number;
    fade_duration?: number;
    fps?: number;
    static?: boolean;
    audio_track?: string | null;
    [key: string]: unknown;
  };
}

export interface PhaseStartedEvent extends BaseEvent {
  type: "phase_started";
  phase: Phase | string;
  total: number | null;
}

export interface DiscoveryCompleteEvent extends BaseEvent {
  type: "discovery_complete";
  images: number;
  videos: number;
  date_range?: { earliest: string; latest: string };
  gps_coverage_percent?: number;
  duplicates_detected?: number;
  /**
   * Month-bucketed density histogram. One entry per month from
   * `date_range.earliest` to `date_range.latest`, zero-filled.
   * Present whenever `date_range` is present.
   */
  date_histogram?: Array<{ month: string; count: number }>;
}

export interface EstimateEvent extends BaseEvent {
  type: "estimate";
  duration_s: number;
  size_bytes: number;
  image_duration_s: number;
  video_duration_s: number;
}

export interface ProgressEvent extends BaseEvent {
  type: "progress";
  phase: Phase | string;
  done: number;
  total: number;
  message: string | null;
}

export interface PhaseCompleteEvent extends BaseEvent {
  type: "phase_complete";
  phase: Phase | string;
  message: string | null;
}

export interface InfoEvent extends BaseEvent {
  type: "info";
  message: string;
}

export interface WarningEvent extends BaseEvent {
  type: "warning";
  message: string;
  file: string | null;
}

export interface ErrorEvent extends BaseEvent {
  type: "error";
  message: string;
}

/**
 * Non-fatal per-item failure: one input file could not be processed and was
 * skipped. The render continues. Surface passively in the UI — no modal.
 */
export interface ItemFailedEvent extends BaseEvent {
  type: "item_failed";
  phase: Phase | string;
  path: string;
  reason: string;
  /** Optional longer diagnostic (e.g. last lines of FFmpeg stderr). */
  detail?: string;
}

export interface CompleteEvent extends BaseEvent {
  type: "complete";
  outputs: Array<{ path: string; size_bytes: number }>;
  elapsed_s: number;
  /** Count of items skipped via `item_failed`. Additive — may be absent on
   *  older engine builds; treat as 0 when missing. */
  items_skipped?: number;
}

export interface CancelledEvent extends BaseEvent {
  type: "cancelled";
  message: string | null;
}

/** Discriminated union of every IPC event the sidecar can emit. */
export type SidecarEvent =
  | StartedEvent
  | PhaseStartedEvent
  | DiscoveryCompleteEvent
  | EstimateEvent
  | ProgressEvent
  | PhaseCompleteEvent
  | InfoEvent
  | WarningEvent
  | ErrorEvent
  | ItemFailedEvent
  | CompleteEvent
  | CancelledEvent;

/**
 * Wire-level envelope from the Rust shell. Mirrors `SidecarMessage`
 * in `src-tauri/src/sidecar.rs`.
 */
export type SidecarMessage =
  | { kind: "event"; payload: SidecarEvent }
  | { kind: "raw"; line: string }
  | { kind: "stderr"; line: string }
  | { kind: "exit"; code: number | null; success: boolean };

export const SIDECAR_EVENT_CHANNEL = "marquee://sidecar-event";
