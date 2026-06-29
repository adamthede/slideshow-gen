# PR #15 Review Log
**PR Title:** feat(ffmpeg): allow GPL build, ship GPLv3 attribution + written source offer
**Branch:** feat/ffmpeg-gpl-license-posture -> main
**URL:** https://github.com/adamthede/slideshow-gen/pull/15

> Dispatched-agent run, finalized by the orchestrating session. Worktree: `.claude/worktrees/ffmpeg-gpl-posture` on `feat/ffmpeg-gpl-license-posture`. Follow-on to E5.S7 (PR #14): switch the FFmpeg license posture from LGPL-only to GPL-allowed (arm's-length subprocess), ship the matching license text + attribution + written source offer, and pin the FFmpeg 8.1.1 vendor build.

## Summary
| Cycle | Date | Found | Actioned | Dismissed | Skipped | Commit | Ratio |
|-------|------|-------|----------|-----------|---------|--------|-------|
| 1 | 2026-06-29 18:38 | 1 | 1 | 0 | 0 | 5297642 | 100% |
| 2 | 2026-06-29 18:46 | 1 | 1 | 0 | 0 | 3de0dce | 100% |
| 3 | 2026-06-29 19:1x | 3 | 3 | 0 | 0 | e1b4437 | 100% |

> ⚠️ **Process note:** the dispatched agent stopped mid-cycle-3 while polling for the re-review and recorded "0 new threads — READY TO MERGE." That was wrong: Gemini's re-review of `3de0dce` posted **3 unresolved threads** (one a genuine license-compliance bug). They were caught and actioned by the orchestrating session by verifying the live GraphQL thread state rather than trusting the agent's status. Lesson reinforced: verify artifacts (`reviewThreads`), never an agent's self-reported "ready."

## Reviewer Effectiveness
| Reviewer | Total Found | T1 (Must) | T2 (Should) | T3 (Consider) | T4 (Dismiss) | Actioned % | Signal:Noise |
|----------|------------|-----------|-------------|---------------|-------------|-----------|-------------|
| Gemini | 5 | 1 | 4 | 0 | 0 | 100% | 5:0 |
| Copilot | 0 | 0 | 0 | 0 | 0 | n/a | — |

> Copilot returned a quota-limit error and produced zero threads (same as PR #14). Gemini was high-signal throughout — 5/5 actioned, including the T1 license-version catch in cycle 3.

## Issue Categories (Cumulative)
| Category | T1 | T2 | T3 | T4 | Total | % of All |
|----------|----|----|----|----|-------|----------|
| error-handling | 0 | 3 | 0 | 0 | 3 | 60% |
| licensing/compliance | 1 | 0 | 0 | 0 | 1 | 20% |
| documentation | 0 | 1 | 0 | 0 | 1 | 20% |

**Status:** All known review threads resolved; PR is MERGEABLE at `e1b4437` with 0 unresolved threads. A Gemini re-review of `e1b4437` may still post a final pass (this security/licensing file has drawn a comment every cycle) — being watched. Signed-build / notarization remain human-gated (Apple Developer ID cert secrets), as on PR #14.

The PR is a license-posture + attribution change (shell guard + docs + shipped license files); **no Python touched**. Validation after the cycle-3 fixes: the vendor script run CI-style against the pinned FFmpeg 8.1.1 build passes sha verify + the relaxed license guard ("no --enable-nonfree; GPL allowed") + all 6 feature guards; `bash -n` clean; `tauri.conf.json` valid JSON with the GPLv3 resource wired. (`pytest tests/` = 19 passed per the cycle-1/2 runs; cycle-3 changes are shell/docs/license-text only.)

## Cycle 1 — 2026-06-29 18:38

### Actioned (1)
#### T2-SHOULD: Fail closed on an empty FFmpeg `configuration:` line
- **File:** `desktop/scripts/vendor-ffmpeg.sh`
- **Category:** `error-handling`
- **Reviewer:** Gemini
- **Disposition:** FIXED — added `if [ -z "$CONFIG_LINE" ]; then fail ...` so a build whose `configuration:` line can't be read is refused rather than silently passing the `--enable-nonfree` guard. Thread `PRRT_kwDOR-Xvl86NECHo` (resolved).
- **Commit:** 5297642

## Cycle 2 — 2026-06-29 18:46

### Actioned (1)
#### T2-SHOULD: Fail closed on the `-encoders`/`-filters` capture (drop masking `|| true`)
- **File:** `desktop/scripts/vendor-ffmpeg.sh`
- **Category:** `error-handling`
- **Reviewer:** Gemini
- **Disposition:** FIXED — the SIGPIPE concern that motivated the table snapshot applies to the per-feature `grep -q`, not to the command-substitution captures (which read ffmpeg to EOF). Replaced `… || true` with `… || fail`. Thread `PRRT_kwDOR-Xvl86NEHHY` (resolved).
- **Commit:** 3de0dce

## Cycle 3 — 2026-06-29 (re-review of 3de0dce)

Gemini's re-review of `3de0dce` posted **3 threads** (the agent had already stopped and mis-recorded this cycle as empty). All three actioned in `e1b4437`.

### Actioned (3)
#### T1-MUST: Shipped license must match the build — it is GPLv3, not GPLv2
- **File:** `desktop/scripts/vendor-ffmpeg.sh` (license guard) + all attribution
- **Category:** `licensing/compliance`
- **Reviewer:** Gemini
- **Comment (paraphrased):** the app conveys GPLv2, but a build with `--enable-version3` is GPLv3; add a guard to fail on `--enable-version3`.
- **Disposition:** FIXED — verified the pinned 8.1.1 build is `--enable-gpl --enable-version3` = **GPLv3**, while the PR shipped GPLv2 text + labels (a real compliance bug). Corrected the *attribution* to GPLv3 (swap bundled license to verbatim GNU GPLv3, rename + rewire `tauri.conf.json`, flip every GPLv2 reference across docs/comments/plan). Did **not** add Gemini's literal fail-on-version3 guard — it would reject the only macOS/arm64 build Martin Riedl publishes, and GPLv3 conveyance is also compliant for a plain `--enable-gpl` ("v2 or later") build; the sha256 pin already fails closed on build-config drift. Rationale documented in the guard comment. Thread `PRRT_kwDOR-Xvl86NEPxN` (resolved).
#### T2-SHOULD: Accurate error messages on the feature-table captures
- **File:** `desktop/scripts/vendor-ffmpeg.sh`
- **Category:** `error-handling`
- **Reviewer:** Gemini
- **Disposition:** FIXED — the smoke check already proves execution, so "corrupt download or arch/linking issue" was wrong here; changed to "failed to retrieve encoders/filters list" + collapsed the double space. Thread `PRRT_kwDOR-Xvl86NENKf` (resolved).
#### T2-SHOULD: Literal ellipsis in the vendor-URL doc table
- **File:** `docs/release-pipeline.md`
- **Category:** `documentation`
- **Reviewer:** Gemini
- **Disposition:** FIXED — replaced `…/download/...` with the full `https://ffmpeg.martin-riedl.de/...` URLs. Thread `PRRT_kwDOR-Xvl86NENKu` (resolved).
- **Commit:** e1b4437

### Recurrence Patterns
- **fail-open / fail-flaky guards in `vendor-ffmpeg.sh`** — now 2 PRs, 4 instances (PR-14 `pipefail`; PR-15 empty-`CONFIG_LINE`, SIGPIPE false-negative, masking `|| true`). Convention candidate already on the dashboard.
- **NEW — shipped license text must be asserted against the actual build config.** The GPLv2/GPLv3 mismatch is the same *fail-open* shape one layer up: attribution that doesn't match `ffmpeg -version` ships the wrong license. Mitigation here is the sha256 pin (locks the exact build+license) + conveying the more-restrictive GPLv3 (compliant for any `--enable-gpl` build). Worth a CLAUDE.md line: *when bundling a copyleft binary, derive the license label from the build's `configuration:` line, not an assumption.*
