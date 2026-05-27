# PR #4 Review Log
**PR Title:** Epic 4.S2: Render progress pipeline + dark-first palette
**Branch:** feat/epic-4-s2-progress-pipeline -> main
**URL:** https://github.com/adamthede/slideshow-gen/pull/4

## Summary
| Cycle | Date | Found | Actioned | Dismissed | Skipped | Commit | Ratio |
|-------|------|-------|----------|-----------|---------|--------|-------|
| 1 | 2026-05-27 14:25 | 7 | 6 | 0 | 1 | 8fe96a4 | 86% |

## Reviewer Effectiveness
| Reviewer | Total Found | T1 (Must) | T2 (Should) | T3 (Consider) | T4 (Dismiss) | Actioned % | Signal:Noise |
|----------|------------|-----------|-------------|---------------|-------------|-----------|-------------|
| Copilot | 3 | 0 | 3 | 0 | 0 | 100% | 3:0 |
| Gemini | 4 | 0 | 3 | 1 | 0 | 75% | 3:1 |

## Issue Categories (Cumulative)
| Category | T1 | T2 | T3 | T4 | Total | % of All |
|----------|----|----|----|----|-------|----------|
| data-integrity | 0 | 3 | 1 | 0 | 4 | 57% |
| documentation | 0 | 2 | 0 | 0 | 2 | 29% |
| error-handling | 0 | 1 | 0 | 0 | 1 | 14% |

**Status:** IN PROGRESS

## Cycle 1 — 2026-05-27 14:25

### Pre-Review Snapshot
- **Files changed:** 11 (996+ / 74-)
- **Test:Code ratio:** 1:8 (`pipeline.test.ts` vs the TS/CSS/config sources; `.md` + lockfile excluded)
- **CI status:** No CI configured on the branch
- **Linter offenses:** N/A (non-Ruby; tsc + vitest + vite build all clean)

### Actioned (6)
#### T2-SHOULD: liveRemainingSeconds can jump up on a backward clock step
- **File:** `desktop/src/lib/pipeline.ts:114`
- **Category:** `data-integrity`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "liveRemainingSeconds can increase the remaining time if nowMs is earlier than capturedAtMs (e.g., system clock adjustment...)"
- **Disposition:** FIXED — clamp `sinceCapture` to >= 0 and reject non-finite/negative `etaSeconds`; matches `liveElapsedSeconds`' clamp. Added 2 unit tests (backward clock, non-finite/negative eta).
- **Thread ID:** PRRT_kwDOR-Xvl86FNE04

#### T2-SHOULD: formatClock renders "NaN:NaN" on non-finite input
- **File:** `desktop/src/components/ui/render-pipeline.tsx:26`
- **Category:** `error-handling`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "To prevent displaying NaN:NaN if progress.t is ever NaN or non-finite, we should add a defensive guard..."
- **Disposition:** FIXED — `formatClock` returns "--:--" for non-finite input (guards a malformed IPC `t` reaching the timer math via `startMsRef`).
- **Thread ID:** PRRT_kwDOR-Xvl86FGJpJ

#### T2-SHOULD: etaSeconds computed for an unknown phase (null === null)
- **File:** `desktop/src/components/ui/render-pipeline.tsx:82`
- **Category:** `data-integrity`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "If both progressStep and activeStep are null... progressStep === activeStep evaluates to true. This can cause etaSeconds to be incorrectly calculated..."
- **Disposition:** FIXED — added `activeStep != null` to the `etaSeconds` guard so an unmapped/unset phase no longer matches via null===null.
- **Thread ID:** PRRT_kwDOR-Xvl86FGJpk

#### T2-SHOULD: progress count shown for an unknown phase (null === null)
- **File:** `desktop/src/components/ui/render-pipeline.tsx:187`
- **Category:** `data-integrity`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "Similar to the etaSeconds calculation, if both progressStep and activeStep are null... progress numbers [are] rendered even when the active step is unknown."
- **Disposition:** FIXED — added `activeStep != null` to the JSX guard for the done/total display. Same root cause as the etaSeconds fix.
- **Thread ID:** PRRT_kwDOR-Xvl86FGJpt

#### T2-SHOULD: component comment says "three-phase" but renders four steps
- **File:** `desktop/src/components/ui/render-pipeline.tsx:45`
- **Category:** `documentation`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "The block comment describes this as a 'three-phase' FFmpeg pipeline, but the component renders a 4-step pipeline..."
- **Disposition:** FIXED — reworded to "four-step horizontal sequence ... (discovery plus the three FFmpeg phases)".
- **Thread ID:** PRRT_kwDOR-Xvl86FNE1Z

#### T2-SHOULD: story doc says "three-phase" but lists four steps
- **File:** `_bmad-output/implementation-artifacts/4-2-progress-pipeline.md:16`
- **Category:** `documentation`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "This document refers to a 'three-phase' pipeline, but the text immediately lists 4 steps..."
- **Disposition:** FIXED — reworded to "four-step ... (discovery plus the three FFmpeg phases)".
- **Thread ID:** PRRT_kwDOR-Xvl86FNE1w

### Skipped (1)
#### T3-CONSIDER: clamp progress fraction to a minimum of 0
- **File:** `desktop/src/components/ui/render-pipeline.tsx:69`
- **Category:** `data-integrity`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** SKIPPED — defensive against a negative `done`, but the IPC protocol guarantees `done` is monotonic and non-negative (see `docs/sidecar-protocol.md`), and the `fraction` guard already requires `progress.total > 0`. No concrete scenario; a trivial `Math.max(0, …)` follow-up if a real negative ever appears.
- **Thread ID:** PRRT_kwDOR-Xvl86FGJpc

### Recurrence Patterns
- **Trust-boundary validation at the periphery** — recurs from PR-2: IPC-derived numeric values (`progress.t`, `progress.done`, phase) fed into display math without finite/null guards. Cycle-1 fixes (NaN guard, clock-step clamp, null===null phase check) all close the same class on the new timer/pipeline code. Consistent with the dashboard's documented hotspot.

### Commit
SHA: 8fe96a4
Message: fix: Address PR review cycle 1 — harden render-pipeline IPC edge cases
