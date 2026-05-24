# PR #1 Review Log
**PR Title:** Epic 1: Tauri shell + Python sidecar + signed DMG (notarize pending)
**Branch:** feat/epic-1-tauri-sidecar -> main
**URL:** https://github.com/adamthede/slideshow-gen/pull/1

## Summary
| Cycle | Date | Found | Actioned | Dismissed | Skipped | Commit | Ratio |
|-------|------|-------|----------|-----------|---------|--------|-------|
| 1 | 2026-05-24 02:00 | 14 | 11 | 2 | 1 | e112f59 | 79% |

## Reviewer Effectiveness
| Reviewer | Total Found | T1 (Must) | T2 (Should) | T3 (Consider) | T4 (Dismiss) | Actioned % | Signal:Noise |
|----------|------------|-----------|-------------|---------------|-------------|-----------|-------------|
| Copilot | 10 | 2 | 8 | 0 | 0 | 100% | 10:0 |
| Gemini | 4 | 0 | 1 | 1 | 2 | 25% | 1:3 |

## Issue Categories (Cumulative)
| Category | T1 | T2 | T3 | T4 | Total | % of All |
|----------|----|----|----|----|-------|----------|
| security | 1 | 0 | 0 | 0 | 1 | 7% |
| data-integrity | 1 | 0 | 1 | 0 | 2 | 14% |
| error-handling | 0 | 3 | 0 | 0 | 3 | 21% |
| documentation | 0 | 4 | 0 | 0 | 4 | 29% |
| style | 0 | 2 | 0 | 2 | 4 | 29% |

**Status:** IN PROGRESS (cycle 1 complete, awaiting bot re-review)

## Cycle 1 — 2026-05-24 02:00

### Pre-Review Snapshot
- **Files changed:** 55 (10219+ / 0-)
- **Test:Code ratio:** 2:53 (mostly inflated by Cargo.lock + package-lock.json)
- **CI status:** no checks reported (no CI configured yet — slated for E5.S1)
- **Linter offenses:** N/A (multi-language project; per-language checks via `cargo test`, `tsc`, `pytest`)

### Actioned (11)

#### T1-MUST: TOCTOU race in sidecar spawn
- **File:** `desktop/src-tauri/src/sidecar.rs:84`
- **Category:** `data-integrity`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "`spawn_sidecar` checks `state.child` under one mutex lock, releases it, then later locks again to store the child handle. Two concurrent `start_scan` calls can both pass the first check and spawn multiple sidecars..."
- **Disposition:** FIXED — hold mutex across check + spawn + set; explicit `drop(guard)` before async task spawn
- **Thread ID:** PRRT_kwDOR-Xvl86EWN3K

#### T1-MUST: CSP disabled in production builds (XSS risk)
- **File:** `desktop/src-tauri/tauri.conf.json:24`
- **Category:** `security`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "Setting `app.security.csp` to `null` disables the Content Security Policy in production builds, increasing XSS risk..."
- **Disposition:** FIXED — restrictive CSP: `default-src 'self' ipc: http://ipc.localhost; style-src 'self' 'unsafe-inline'; img-src 'self' asset: http://asset.localhost data:; connect-src 'self' ipc: http://ipc.localhost`
- **Thread ID:** PRRT_kwDOR-Xvl86EWN3a

#### T2-SHOULD: Partial reads / UTF-8 corruption / multi-line chunks in sidecar bridge
- **File:** `desktop/src-tauri/src/sidecar.rs:112`
- **Category:** `error-handling`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Comment:** "The current implementation assumes that each `CommandEvent::Stdout` or `Stderr` contains exactly one complete line. However, data from process pipes is chunked arbitrarily by the OS..."
- **Disposition:** FIXED — added `extract_lines(buf: &mut Vec<u8>)` that drains complete `\n`-terminated lines from a persistent per-stream buffer; conversion via `from_utf8_lossy` happens at line boundaries (where multi-byte sequences are complete); trailing partial preserved across chunks; remainder flushed on `Terminated`. 6 new unit tests cover the buffer semantics including split-multibyte-UTF-8.
- **Thread ID:** PRRT_kwDOR-Xvl86EV3k9

#### T2-SHOULD: Empty lines emitted as Raw diagnostics noise
- **File:** `desktop/src-tauri/src/sidecar.rs:108`
- **Category:** `error-handling`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "`parse_sidecar_line` returns `None` for empty/whitespace-only lines, but the stdout handler treats any `None` as `SidecarMessage::Raw` and emits it..."
- **Disposition:** FIXED — extracted `classify_stdout_line()` which returns `None` (skip) for empty/whitespace lines, `Some(Raw)` only for non-empty unparseable lines. Same skip applied to stderr.
- **Thread ID:** PRRT_kwDOR-Xvl86EWN3T

#### T2-SHOULD: Brittle DMG glob in release.sh
- **File:** `desktop/scripts/release.sh:41`
- **Category:** `error-handling`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "`DMG=$(ls ... | head -1)` is brittle under `set -euo pipefail`: if the glob matches nothing, the script may exit before the later `-f` check runs..."
- **Disposition:** FIXED — `shopt -s nullglob` + array check + explicit empty-count error + `ls -t | head -1` for deterministic newest-by-mtime selection.
- **Thread ID:** PRRT_kwDOR-Xvl86EWN3f

