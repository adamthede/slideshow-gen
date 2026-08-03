# PR #7 Review Log
**PR Title:** ci: Epic 5.S1 — signed + notarized release pipeline
**Branch:** ci/epic-5-s1-release-pipeline -> main
**URL:** https://github.com/adamthede/slideshow-gen/pull/7

## Summary
| Cycle | Date | Found | Actioned | Dismissed | Skipped | Commit | Ratio |
|-------|------|-------|----------|-----------|---------|--------|-------|
| 1 | 2026-05-28 22:37 | 6 | 3 | 2 | 1 | 83f4d25 | 50% |
| 2 | 2026-05-28 22:50 | 2 | 0 | 1 | 1 | — | 0% |

## Reviewer Effectiveness
| Reviewer | Total Found | T1 (Must) | T2 (Should) | T3 (Consider) | T4 (Dismiss) | Actioned % | Signal:Noise |
|----------|------------|-----------|-------------|---------------|-------------|-----------|-------------|
| Copilot | 5 | 2 | 1 | 1 | 1 | 60% | 3:2 |
| Gemini | 3 | 0 | 0 | 1 | 2 | 0% | 0:3 |

## Issue Categories (Cumulative)
| Category | T1 | T2 | T3 | T4 | Total | % of All |
|----------|----|----|----|----|-------|----------|
| error-handling | 1 | 0 | 0 | 0 | 1 | 13% |
| data-integrity | 1 | 0 | 0 | 0 | 1 | 13% |
| api-contract | 0 | 1 | 0 | 0 | 1 | 13% |
| documentation | 0 | 0 | 2 | 2 | 4 | 50% |
| style | 0 | 0 | 0 | 1 | 1 | 13% |

**Status:** READY TO MERGE (2 consecutive cycles with 0 actioned items in cycle 2; T3/T4 only)

---

## Cycle 1 — 2026-05-28 22:37

**Worktree:** `.claude/worktrees/agent-a9c690d3a6942366d` (repo-relative)

### Pre-Review Snapshot
- **Files changed:** 4 (410+ / 0-)
- **Test:Code ratio:** 0:4 (no test files changed; workflow/docs/config only)
- **CI status:** No checks reported on this branch yet
- **Linter offenses:** N/A (YAML/Markdown/JSON — no Python linter applicable)

### Actioned (3)

#### T1-MUST: PyInstaller uses cli.py instead of sidecar_entry.py — multiprocessing crashloop risk
- **File:** `.github/workflows/release.yml:67`
- **Category:** `error-handling`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "The PyInstaller build is using `src/slideshow_gen/cli.py` as the entry script, but the repo's existing PyInstaller setup uses `desktop/scripts/sidecar_entry.py` specifically to call `multiprocessing.freeze_support()` before Click runs. Without that shim..."
- **Disposition:** FIXED — Changed PyInstaller entry from `src/slideshow_gen/cli.py` to `desktop/scripts/sidecar_entry.py`
- **Thread ID:** PRRT_kwDOR-Xvl86Fh20E

#### T1-MUST: base64 --decode -o flag incompatible with macOS BSD base64
- **File:** `.github/workflows/release.yml:114`
- **Category:** `data-integrity`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "On `macos-14` runners, the BSD `base64` utility typically does not support the GNU-style `--decode` flag. This will likely fail to decode the `.p12` and break signing..."
- **Disposition:** FIXED — Changed `base64 --decode -o "$CERT_PATH"` to `base64 --decode > "$CERT_PATH"` (redirect is unambiguous across BSD/GNU)
- **Thread ID:** PRRT_kwDOR-Xvl86Fh20U

#### T2-SHOULD: workflow_dispatch `tag` input not wired into checkout — misleading UX
- **File:** `.github/workflows/release.yml:7-12`
- **Category:** `api-contract`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "`workflow_dispatch` defines an input `tag`, but the workflow never uses it (e.g., to set `actions/checkout`'s `ref`). As written, manual runs always build the checked-out branch/commit regardless of the input..."
- **Disposition:** FIXED — Added `ref: ${{ inputs.tag != '' && inputs.tag || github.ref }}` to the checkout step
- **Thread ID:** PRRT_kwDOR-Xvl86Fh2zx

