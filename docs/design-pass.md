# Design pass — applying data-as-design to Marquee

**Status:** Planned. Not yet started.
**Source aesthetic:** the "data-as-design" principles applied across Thede Technologies apps. The source `design-principles.md` lives in a separate repo and is not vendored here.
**Companion docs:** [ADR-0001](adr/0001-app-stack.md) (stack), [PRD](../_bmad-output/planning-artifacts/prd.md) (epics)
**Date filed:** 2026-05-25

## Why this doc exists

Marquee currently ships in plain shadcn — functional, but visually generic. Adam has a recognizable design aesthetic he calls **data-as-design**, applied to his other apps (Lifeslice, Tractor, etc.). This doc captures (a) which of those principles transfer to Marquee, (b) the concrete UI moves that follow, and (c) where in the roadmap to land them so the work isn't paid for twice.

The full analysis was produced by a background agent reading the Lifeslice design-principles doc against the current Marquee UI; this is the distilled output.

## The five principles that define the aesthetic

1. **Warm near-black + amber + stone neutrals** — never cool gray dashboard chrome.
2. **Typography-as-structure** — dramatic size jumps, small-caps tracked labels, hero numerics replacing chart titles.
3. **Anti-box composition** — "boxes glued together" is explicitly the enemy; group by whitespace + shared baselines, not bordered Cards.
4. **Timeline-as-narrative** — time rendered spatially (rhythm, density, range), not as log lines.
5. **Calm density** — generous margins around dense, considered information; progressive disclosure over tabs/modals.

## What transfers to Marquee — and what doesn't

| Surface | Treatment |
|---|---|
| **Summary card** | ✅ Prime target. 4 stat tiles + a date string is exactly the spreadsheet the principles fight. |
| **Estimates** | ✅ Hero numerics + sense of scale. |
| **Settings summary line (collapsed)** | ✅ Already doing typography-as-structure; lean further in. |
| **Epic 4 progress UI** | ✅ The three-phase FFmpeg pipeline IS a timeline — highest-leverage surface in the app. |
| **Epic 4 result/preview view** | ✅ Feltron-style "render report" (inputs, settings, outputs, phase sparkline). |
| **Settings form fields** | ❌ Keep utility-grade. Don't art-direct a numeric stepper. |
| **Folder picker / drag-drop** | ❌ Functional affordance; needs clarity, not narrative. |
| **Diagnostics `<details>`** | ❌ Keep as the monospace escape hatch it already is. |

## The six concrete moves

### 1. Dark-first palette swap
Replace cool slate dark tokens in `desktop/src/index.css` with stone/amber:
- `#1C1917` background
- `#292524` surface
- `#FAFAF9 / #A8A29E / #78716C` text scale
- `#F59E0B` accent
Default to dark; light becomes the alternate (currently it's the inverse — light defaults via `prefers-color-scheme`).

### 2. De-card the Summary
Drop the Card chrome around the Summary block. Render the four hero metrics inline with generous margin and a hairline divider. Composition by whitespace, not by bordered container.

### 3. Date-range timeline bar
Replace the `2020-01-15 → 2024-08-03` string with a thin horizontal axis spanning the content width:
- Year tick marks
- Density histogram of photo counts per month bucketed across the range

This single move converts the summary from log to narrative. It earns its keep when a 10-year archive looks visibly different from a vacation folder. Data already available (we have `parsed_date` on every `MediaItem`); needs a sidecar protocol addition to emit a date-bucket histogram, or front-end derivation from a per-item date stream (TBD during planning).

### 4. GPS + dupes as inline glyphs, not equal tiles
- **GPS coverage** becomes a thin filled bar under the Images number: `3,412 images · ▰▰▰▰▰▱▱ 71% geotagged`
- **Duplicates** become a muted footnote, not a fourth hero stat

Equal weight for unequal importance is called out as an anti-pattern. Images and Videos are the primary metric; GPS and dupes are secondary descriptors of that primary set.

### 5. Phase pipeline progress (Epic 4)
Render the three FFmpeg phases (images → batching → compositing) as a horizontal pipeline:
- Three segments side-by-side
- Each fills left-to-right as it runs
- Elapsed time + ETA shown underneath the active segment
- Amber for in-flight, muted stone for pending/done
- State transitions morph (not replace)

This is the strongest data-as-design surface in the whole app. Don't ship it as a generic progress bar.

### 6. Render report on completion (Epic 4)
When the render finishes, Summary + Estimates + final stats collapse into a single Feltron-style composition above the `<video>` preview:
- Hero duration, hero file size
- The same date-range timeline from move #3, now annotated with the audio waveform if a track was used
- Settings used (compact, recoverable for "render again with same settings")

## Roadmap placement

**Recommendation:** dedicated design pass between Epic 4 and Epic 5, **with two exceptions pulled forward into Epic 4 from day one**.

### Pull into Epic 4 (must ship in the first render-capable build)
- **Move #1: Dark-first palette swap**
- **Move #5: Phase pipeline progress**

**Reason:** Epic 4 is when the app gets its first "watch it work and see the result" moment. Shipping that in plain shadcn dark-slate and re-skinning later wastes the strongest first-impression surface in the product. Both moves are tightly scoped (palette is a CSS variables swap; phase pipeline is a single component) and don't require waiting for the broader pass.

### Defer to the design pass (between Epic 4 and Epic 5)
- **Move #2: De-card the Summary**
- **Move #3: Date-range timeline bar**
- **Move #4: GPS + dupes as inline glyphs**
- **Move #6: Render report on completion**

**Reason:** these are layered visual upgrades on data we already have. They benefit from being landed together as a coherent pass, and from the full data shape (including Epic 4's render-completion data) being locked first so move #6 doesn't have to be redone.

### What this means for the next few commits

- **Right now:** finish merging PR #2 (Epic 2 close-out). No design work here.
- **Epic 3 (browse/exclude grid):** still optional per PRD; deferred. Skipping it does not affect this plan.
- **Epic 4 start:** include moves #1 and #5 in the Epic 4 scope from the start. They're not "polish" — they're part of the first render-capable build.
- **Between Epic 4 ship and Epic 5 kickoff:** open a focused branch for the design pass landing moves #2–#4 + #6. One PR, scoped to the visual reorganization, no functional changes.

## Files most affected (when work begins)

- `desktop/src/index.css` — tokens for move #1
- `desktop/src/App.tsx` — Summary block (~lines 600-670), Estimates block, future progress UI replacing the placeholder (~lines 565-600)
- `desktop/src/components/ui/` — likely new primitives: `Pipeline.tsx` (move #5), `Timeline.tsx` (move #3), `RenderReport.tsx` (move #6)
- Possibly a sidecar protocol extension for the date histogram (TBD during move #3 planning)

## What this doc is not

- Not a spec — these are design intents, not pixel-accurate mocks. Adam will exercise judgment on exact spacing, typography scale, and chart treatments at build time.
- Not a complete redesign — the form fields, picker, and diagnostics stay as-is.
- Not blocking — Epic 4 can be planned independently; this just calls out which two moves should not be deferred.