#### T2-SHOULD: README mentions unused create-dmg dep
- **File:** `desktop/README.md:25`
- **Category:** `documentation`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "The prerequisites list mentions `create-dmg` as required for `release.sh`, but `release.sh` doesn't invoke `create-dmg`..."
- **Disposition:** FIXED — removed the create-dmg prerequisite line. Tauri produces the DMG natively.
- **Thread ID:** PRRT_kwDOR-Xvl86EWN3i

#### T2-SHOULD: README claims a placeholder stub is checked in (it isn't)
- **File:** `desktop/README.md:37`
- **Category:** `documentation`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "This README claims a placeholder stub is checked in at `src-tauri/binaries/slideshow-gen-aarch64-apple-darwin`, but `desktop/src-tauri/binaries/` isn't present and `desktop/.gitignore` ignores `src-tauri/binaries/`..."
- **Disposition:** FIXED — removed the stub claim; doc now says "binary is gitignored; run `./scripts/build-sidecar.sh` before `cargo check` / `npm run tauri dev`."
- **Thread ID:** PRRT_kwDOR-Xvl86EWN3j

#### T2-SHOULD: ADR-0002 also claims a placeholder stub (same drift)
- **File:** `docs/adr/0002-sidecar-packaging.md:98`
- **Category:** `documentation`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "This ADR states a placeholder stub is checked in at `desktop/src-tauri/binaries/slideshow-gen-aarch64-apple-darwin`, but `desktop/src-tauri/binaries/` isn't present..."
- **Disposition:** FIXED — same correction applied to the ADR.
- **Thread ID:** PRRT_kwDOR-Xvl86EWN3n

#### T2-SHOULD: Invalid HTML — `<pre>` containing `<div>` children (event log)
- **File:** `desktop/src/App.tsx:166`
- **Category:** `style`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "`<pre>` elements should contain phrasing content; rendering a list of `<div>`s inside `<pre>` is invalid HTML and can confuse layout/accessibility tooling..."
- **Disposition:** FIXED — replaced `<pre>` with semantic `<div role="log" aria-live="polite">` keeping the `whitespace-pre-wrap` / `font-mono` styling.
- **Thread ID:** PRRT_kwDOR-Xvl86EWN3q

#### T2-SHOULD: Invalid HTML — same issue in diagnostics block
- **File:** `desktop/src/App.tsx:178`
- **Category:** `style`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "Same issue in the diagnostics section: `<pre>` contains `<div>` children, which is invalid HTML..."
- **Disposition:** FIXED — replaced `<pre>` with `<div>` (no a11y attrs needed; it's a collapsible diagnostics panel).
- **Thread ID:** PRRT_kwDOR-Xvl86EWN3y

#### T2-SHOULD: Default template `<title>` shipped in index.html
- **File:** `desktop/index.html:7`
- **Category:** `documentation`
- **Reviewer:** Copilot (`copilot-pull-request-reviewer`)
- **Comment:** "The HTML `<title>` is still the default template text. Updating it to 'Marquee' will keep the document title consistent with the app/window branding."
- **Disposition:** FIXED — title set to "Marquee".
- **Thread ID:** PRRT_kwDOR-Xvl86EWN38

### Dismissed (2)

#### T4-DISMISS: Hardcoded signingIdentity in tauri.conf.json
- **File:** `desktop/src-tauri/tauri.conf.json:44`
- **Category:** `style`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** DISMISSED — scope creep for this project. Marquee is a single-developer business app under Thede Technologies LLC; the signing identity is intentional and locked in by [ADR-0001](../adr/0001-app-stack.md). There are no other contributors who need to build under different identities. Moving the value to an env var would add ceremony without benefit.
- **Thread ID:** PRRT_kwDOR-Xvl86EV3k-

#### T4-DISMISS: Apple ID "hardcoded" in release.sh
- **File:** `desktop/scripts/release.sh:16`
- **Category:** `style`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** DISMISSED — false positive. The Apple ID appears only in a *comment* documenting how to store credentials (`xcrun notarytool store-credentials AC_PASSWORD --apple-id ...`). The script itself uses `--keychain-profile "$KEYCHAIN_PROFILE"` and never touches the Apple ID at runtime. Not a credentials risk.
- **Thread ID:** PRRT_kwDOR-Xvl86EV3lA

### Skipped (1)

#### T3-CONSIDER: tmp filename collision in start_scan
- **File:** `desktop/src-tauri/src/lib.rs:17`
- **Category:** `data-integrity`
- **Reviewer:** Gemini (`gemini-code-assist`)
- **Disposition:** SKIPPED — not yet exploitable. E1 always invokes `--estimate-only`, which exits before any file is written to the path. The collision becomes a real concern when E4 enables actual renders. Deferred to E4 alongside the cancellation work.
- **Thread ID:** PRRT_kwDOR-Xvl86EV3lB

### Recurrence Patterns
No prior PR review logs exist in this repository — cycle 1 is the baseline. Future cycles should check whether `error-handling` issues in subprocess/IPC code recur, or whether `documentation` drift between docs and gitignored binaries becomes a pattern as more PyInstaller-style follow-ups land.

### Commit
SHA: e112f59
Message: fix: Address PR review cycle 1 — security, races, IPC robustness, docs
