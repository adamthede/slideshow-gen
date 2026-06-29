# PR #14 Review Log
**PR Title:** feat(release): bundle a signed FFmpeg into Marquee.app (E5.S7)
**Branch:** feat/epic-5-s7-bundle-ffmpeg -> main
**URL:** https://github.com/adamthede/slideshow-gen/pull/14

## Summary
| Cycle | Date | Found | Actioned | Dismissed | Skipped | Commit | Ratio |
|-------|------|-------|----------|-----------|---------|--------|-------|
| 1 | 2026-06-26 20:35 | 2 | 2 | 0 | 0 | c3102f9 | 100% |
| 2 | 2026-06-26 20:37 | 2 | 1 | 1 | 0 | bf6ea5c | 50% |
| 3 | 2026-06-26 20:40 | 1 | 1 | 0 | 0 | b0c6b85 | 100% |
| 4 | 2026-06-26 20:45 | 2 | 1 | 1 | 0 | d0754e4 | 50% |
| 5 | 2026-06-28 | 0 | 0 | 0 | 0 | — | — |

## Reviewer Effectiveness
| Reviewer | Total Found | T1 (Must) | T2 (Should) | T3 (Consider) | T4 (Dismiss) | Actioned % | Signal:Noise |
|----------|------------|-----------|-------------|---------------|-------------|-----------|-------------|
| Gemini | 7 | 0 | 5 | 0 | 2 | 71% | 5:2 |
| Copilot | 0 | 0 | 0 | 0 | 0 | n/a | — |

> Copilot was requested (cycle 1) but returned "unable to review … the user who requested the review has reached their quota limit" — it produced zero review threads on this PR.

## Issue Categories (Cumulative)
| Category | T1 | T2 | T3 | T4 | Total | % of All |
|----------|----|----|----|----|-------|----------|
| error-handling | 0 | 3 | 0 | 0 | 3 | 43% |
| test-coverage | 0 | 1 | 0 | 1 | 2 | 29% |
| security | 0 | 1 | 0 | 0 | 1 | 14% |
| api-contract | 0 | 0 | 0 | 1 | 1 | 14% |

**Status:** READY TO MERGE (confirmed clean — cycle 5 found 0 new unresolved threads)

Loop terminated at the cycle-4 hard cap. Trend 100% → 50% → 100% → 50%: every Gemini finding through cycle 4 except one was a genuine T2 and was fixed (5 of 7 actioned). Cycle 4 produced two threads — a real `pipefail` error-handling bug in the vendor script (fixed) and a confidently-wrong "CRITICAL" false positive (Tauri `resources` schema), dismissed with a reasoned inline reply after verifying against the vendored crate source. All 7 bot threads are resolved; no actionable items remain. The signed-build / clean-Mac verification is human-gated (Apple secrets) and called out in the PR body.

## Cycle 1 — 2026-06-26 20:35

### Pre-Review Snapshot
- **Files changed:** 13 (481+ / 33-)
- **Test:Code ratio:** 1:12 (one new test module; remainder engine/shell/CI/docs)
- **CI status:** no checks run on push (release.yml is tag/`workflow_dispatch` only)
- **Linter offenses:** n/a (no Ruby; ruff/mypy not configured)

### Actioned (2)
#### T2-SHOULD: check_ffmpeg crashes on a non-executable bundled binary
- **File:** `src/slideshow_gen/ffmpeg.py:28`
- **Category:** `error-handling`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "If executing the FFmpeg binary fails due to a permission issue … PermissionError … will not be caught …"
- **Disposition:** FIXED — catch `OSError` (superclass of FileNotFoundError; also covers PermissionError/ENOEXEC) instead of `FileNotFoundError`.
- **Thread ID:** PRRT_kwDOR-Xvl86MoR-O

#### T2-SHOULD: tilde-expansion test doesn't actually test tilde expansion
- **File:** `tests/test_ffbin.py:73`
- **Category:** `test-coverage`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "sets the environment variable to str(bundled_ffmpeg), which is already an absolute path … does not contain ~ …"
- **Disposition:** FIXED — rewrote to mock `HOME` and use a `~/ffmpeg` override so expansion is exercised.
- **Thread ID:** PRRT_kwDOR-Xvl86MoR-g

### Commit
SHA: c3102f9
Message: fix: Address PR review cycle 1 — robust check_ffmpeg + real tilde test

