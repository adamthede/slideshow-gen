# PR #2 Review Log
**PR Title:** Epic 2: Ingestion + pre-render summary UI
**Branch:** feat/epic-2-summary-ui -> main
**URL:** https://github.com/adamthede/slideshow-gen/pull/2

## Summary
| Cycle | Date | Found | Actioned | Dismissed | Skipped | Commit | Ratio |
|-------|------|-------|----------|-----------|---------|--------|-------|
| 1 | 2026-05-25 01:50 | 13 | 11 | 1 | 1 | cc7b3e4 | 85% |
| 2 | 2026-05-25 01:58 | 3 | 0 | 3 | 0 | — | 0% |
| 3 | 2026-05-25 02:01 | 0 | 0 | 0 | 0 | — | — |

## Reviewer Effectiveness
| Reviewer | Total Found | T1 (Must) | T2 (Should) | T3 (Consider) | T4 (Dismiss) | Actioned % | Signal:Noise |
|----------|------------|-----------|-------------|---------------|-------------|-----------|-------------|
| Copilot | 10 | 0 | 8 | 1 | 1 | 80% | 4:1 |
| Gemini | 6 | 0 | 3 | 0 | 3 | 50% | 1:1 |

## Issue Categories (Cumulative)
| Category | T1 | T2 | T3 | T4 | Total | % of All |
|----------|----|----|----|----|-------|----------|
| data-integrity | 0 | 4 | 0 | 0 | 4 | 25% |
| error-handling | 0 | 3 | 0 | 1 | 4 | 25% |
| style | 0 | 1 | 1 | 2 | 4 | 25% |
| api-contract | 0 | 2 | 0 | 0 | 2 | 13% |
| test-coverage | 0 | 1 | 0 | 0 | 1 | 6% |
| documentation | 0 | 0 | 0 | 1 | 1 | 6% |

**Status:** READY TO MERGE — exited at cycle 3 via criterion 5 (current cycle 0 new threads AND prior cycle actioned 0). All 16 threads across 2 substantive cycles resolved; all T2 items fixed; both T3/T4 dispositions defensible.

## Cycle 1 — 2026-05-25 01:50

### Pre-Review Snapshot
- **Files changed:** 12 (966+ / 183-)
- **Test:Code ratio:** 1:9 (1 test file, 9 code files, 2 docs)
- **CI status:** no checks reported (no CI configured yet — slated for E5.S1)
- **Linter offenses:** N/A (multi-language project; per-language checks via `cargo check`, `tsc --noEmit`, `pytest`)

### Actioned (11)

#### T2-SHOULD: GPS coverage misses (0.0, 0.0) coordinates
- **File:** `src/slideshow_gen/pipeline.py:104`
- **Category:** `data-integrity`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "The current check `if i.gps_lat and i.gps_lon` will incorrectly evaluate to `False` if either coordinate is exactly `0.0` (e.g., locations on the Equator or Prime Meridian)..."
- **Disposition:** FIXED — explicit `i.gps_lat is not None and i.gps_lon is not None`. (Edge case is real — gull-island and similar locations exist on the equator.)
- **Thread ID:** PRRT_kwDOR-Xvl86EbnUM

#### T2-SHOULD: GPS coverage misses (0.0, 0.0) — duplicate
- **File:** `src/slideshow_gen/pipeline.py:104`
- **Category:** `data-integrity`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "GPS coverage is computed using truthiness (`if i.gps_lat and i.gps_lon`), which will incorrectly treat valid coordinates like `0.0` as 'missing'. Use explicit `is not None` checks..."
- **Disposition:** FIXED — same edit as above.
- **Thread ID:** PRRT_kwDOR-Xvl86Eb6u9

#### T2-SHOULD: `duplicates_removed` field is misnamed
- **File:** `src/slideshow_gen/pipeline.py:109`
- **Category:** `data-integrity`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "While duplicates are detected and counted, they are not actually removed from the `items` list. This means the subsequent `estimate_output(items, ...)` and the actual render process will still include these duplicate files..."
- **Disposition:** FIXED via rename — `duplicates_removed` → `duplicates_detected` across Python, TS interface, App.tsx, sidecar-protocol.md. Honest naming for what the code actually does. Actually removing dupes from the render is a deliberate behavior change deferred to a future PR (not Epic 2 scope).
- **Thread ID:** PRRT_kwDOR-Xvl86EbnUR

