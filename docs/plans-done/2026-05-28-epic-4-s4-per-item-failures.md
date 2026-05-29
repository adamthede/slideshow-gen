---
title: "Epic 4.S4: Per-item failure handling (passive warnings panel)"
status: "Done"
created: 2026-05-28
completed: 2026-05-28
linked_pr: "https://github.com/adamthede/slideshow-gen/pull/8"
---

## Goal

A single bad input file must not abort an entire render. Per-item failures are surfaced **passively** in the UI — no modals, no required user action.

## Scope (do)

**Engine (Python sidecar)**
- Wrap per-item processing in Phase 1 (Ken Burns clip render) and Phase 3 (final composite, where item-scoped) in `try/except` so one failure doesn't kill the pipeline. Phase 2 (batch reduction) is batch-scoped — if a whole batch fails, that's a different class; for S4, focus on per-image and per-video failures.
- On per-item failure, emit a new IPC event `item_failed` carrying: `phase` (string), `path` (absolute string), `reason` (short string — e.g. "ffmpeg returned non-zero", "image unreadable"), `detail` (optional longer string, may include last N lines of stderr).
- Continue the render with that item skipped. Progress counts in `progress` events should reflect *attempted* total so the bar still completes.
- Extend the `complete` event with a new field `items_skipped: integer` (additive; default `0` if no failures). Keep `v: 1` — this is purely additive.
- Cancellation behavior (SIGTERM) is unchanged.

**IPC protocol**
- Document `item_failed` in `docs/sidecar-protocol.md` with schema + example. Document `items_skipped` addition to `complete`.
- Add `ItemFailedEvent` TypeScript type to `desktop/src/lib/sidecar-events.ts`. Extend `CompleteEvent` with `items_skipped?: number`.

**UI (Tauri/React)**
- Extend `useSidecar.ts` reducer to collect `item_failed` events into a `warnings: ItemFailedEvent[]` array on `SidecarState`. Initialize empty.
- Add a passive warnings surface in `App.tsx`:
  - **During render:** a small muted strip or chip in the rendering card showing `N items skipped` when `warnings.length > 0`. No click required. Style consistent with the dark palette shipped in E4.S2.
  - **On post-render / complete view:** a compact section listing skipped items (file basenames + reason). Collapsible is fine but not required. No blocking modal.
- Do NOT touch the cancel/cancelled/error flow. Do NOT touch the pre-render summary section (lines ~600–670 of App.tsx are reserved for a parallel design-pass effort).

**Tests**
- Add a test in `tests/test_ipc_protocol.py` (or a new sibling module) that:
  - Injects a synthetic failing item (e.g., monkey-patch the per-item runner to raise, or use a deliberately corrupted fixture).
  - Asserts the run completes with `items_skipped > 0`.
  - Asserts at least one `item_failed` event was emitted with the right shape.

## Out of scope (don't)

- Retry / skip / exclude affordances. Passive only.
- Catalog-wide failure modes (e.g., unreadable directory) — those should still abort. Don't try to "fix" them.
- The render report / Feltron composition — that's a separate story.
- Any change to the pre-render Summary section in App.tsx (parallel work; will conflict).
- Any change to `.github/workflows/` (parallel work in Epic 5.S1).

## Files expected to touch

- `src/slideshow_gen/pipeline.py`
- `src/slideshow_gen/ffmpeg.py`
- `src/slideshow_gen/events.py` (Reporter API addition for `item_failed`)
- `docs/sidecar-protocol.md`
- `desktop/src/lib/sidecar-events.ts`
- `desktop/src/hooks/useSidecar.ts`
- `desktop/src/App.tsx` (warnings strip + post-render section only — NOT the pre-render Summary)
- `tests/test_ipc_protocol.py` (or new test file)

## Success criteria

- A render with a deliberately bad image completes; `items_skipped > 0`; UI shows the basename in a passive panel.
- All existing tests pass; new failure-path test passes.
- PR is mergeable into `main` with no conflicts.
