---
title: Epic 4.S5 — post-render result view + Move #6 render report
status: In Progress
linked_pr: ""
---

# Epic 4.S5: In-app result view + Feltron-style render report

## Goal

When a render completes, replace the small "Render complete" success card with a real **result view**: a Feltron-style render report stacked above an in-app `<video>` preview, with primary actions (Reveal in Finder, Open in QuickTime, Render Again).

This is the natural conclusion of the render journey. Today the user gets a "complete" card and has to leave the app to actually see what they made; this story closes that loop.

## Scope

### In scope (Agent owns end-to-end)

**1. Render report (Move #6, Feltron-style):**
Above the video, render a compact "report card" displaying:
- **Duration** of the output (mm:ss)
- **Output file size** (formatted: e.g. "84.2 MB")
- **Item count** rendered (e.g. "127 images + 4 videos")
- **Items skipped** (only if > 0 — surface the existing `items_skipped` count from the `complete` event)
- **Settings used** (compact line: e.g. "1080p · Ken Burns · 4s per image, 1s crossfade") — pulled from the `start` event's settings payload or the existing render request
- Layout: Feltron-influenced — small grid of stat blocks with large numeric values + small uppercase labels. No icons in the numeric blocks. Generous whitespace.

**2. In-app `<video>` preview:**
- Standard HTML `<video controls>` element below the report
- `src` = `convertFileSrc(output_path)` (Tauri's asset protocol helper from `@tauri-apps/api/core`) — required for the webview to load a local file
- Verify Tauri's asset protocol is enabled in `tauri.conf.json` for the output directory (or wherever the user's chosen destination is). If it isn't, add `assetProtocol.scope` entries for the user's home/chosen output dir, OR use a `read_file_as_data_url`-style command. Make the call your judgment, but document the choice in the PR description.
- Reasonable max width/height so it fits the window; preserve aspect ratio
- Poster frame is optional — if trivial, generate one; if not, skip

**3. Primary actions (button row beneath the video):**
- **Reveal in Finder** — invoke a Tauri command that calls `open -R "$output_path"` (or equivalent `Command::new("open").args(["-R", path])`)
- **Open in QuickTime** — invoke a Tauri command that calls `open -a "QuickTime Player" "$output_path"`
- **Render Again** — reset the UI state back to the Summary/render-trigger view so the user can run the same job (or a new one) without restarting the app. Reuse the existing scan → summary → render flow. Do NOT auto-rerun; just return to the pre-render state.

### Out of scope

- Editing the render after the fact (no "tweak settings and re-render" — that's `Render Again` returning to Summary)
- Sharing/upload integrations
- Thumbnail strip / scrubbing affordances beyond what `<video controls>` gives for free
- Any change to pre-render Summary section (that's the parallel Agent 2 work — **do not touch the Summary section of `App.tsx`**)
- Any change to the engine, sidecar protocol, or `useSidecar.ts` reducer logic. The `complete` event already carries `output_path`, `duration` (if not, add it from the existing render stats), and `items_skipped`. If a stat you need is genuinely missing from the IPC payload, **stop and add it as a separate atomic commit** before building the UI on top.

## Files expected to change

- `desktop/src/App.tsx` — replace the completion branch (the "Render complete" card) with the new result view. Touch ONLY the completion branch (search for the existing `complete` / `Render complete` card). Do not touch the Summary section.
- `desktop/src-tauri/src/commands.rs` (or wherever Tauri commands live — discover via grep) — add `reveal_in_finder(path)` and `open_in_quicktime(path)` commands
- `desktop/src-tauri/src/lib.rs` — register the new commands in the invoke handler
- `desktop/src-tauri/tauri.conf.json` — possibly extend `assetProtocol.scope` if needed for the `<video>` src to load (see note above)
- Possibly small additions to `desktop/src/lib/sidecar-events.ts` if the `complete` event TypeScript shape is missing a field you need (e.g. `output_size`, `duration_seconds`). Keep additions optional (`?:`) for protocol-compat.
- If `duration_seconds` / `output_size_bytes` aren't already in the engine's `complete` emit, add them in `src/slideshow_gen/events.py` and `src/slideshow_gen/pipeline.py` (compute via `os.path.getsize` and an `ffprobe` call or by summing what the pipeline already tracks). Update `docs/sidecar-protocol.md` and `tests/test_ipc_protocol.py` to assert the new fields. Keep the additions additive (no breaking changes).

## Success criteria

- After a successful render, the result view shows: report stats, playable `<video>`, three working buttons.
- "Reveal in Finder" highlights the output file in a Finder window.
- "Open in QuickTime" opens the file in QuickTime Player.
- "Render Again" returns to the pre-render Summary state cleanly (no stale rendering/error state leakage).
- `items_skipped` block appears only when count > 0.
- No regressions in the rendering / cancellation / error flows.
- Manual smoke test in `npm run tauri dev` against a real small render.

## Constraints

- macOS-only (per PRD NFR6 — `open` and `open -a` are macOS commands; that's fine).
- Do not touch the Summary section of `App.tsx` (parallel work in progress).
- Do not change the `start`, `progress`, `cancelled`, `error`, or `item_failed` event handlers — only the `complete` handling and the post-complete UI.
- Follow existing card / button styling from shadcn/ui already in use.
