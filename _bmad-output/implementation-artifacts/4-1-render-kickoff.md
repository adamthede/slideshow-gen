# Story 4.1: Render kickoff

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Marquee user who has scanned a folder and reviewed the estimate,
I want to hit **Render** and have the app run a real slideshow render to an output file I choose,
so that I get an actual MP4 on disk instead of just a pre-render preview.

## Context

This is the first story of **Epic 4 — Render execution and result**. Epics 1–2 stood up the Tauri shell, the signed Python sidecar, and the full ingestion → summary → estimate flow. Today the app **always** invokes the sidecar with `--estimate-only` and `--workers 1`, writing to a throwaway temp path that is never actually produced (the sidecar exits after the `estimate` event). See `desktop/src-tauri/src/lib.rs:46-92`.

E4.S1's job is the **kickoff**: turn that estimate-only invocation into a real render — drop `--estimate-only`, restore real worker parallelism, send the full settings payload, and write to a user-chosen output destination. It deliberately does **not** build the rich progress UI (that's **E4.S2**), cancellation (**E4.S3**), per-item warning panel (**E4.S4**), or the in-app result/preview view (**E4.S5**). Those stack on top of this story. Minimal "render running / render done / render failed" feedback is in scope so the story is independently demoable; polished phase-by-phase progress is not.

The IPC protocol already emits everything a real render needs (`phase_started`, `progress`, `phase_complete`, `complete`) — the engine is fully instrumented (see `docs/sidecar-protocol.md`). No Python engine changes are expected for this story.

## Acceptance Criteria

1. **Real render dispatch** — Given scanned folder(s) and chosen settings, when the user triggers Render, the sidecar is invoked **without** `--estimate-only` and runs the full three-phase pipeline to a `complete` event (not an early estimate-only exit).

2. **Output destination selection** — The user can choose where the output MP4 is written via a native save/destination picker. The chosen path is passed to the sidecar as `-o <path>`. If the user has not chosen one, a sensible default is used (e.g. `~/Movies/` or `~/Downloads/` with a generated filename) and surfaced to the user before render — the app never silently writes to a temp path for a real render.

3. **Full settings payload** — All user-tuned settings established in E2.S5 (resolution, slide/fade duration, fps, recursive, audio track + volume, appearance flags) are forwarded to the render invocation using the existing override-diff-against-`DEFAULT_SETTINGS` mechanism. Settings that match defaults are omitted; the CLI applies its own defaults.

4. **Worker parallelism restored** — The hardcoded `--workers 1` (forced for the cheap estimate-only path) is removed for real renders, letting the CLI apply its default worker count (or a user/Epic-4 setting if exposed). Estimate-only scans, if still invoked elsewhere, are unaffected.

5. **Estimate vs. Render are distinct actions** — Triggering a real render is a separate, explicit user action from the existing scan/estimate. The scan/estimate flow (E2.S2–S4) continues to work unchanged; a real render does not clobber the estimate-only code path.

6. **Minimal lifecycle feedback** — While a render runs the UI shows a running state (busy/disabled Render control + basic indicator), on `complete` it shows success including the output path(s) from the `complete` event's `outputs`, and on `error`/non-zero exit it shows a failure message. Rich per-phase progress UI is explicitly deferred to E4.S2.

7. **Single-render concurrency** — Only one sidecar render runs at a time; the existing spawn mutex (`sidecar.rs:121-126`) is respected and the Render control reflects busy state. Starting a render while one is in flight is prevented.

8. **No regression to estimate path** — Existing tests pass; the IPC protocol tests (`tests/test_ipc_protocol.py`), `cargo check`, `npx tsc --noEmit`, and `npm run build` are all clean.

## Tasks / Subtasks