### Dismissed (2)

#### T4-DISMISS: Plan doc says --onedir; implementation uses --onefile
- **File:** `docs/plans-to-do/2026-05-28-epic-5-s1-build-sign-notarize.md:62-64`
- **Category:** `documentation`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** DISMISSED — The plan doc's "Known unknowns" section accurately reflects the discovery process. The decision to use `--onefile` is documented in the workflow comments and `docs/release-pipeline.md`. Planning docs are living artifacts, not specs; the implementation is authoritative. No code risk.
- **Thread ID:** PRRT_kwDOR-Xvl86Fh0CL

#### T4-DISMISS: Personal email athede@gmail.com hardcoded in docs
- **File:** `docs/release-pipeline.md:46-50`
- **Category:** `style`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Disposition:** DISMISSED — This is a private repo. The email is the repo owner's and is used as an example/placeholder in secret documentation. No security risk in a private repository; this is Adam's personal project. The secrets table row already clarifies it's illustrative.
- **Thread ID:** PRRT_kwDOR-Xvl86Fh20k

### Skipped (1)

#### T3-CONSIDER: tauri.conf.json signingIdentity should be env-driven (APPLE_SIGNING_IDENTITY)
- **File:** `docs/plans-to-do/2026-05-28-epic-5-s1-build-sign-notarize.md:26-28`
- **Category:** `documentation`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Disposition:** SKIPPED — The workflow already sets `APPLE_SIGNING_IDENTITY` as an env var. The tauri.conf.json has the signing identity hardcoded to the same string. While env-driven config is cleaner, the workflow functions correctly as-is (Tauri 2.x uses the env var for signing regardless of the conf value). The plan correctly noted this as aspirational scope. Not a production bug.
- **Thread ID:** PRRT_kwDOR-Xvl86Fh20z

### Recurrence Patterns
No recurring patterns detected this cycle.

### Commit
SHA: 83f4d25
Message: fix: Address PR review cycle 1 — sidecar entry shim, base64 decode, tag input

---

## Cycle 2 — 2026-05-28 22:50

**Worktree:** `.claude/worktrees/agent-a9c690d3a6942366d` (repo-relative)

### Actioned (0)
No T1 or T2 items this cycle.

### Dismissed (1)

#### T4-DISMISS: Plan doc says --onedir; implementation uses --onefile (re-raised by Gemini)
- **File:** `docs/plans-to-do/2026-05-28-epic-5-s1-build-sign-notarize.md:64`
- **Category:** `documentation`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** DISMISSED — Identical concern to cycle 1 thread PRRT_kwDOR-Xvl86Fh0CL (also dismissed). Gemini re-raised this after the cycle 1 thread was resolved, citing the `.spec` file as additional evidence. Planning docs are not the authoritative spec; the workflow implementation and `docs/release-pipeline.md` are. Duplicate dismissal.
- **Thread ID:** PRRT_kwDOR-Xvl86FiYI_

### Skipped (1)

#### T3-CONSIDER: *.spec in .gitignore shadows tracked desktop/scripts/slideshow-gen.spec
- **File:** `.gitignore:24`
- **Category:** `documentation`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** SKIPPED — `slideshow-gen.spec` is tracked in git (`git ls-files` confirms). Git never ignores already-tracked files regardless of `.gitignore` patterns, so there is no actual risk of the spec being silently dropped. The suggestion (`!desktop/scripts/slideshow-gen.spec` negation) is purely a hygiene improvement for developer clarity, not a correctness bug. Would be T3 in a project with new contributors; acceptable as-is for a single-dev private repo.
- **Thread ID:** PRRT_kwDOR-Xvl86FiYI8

### Recurrence Patterns
- **Recurring:** `documentation` category in planning docs — Gemini raised plan-vs-implementation contradiction in both cycle 1 and cycle 2 (same underlying concern, different thread). Pattern: Gemini generates documentation consistency comments that are technically correct but not production-risk. Both dismissed.

### Commit
SHA: — (No code changes this cycle)
Message: No code changes this cycle
