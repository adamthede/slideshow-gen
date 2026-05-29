# PR #10 Review Log
**PR Title:** feat: Epic 4.S5 — post-render result view + render report
**Branch:** feat/epic-4-s5-result-view -> main
**URL:** https://github.com/adamthede/slideshow-gen/pull/10

## Summary
| Cycle | Date | Found | Actioned | Dismissed | Skipped | Commit | Ratio |
|-------|------|-------|----------|-----------|---------|--------|-------|
| 1 | 2026-05-29 16:54 | 2 | 2 | 0 | 0 | 447bd5a | 100% |
| 2 | 2026-05-29 17:09 | 7 | 7 | 0 | 0 | ec5857d | 100% |
| 3 | 2026-05-29 17:15 | 2 | 2 | 0 | 0 | 55fb69f | 100% |
| 4 | 2026-05-29 17:21 | 2 | 1 | 1 | 0 | f584b6d | 50% |

## Reviewer Effectiveness
| Reviewer | Total Found | T1 (Must) | T2 (Should) | T3 (Consider) | T4 (Dismiss) | Actioned % | Signal:Noise |
|----------|------------|-----------|-------------|---------------|-------------|-----------|-------------|
| Gemini | 13 | 0 | 12 | 0 | 1 | 92% | 12:1 |

(Copilot was re-requested each cycle but produced no new review comments on this PR.)

## Issue Categories (Cumulative)
| Category | T1 | T2 | T3 | T4 | Total | % of All |
|----------|----|----|----|----|-------|----------|
| security | 0 | 6 | 0 | 0 | 6 | 46% |
| data-integrity | 0 | 4 | 0 | 0 | 4 | 31% |
| style | 0 | 2 | 0 | 1 | 3 | 23% |

**Status:** MAX CYCLES REACHED

Loop terminated at the 4-cycle hard cap. Gemini's chained security findings produced an unusually high actioned rate (12 of 13). The cycle-4 cap fired exactly when bikeshedding would normally start; the final unactioned item was a platform-portability re-raise (DASHBOARD hotspot — macOS-only project).

## Cycle 1 — 2026-05-29 16:54

### Pre-Review Snapshot
- **Files changed:** 9 (527+ / 85-)
- **Test:Code ratio:** 0:9 (no test files in the diff — App.tsx, hooks, Tauri Rust, Tauri config, plus 3 plan docs)
- **CI status:** no checks configured on this branch
- **Linter offenses:** N/A (no Ruby in this project)

### Actioned (2)
#### T2-SHOULD: `Command::new("open")` lacks `--` separator (reveal_in_finder)
- **File:** `desktop/src-tauri/src/lib.rs:192`
- **Category:** `security`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "To prevent binary hijacking and argument injection, it is highly recommended to use the absolute path to the `open` binary..."
- **Disposition:** FIXED — Switched to `/usr/bin/open` + `--` separator. Real (if narrow) hardening: a user-chosen output path starting with `-` would otherwise be parsed as an option.
- **Thread ID:** PRRT_kwDOR-Xvl86Fk0dm

#### T2-SHOULD: `Command::new("open")` lacks `--` separator (open_in_quicktime)
- **File:** `desktop/src-tauri/src/lib.rs:214`
- **Category:** `security`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "Similar to `reveal_in_finder`, using the absolute path `/usr/bin/open` and separating options from the path argument with `--`..."
- **Disposition:** FIXED — Same hardening applied. (Note: `reveal_in_finder` itself was removed in cycle 2 in favor of the plugin; this cycle-1 hardening only sticks for `open_in_quicktime`.)
- **Thread ID:** PRRT_kwDOR-Xvl86Fk0do

### Dismissed (0)
None.

### Skipped (0)
None.

### Recurrence Patterns
- **Recurring:** `security` in *trust-boundary validation* — same family as PR-6 cycle 1's `os.setpgrp` silent-success and PR-2's GPS truthiness hotspot. Class is "don't blindly trust the shape of values from outside the program." Here the values are CLI argv positional args that `open(1)` may reinterpret as flags.

