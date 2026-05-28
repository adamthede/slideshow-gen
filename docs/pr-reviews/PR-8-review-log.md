# PR #8 Review Log
**PR Title:** feat: Epic 4.S4 — per-item failure handling (passive warnings panel)
**Branch:** feat/epic-4-s4-per-item-failures -> main
**URL:** https://github.com/adamthede/slideshow-gen/pull/8

## Summary
| Cycle | Date | Found | Actioned | Dismissed | Skipped | Commit | Ratio |
|-------|------|-------|----------|-----------|---------|--------|-------|
| 1 | 2026-05-28 17:38 | 5 | 3 | 2 | 0 | 9e6eae8 | 60% |
| 2 | 2026-05-28 17:47 | 2 | 0 | 2 | 0 | — | 0% |

## Reviewer Effectiveness
| Reviewer | Total Found | T1 (Must) | T2 (Should) | T3 (Consider) | T4 (Dismiss) | Actioned % | Signal:Noise |
|----------|------------|-----------|-------------|---------------|-------------|-----------|-------------|
| Copilot | 3 | 0 | 3 | 0 | 0 | 100% | 3:0 |
| Gemini | 4 | 0 | 0 | 0 | 4 | 0% | 0:4 |

## Issue Categories (Cumulative)
| Category | T1 | T2 | T3 | T4 | Total | % of All |
|----------|----|----|----|----|-------|----------|
| api-contract | 0 | 3 | 0 | 0 | 3 | 43% |
| style | 0 | 0 | 0 | 4 | 4 | 57% |

**Status:** READY TO MERGE

---

## Cycle 1 — 2026-05-28 17:38

### Pre-Review Snapshot
- **Files changed:** 9 (377+ / 28-)
- **Test:Code ratio:** 1:8 (tests/test_ipc_protocol.py : 8 code/config files)
- **CI status:** No CI checks configured
- **Linter offenses:** N/A (Python, no rubocop; pytest 4/4 pass)

### Actioned (3)

#### T2-SHOULD: resolve item.path before emitting item_failed in _render_worker
- **File:** `src/slideshow_gen/ffmpeg.py:137`
- **Category:** `api-contract`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "The `item_failed.path` value is built from `item.path` without resolving it, so invoking the CLI with a relative `--dir` can emit a relative path even though the new protocol documents this field as an absolute path..."
- **Disposition:** FIXED — Changed `str(item.path)` to `str(item.path.resolve())` in `_render_worker` return tuple
- **Thread ID:** PRRT_kwDOR-Xvl86FiMgT

#### T2-SHOULD: resolve item.path in pipeline.py video prep item_failed events
- **File:** `src/slideshow_gen/pipeline.py:570`
- **Category:** `api-contract`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "Video-prep `item_failed` events also pass through `str(item.path)` directly, which can be relative when the source directory was supplied as a relative CLI path..."
- **Disposition:** FIXED — Changed both `str(item.path)` calls (video prep failure and exception paths) to `str(item.path.resolve())` in `_prep_video_item`
- **Thread ID:** PRRT_kwDOR-Xvl86FiMgp

#### T2-SHOULD: resolve path in idx_to_path worker crash fallback map
- **File:** `src/slideshow_gen/ffmpeg.py:193`
- **Category:** `api-contract`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "The fallback path used for crashed workers is also derived with `str(item.path)`, so it can violate the documented absolute-path contract for `item_failed.path` when inputs are relative..."
- **Disposition:** FIXED — Changed `str(item.path)` to `str(item.path.resolve())` in `idx_to_path` dict comprehension
- **Thread ID:** PRRT_kwDOR-Xvl86FiMgw

### Dismissed (2)

#### T4-DISMISS: Windows backslash path separator in App.tsx line 80
- **File:** `desktop/src/App.tsx:80`
- **Category:** `style`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** DISMISSED — Marquee is macOS-only per PRD NFR6. Windows portability suggestions are a stable recurrence pattern (documented in DASHBOARD.md Recurrence Hotspots). This is the same class of noise seen in PR-2, PR-3, PR-6.
- **Thread ID:** PRRT_kwDOR-Xvl86FiA0n

#### T4-DISMISS: Windows backslash path separator in App.tsx line 840
- **File:** `desktop/src/App.tsx:840`
- **Category:** `style`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** DISMISSED — Same reason as above. Duplicate cross-platform portability suggestion for the same pattern on a different line.
- **Thread ID:** PRRT_kwDOR-Xvl86FiA0t

### Skipped (0)
No T3 items this cycle.

### Recurrence Patterns
- **Recurring:** `style` / Windows path-separator suggestions in `desktop/src/` — also seen in PR-2 (temp-file collision), PR-3 (Finder/Folder), PR-6 (setpgrp/killpg). Gemini's stable cross-platform noise pattern. This is now 5+ occurrences — the DASHBOARD.md "Gemini repeated platform noise" hotspot rule covers it.
- No new T1/T2 recurrence patterns detected.

### Commit
SHA: 9e6eae8
Message: fix: Address PR review cycle 1 — resolve relative paths in item_failed events

---

## Cycle 2 — 2026-05-28 17:47

### Actioned (0)
No T1 or T2 items this cycle.

### Dismissed (2)

#### T4-DISMISS: Windows backslash path separator in App.tsx line 80 (re-raise)
- **File:** `desktop/src/App.tsx:80`
- **Category:** `style`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** DISMISSED — Identical re-raise of cycle 1 thread 1. Marquee is macOS-only per PRD NFR6. Gemini stable noise pattern.
- **Thread ID:** PRRT_kwDOR-Xvl86FiYx4

#### T4-DISMISS: Windows backslash path separator in App.tsx line 840 (re-raise)
- **File:** `desktop/src/App.tsx:840`
- **Category:** `style`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** DISMISSED — Identical re-raise of cycle 1 thread 2. Marquee is macOS-only per PRD NFR6. Gemini stable noise pattern.
- **Thread ID:** PRRT_kwDOR-Xvl86FiYx9

### Skipped (0)
No T3 items this cycle.

### Recurrence Patterns
- **Gemini Windows path-separator noise is now confirmed in cycle 2 of this PR as well.** Gemini re-raised the exact same 2 comments after the cycle 1 push (which made no changes to App.tsx). This matches the documented hotspot: Gemini will re-raise Windows portability suggestions even when the fix pushed was unrelated to the flagged lines. **Recommendation:** Add to CLAUDE.md — on any PR touching `desktop/src/`, immediately dismiss Gemini path-separator Windows portability suggestions without reading them.

### Commit
SHA: — (no code changes this cycle)

### Loop Termination
Termination criterion 5 met: cycle 2 actioned=0 and current check found 0 unresolved threads. **Status: READY TO MERGE.**
