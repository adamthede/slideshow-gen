# PR #4 Review Log
**PR Title:** Epic 4.S2: Render progress pipeline + dark-first palette
**Branch:** feat/epic-4-s2-progress-pipeline -> main
**URL:** https://github.com/adamthede/slideshow-gen/pull/4

## Summary
| Cycle | Date | Found | Actioned | Dismissed | Skipped | Commit | Ratio |
|-------|------|-------|----------|-----------|---------|--------|-------|
| 1 | 2026-05-27 14:25 | 7 | 6 | 0 | 1 | 8fe96a4 | 86% |
| 2 | 2026-05-27 15:14 | 1 | 1 | 0 | 0 | d532760 | 100% |
| 3 | 2026-05-27 15:20 | 3 | 1 | 0 | 2 | 20c9260 | 33% |
| 4 | 2026-05-27 15:25 | 7 | 6 | 1 | 0 | 465977b | 86% |

## Reviewer Effectiveness
| Reviewer | Total Found | T1 (Must) | T2 (Should) | T3 (Consider) | T4 (Dismiss) | Actioned % | Signal:Noise |
|----------|------------|-----------|-------------|---------------|-------------|-----------|-------------|
| Copilot | 8 | 0 | 8 | 0 | 0 | 100% | 8:0 |
| Gemini | 10 | 0 | 6 | 3 | 1 | 60% | 6:4 |

## Issue Categories (Cumulative)
| Category | T1 | T2 | T3 | T4 | Total | % of All |
|----------|----|----|----|----|-------|----------|
| data-integrity | 0 | 6 | 3 | 0 | 9 | 50% |
| documentation | 0 | 7 | 0 | 0 | 7 | 39% |
| error-handling | 0 | 1 | 0 | 0 | 1 | 6% |
| style | 0 | 0 | 0 | 1 | 1 | 6% |

**Status:** MAX CYCLES REACHED

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

## Cycle 2 — 2026-05-27 15:14

### Actioned (1)
#### T2-SHOULD: stale timer-anchor render lag (up to 1s)
- **File:** `desktop/src/components/ui/render-pipeline.tsx:98`
- **Category:** `data-integrity`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "There is a synchronization bug in how startMsRef and etaRef/etaAtMsRef are updated... the useEffect hooks that update these refs... have not run yet... renders the timers using the stale ref values."
- **Disposition:** FIXED — re-seed the elapsed/ETA wall-clock anchors synchronously during render (guarded by a prev-value ref) instead of in a `useEffect`, eliminating the up-to-1s display lag and removing two effects. Idiomatic React "store info from previous render" pattern. Pure timer math unchanged (tests still 21/21).
- **Thread ID:** PRRT_kwDOR-Xvl86FNPp3

### Recurrence Patterns
No recurring patterns detected this cycle (single React render/effect-ordering bug).

### Commit
SHA: d532760
Message: fix: Address PR review cycle 2 — eliminate stale timer-anchor render lag

## Cycle 3 — 2026-05-27 15:20

Three Gemini comments shared one root cause — a malformed/version-mismatched `progress`
payload carrying undefined/NaN — so a **single boundary fix in `useSidecar` resolved all
three**. Classified by individual severity (one crash-risk T2; two cosmetic/already-graceful
T3), but all three threads are addressed by the same commit.

### Actioned (1)
#### T2-SHOULD: malformed progress payload crashes the render tree
- **File:** `desktop/src/components/ui/render-pipeline.tsx:204`
- **Category:** `data-integrity`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "If progress.done or progress.total is undefined or null at runtime... calling toLocaleString() on them will throw a TypeError and crash the entire React render tree."
- **Disposition:** FIXED at the boundary — `useSidecar` now coerces + validates `done/total/t` to finite numbers and drops a malformed tick (last good progress stays on screen). Prevents the `.toLocaleString()` crash and NaN propagation at the source rather than via scattered component guards. Matches the trust-boundary hotspot.
- **Thread ID:** PRRT_kwDOR-Xvl86FN_Dj

