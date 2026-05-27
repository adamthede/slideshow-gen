import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import {
  PIPELINE_STEPS,
  phaseToStepIndex,
  computePhaseEtaSeconds,
  liveElapsedSeconds,
  liveRemainingSeconds,
} from "@/lib/pipeline";

export interface RenderPipelineProps {
  /** Current engine phase (from `phase_started`). */
  phase: string | null;
  /** Elapsed seconds at which the current phase started. */
  phaseStartedAt: number | null;
  /** Latest progress tick. */
  progress: { done: number; total: number; phase: string; t: number } | null;
}

/** mm:ss clock (m can exceed 59 for long renders). */
function formatClock(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}:${rem.toString().padStart(2, "0")}`;
}

/** Re-renders every second while `active`, returning the current epoch ms.
 *  Clears its interval on unmount / when `active` goes false (no leaked timer). */
function useSecondTicker(active: boolean): number {
  const [nowMs, setNowMs] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    setNowMs(Date.now());
    const id = setInterval(() => setNowMs(Date.now()), 1000);
    return () => clearInterval(id);
  }, [active]);
  return nowMs;
}

/**
 * The render progress pipeline (design-pass move #5): the three-phase
 * FFmpeg pipeline rendered as a horizontal sequence — Discovery → Clips →
 * Batching → Composite. The active step fills amber as it runs; completed
 * steps are muted-amber and full; pending steps are an empty stone track.
 *
 * Beneath it sit two live timers that tick every second: a count-up elapsed
 * clock (re-aligned to the engine's reported time on each progress tick) and a
 * per-phase count-down of estimated time remaining. Deliberately not a generic
 * progress bar — this is the strongest data-as-design surface.
 */
export function RenderPipeline({
  phase,
  phaseStartedAt,
  progress,
}: RenderPipelineProps) {
  const activeStep = phaseToStepIndex(phase);
  // Only apply the fill fraction when the latest progress tick belongs to
  // the active step — otherwise a stale tick from the prior phase would
  // mis-fill the bar during the brief gap before the next phase_started.
  const progressStep =
    progress != null ? phaseToStepIndex(progress.phase) : null;
  const fraction =
    progress != null &&
    progress.total > 0 &&
    progressStep != null &&
    progressStep === activeStep
      ? Math.min(1, progress.done / progress.total)
      : 0;

  const phaseElapsedS =
    progress != null && phaseStartedAt != null
      ? progress.t - phaseStartedAt
      : null;
  const etaSeconds =
    progress != null && progressStep === activeStep && phaseElapsedS != null
      ? computePhaseEtaSeconds({
          done: progress.done,
          total: progress.total,
          phaseElapsedS,
        })
      : null;

  // Live timers. The ticker drives a re-render every second; the anchors below
  // are re-seeded from the engine on each progress tick so the numbers stay
  // accurate while ticking smoothly between ticks.
  const nowMs = useSecondTicker(true);

  // Wall-clock instant corresponding to engine elapsed t=0, re-aligned to the
  // engine's reported elapsed on each tick.
  const startMsRef = useRef<number>(Date.now());
  useEffect(() => {
    if (progress != null) {
      startMsRef.current = Date.now() - progress.t * 1000;
    }
  }, [progress]);

  // The per-phase ETA and the wall-clock time it was computed, so the
  // countdown ticks down between progress ticks and re-seeds on each new one.
  const etaRef = useRef<number | null>(null);
  const etaAtMsRef = useRef<number>(Date.now());
  useEffect(() => {
    etaRef.current = etaSeconds;
    etaAtMsRef.current = Date.now();
  }, [etaSeconds]);

  const liveElapsed = liveElapsedSeconds(startMsRef.current, nowMs);
  const liveRemaining = liveRemainingSeconds(
    etaRef.current,
    etaAtMsRef.current,
    nowMs,
  );

  const activeLabel =
    activeStep != null ? PIPELINE_STEPS[activeStep].label : null;

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
          Rendering
        </span>
        <span className="font-mono text-sm tabular-nums text-foreground">
          {formatClock(liveElapsed)}
          <span className="ml-1 text-xs text-muted-foreground">elapsed</span>
        </span>
      </div>

      <div className="grid grid-cols-4 gap-2.5">
        {PIPELINE_STEPS.map((step, i) => {
          const state =
            activeStep == null
              ? "pending"
              : i < activeStep
                ? "done"
                : i === activeStep
                  ? "active"
                  : "pending";
          const fillPct =
            state === "done" ? 100 : state === "active" ? fraction * 100 : 0;
          return (
            <div key={step.key} className="space-y-1.5">
              <div
                className={cn(
                  "text-[10px] font-medium uppercase tracking-[0.12em] transition-colors",
                  state === "active"
                    ? "text-primary"
                    : state === "done"
                      ? "text-muted-foreground"
                      : "text-muted-foreground/50",
                )}
              >
                {step.label}
              </div>
              <div
                className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
                role="progressbar"
                aria-label={step.label}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(fillPct)}
              >
                <div
                  className={cn(
                    "h-full rounded-full transition-[width,background-color] duration-300 ease-out",
                    state === "done" ? "bg-primary/40" : "bg-primary",
                  )}
                  style={{ width: `${fillPct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex items-baseline justify-between text-sm">
        <span className="text-foreground">
          {activeLabel ?? "Starting render…"}
          {progress != null &&
          progress.total > 0 &&
          progressStep === activeStep ? (
            <span className="text-muted-foreground">
              {" · "}
              {progress.done.toLocaleString()} /{" "}
              {progress.total.toLocaleString()}
            </span>
          ) : null}
        </span>
        {liveRemaining != null && (
          <span className="font-mono tabular-nums text-muted-foreground">
            {formatClock(liveRemaining)}
            <span className="ml-1 text-xs">left in phase</span>
          </span>
        )}
      </div>
    </div>
  );
}
