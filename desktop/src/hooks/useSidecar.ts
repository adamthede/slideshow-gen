import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import {
  SIDECAR_EVENT_CHANNEL,
  type CompleteEvent,
  type DiscoveryCompleteEvent,
  type EstimateEvent,
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

  const reset = useCallback(() => setState(initialState), []);

  return { state, start, startRender, reset };
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
          // Reset the per-phase ETA clock to this phase's start time.
          next.phaseStartedAt = event.t;
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
        case "complete":
          next.complete = event;
          next.done = true;
          // Deliberately leave `running` true here. The sidecar child is
          // still alive until the later `exit` message clears the Rust-side
          // process mutex; re-enabling controls now would let a fast re-click
          // hit "already in progress". The UI swaps the Rendering→Complete
          // card off `complete` instead (see `rendering` in App.tsx).
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
        done: true,
        exitCode: msg.code,
      };
  }
}
