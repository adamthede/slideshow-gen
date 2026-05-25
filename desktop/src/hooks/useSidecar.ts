import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import {
  SIDECAR_EVENT_CHANNEL,
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
  /** Latest progress tick, or null. */
  progress: { done: number; total: number; phase: string } | null;
  /** Latest discovery_complete event, or null. */
  discovery: DiscoveryCompleteEvent | null;
  /** Latest estimate event, or null. */
  estimate: EstimateEvent | null;
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
  progress: null,
  discovery: null,
  estimate: null,
  error: null,
  done: false,
  running: false,
  exitCode: null,
};

/**
 * Subscribe to the sidecar event channel and expose typed state.
 *
 * Returns `{ state, start, reset }`. Call `start(folder)` to spawn a
 * scan against a folder; the state updates as events stream in.
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

  const reset = useCallback(() => setState(initialState), []);

  return { state, start, reset };
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
          break;
        case "phase_complete":
          // Keep phase visible so the UI can show the most recent completed phase.
          break;
        case "progress":
          next.progress = {
            done: event.done,
            total: event.total,
            phase: event.phase,
          };
          break;
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
        done: true,
        exitCode: msg.code,
      };
  }
}