#### T2-SHOULD: `duplicates_removed` misnaming — duplicate
- **File:** `src/slideshow_gen/pipeline.py:109`
- **Category:** `data-integrity`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "`duplicates_removed` is emitted based on `len(detect_duplicates(items))`, but the code doesn't actually remove duplicates from `items`... Either (a) actually drop duplicate items before estimating/rendering, or (b) rename..."
- **Disposition:** FIXED — chose option (b) rename. Same edit as above.
- **Thread ID:** PRRT_kwDOR-Xvl86Eb6vA

#### T2-SHOULD: `dict[str, any]` references built-in `any()` not `typing.Any`
- **File:** `src/slideshow_gen/events.py:202`
- **Category:** `style`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "`payload` is annotated as `dict[str, any]`, but `any` here refers to Python's built-in function rather than `typing.Any`. This makes the annotation incorrect/misleading..."
- **Disposition:** FIXED — `dict[str, Any]` (Any was already imported).
- **Thread ID:** PRRT_kwDOR-Xvl86Eb6u6

#### T2-SHOULD: Protocol docs claim conditional fields but impl always emits
- **File:** `src/slideshow_gen/pipeline.py:117`
- **Category:** `api-contract`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "The protocol docs say some `discovery_complete` metadata fields are only present conditionally (e.g., GPS coverage only if any item has GPS, duplicates only if duplicates found), but this call always passes numeric values (including 0)..."
- **Disposition:** FIXED — updated docs (not the emitter). Always-present fields are easier for embedders to handle; clarified that `0.0` means "no GPS data", not "missing".
- **Thread ID:** PRRT_kwDOR-Xvl86Eb6vD

#### T2-SHOULD: Protocol docs vs impl — duplicate
- **File:** `docs/sidecar-protocol.md:107`
- **Category:** `api-contract`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "This section says `gps_coverage_percent` is 'Present only if any items have GPS data' and `duplicates_removed` is 'Present only if duplicates were found', but the current implementation always computes and emits numeric values..."
- **Disposition:** FIXED — same doc update as above.
- **Thread ID:** PRRT_kwDOR-Xvl86Eb6vZ

#### T2-SHOULD: useEffect cleanup race for drag-drop listener
- **File:** `desktop/src/App.tsx:218`
- **Category:** `error-handling`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "There is a potential race condition in the `useEffect` cleanup. The `unlisten` function is assigned asynchronously inside a `.then()` block. If the component unmounts before the promise resolves, the cleanup function will execute while `unlisten` is still `null`..."
- **Disposition:** FIXED — added `cancelled` flag; if cleanup runs before the promise resolves, the listener is unregistered as soon as it lands (`fn()` invoked immediately when cancelled).
- **Thread ID:** PRRT_kwDOR-Xvl86EbnUU

#### T2-SHOULD: useEffect cleanup race — duplicate
- **File:** `desktop/src/App.tsx:217`
- **Category:** `error-handling`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "The drag-drop unlisten handle is assigned asynchronously (`.then((fn) => { unlisten = fn })`). If the component unmounts before the promise resolves, the cleanup runs with `unlisten === null` and the listener can leak. Consider guarding with a `cancelled` flag..."
- **Disposition:** FIXED — same cancelled-flag pattern.
- **Thread ID:** PRRT_kwDOR-Xvl86Eb6vH

#### T2-SHOULD: Folder × button mutates state during in-flight scan
- **File:** `desktop/src/App.tsx:344`
- **Category:** `error-handling`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "Folder removal is still enabled while a scan is running. Clicking × during a scan will reset UI state and mutate the folder list while the sidecar continues scanning, which can leave the UI out of sync. Consider disabling the remove button (or all folder editing) when `running` is true."
- **Disposition:** FIXED — `disabled={running}` on the × button with `disabled:opacity-30 disabled:cursor-not-allowed`. Real cancellation is Epic 4.
- **Thread ID:** PRRT_kwDOR-Xvl86Eb6vL

