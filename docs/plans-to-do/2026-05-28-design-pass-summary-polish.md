---
title: Design pass #2/#4 — Summary section polish (de-card + inline glyphs)
status: To Do
linked_pr: ""
---

# Design pass: Summary section polish

## Goal

Polish the pre-render **Summary section** (the card that appears after a successful scan, before render starts). Two related design moves bundled as one pass:

- **Move #2: De-card the Summary.** The Summary today is one heavy `<Card>` with a single dense body. Open it up — replace the card chrome with a lighter section layout: section heading + horizontal rule + content arranged in a grid. Make it feel like the centerpiece of the pre-render view, not just another card in a stack of cards.
- **Move #4: Inline glyphs for GPS / duplicates / HEIC.** The three metadata facts the Summary surfaces (GPS coverage %, duplicate count, HEIC file count) currently render as plain text rows. Add a small leading glyph (lucide-react icon) for each: `MapPin` for GPS, `Copy` for duplicates, `Image` (or a HEIC-specific suggestion) for HEIC. Color the glyph muted unless the value is notable (e.g. duplicates > 0 → amber; GPS < 50% → muted; HEIC count > 0 → neutral). Make values prominent (larger / bolder) with small muted labels.

## Scope

### In scope (Agent owns end-to-end)

- Refactor the Summary section's JSX in `desktop/src/App.tsx` (it lives in the post-scan / pre-render branch — search for `Summary` or the GPS / duplicates / HEIC labels)
- Replace the outer `<Card>` wrapper with a lighter section layout (section heading + `<Separator>` + grid of stat blocks)
- Add lucide-react icon glyphs (already a dependency — verify with `grep lucide-react desktop/package.json`)
- Apply conditional muted/amber/neutral coloring based on the values' significance
- Preserve all existing data: file counts, GPS coverage %, duplicate count, HEIC count, total estimated duration, any error / warning chips already shown
- Preserve the "Render" CTA button and its disabled / loading states
- Keep responsive behavior — looks reasonable at the app's default window size (1024×640 or whatever the Tauri config sets)

### Out of scope

- The completion / post-render result view (that's parallel Agent 1 work — **do not touch the completion branch of `App.tsx`**)
- The rendering progress card, cancellation card, error card — all untouched
- Any changes to scan / discovery / IPC / engine code
- New design system primitives (use what shadcn/ui already provides: `Separator`, existing typography classes, existing color tokens)
- Adding new fields to the Summary that aren't there today — pure presentational refactor

## Files expected to change

- `desktop/src/App.tsx` — Summary section JSX only (the post-scan / pre-render branch). Touch ONLY that section. Do not touch the completion / "Render complete" branch.
- Possibly a small new component file (`desktop/src/components/SummaryStat.tsx`) if extracting a `<SummaryStat icon={...} label={...} value={...} tone={...} />` cleans up the JSX. Use judgment — don't over-extract.

## Success criteria

- Pre-render Summary no longer feels like a card stuck in a stack of cards; reads as the centerpiece of the pre-render view
- GPS / duplicates / HEIC each have a leading icon glyph
- Conditional coloring works: duplicates > 0 is visually distinct, GPS coverage low is muted, no values means no jarring color
- All existing Summary data still present
- "Render" CTA still works, still disables appropriately
- Manual smoke test in `npm run tauri dev` against a real scan

## Constraints

- macOS-only project; use the existing dark-first palette (don't introduce new colors outside the existing token set)
- Do not touch the completion branch of `App.tsx` (parallel work in progress)
- Do not touch the rendering / cancelled / error cards
- Do not change the scan IPC contract, `useSidecar.ts`, or any engine code
- Follow existing shadcn/ui conventions already established in the codebase