### Recurrence Patterns
- **Trust-boundary validation at the periphery (now extends to a fetched binary's execution).** The cycle-1 `OSError` fix and the cycle-2/3 vendor-script hardening continue the cross-PR "validate at the boundary" theme (PR-2/6/10), here applied to "treat any OS-level failure of an external binary as unavailable, don't crash."

## Cycle 2 — 2026-06-26 20:37

### Actioned (1)
#### T2-SHOULD: download+execute unverified binary in a secrets-bearing CI job
- **File:** `desktop/scripts/vendor-ffmpeg.sh:41`
- **Category:** `security`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "Downloading and executing binaries from a third-party personal domain without verifying their SHA256 checksums by default poses a significant security … risk … CI runner has access to highly sensitive secrets …"
- **Disposition:** FIXED — fail-closed in CI (`CI=true`/`REQUIRE_PINNED_SHA256`) unless both `*_SHA256` are pinned; wired URL+sha repo variables into `release.yml`; documented the required repo variables and one-time pinning step in `docs/release-pipeline.md`.
- **Thread ID:** PRRT_kwDOR-Xvl86MoTUx

### Dismissed (1)
#### T4-DISMISS: tilde test (re-raise, outdated)
- **File:** `tests/test_ffbin.py`
- **Category:** `test-coverage`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** DISMISSED — identical to the cycle-1 finding, already fixed; thread `isOutdated=true`. The current code already matches Gemini's suggestion.
- **Thread ID:** PRRT_kwDOR-Xvl86MoTU7

### Commit
SHA: bf6ea5c
Message: fix: Address PR review cycle 2 — require pinned FFmpeg checksums in CI

### Recurrence Patterns
- **Supply-chain / CI security (new flavor of `security`).** Prior `security` findings on this repo were Tauri-command trust boundaries (PR-10). This is the first **supply-chain** instance: fetch-then-execute of a third-party binary on a runner holding signing secrets. Watch: any future "download a tool at build time" step should pin a checksum and fail-closed in CI.

## Cycle 3 — 2026-06-26 20:40

### Actioned (1)
#### T2-SHOULD: no executability smoke check before the license/feature guards
- **File:** `desktop/scripts/vendor-ffmpeg.sh:103`
- **Category:** `error-handling`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "verify that the downloaded binaries can actually execute … before proceeding with license and feature checks …"
- **Disposition:** FIXED — run `ffmpeg`/`ffprobe -version` before the guards. Beyond clearer diagnostics, this closes a real gap: without it, a non-runnable binary yields an empty `-version`, making the `--enable-gpl` grep a silent no-op (false-negative on the license guard).
- **Thread ID:** PRRT_kwDOR-Xvl86MoUuA

### Commit
SHA: b0c6b85
Message: fix: Address PR review cycle 3 — executability smoke check before guards

### Recurrence Patterns
No recurring patterns detected this cycle (script-internal diagnostics/guard ordering).

## Cycle 4 — 2026-06-26 20:45

### Actioned (1)
#### T2-SHOULD: Mach-O grep can crash the script under `set -euo pipefail`
- **File:** `desktop/scripts/vendor-ffmpeg.sh:89`
- **Category:** `error-handling`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "if `grep -i 'Mach-O'` fails to find any matching line … the entire pipeline will return a non-zero exit code … bypassing the descriptive error message …"
- **Disposition:** FIXED — appended `|| true` to the fallback pipeline so a no-match falls through to the descriptive `fail "could not find the $name executable"` instead of an opaque `pipefail` exit. Verified: a no-Mach-O archive now reaches the descriptive error.
- **Thread ID:** PRRT_kwDOR-Xvl86MoaMe

### Dismissed (1)
#### T4-DISMISS: "Tauri v2 resources must be an array" (CRITICAL, false positive)
- **File:** `desktop/src-tauri/tauri.conf.json:50`
- **Category:** `api-contract`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** DISMISSED — factually wrong. Tauri v2 `BundleResources` is an untagged enum `List(Vec<String>)` | `Map(HashMap<String,String>)` (tauri-utils 2.9.2 `config.rs:1508`); the map (source→target) form is intentional so the binaries land at `Contents/Resources/{ffmpeg,ffprobe}`. Empirically verified: `cargo test --lib` runs `tauri-build`, which deserialized this exact config and proceeded past resource parsing. Replied inline with the rationale before resolving.
- **Thread ID:** PRRT_kwDOR-Xvl86MoYwW

### Commit
No code changes this cycle.

### Recurrence Patterns
- **Gemini confidently-wrong on Tauri v2 schema (extends the platform/schema noise pattern, now 7 PRs).** Joins the established "Gemini re-raises platform/portability/schema concerns that don't hold" pattern (PR-2/3/6/10/11). Here it escalated a *correct* config to "CRITICAL build-breaking" against the actual Tauri v2 schema. **Convention reinforced:** verify bot schema/build claims against the vendored crate source (or an empirical `cargo`/`tauri-build` run) before acting — do not take a "CRITICAL" label at face value.

## Cycle 5 — 2026-06-28 (final verification)

Zero new unresolved bot threads. All 7 threads from prior cycles remain resolved. GraphQL `isResolved: true` confirmed on all nodes. No code changes; no dismissals; no new findings. Copilot was present (quota-blocked review from `copilot-pull-request-reviewer`; no reviewThreads generated).

**Termination: READY TO MERGE** — two consecutive "0 actioned" cycles (cycle 4 had 0 code changes; cycle 5 has 0 threads). PR is clean.

### Commit
No code changes this cycle.
