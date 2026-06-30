# PR #17 Review Log
**PR Title:** ci(release): install Developer ID G2 intermediate so codesign embeds full chain
**Branch:** ci/developer-id-intermediate -> main
**URL:** https://github.com/adamthede/slideshow-gen/pull/17

## Summary
| Cycle | Date | Found | Actioned | Dismissed | Skipped | Commit | Ratio |
|-------|------|-------|----------|-----------|---------|--------|-------|
| 1 | 2026-06-29 23:40 | 0 (bot) | 0 | 0 | 0 | c6e0d3a (self-review) | n/a |
| 2 | 2026-06-29 23:48 | 1 | 0 | 1 | 0 | — | 0% |

> Cycle 1 had **no actionable bot threads**: Gemini reviewed clean (summary only,
> "no additional feedback"); Copilot was **quota-blocked** ("the user who requested
> the review has reached their quota limit") and never actually reviewed. With bot
> coverage near-zero, a manual staff-engineer self-review against the repo's own
> promoted conventions produced commit `c6e0d3a` (SHA256-pin the downloaded
> intermediate + replace two `| grep -q` guards that are fragile under `pipefail`).

## Reviewer Effectiveness
| Reviewer | Total Found | T1 (Must) | T2 (Should) | T3 (Consider) | T4 (Dismiss) | Actioned % | Signal:Noise |
|----------|------------|-----------|-------------|---------------|-------------|-----------|-------------|
| Gemini | 1 | 0 | 0 | 0 | 1 | 0% | 0:1 |
| Copilot | 0 | 0 | 0 | 0 | 0 | n/a | quota-blocked, no review |

## Issue Categories (Cumulative)
| Category | T1 | T2 | T3 | T4 | Total | % of All |
|----------|----|----|----|----|-------|----------|
| documentation | 0 | 0 | 0 | 1 | 1 | 100% |

**Status:** READY TO MERGE (caveat: Copilot quota-blocked, so only Gemini provided automated coverage)

## Cycle 1 — 2026-06-29 23:40

### Pre-Review Snapshot
- **Files changed:** 2 (97+ / 1-) — `.github/workflows/release.yml`, plan doc
- **Test:Code ratio:** 0:1 (CI workflow change — not unit-testable; validated via `bash -n` + post-merge `workflow_dispatch` dry run)
- **CI status:** no checks registered on the PR branch (release.yml only triggers on tag push / workflow_dispatch — expected)
- **Linter offenses:** n/a (YAML + shell); `python yaml.safe_load` OK, `bash -n` OK on the extracted run block

### Bot coverage
- **Gemini:** COMMENTED 2026-06-30T03:35Z — PR summary only, "As there are no review comments, I have no additional feedback to provide." 0 inline threads.
- **Copilot:** requested via REST `copilot-pull-request-reviewer[bot]` (the `gh pr edit --add-reviewer @copilot` form did not register); responded 2026-06-30T03:38Z with "unable to review … quota limit." No code comments produced.

### Self-review hardening (not bot-driven) — commit c6e0d3a
Applied because bot coverage was near-zero and the repo's DASHBOARD documents two
promoted conventions this PR's new code initially violated:
- **Supply-chain (PR-14 convention):** the G2 intermediate is downloaded on a
  runner that holds the Apple signing secrets. Pinned its SHA256
  (`f16cd3c5…d2df3a`) and fail-closed on mismatch, instead of a subject-string
  check any cert with that CN would pass.
- **pipefail safety (PR-15 vendor-ffmpeg convention):** replaced both
  `… | grep -q …` guards with snapshot-then-match. Under `set -o pipefail`,
  `grep -q` closing the pipe early can SIGPIPE the upstream (`openssl` /
  `find-identity`), whose non-zero status pipefail propagates — turning a VALID
  cert/identity into a spurious job failure.

### Recurrence Patterns
- **PR-14 "supply-chain fetch-then-execute in a secrets-bearing CI job"** and
  **PR-15 "fail-open / pipefail-fragile guards"** — both promoted conventions
  applied here proactively to brand-new code in the same release workflow. Same
  job, same hazards; the conventions held.

### Commit
SHA: c6e0d3a — `fix(ci): pin Developer ID G2 intermediate SHA256 + drop pipefail-fragile grep`

## Cycle 2 — 2026-06-29 23:48

Re-requested Gemini after pushing `c6e0d3a` (Copilot not re-requested — quota-blocked).

### Dismissed (1)
#### T4-DISMISS: "security import does not support -f x509"
- **File:** `docs/plans-to-do/2026-06-29-ci-developer-id-intermediate.md:39` (same `-f x509` is in the workflow)
- **Category:** `documentation`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "The `security import` command on macOS does not support `x509` as a valid argument for the `-f` (format) option…"
- **Disposition:** DISMISSED — **confidently wrong, verified against reality.** `man security` lists the import `-f` formats as *openssl, bsafe, pkcs7, pkcs8, pkcs12, **x509**, openssh1, openssh2, pemseq*; the formats Gemini claimed (`pem.cert`, `pem.key`, `ssh1`, `ssh2`, `bare.key`, `xml`) are not `security import` values. Empirical: `security import DeveloperIDG2CA.cer -t cert -f x509 -k <throwaway-keychain>` → "1 certificate imported" (exit 0), cert present. Posted the verification as a thread reply before resolving. The PR also SHA256-pins the cert, so the bytes are fixed regardless of format auto-detection.
- **Thread ID:** PRRT_kwDOR-Xvl86NJ3Cx

### Recurrence Patterns
- **Gemini confidently-wrong build/CLI claims → verify against the man page / a real run (now 8 PRs).** Mirrors PR-14 cycle 4 (Serde "CRITICAL" that wasn't) and the platform-noise lineage. Same lesson: a priority badge is not evidence; reproduce before acting.

### Commit
No code changes this cycle (the sole thread was a verified-wrong dismiss).

## Loop Termination
- **Status:** READY TO MERGE
- **Criterion:** two consecutive cycles with 0 actioned bot items (Cycle 1: 0 actionable bot threads; Cycle 2: 1 found, 0 actioned). Bots exhausted — Gemini's only output was a wrong nit, Copilot cannot run (quota).
- **Caveat for the human reviewer:** automated coverage on this PR was effectively Gemini-only. The change was self-reviewed by hand against the repo's promoted conventions and validated (`bash -n`, YAML parse, empirical `security import` test). End-to-end CI validation is the post-merge `workflow_dispatch` dry run.