### Skipped (2)
#### T3-CONSIDER: fraction can be NaN -> "NaN%" bar width
- **File:** `desktop/src/components/ui/render-pipeline.tsx:73`
- **Category:** `data-integrity`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** SKIPPED as a separate change but RESOLVED by the cycle-3 boundary fix — `done/total` are now guaranteed finite, so `fraction` can't be NaN. Cosmetic-only on its own (invalid CSS width is ignored, no crash).
- **Thread ID:** PRRT_kwDOR-Xvl86FN_Dm

#### T3-CONSIDER: progress.t NaN -> NaN elapsed anchor
- **File:** `desktop/src/components/ui/render-pipeline.tsx:110`
- **Category:** `data-integrity`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** SKIPPED as a separate change but RESOLVED by the boundary fix; also already degraded gracefully via the cycle-1 `formatClock` "--:--" guard. No crash path.
- **Thread ID:** PRRT_kwDOR-Xvl86FN_Dv

### Recurrence Patterns
- **Trust-boundary validation at the periphery (recurring).** Third PR-4 instance of IPC-derived numerics needing guards. Resolved the *class* by validating at the `useSidecar` boundary rather than per-call-site — exactly the dashboard hotspot's recommended pattern.

### Commit
SHA: 20c9260
Message: fix: Address PR review cycle 3 — validate progress IPC fields at the boundary

## Cycle 4 — 2026-05-27 15:25

### Actioned (6)
#### T2-SHOULD: phase_started `t` -> phaseStartedAt not validated
- **File:** `desktop/src/hooks/useSidecar.ts:144`
- **Category:** `data-integrity`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "The event.t value... is assigned directly to next.phaseStartedAt without validation... a malformed or missing t field could propagate NaN..."
- **Disposition:** FIXED — validate/coerce `phaseStartedAt` the same way as `progress.t` (cycle 3). Completes the trust-boundary guard so neither path can NaN the per-phase math.
- **Thread ID:** PRRT_kwDOR-Xvl86FOEQN

#### T2-SHOULD: "the render rendered as" duplicated-word typo
- **File:** `desktop/src/components/ui/render-pipeline.tsx:45`
- **Category:** `documentation`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Disposition:** FIXED — reworded to "the render shown as". (Typo introduced by the cycle-1 three-phase→four-step reword.)
- **Thread ID:** PRRT_kwDOR-Xvl86FOCaK

#### T2-SHOULD: stale vitest counts in the story doc (x4)
- **File:** `_bmad-output/implementation-artifacts/4-2-progress-pipeline.md:32,67,75,85`
- **Category:** `documentation`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "claims '14/14' / '19 cases'... pipeline.test.ts currently has 21 it(...) tests."
- **Disposition:** FIXED — updated the In-scope (19→21), File List (14→21), Verification (14/14→21/21), and TDD note (clarified 14/14-at-the-time → 21/21 now) references.
- **Thread IDs:** PRRT_kwDOR-Xvl86FOCZn, PRRT_kwDOR-Xvl86FOCaf, PRRT_kwDOR-Xvl86FOCa5, PRRT_kwDOR-Xvl86FOCZ3

### Dismissed (1)
#### T4-DISMISS: `__dirname` in ESM vitest.config.ts
- **File:** `desktop/vitest.config.ts:15`
- **Category:** `style`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** DISMISSED — empirically false here: `npm test` runs 21/21 green using this config, and `vite.config.ts` uses the identical `__dirname` pattern (Vite/Vitest's config loader shims it). Switching only `vitest.config.ts` to `import.meta.url` would create inconsistency with `vite.config.ts` for no functional gain.
- **Thread ID:** PRRT_kwDOR-Xvl86FOEQl

### Recurrence Patterns
- **Trust-boundary validation (recurring, now closed).** The `phaseStartedAt` guard finishes the IPC-numeric validation begun in cycle 3 — both `progress.t` and `phase_started.t` are now validated at the `useSidecar` boundary.

### Commit
SHA: 465977b
Message: fix: Address PR review cycle 4 — phaseStartedAt guard + doc accuracy
