import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import {
  SIDECAR_EVENT_CHANNEL,
  type CancelledEvent,
  type CompleteEvent,
  type DiscoveryCompleteEvent,
  type EstimateEvent,
  type ItemFailedEvent,
  type SidecarEvent,
  type SidecarMessage,
} from "@/lib/sidecar-events";

export interface SidecarState {
  /** Every JSON-line event received so far, in order. */
  events: SidecarEvent[];
  /** Raw lines (stderr or non-JSON stdout). Useful for diagnostics. */
  diagnostics: Array<{ source: "stderr" | "raw"; line: string }>;
  /** Most recent `phase_started` phase, or null. */
  phase: string | null;
  /** Elapsed seconds (`t`) at which the current phase started, or null.
   *  Used with `progress.t` to extrapolate a per-phase ETA. */
  phaseStartedAt: number | null;
  /** Latest progress tick, or null. `t` is elapsed seconds at the tick. */
  progress: { done: number; total: number; phase: string; t: number } | null;
  /** Latest discovery_complete event, or null. */
  discovery: DiscoveryCompleteEvent | null;
  /** Latest estimate event, or null. */
  estimate: EstimateEvent | null;
  /** The `complete` event from a finished render, or null. Carries the
   *  written output file(s). Only emitted by real renders, not scans. */
  complete: CompleteEvent | null;
  /** The `cancelled` event from a cancelled render, or null. Primary,
   *  unambiguous signal that the user's cancel took effect. */
  cancelled: CancelledEvent | null;
  /** True from the moment a cancel is requested until the process exits.
   *  Drives the "Cancelling…" affordance and keeps the Cancel button disabled. */
  cancelling: boolean;
  /** Per-item failures collected from `item_failed` events. Passive surface —
   *  display as a muted strip during render and a compact list post-render.
   *  Never blocks the user. The terminating `complete` event also carries an
   *  `items_skipped` count, which should always equal `warnings.length`. */
  warnings: ItemFailedEvent[];
  /** Latest error message, or null. */
  error: string | null;
  /** True after `complete` event OR after process exit. */
  done: boolean;
  /** True between `start` invocation and process exit. */
  running: boolean;
  /** Exit code, if process has terminated. */
  exitCode: number | null;
}

const initialState: SidecarState = {
  events: [],
  diagnostics: [],
  phase: null,
  phaseStartedAt: null,
  progress: null,
  discovery: null,
  estimate: null,
  complete: null,
  cancelled: null,
  cancelling: false,
  warnings: [],
  error: null,
  done: false,
  running: false,
  exitCode: null,
};

/**
 * Subscribe to the sidecar event channel and expose typed state.
 *
 * Returns `{ state, start, startRender, reset }`. Call `start(folders)`
 * to spawn an estimate-only scan, or `startRender(folders, output)` to
 * run a real render; the state updates as events stream in.
 */
export function useSidecar() {
  const [state, setState] = useState<SidecarState>(initialState);
  const unlistenRef = useRef<UnlistenFn | null>(null);

  useEffect(() => {
    let cancelled = false;
    listen<SidecarMessage>(SIDECAR_EVENT_CHANNEL, (message) => {
      if (cancelled) return;
      setState((prev) => reduce(prev, message.payload));
    }).then((unlisten) => {
      if (cancelled) {
        unlisten();
      } else {
        unlistenRef.current = unlisten;
      }
    });

    return () => {
      cancelled = true;
      unlistenRef.current?.();
      unlistenRef.current = null;
    };
  }, []);

  const start = useCallback(
    async (folders: string[], settings?: Record<string, unknown>) => {
      setState({ ...initialState, running: true });
      try {
        await invoke("start_scan", { folders, settings });
      } catch (err) {
        setState((prev) => ({
          ...prev,
          running: false,
          done: true,
          error: typeof err === "string" ? err : String(err),
        }));
      }
    },
    [],
  );

  const startRender = useCallback(
    async (
      folders: string[],
      output: string,
      settings?: Record<string, unknown>,
    ) => {
      setState({ ...initialState, running: true });
      try {
        await invoke("start_render", { folders, output, settings });
      } catch (err) {
        setState((prev) => ({
          ...prev,
          running: false,
          done: true,
          error: typeof err === "string" ? err : String(err),
        }));
      }
    },
    [],
  );

  const cancelRender = useCallback(async () => {
    // Optimistically flag the in-flight cancel so the UI can disable the
    // button and show "Cancelling…". The authoritative end-state still comes
    // from the `cancelled` event + process `exit` (see the reducer), never
    // from this call resolving.
    setState((prev) => (prev.running ? { ...prev, cancelling: true } : prev));
    try {
      await invoke("cancel_render");
    } catch (err) {
      // Most likely "No render is running" — a benign race where the engine
      // exited between the click and the IPC dispatch. The `exit` message
      // (already in flight or already processed) reconciles the rest, so just
      // clear the optimistic flag. Surfacing this as state.error would pop
      // the red error card for a harmless race.
      console.warn("[marquee] cancel_render failed (likely a benign race):", err);
      setState((prev) => ({ ...prev, cancelling: false }));
    }
  }, []);

  const reset = useCallback(() => setState(initialState), []);

  /**
   * Clear terminal/post-render state (complete, cancelled, error, warnings,
   * progress, raw events) while preserving the pre-render discovery and
   * estimate snapshots. Used by the result view's "Render Again" action so the
   * user returns to the Summary/Estimates view without losing what was scanned.
   */
  const clearCompletion = useCallback(() => {
    setState((prev) => ({
      ...prev,
      events: [],
      diagnostics: [],
      phase: null,
      phaseStartedAt: null,
      progress: null,
      complete: null,
      cancelled: null,
      cancelling: false,
      warnings: [],
      error: null,
      done: false,
      exitCode: null,
    }));
  }, []);

  return { state, start, startRender, cancelRender, reset, clearCompletion };
}

