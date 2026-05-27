# Epic 4.S2 — Render progress pipeline (data-as-design)

**Status:** Ready for review
**Branch:** `feat/epic-4-s2-progress-pipeline`
**Depends on:** E4.S1 (render kickoff, PR #3, merged)
**Design source:** `docs/design-pass.md` moves #1 + #5

## Scope

E4.S2 builds the render progress UI. Per `docs/design-pass.md`, two "day one of Epic 4"
design moves land here rather than as later polish:

- **Move #5 — Phase pipeline progress.** The three-phase FFmpeg pipeline rendered as a
  horizontal pipeline (discovery → clips → batching → composite), amber for in-flight,
  muted stone for pending/done, elapsed + ETA under the active segment. The strongest
  data-as-design surface in the app — explicitly *not* a generic progress bar.
- **Move #1 — Dark-first palette swap.** Replace cool slate tokens with warm
  stone/amber in `index.css`; default to dark, light becomes the alternate.

### In scope
- Warm stone/amber design tokens (light + dark), dark-first default.
- A `RenderPipeline` component: 4-segment phase indicator, per-phase progress bar,
  per-phase ETA, elapsed time. Active segment amber; done/pending muted.
- **Live timers (added after QA feedback):** a count-up elapsed clock and a per-phase
  count-down of remaining time, both ticking every second via a `useSecondTicker` hook.
  The elapsed anchor is re-aligned to the engine's reported time on each progress tick,
  and the countdown re-seeds from the per-phase ETA each tick (clamped at 0:00). Gives
  the user a live read on progress beyond the bar + image count. Whole-render ETA is
  deferred — it needs render-time calibration (E0.S3); this countdown is per-phase only.
- Pure phase-mapping + ETA + live-timer math extracted to `lib/pipeline.ts`, unit-tested
  (vitest, 19 cases).
- Hook captures event timestamps so per-phase ETA can be computed.

### Out of scope (deferred)
- **Cancel button + cancellation** → E4.S3 (SIGTERM propagation, temp cleanup,
  `--keep-temp` parity). A bare kill here would orphan FFmpeg children and leak temp
  dirs — exactly what S3 handles. No dead/placeholder button shipped.
- Render report on completion (move #6), de-card summary (#2), date-range timeline (#3),
  GPS/dupes glyphs (#4) → dedicated design pass between Epic 4 and Epic 5.

## Acceptance criteria
1. During a render, a horizontal 4-step pipeline shows Discovery → Clips → Batching →
   Composite, with the active step highlighted (amber) and progress filling it.
2. The active step shows a per-phase ETA derived from the observed progress rate, and
   the cumulative elapsed time.
3. Engine phases map correctly to the 4 user-facing steps (discovery+dedup→Discovery;
   images+static-batching→Clips; batching+chunking→Batching; compositing→Composite).
4. The app is dark-first with the warm stone/amber palette; light is the alternate.
5. ETA is robust to zero/early progress (no NaN/Infinity), and never shown before there
   is enough data to estimate.
6. tsc clean, vite build clean, vitest green, cargo unaffected.

## Phase → step mapping

| Engine phase (protocol) | Pipeline step |
|---|---|
| `discovery`, `deduplication` | 0 — Discovery |
| `images`, `static-batching` | 1 — Clips |
| `batching`, `chunking` | 2 — Batching |
| `compositing` | 3 — Composite |

## File List
- `desktop/src/index.css` (modified) — warm stone/amber tokens, amber as `--primary` (move #1)
- `desktop/src/main.tsx` (modified) — dark-first default; light only on explicit OS preference (move #1)
- `desktop/src/lib/pipeline.ts` (new) — pure `PIPELINE_STEPS`, `phaseToStepIndex`, `computePhaseEtaSeconds`, `formatEta`
- `desktop/src/lib/pipeline.test.ts` (new) — 14 vitest unit tests for the above
- `desktop/src/components/ui/render-pipeline.tsx` (new) — 4-segment phase pipeline (move #5)
- `desktop/src/hooks/useSidecar.ts` (modified) — capture `phaseStartedAt` + progress `t` for per-phase ETA
- `desktop/src/App.tsx` (modified) — replaced generic Rendering card with `<RenderPipeline>`
- `desktop/package.json` (modified) — `vitest` devDep + `test` script
- `desktop/vitest.config.ts` (new) — vitest config (node env, `@` alias)

## Verification
- `npm test` — 14/14 vitest green (phase mapping, ETA extrapolation, edge cases, formatting)
- `npx tsc --noEmit` (via `npm run build`) — clean
- `npm run build` (tsc + vite) — clean, 49 modules
- No Rust changes — cargo unaffected by construction
- **Manual QA (pending, not headless-runnable per S1 precedent):** `npm run tauri dev`, run a
  real render, confirm the pipeline highlights the active step in amber, fills per-phase,
  shows ETA + elapsed, and that the app is dark-first with the warm palette.

## TDD note
Pure logic (`pipeline.ts`) was built test-first: wrote `pipeline.test.ts`, confirmed red
(10 failing against stubs), implemented, confirmed green (14/14). The component and palette
are presentational and verified via tsc + build + manual QA, matching the S1 testing split.
