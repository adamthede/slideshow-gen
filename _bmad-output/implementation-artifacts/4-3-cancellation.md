# Story 4.3: Render cancellation

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Marquee user who has started a render,
I want to cancel it mid-flight and have the app stop cleanly,
so that a wrong folder, wrong settings, or a render that's taking too long doesn't force me to wait it out or kill the app — and doesn't leave orphaned FFmpeg processes or gigabytes of temp files behind.

## Context

Third story of **Epic 4 — Render execution and result**. E4.S1 (PR #3) wired the real render dispatch; E4.S2 (PR #4) built the phase-pipeline progress UI. E4.S2 **deliberately shipped without a Cancel button** — the story doc and PR notes both call out that a bare process kill would orphan FFmpeg children and leak temp directories, "exactly what S3 handles." This is that story.

Cancellation is the one Epic 4 story that **requires Python engine changes** — S1 and S2 rode entirely on the existing IPC contract. Here the engine has to (a) catch a termination signal, (b) tear down its in-flight FFmpeg children, (c) run its temp cleanup, and (d) ideally announce that it stopped. That means **the frozen sidecar binary must be rebuilt and re-signed** for the first time since Epic 1 — a step S1/S2 explicitly skipped.

### What's already in place (and what's missing)

- **Rust handle:** `SidecarState.child: Mutex<Option<CommandChild>>` already stores the spawned child (`sidecar.rs:40-43`), set under the spawn mutex and cleared on `Terminated` (`sidecar.rs:188-192`). The comment on the struct literally says "so a future cancel command can SIGTERM the child." That future is now.
- **The trap:** `tauri-plugin-shell` 2.3.5 `CommandChild::kill(self)` (`process/mod.rs:77-83`) sends **SIGKILL** via `shared_child`, and only to the **direct child PID**. SIGKILL is uncatchable, so Python's cleanup never runs; and the direct child is the PyInstaller bootloader / Python parent — FFmpeg grandchildren spawned by the worker pool are *not* reached. Using `kill()` would produce precisely the orphan-and-leak outcome S2 refused to ship. We need a **graceful SIGTERM to the right target**, with `kill()`/SIGKILL only as a last-resort escalation. `CommandChild` exposes `pid()` (`process/mod.rs:84`), which is what we'll signal.
- **Python temp cleanup** lives in a `finally` block (`pipeline.py:195-203`). A `finally` runs on a normal return and on a raised exception (incl. `KeyboardInterrupt` from SIGINT) — but **not** on a default SIGTERM, which terminates the interpreter immediately without unwinding. So a SIGTERM today would skip cleanup. The engine needs an explicit SIGTERM handler that converts the signal into an exception (or an explicit cleanup path) so `finally` fires.
- **FFmpeg children:** phase 1 fans out via `ProcessPoolExecutor` (`ffmpeg.py:176-181`); phases 2–3 use `subprocess.run` / `Popen` (`ffmpeg.py:299,425,511`). On cancel these must be terminated or they keep encoding after the UI says "cancelled."
- **Protocol:** `docs/sidecar-protocol.md:201-203` already specs cancellation as "future": SIGTERM → clean temp → exit without `complete`, embedder infers cancel from *absence-of-`complete` + non-zero exit + recent `progress`*. That heuristic is brittle (it's indistinguishable from a mid-render crash). **Decision (this story): add an explicit `cancelled` event** as the primary signal, keep the heuristic only as a fallback for a SIGKILL'd process. See Dev Notes.
- **`--keep-temp`** already exists as a CLI flag (`cli.py:67`, `pipeline.py:45,198`) but is not exposed in the app. PRD E4.S3 calls for "`--keep-temp` parity exposed as a setting."

### Spike completed — the two hard questions are answered (with evidence)

Both open questions from the first draft were resolved empirically by freezing onefile PyInstaller probe binaries (matching `slideshow-gen.spec`: `--onefile`, `bootloader_ignore_signals=False`) and signaling them. **The implementer does not need to re-spike these; the mechanism below is verified.** Rebuild-time re-verification is still a task (the real engine differs from the probe), but the design is settled.

**Q(b) — Does SIGTERM survive the PyInstaller onefile bootloader?** ✅ **Yes.** The bootloader is the parent PID (what Tauri's `CommandChild::pid()` returns); the real Python interpreter is a forked child. With `bootloader_ignore_signals=False`, the bootloader forwards SIGTERM to the child *by PID*. Measured: SIGTERM to the bootloader → child's `signal.SIGTERM` handler ran → child `sys.exit(3)` → bootloader exited 3. Forwarding still works **after the child changes its own process group** (see Q(a)).

**Q(a) — Engine-owned teardown vs. OS process-group signaling?** ✅ **Engine-owned teardown, via a dedicated process group created *inside* the engine.** Findings:
- A naive handler that exits without touching children **orphans the FFmpeg-equivalent grandchildren** (measured: they reparent to PID 1 and keep running). So explicit teardown is mandatory — confirming exactly why S2 deferred the button.
- Rust-side `killpg` is **unsafe**: `tauri-plugin-shell` spawns the child in **Marquee's** process group (it exposes no new-group/new-session option), so signaling the group from Rust could signal the app itself.
- **Verified safe mechanism:** the engine calls `os.setpgrp()` at render start (before spawning the pool/FFmpeg), isolating its whole subtree into a *new* group whose leader is the Python process — distinct from Marquee's group. The SIGTERM handler then calls `os.killpg(os.getpgrp(), SIGTERM)`, which reaps the pool workers **and** their FFmpeg grandchildren **and** the direct `Popen` FFmpeg in one shot, then runs the existing temp cleanup, emits `cancelled`, and exits non-zero. Measured end-to-end: both grandchildren reaped, no orphans, exit 3 propagated. Because the group leader is the engine (not Marquee), `killpg(own-group)` provably cannot reach the app.

Net: **Rust sends SIGTERM to `CommandChild::pid()`** (never `kill()`/SIGKILL except as escalation); **the engine owns the teardown of its own process group.** This keeps the orphan-reaping logic where the children are owned, needs no plugin fork, and is unit-testable in pure Python.

## Acceptance Criteria

1. **Cancel control** — While a render is running, the progress UI shows a Cancel action (the button deferred from E4.S2). It is only present/enabled during an active render, not during estimate-only scans, not after completion.

2. **Graceful termination** — Triggering Cancel sends **SIGTERM** (not SIGKILL) to the sidecar so the engine can run its shutdown path. SIGKILL is used only as an escalation if the process has not exited within a bounded grace period (e.g. 5 s).

3. **No orphaned FFmpeg processes** — After a cancel, no `ffmpeg` child processes spawned by the render remain running. (Verified by checking for stray `ffmpeg` PIDs after cancelling a multi-image render.)

4. **Temp directory cleaned** — On cancel, the engine's temp directory (`slideshow-gen-*`) is removed, honoring `--keep-temp` when set (preserved + path reported, mirroring the normal-exit behavior in `pipeline.py:196-203`).

5. **No `complete` on cancel** — A cancelled render does **not** emit `complete` and does **not** write a final output MP4 (a partial/temp output must not masquerade as a finished render).

6. **Unambiguous cancelled state in the UI** — The app distinguishes *cancelled* from *succeeded*, *failed*, and *still-running*. The UI shows a clear "Render cancelled" state and offers the recovery paths from PR #5 (New slideshow / Render again). (Mechanism — explicit `cancelled` event vs. the absence-of-`complete` heuristic — decided in Dev Notes / Task 1.)

7. **Lifecycle-correct controls (no re-click race)** — Per the documented recurrence hotspot: client `running`/in-flight state tracks the **sidecar process lifecycle (`exit`)**, not the cancel request or any single event. The Cancel button disables the instant cancel is requested (showing "Cancelling…"), and render/scan controls re-enable only on process `exit`. A second Cancel click or a Render click during teardown cannot hit "already in progress."

8. **`--keep-temp` parity** — A Marquee setting forwards `--keep-temp` to the render invocation, so a user debugging a render can preserve the temp dir across both normal completion and cancellation.

9. **No regression** — `python -m pytest tests/` (incl. `tests/test_ipc_protocol.py`), `cargo test --lib` + `cargo check`, `npx tsc --noEmit`, and `npm run build` are all clean. The sidecar is rebuilt and the new signal path is exercised against the **frozen binary**, not just `python -m`.

## Tasks / Subtasks

- [x] **Task 1: Cancel-signaling contract — DECIDED** (AC: #5, #6)
  - **Decision:** add an explicit `cancelled` event (additive → **no** `PROTOCOL_VERSION` bump per `sidecar-protocol.md:212-214`; the Rust parser at `sidecar.rs:50-70` already forwards unknown-but-well-formed events, and the TS union ignores unrecognized ones). The absence-of-`complete` heuristic is retained only as a fallback for a SIGKILL'd process that never got to emit `cancelled`.
  - [x] Done: promoted promote `docs/sidecar-protocol.md` "Cancellation (future)" → real, documenting the `cancelled` event shape + non-zero exit code.

- [x] **Task 2: Engine — isolate process group, catch SIGTERM, reap subtree, clean temp** (AC: #2, #3, #4, #5) — *mechanism verified in spike, see Dev Notes*
  - [ ] On the `--ipc` render path only, call `os.setpgrp()` at render start **before** any pool/FFmpeg spawn, so the engine subtree forms its own process group (leader = the Python process, distinct from Marquee's group). Guard so the human CLI path is unaffected.
  - [ ] Install a SIGTERM handler that: (1) `os.killpg(os.getpgrp(), signal.SIGTERM)` to reap `ProcessPoolExecutor` workers (`ffmpeg.py:176`) + their FFmpeg children + the direct `Popen`/`subprocess.run` FFmpeg (`ffmpeg.py:299,425,511`) in one shot; (2) runs the existing temp cleanup (raise into the `finally` at `pipeline.py:195-203`, or call the cleanup directly — honoring `keep_temp`); (3) emits `cancelled` via the reporter *before* exit; (4) exits non-zero.
  - [ ] Confirm `complete` is never emitted on cancel and no output MP4 is written (a partial/temp file must not survive as a finished render).

- [x] **Task 3: Rust — `cancel_render` command (SIGTERM to pid + SIGKILL escalation)** (AC: #2, #7)
  - [ ] Add a `cancel_render` `#[tauri::command]` that reads the stored child's `pid()` (`sidecar.rs:40-43`) and sends **SIGTERM** to that PID via `nix`/`libc` `kill` — **not** `CommandChild::kill()` (which is SIGKILL and uncatchable). The onefile bootloader forwards SIGTERM to the Python child (verified). Hold the `SidecarState` mutex appropriately.
  - [ ] Escalation: if the child hasn't reached `Terminated` within a grace window (~5 s), send SIGKILL to the pid as a last resort so a wedged FFmpeg can't hang cancellation forever. (Engine-owned `killpg` should make this rare.)
  - [ ] Leave the existing `Terminated` handler as the single place that clears the child handle (`sidecar.rs:188-192`) — cancel *requests* the stop; `exit` *confirms* it.
  - [ ] Register `cancel_render` in `invoke_handler`. Add `nix` (or `libc`) to `Cargo.toml` if not already present.

- [x] **Task 4: Frontend — Cancel button + cancelled state** (AC: #1, #6, #7)
  - [ ] Add `cancelRender()` to `useSidecar.ts` (invokes `cancel_render`); add a `cancelling` flag and a `cancelled` state derived from the `cancelled` event (or the heuristic). Validate any new event fields at the reducer trust boundary (consistent with the S2 cycle-3/4 hardening).
  - [ ] Add the Cancel button to `RenderPipeline` (the slot S2 deferred). Disable on click → "Cancelling…"; never re-enable render/scan until `exit` (AC #7, the recurrence-hotspot rule).
  - [ ] Add a "Render cancelled" card/state in `App.tsx`, wired to the PR #5 recovery actions (New slideshow / Render again).

- [x] **Task 5: `--keep-temp` setting parity** (AC: #8)
  - [ ] Expose a keep-temp toggle in the settings drawer (`settings.ts` + the override-diff in `App.tsx`); forward `--keep-temp` via the existing `append_settings()` mechanism in `lib.rs`.

- [x] **Task 6: Tests + rebuild + manual cancel QA** (AC: #3, #9)
  - [ ] Python: a test asserting SIGTERM → temp dir removed + no `complete` (and `cancelled` emitted if chosen). Extend `tests/test_ipc_protocol.py` if a new event is added.
  - [ ] Rust: unit-test the arg/command wiring; (signal delivery itself is integration-level — cover via manual QA).
  - [ ] Frontend: `tsc` + `npm run build` clean; add vitest for any new pure state-derivation logic.
  - [ ] **Rebuild the sidecar** (`desktop/scripts/build-sidecar.sh`) and re-sign — first Python change since the freeze. Re-verify the spike's result against the *real* engine: start a render, SIGTERM the bootloader PID mid-phase-1, assert exit non-zero, `cancelled` emitted, temp gone (honoring `--keep-temp`), **zero stray `ffmpeg` PIDs**, no output file. (The spike confirmed the onefile bootloader forwards SIGTERM and that `setpgrp`+`killpg` reaps grandchildren; this step confirms it holds with the actual pool/Popen call sites.)
  - [ ] Manual GUI QA (`npm run tauri dev`): cancel during each phase; confirm cancelled card, recovery actions, and that a subsequent render starts cleanly (no "already in progress").

## Dev Notes

### The core risk: SIGKILL vs SIGTERM, and reaching the grandchildren (RESOLVED)
`CommandChild::kill()` (plugin-shell 2.3.5, `process/mod.rs:77-83`) is **SIGKILL on the direct child only** — two failure modes if used naively: (1) uncatchable → Python's `finally` temp cleanup never runs → leaked temp dirs; (2) direct-child-only → `ProcessPoolExecutor` workers and their `ffmpeg` subprocesses orphan and keep encoding. Both were reproduced in the spike.

**The verified mechanism** (see the "Spike completed" block in Context for the evidence): Rust sends **SIGTERM to `CommandChild::pid()`**; the onefile bootloader forwards it to the Python child; the engine — having called `os.setpgrp()` at render start to isolate its subtree into a dedicated group — reaps the whole subtree with `os.killpg(os.getpgrp(), SIGTERM)`, cleans temp, emits `cancelled`, and exits non-zero. SIGKILL-to-pid is the escalation-only fallback. Rust-side `killpg` was rejected: plugin-shell leaves the child in **Marquee's** process group, so signaling the group from Rust could hit the app — the group boundary must be created inside the engine.

### `cancelled` event vs. the absence-of-`complete` heuristic (DECIDED — emit `cancelled`)
The protocol's current "future" plan (`sidecar-protocol.md:201-203`) infers cancellation from *no `complete` + non-zero exit + recent `progress`* — **identical to the signature of a mid-render crash**, so the UI can't honestly say "cancelled" vs "failed." We emit an explicit `cancelled` event as the primary signal (additive, no version bump), keeping the heuristic only as the fallback for a SIGKILL-escalated process that never got to emit it.

### Lifecycle-correct controls (recurrence hotspot)
This is the project's most-repeated review finding (DASHBOARD.md: "Mid-job client-state mutation … now 3 PRs"). The rule: **client `running`/in-flight state tracks the sidecar process lifecycle (`exit`), not an IPC event.** Cancel *requests* the stop; the Rust `Terminated` handler clears the mutex (`sidecar.rs:188-192`) and the frontend re-enables controls on the `exit` message — never on the cancel click or the `cancelled` event. Disable the Cancel button AND guard the `cancel_render` handler so a double-click or a Render-during-teardown can't race. Build this in from the start; it's been a review finding on every prior render PR.

### Trust-boundary validation
Any new event (`cancelled`) or field gets coerced/validated at the `useSidecar` reducer, matching the S2 cycle-3/4 pattern (drop malformed ticks rather than propagate NaN/undefined). Don't scatter component-level guards.

### Sidecar rebuild + signing
Unlike S1/S2 (no Python changes), this story edits the engine, so `desktop/scripts/build-sidecar.sh` must rebuild the frozen binary and it must be re-signed. Acceptance proof is the cancel path through the **frozen** binary, not `python -m` — signal handling and child-process teardown can differ under PyInstaller.

### Scope guardrails (do NOT build here)
- **E4.S4** — per-item failure/warning panel. `warning` events already flow into state; the dedicated panel is S4.
- **E4.S5** — in-app `<video>` preview, Open in QuickTime. (Reveal in Finder + Render-again already landed in S1/PR #5.)
- Do not expose `--workers` / `--batch-size` / `--chunk-duration` as settings here (optional follow-ups); only `--keep-temp` is in scope (AC #8).

### References
- [Source: prd.md#Epic 4 — E4.S3] — "Cancellation: terminate the sidecar process, which propagates SIGTERM to in-flight FFmpeg children; sidecar cleans temp directory before exit. `--keep-temp` parity exposed as a setting."
- [Source: docs/sidecar-protocol.md:201-214] — Cancellation (future) + additive versioning rule.
- [Source: desktop/src-tauri/src/sidecar.rs:40-43,111-205] — stored child handle; spawn mutex; `Terminated` clears the handle.
- [Source: ~/.cargo/.../tauri-plugin-shell-2.3.5/src/process/mod.rs:77-84] — `CommandChild::kill()` = SIGKILL on direct child; `pid()` exposed.
- [Source: src/slideshow_gen/pipeline.py:155-203] — temp dir creation + `finally` cleanup honoring `keep_temp`.
- [Source: src/slideshow_gen/ffmpeg.py:176-181,299,425,511] — ProcessPoolExecutor + Popen/subprocess children to tear down.
- [Source: src/slideshow_gen/events.py:160-251] — `JsonReporter._emit`; where a `cancelled` event would be added.
- [Source: src/slideshow_gen/cli.py:67,143] — existing `--keep-temp` flag to surface as a setting.
- [Source: docs/pr-reviews/DASHBOARD.md — Recurrence Hotspots] — client running-state-tracks-lifecycle rule.
- [Source: _bmad-output/implementation-artifacts/4-2-progress-pipeline.md] — Cancel button explicitly deferred from S2 to S3.

## Dev Agent Record

### Agent Model Used
claude-opus-4-7 (Claude Code), implemented interactively on `feat/epic-4-s3-cancellation`.

### Completion Notes
- **Engine** (`pipeline.py`, `events.py`, `cli.py`): `RenderPipeline(cancellable=…)` (set from `--ipc`) calls `os.setpgrp()` at `run()` start and installs a SIGTERM handler that `killpg`-reaps its own group, runs the shared `_cleanup_temp()` (honoring `--keep-temp`), emits a new `cancelled` reporter event, and `os._exit(130)`. The `finally` path was refactored onto the same `_cleanup_temp()` helper. Console/Json reporters both implement `cancelled`. Interactive (non-IPC) runs are untouched — no setpgrp, normal Ctrl-C.
- **Rust** (`sidecar.rs`, `lib.rs`, `Cargo.toml`): `cancel_render` command → `cancel_sidecar()` sends `libc::kill(pid, SIGTERM)` (not `CommandChild::kill()`/SIGKILL), leaves the handle in place so the existing `Terminated`→`exit` path drives the UI, and spawns a thread that escalates to SIGKILL after a 5 s grace only if the same pid is still registered. `libc` declared explicitly (already transitive). `keep_temp` setting → `--keep-temp`.
- **Frontend** (`sidecar-events.ts`, `useSidecar.ts`, `render-pipeline.tsx`, `App.tsx`, `settings.ts`): `CancelledEvent` type; `cancelled`/`cancelling` state + `cancelRender()` action; reducer leaves `running` true on `cancelled` and clears `cancelling` only on `exit` (lifecycle-correct, per the recurrence hotspot). Cancel button in `RenderPipeline` (→ "Cancelling…", disabled). "Render cancelled" card with Render again / New slideshow recovery. `keepTemp` setting + drawer toggle + `buildOverrides`.
- **Decision recorded:** explicit `cancelled` event is the primary signal; the absence-of-`complete` heuristic is documented as the SIGKILL-only fallback. Protocol doc updated.

### Verification
- `pytest tests/` — 11/11 (incl. new `test_ipc_cancel_cleans_up_and_emits_cancelled`: SIGTERM mid-render → `cancelled`, temp removed, no `complete`, no output, no orphan ffmpeg, exit 130).
- `cargo test --lib` — 23/23 (+2 keep-temp arg tests; `cancelled` added to the parser vocabulary test).
- `tsc --noEmit` clean; `vite build` clean (50 modules); `vitest` 21/21.
- **Sidecar rebuilt + re-signed** (Developer ID, signature verified). **Cancel verified against the frozen binary** twice — including with two ffmpeg workers actively encoding at signal time: exit 130, `cancelled` emitted, temp cleaned, no output, **both ffmpeg workers reaped (no orphans)**. Confirms the spike's `setpgrp`+`killpg` mechanism survives the real PyInstaller bootloader.
- **Deferred to the user:** interactive GUI QA via the running `npm run tauri dev` (cancel button, cancelled card, recovery, controls re-enabling on exit) — not headless-runnable, per S1/S2 precedent.

### File List
- `src/slideshow_gen/events.py` (modified) — `cancelled` reporter method (ABC + Console + Json).
- `src/slideshow_gen/pipeline.py` (modified) — `cancellable`, `_install_cancel_handler`, `_on_sigterm`, `_cleanup_temp`; `CANCEL_EXIT_CODE`.
- `src/slideshow_gen/cli.py` (modified) — pass `cancellable=ipc`.
- `tests/test_ipc_protocol.py` (modified) — cancel test + `_make_assets(count)` + `_list_ffmpeg_pids`.
- `docs/sidecar-protocol.md` (modified) — `cancelled` event + real Cancellation section.
- `desktop/src-tauri/src/sidecar.rs` (modified) — `cancel_sidecar` + escalation; `cancelled` in vocab test.
- `desktop/src-tauri/src/lib.rs` (modified) — `cancel_render` command, `keep_temp` setting, keep-temp tests.
- `desktop/src-tauri/Cargo.toml` (modified) — `libc`.
- `desktop/src/lib/sidecar-events.ts` (modified) — `CancelledEvent`.
- `desktop/src/hooks/useSidecar.ts` (modified) — cancelled/cancelling state, `cancelRender`, reducer cases.
- `desktop/src/components/ui/render-pipeline.tsx` (modified) — Cancel button.
- `desktop/src/App.tsx` (modified) — cancelled card, wiring, keep-temp toggle.
- `desktop/src/lib/settings.ts` (modified) — `keepTemp` setting + load guard.

## Change Log

| Date | Change |
|------|--------|
| 2026-05-27 | Story drafted from PRD E4.S3 + codebase reconnaissance (Rust SIGKILL trap, Python `finally`-cleanup gap, FFmpeg child teardown, `cancelled`-event decision). Status → draft. |
| 2026-05-27 | Spike resolved both open questions with frozen onefile probes: (b) bootloader forwards SIGTERM to the Python child by PID, even across a child `setpgrp`; (a) engine-owned teardown via `os.setpgrp()` + `os.killpg(own-group, SIGTERM)` reaps pool workers + FFmpeg grandchildren with no orphans, and is provably app-safe (group leader is the engine, not Marquee). Tasks 1–3 + Dev Notes updated to the verified mechanism. Status → ready for dispatch. |
| 2026-05-27 | Implemented all six tasks across engine/Rust/frontend (3 commits). Sidecar rebuilt + re-signed; cancel verified against the frozen binary with ffmpeg actively encoding (exit 130, `cancelled`, temp cleaned, no output, no orphans). pytest 11/11, cargo 23/23, tsc/vite clean, vitest 21/21. Interactive GUI QA left to the user. Status → review. |
