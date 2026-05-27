/**
 * Pure logic for the render progress pipeline (E4.S2, design-pass move #5).
 *
 * Maps the engine's fine-grained IPC phases onto the four user-facing
 * pipeline steps, and extrapolates a per-phase ETA from the observed
 * progress rate. Kept free of React/DOM so it is unit-testable.
 */

export interface PipelineStep {
  /** Stable key for the user-facing step. */
  key: "discovery" | "clips" | "batching" | "composite";
  /** Display label. */
  label: string;
}

/** The four user-facing pipeline steps, in order. */
export const PIPELINE_STEPS: PipelineStep[] = [
  { key: "discovery", label: "Discovery" },
  { key: "clips", label: "Clips" },
  { key: "batching", label: "Batching" },
  { key: "composite", label: "Composite" },
];

/**
 * Map an engine phase name (see `docs/sidecar-protocol.md`) to a
 * pipeline step index (0–3), or `null` if the phase is unknown/absent.
 *
 * Several fine-grained engine phases collapse into one user-facing step:
 * `deduplication` rides with `discovery`, `static-batching` with the
 * Ken Burns `images` pass, and `chunking` with `batching`.
 */
export function phaseToStepIndex(phase: string | null): number | null {
  switch (phase) {
    case "discovery":
    case "deduplication":
      return 0;
    case "images":
    case "static-batching":
      return 1;
    case "batching":
    case "chunking":
      return 2;
    case "compositing":
      return 3;
    default:
      return null;
  }
}

/**
 * Per-phase ETA in seconds, extrapolated from the rate observed so far
 * within the current phase. Returns `null` when there is not enough
 * data to estimate (no progress yet, no elapsed time, or bad inputs),
 * and `0` once the phase has completed.
 */
export function computePhaseEtaSeconds(args: {
  done: number;
  total: number;
  phaseElapsedS: number;
}): number | null {
  const { done, total, phaseElapsedS } = args;
  if (
    !Number.isFinite(done) ||
    !Number.isFinite(total) ||
    !Number.isFinite(phaseElapsedS)
  ) {
    return null;
  }
  if (done <= 0 || total <= 0 || phaseElapsedS <= 0) return null;
  if (done >= total) return 0;
  const rate = done / phaseElapsedS; // units per second
  if (rate <= 0) return null;
  const remaining = (total - done) / rate;
  if (!Number.isFinite(remaining) || remaining < 0) return null;
  return remaining;
}

/** Format an ETA in seconds as a compact string ("~1m 40s"), or `null`. */
export function formatEta(seconds: number | null): string | null {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return null;
  const s = Math.round(seconds);
  if (s < 60) return `~${s}s`;
  const m = Math.floor(s / 60);
  const remS = s % 60;
  if (m < 60) return remS === 0 ? `~${m}m` : `~${m}m ${remS}s`;
  const h = Math.floor(m / 60);
  const remM = m % 60;
  return remM === 0 ? `~${h}h` : `~${h}h ${remM}m`;
}