### Commit
SHA: 447bd5a
Message: fix: Address PR review cycle 1 — harden open invocation in Tauri commands

## Cycle 2 — 2026-05-29 17:09

### Actioned (7)
#### T2-SHOULD: `$HOME/**` asset-protocol scope is overly permissive
- **File:** `desktop/src-tauri/tauri.conf.json:30`
- **Category:** `security`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** FIXED — Replaced `$HOME/**` with per-file dynamic scope. Added new `allow_output_file(path)` Tauri command that calls `app.asset_protocol_scope().allow_file(&path)` before the frontend exposes the asset URL. Static scope now just `$TEMP/**`.
- **Thread ID:** PRRT_kwDOR-Xvl86Fvr67

#### T2-SHOULD: Import `tauri::Manager` for dynamic scoping
- **File:** `desktop/src-tauri/src/lib.rs:7`
- **Category:** `security`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** FIXED — Mechanical companion to the dynamic-scope refactor.
- **Thread ID:** PRRT_kwDOR-Xvl86Fvr6t

#### T2-SHOULD: Custom `reveal_in_finder` redundant with plugin
- **File:** `desktop/src-tauri/src/lib.rs:215`
- **Category:** `style`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** FIXED — Removed `reveal_in_finder` Tauri command. Frontend now uses `revealItemInDir` from `@tauri-apps/plugin-opener` (already a dependency). The audited plugin path replaces the custom argv plumbing I hardened in cycle 1 — a cleaner end state.
- **Thread ID:** PRRT_kwDOR-Xvl86Fvr7E

#### T2-SHOULD: Remove `reveal_in_finder` from invoke handler registration
- **File:** `desktop/src-tauri/src/lib.rs:240`
- **Category:** `style`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** FIXED — Companion to the previous removal.
- **Thread ID:** PRRT_kwDOR-Xvl86Fvr7M

#### T2-SHOULD: Import `revealItemInDir` in App.tsx
- **File:** `desktop/src/App.tsx:6`
- **Category:** `style`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** FIXED — Companion to the plugin migration.
- **Thread ID:** PRRT_kwDOR-Xvl86Fvr7U

#### T2-SHOULD: Skipped items only subtracted from images (overflow ignored)
- **File:** `desktop/src/App.tsx:273`
- **Category:** `data-integrity`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "There is a logic bug in how skipped items are subtracted from the rendered item counts. Currently, `skipped` is only subtracted from `discovery.images`..."
- **Disposition:** FIXED — Real reachable bug. The engine emits `item_failed` from Phase 3 (video compositing) too, so a video failure left the displayed video count stale. Skip now overflows from images into videos with the suggested two-step `Math.min` clamp.
- **Thread ID:** PRRT_kwDOR-Xvl86Fvr7i

#### T2-SHOULD: handleReveal should use `revealItemInDir` (plugin)
- **File:** `desktop/src/App.tsx:294`
- **Category:** `style`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** FIXED — `handleReveal` now calls `revealItemInDir(path)` instead of `invoke("reveal_in_finder")`.
- **Thread ID:** PRRT_kwDOR-Xvl86Fvr7k

### Dismissed (0)
None.

### Skipped (0)
None.