- [x] **Task 1: Output destination (transient session state)** (AC: #2, #3)
  - [x] Decided output path is **transient React state** in `App.tsx` (`outputPath`), NOT persisted in `marquee.renderSettings.v1` — a stale absolute path surviving relaunch is a footgun. So `RenderSettings`/`DEFAULT_SETTINGS`/`loadSettings` were left untouched.
  - [x] Output is passed as a **dedicated `output: String` parameter** of the new `start_render` command, not a field of `ScanSettings`. Cleaner separation: settings = optional overrides, output = a required render input. `ScanSettings` unchanged.

- [x] **Task 2: Add a real-render Tauri command** (AC: #1, #4, #5)
  - [x] Added `start_render` `#[tauri::command]` alongside `start_scan`. Extracted a pure `build_args(folders, output, estimate_only, settings)` helper shared by both: `estimate_only=true` keeps the E2 path (`--workers 1` + `--estimate-only`); `estimate_only=false` (render) omits both, so the CLI uses default parallelism and runs to `complete`. Writes to the real `-o output`.
  - [x] Settings arg-assembly extracted to `append_settings()` and reused — only appends a flag when the matching `Option.is_some()`.
  - [x] Registered `start_render` in the `invoke_handler` (`generate_handler![start_scan, start_render]`).
  - [x] `spawn_sidecar()` reused unchanged (still stores the child handle in `SidecarState` for E4.S3 cancel).

- [x] **Task 3: Wire the frontend render action** (AC: #1, #3, #5, #6, #7)
  - [x] Added `startRender(folders, output, settings?)` to `useSidecar.ts`, mirroring `start()`, invoking `start_render`. Exposed alongside `start`/`reset`.
  - [x] Added explicit **Render** button in `App.tsx` distinct from Scan. Extracted shared `buildOverrides()` (used by both `runScan` and `runRender`).
  - [x] Render control disabled when `running` (single-render concurrency, AC #7); scan/render mutually gated.

- [x] **Task 4: Output destination picker UI** (AC: #2)
  - [x] Added a "Choose destination… / Change destination" control using `@tauri-apps/plugin-dialog`'s `save()` with a `slideshow-YYYY-MM-DD.mp4` default name and `.mp4` filter. Added the required `dialog:allow-save` capability (only `dialog:allow-open` was granted before).
  - [x] If no destination chosen, `runRender` prompts via the save dialog before starting — never silently writes to a temp path (AC #2). UI shows "Render will ask where to save." when unset.

- [x] **Task 5: Minimal lifecycle feedback** (AC: #6)
  - [x] Captured the `complete` event in `useSidecar` state (`complete: CompleteEvent | null`). Added a lightweight "Rendering…" card (phase + single progress bar) and a "Render complete" card listing `outputs` (path + size) and elapsed time. Errors reuse the existing error card. Rich per-phase UI deferred to E4.S2 as scoped.

- [x] **Task 6: Verify and guard against regressions** (AC: #8)
  - [x] `python -m pytest tests/` — 10 passed (no engine change).
  - [x] `cargo test --lib` — 21 passed (16 existing + 5 new arg-builder tests); `cargo check` clean.
  - [x] `npx tsc --noEmit` — clean.
  - [x] `npm run build` — clean Vite production build.
  - [x] Sidecar NOT rebuilt — no Python changes.
  - [x] End-to-end smoke through the **frozen sidecar binary**: real render (no `--estimate-only`) of a 3-image fixture → full lifecycle to `complete`, 171 KB MP4 written, 2.6 s duration matching the estimate. (Full GUI E2E via `npm run tauri dev` deferred to manual QA — headless here.)

## Dev Notes

### Current invocation path (what you are changing)
- `desktop/src-tauri/src/lib.rs:33-95` — `start_scan` command assembles: `["render", "--ipc", "--dir", <folder>, "-o", <PID temp path>, "--workers", "1", "--estimate-only", ...settings]`. The PID temp path (`lib.rs:48-51`, `marquee-estimate-{pid}.mp4`) is intentionally a throwaway because estimate-only exits before any encode. **Your render path replaces this temp path with the user's destination and drops both `--estimate-only` and the forced `--workers 1`.**
- `desktop/src-tauri/src/sidecar.rs:116-200` — `spawn_sidecar()` is render-agnostic: it spawns, stores the `CommandChild` in `SidecarState` (`Mutex<Option<CommandChild>>`, used later by E4.S3 cancel), and streams JSON-line events as `marquee://sidecar-event`. **Reuse as-is.**

### IPC: a real render emits more events than estimate-only
- Estimate-only lifecycle ends at `estimate` + `info` (`sidecar-protocol.md:169-179`). A **real render** continues: `phase_started(images)` → `progress(images)×N` → `phase_complete(images)` → batching/compositing → **`complete`** with `outputs: [{path, size_bytes}]` and `elapsed_s` (`sidecar-protocol.md:138-167`).
- The frontend reducer (`useSidecar.ts:110-141`) already handles `complete` (sets `done`) and `error`. The TS types in `sidecar-events.ts:95-105` already cover all render events. **No new event types needed** — this story consumes the existing contract; it just lets the render run past the estimate-only early-exit.

### Settings override mechanism (reuse, don't reinvent)
- `App.tsx:330-355` diffs each field against `DEFAULT_SETTINGS` and only includes overrides. `lib.rs:46-92` appends a CLI flag only when the matching `Option` is `Some`. Keep this two-sided minimalism — it's the project's "one source of truth for defaults: the CLI" principle from the PR #2 notes and CLAUDE.md.

### Output path — design decision to make and document
- `RenderSettings` (`settings.ts:10-26`) and `ScanSettings` (`lib.rs:7-29`) currently have **no** output field — deferred from E2.S5 explicitly to Epic 4 (PRD `prd.md:185`).
- Recommendation: treat output path as **transient session state**, not persisted in `marquee.renderSettings.v1`, to avoid a stale absolute path surviving across launches. Confirm and note your decision.
- Use `@tauri-apps/plugin-dialog`'s `save()` for the picker. The dialog plugin is already loaded (`lib.rs:97-104`, `Cargo.toml`). The audio picker (`App.tsx:305-313`) is the closest existing pattern.

### Scope guardrails (do NOT build these here)
- **E4.S2** — phase indicator, per-phase progress bars, ETA, cancel button. This story's feedback is minimal (running / done / failed) only.
- **E4.S3** — cancellation (SIGTERM the child stored in `SidecarState`). The handle is already stored; do not wire cancel UI here.
- **E4.S4** — per-item warning panel. `warning` events already flow into `state` but a dedicated panel is later.
- **E4.S5** — in-app `<video>` preview, Reveal in Finder, Open in QuickTime. This story only shows the output path text on `complete`.
- Other Epic-4-deferred settings (`--workers` as a user setting, `--batch-size`, `--chunk-duration`) — only `--workers` default restoration is in scope (AC #4). Exposing them as UI settings is optional/follow-up, not required.

### Testing standards
- Python engine: pytest in `tests/` (10 tests as of PR #2), with `tests/test_ipc_protocol.py` locking the protocol. No engine change expected — if you find yourself editing Python, reconsider scope.
- Rust: `cargo check`; existing `sidecar.rs` unit tests (`sidecar.rs:202-321`) cover parsing/buffering — extend only if you change parsing (you shouldn't).
- Frontend: `npx tsc --noEmit` + `npm run build` must stay clean.
- Manual E2E through the real sidecar binary is the acceptance proof — a render isn't "done" until an MP4 exists at the chosen path.

### Project Structure Notes
- Desktop app lives under `desktop/` (Tauri v2 + React + TS + Tailwind + shadcn/ui). Rust shell in `desktop/src-tauri/src/` (`lib.rs`, `sidecar.rs`, `main.rs`). Frontend in `desktop/src/` (`App.tsx`, `lib/settings.ts`, `lib/sidecar-events.ts`, `hooks/useSidecar.ts`).
- Sidecar binary: `desktop/src-tauri/binaries/slideshow-gen-aarch64-apple-darwin` (gitignored; built via `desktop/scripts/build-sidecar.sh`, embedded via `tauri.conf.json` `externalBin`).
- No conflicts with existing structure — this story extends `lib.rs` and `App.tsx`, adds no new top-level modules.

### References
- [Source: _bmad-output/planning-artifacts/prd.md#Epic 4 — Render execution and result] — E4.S1 definition, deferred settings.
- [Source: docs/sidecar-protocol.md#complete] — `complete` event shape (`outputs`, `elapsed_s`); estimate-only vs. happy-path lifecycles (`#Lifecycle examples`).
- [Source: docs/adr/0001-app-stack.md] — Tauri + React + Python sidecar architecture rationale.
- [Source: desktop/src-tauri/src/lib.rs:33-95] — current `start_scan` invocation to extend.
- [Source: desktop/src-tauri/src/sidecar.rs:116-200] — `spawn_sidecar` event bridge (reused as-is).
- [Source: desktop/src/App.tsx:330-355] — override-diff payload construction.
- [Source: desktop/src/lib/settings.ts:10-41] — `RenderSettings` + `DEFAULT_SETTINGS`.
- [Source: desktop/src/lib/sidecar-events.ts:95-105] — typed IPC event union.
- [Source: desktop/src/hooks/useSidecar.ts:81-141] — `start` invoke + reducer.
- [Source: PR #2 body — "What's deferred"] — "Epic 4 is next: drop `--estimate-only`, bump workers, add Output destination picker."

## Dev Agent Record

### Agent Model Used

claude-haiku-4-5-20251001 (Claude Code)

### Debug Log References

- **Stale-repo recovery (pre-implementation):** The local working tree was on a stale `origin/main` mirror (PR #1 / Epic 1). A `git fetch` revealed the real `origin/main` at `cd4d8d3` (PR #2 / Epic 2 merge); fast-forwarded to it before implementing. Implementation began on new branch `feat/epic-4-render-kickoff` cut from the real Epic 2 main.
- **E2E render smoke:** `binaries/slideshow-gen-aarch64-apple-darwin render --ipc --dir <fixture> -o <out.mp4> --slide-duration 1 --fade-duration 0.2` → emitted `started → discovery → estimate → phase_started(images) → phase_complete(images) → phase_started(compositing) → complete`, exit 0, 171 KB MP4, ffprobe duration 2.602 s.

### Completion Notes List

- Implemented a real render path without touching the Python engine — the IPC contract already supported the full render lifecycle; the only blocker was the shell forcing `--estimate-only`/`--workers 1`.
- **Key design decision:** output destination is a dedicated `output: String` parameter on `start_render` and transient React state, NOT a persisted setting. Keeps "optional overrides" (settings) cleanly separate from "required render input" (output) and avoids stale-path footguns.
- **Refactor for testability:** extracted pure `build_args()` + `append_settings()` in `lib.rs`, enabling 5 new Rust unit tests that lock the estimate-vs-render arg differences (no `--estimate-only`/no `--workers` on renders; real output + dirs forwarded; settings appended; audio-volume dropped without a track).
- Added missing `dialog:allow-save` capability — the save picker would have failed at runtime without it (only `dialog:allow-open` was granted).
- Scope held: no progress-phase UI (E4.S2), no cancel (E4.S3), no warning panel (E4.S4). **One E4.S5 item pulled forward:** "Reveal in Finder" button on each completed output (`revealItemInDir` via `@tauri-apps/plugin-opener` + `opener:allow-reveal-item-in-dir` capability). Result card shows output path + size text + Reveal button.
- Verification: pytest 10/10, cargo 21/21, tsc clean, vite build clean, real-render smoke through the frozen sidecar binary. Full GUI E2E (`npm run tauri dev`) left for manual QA — not runnable headless.

### File List

- `desktop/src-tauri/src/lib.rs` (modified) — extracted `append_settings()` + `build_args()`; added `start_render` command; registered it; added `#[cfg(test)]` arg-builder tests.
- `desktop/src-tauri/capabilities/default.json` (modified) — added `dialog:allow-save` and `opener:allow-reveal-item-in-dir`.
- `desktop/src/hooks/useSidecar.ts` (modified) — `complete` event captured in state; added `startRender()`.
- `desktop/src/App.tsx` (modified) — transient `outputPath`/`isRendering` state; `buildOverrides()`/`runRender()`/`pickOutput()`; Render button + output picker UI; Rendering + Render-complete cards.

## Change Log

| Date | Change |
|------|--------|
| 2026-05-25 | E4.S1 implemented: real render command (`start_render`), output-destination picker (`save()` + `dialog:allow-save`), full settings payload reuse, worker parallelism restored, minimal render lifecycle UI. Verified via pytest (10), cargo (21), tsc, vite build, and a real-render smoke through the frozen sidecar binary. Status → review. |
| 2026-05-25 | Pulled one E4.S5 item forward by request: "Reveal in Finder" button on each completed output, via `revealItemInDir` (`@tauri-apps/plugin-opener`) + `opener:allow-reveal-item-in-dir` capability. Confirmed working in the real GUI after a full render. tsc + build clean. |