function reduce(prev: SidecarState, msg: SidecarMessage): SidecarState {
  switch (msg.kind) {
    case "event": {
      const event = msg.payload;
      const next: SidecarState = {
        ...prev,
        events: [...prev.events, event],
      };
      switch (event.type) {
        case "phase_started":
          next.phase = event.phase;
          // Reset the per-phase ETA clock to this phase's start time, with
          // the same trust-boundary validation as `progress.t`: a malformed
          // `t` must not poison the per-phase elapsed/ETA math with NaN.
          {
            const startedAt = Number(event.t);
            next.phaseStartedAt = Number.isFinite(startedAt) ? startedAt : null;
          }
          break;
        case "phase_complete":
          // Keep phase visible so the UI can show the most recent completed phase.
          break;
        case "progress": {
          // Validate the numeric fields at the IPC trust boundary: a malformed
          // or version-mismatched payload could carry undefined/NaN, which
          // would otherwise crash the render tree (`.toLocaleString()` on a
          // non-number) or propagate NaN into the progress bar / timers.
          // Drop a malformed tick rather than poison the UI — the last good
          // progress stays on screen.
          const done = Number(event.done);
          const total = Number(event.total);
          const t = Number(event.t);
          if (
            Number.isFinite(done) &&
            Number.isFinite(total) &&
            Number.isFinite(t)
          ) {
            next.progress = { done, total, phase: event.phase, t };
          }
          break;
        }
        case "discovery_complete":
          next.discovery = event;
          break;
        case "estimate":
          next.estimate = event;
          break;
        case "error":
          next.error = event.message;
          break;
        case "item_failed":
          // Passive collection — never blocks the UI. App.tsx renders these
          // as a muted strip during render and a compact list post-render.
          next.warnings = [...prev.warnings, event];
          break;
        case "complete":
          next.complete = event;
          next.done = true;
          // Deliberately leave `running` true here. The sidecar child is
          // still alive until the later `exit` message clears the Rust-side
          // process mutex; re-enabling controls now would let a fast re-click
          // hit "already in progress". The UI swaps the Rendering→Complete
          // card off `complete` instead (see `rendering` in App.tsx).
          break;
        case "cancelled":
          // Primary, unambiguous cancel signal. Like `complete`, leave
          // `running` true — controls re-enable only on `exit` so a fast
          // re-click can't race the still-terminating sidecar.
          next.cancelled = event;
          next.done = true;
          break;
      }
      return next;
    }
    case "raw":
      return {
        ...prev,
        diagnostics: [
          ...prev.diagnostics,
          { source: "raw", line: msg.line },
        ],
      };
    case "stderr":
      return {
        ...prev,
        diagnostics: [
          ...prev.diagnostics,
          { source: "stderr", line: msg.line },
        ],
      };
    case "exit":
      return {
        ...prev,
        running: false,
        cancelling: false,
        done: true,
        exitCode: msg.code,
      };
  }
}
