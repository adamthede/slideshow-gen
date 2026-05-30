---
title: Design pass — Move #3 (date-range timeline + density histogram)
status: In Progress
---

# Design pass — Move #3: date-range timeline + density histogram

## Goal

Replace the plain `2020-01-15 → 2024-08-03` date-range string in the Summary
section with a thin horizontal timeline bar carrying a per-month density
histogram of photo counts. This is the last unshipped move from
`docs/design-pass.md` and the one called out as "converts the summary from
log to narrative."

## Approach

1. **Sidecar protocol extension.** Add an optional `date_histogram` field to
   the `discovery_complete` event: a list of `{month: "YYYY-MM", count: N}`
   entries spanning every month from the earliest to the latest parsed date
   (zero-fill missing months so the timeline shows true gaps). Items without
   a parsed date are excluded from the histogram (consistent with how
   `date_range` is computed today).
2. **Frontend Timeline component.** New `desktop/src/components/Timeline.tsx`
   renders an SVG density histogram: month-bars rising from a baseline, year
   tick labels along the axis, earliest/latest date labels at the ends.
3. **Wire into Summary.** Replace the existing `date_range` arrow row in
   `App.tsx` with the new `Timeline` when a `date_histogram` is present.
   Fall back to the current arrow-string rendering when only `date_range` is
   available (older sidecar / parity safety).

## Constraints

- **Backward-compatible IPC.** `date_histogram` is optional; existing
  consumers must keep working. The protocol version stays `1`.
- **No new dependencies on the frontend.** Pure SVG; no charting library.
- **Match the design-pass aesthetic.** Amber accent on bars, stone-muted
  axis and labels, generous whitespace, typography-as-structure for the
  YEAR ticks.
- **Performance.** A 10-year archive is at most 120 month-buckets — render
  cost is negligible. No virtualization needed.

## Scope

### In scope
- `src/slideshow_gen/pipeline.py`: compute month-bucket histogram alongside
  `date_range`, pass to `reporter.discovery_complete`.
- `src/slideshow_gen/events.py`: accept `date_histogram` kwarg on both the
  base `EventReporter` and `IPCReporter`; serialize as
  `[{month, count}, ...]` only when non-empty.
- `tests/test_ipc_protocol.py`: assert `date_histogram` shape on the full
  render lifecycle test.
- `docs/sidecar-protocol.md`: document the new field.
- `desktop/src/lib/sidecar-events.ts`: add `date_histogram` to
  `DiscoveryCompleteEvent`.
- `desktop/src/components/Timeline.tsx`: new component.
- `desktop/src/App.tsx`: render Timeline in the Summary section.

### Out of scope
- Audio waveform annotation on the timeline (mentioned in design-pass move
  #6 — separate work, requires audio-file analysis).
- Per-day histogram. Monthly buckets are the right granularity for the
  spans this app handles (vacation folder → multi-year archive).
- Hover tooltips with month-by-month counts. Could be added later but the
  primary signal is the silhouette, not the readouts.

## Files

- Modify: `src/slideshow_gen/pipeline.py`
- Modify: `src/slideshow_gen/events.py`
- Modify: `tests/test_ipc_protocol.py`
- Modify: `docs/sidecar-protocol.md`
- Modify: `desktop/src/lib/sidecar-events.ts`
- Create: `desktop/src/components/Timeline.tsx`
- Modify: `desktop/src/App.tsx`

## Success criteria

- New IPC test passes; existing IPC tests stay green.
- `npm run build` in `desktop/` succeeds; no TypeScript errors.
- Manually inspect: scan a folder with mixed dates → Summary shows the
  histogram with year ticks; a single-month folder shows a single
  populated bar at the right side; a folder with no parsed dates falls
  back gracefully (no Timeline rendered).