#### T2-SHOULD: Test assertion doesn't match its comment
- **File:** `tests/test_ipc_protocol.py:75`
- **Category:** `test-coverage`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "The comment says discovery `progress` events 'must sit between phase_started and discovery_complete', but the assertions here don't actually enforce that ordering (they only filter `progress` out of the type list). If ordering matters to the contract, add an explicit check..."
- **Disposition:** FIXED — added explicit index-based ordering check (`phase_started_idx < i < discovery_complete_idx`) plus monotonic-`done` check across consecutive ticks.
- **Thread ID:** PRRT_kwDOR-Xvl86Eb6vS

### Skipped (1)

#### T3-CONSIDER: Reset to defaults doesn't clear localStorage
- **File:** `desktop/src/App.tsx:538`
- **Category:** `style`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Disposition:** SKIPPED — real concern but speculative impact. We haven't yet evolved defaults; the next useEffect tick re-writes the current `DEFAULT_SETTINGS` to storage anyway. Revisit when we actually change a default (likely with a versioned migration rather than a clear-on-reset).
- **Thread ID:** PRRT_kwDOR-Xvl86Eb6vb

### Dismissed (1)

#### T4-DISMISS: "Each field is optional" header comment
- **File:** `desktop/src/lib/settings.ts:5`
- **Category:** `documentation`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Disposition:** DISMISSED — comment describes the user-facing CLI semantics (any field unset by the user → CLI default applies), not the TypeScript type shape. As written it's accurate; rewording would arguably be less clear.
- **Thread ID:** PRRT_kwDOR-Xvl86Eb6vO

### Recurrence Patterns

- **`data-integrity` from `None`-vs-falsy distinction in Python boundary code** — 2 of 4 data-integrity threads (GPS truthiness, duplicates field naming) trace to the same root: treating "absent" and "zero/empty" as the same thing at the Python↔IPC boundary. Cross-PR check: PR-1 cycle 1 had a similar `parse_sidecar_line` issue where `"type": 42` was forwarded as `kind:"event"`. **Suggestion:** When emitting protocol fields, prefer explicit `is None` checks and field names that don't promise a behavior the code doesn't perform.

### Commit
SHA: cc7b3e4
Message: `fix: Address PR #2 review cycle 1 — correctness, race, protocol honesty`

## Cycle 2 — 2026-05-25 01:58

### Dismissed (3)

#### T4-DISMISS: Temp filename collision in --estimate-only path
- **File:** `desktop/src-tauri/src/lib.rs:51`
- **Category:** `error-handling`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** DISMISSED — the throwaway output path is for `--estimate-only`, which exits before any encode is started. The file is *never written*. Tauri also single-instances macOS apps by default. Adding a PID to the filename addresses a non-existent risk.
- **Thread ID:** PRRT_kwDOR-Xvl86Eb_wL

#### T4-DISMISS: Path split doesn't handle Windows backslashes
- **File:** `desktop/src/App.tsx:159`
- **Category:** `style`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** DISMISSED — scope creep. PRD NFR6 and ADR-0001 both lock v1 to macOS only. Windows is explicitly out of scope; adding Windows-aware code now would be dead code.
- **Thread ID:** PRRT_kwDOR-Xvl86Eb_wS

#### T4-DISMISS: Path split doesn't handle Windows backslashes — duplicate line
- **File:** `desktop/src/App.tsx:513`
- **Category:** `style`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** DISMISSED — same Windows out-of-scope concern, different line.
- **Thread ID:** PRRT_kwDOR-Xvl86Eb_wT

### Commit
SHA: — (no code changes)
Message: no commit — all items dismissed.

## Cycle 3 — 2026-05-25 02:01

Cycle 3 fetched 0 unresolved bot threads. Termination criterion 5 fires (current cycle 0 new threads AND previous cycle actioned 0). Exit READY TO MERGE.

### Commit
SHA: — (no code changes)