### Recurrence Patterns
- **Recurring:** `data-integrity` in *count-arithmetic with skipped/excluded subsets* — same family as PR-2's "GPS truthiness" + PR-4's progress-payload validation. Pattern: when totals are derived by subtracting a known subset, the subtraction must distribute correctly across the constituent categories, not just the first one.
- **New convention candidate:** When a Tauri-plugin equivalent exists (e.g. `tauri-plugin-opener`'s `revealItemInDir`), prefer the plugin over a custom Tauri command. Less audit surface, fewer argv-hardening edge cases. Add to CLAUDE.md if a second instance shows up.

### Commit
SHA: ec5857d
Message: fix: Address PR review cycle 2 — dynamic asset scope, plugin reveal, skip math

## Cycle 3 — 2026-05-29 17:15

### Actioned (2)
#### T2-SHOULD: `allow_output_file` lacks path validation (file-disclosure surface)
- **File:** `desktop/src-tauri/src/lib.rs:188`
- **Category:** `security`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "The `allow_output_file` command dynamically extends the asset protocol scope to allow the webview to read the file at `path`. However, there is no validation on the provided `path`..."
- **Disposition:** FIXED — Added `is_absolute()` check and `.mp4` extension gate before calling `allow_file`. Threat model is "compromised webview invokes allow_output_file with an arbitrary sensitive path" — a real-enough concern for a webview-touching command that this should not be wide open.
- **Thread ID:** PRRT_kwDOR-Xvl86FvwRK

#### T2-SHOULD: Async useEffect missing cleanup flag (state-after-unmount race)
- **File:** `desktop/src/App.tsx:306`
- **Category:** `data-integrity`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** FIXED — Added `let active = true; return () => { active = false; }` and gated the `setVideoAllowed(true)` on `active`. Real race window: user opens render-complete, clicks Render Again, completes a second render quickly; the in-flight invoke from the first render could otherwise flip `videoAllowed` after the second render replaced state.
- **Thread ID:** PRRT_kwDOR-Xvl86FvwRL

### Dismissed (0)
None.

### Skipped (0)
None.

### Recurrence Patterns
- **Recurring:** `data-integrity` in *async-effect lifecycle* — Marquee's first instance, but a generic React pattern. Worth a CLAUDE.md note if it recurs: any `useEffect` that awaits something must include an `active` cleanup flag before calling `setState`.

### Commit
SHA: 55fb69f
Message: fix: Address PR review cycle 3 — path validation + effect cleanup

## Cycle 4 — 2026-05-29 17:21

### Actioned (1)
#### T2-SHOULD: Symlink + case-sensitivity bypass of `.mp4` check
- **File:** `desktop/src-tauri/src/lib.rs:195`
- **Category:** `security`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "Allowing arbitrary paths to be added to the asset protocol scope without canonicalization can lead to local file disclosure. If a user-controlled path is a symlink named `render.mp4` pointing to a sensitive file..."
- **Disposition:** FIXED — `fs::canonicalize` before the extension check; case-insensitive `eq_ignore_ascii_case("mp4")`; canonicalized path passed to `allow_file`. Closes the symlink-bypass chain on the cycle-3 validation, and fixes the side bug where `.MP4` would have been rejected on macOS's case-insensitive filesystem.
- **Thread ID:** PRRT_kwDOR-Xvl86FvzY-

### Dismissed (1)
#### T4-DISMISS: `#[cfg(target_os = "macos")]` guard on open_in_quicktime
- **File:** `desktop/src-tauri/src/lib.rs:217`
- **Category:** `style`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** DISMISSED — DASHBOARD hotspot: "Gemini repeated platform/re-raise noise." Marquee is macOS-only per PRD NFR6 (videotoolbox encoder, Developer ID signing; sidecar built only for `aarch64-apple-darwin`). Convention held.
- **Thread ID:** PRRT_kwDOR-Xvl86FvzZR

### Skipped (0)
None.

### Recurrence Patterns
- **Recurring:** Gemini platform-portability re-raise — fifth PR demonstrating the documented hotspot. Convention is stable and held cleanly.
- **Note:** Gemini's chained security findings on `allow_output_file` (extension check → symlink bypass → case sensitivity) is a clean example of "each fix surfaces the next layer." Worth flagging in DASHBOARD: dynamically-scoped privileged commands deserve a fresh round of bot review after every parameter-validation change.

### Commit
SHA: f584b6d
Message: fix: Address PR review cycle 4 — canonicalize allow_output_file path
