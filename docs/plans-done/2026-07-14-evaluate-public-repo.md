---
title: "Evaluate making slideshow-gen (Marquee) a public repo"
status: "Done"
priority: "P3"
project: "slideshow-gen"
created: 2026-07-14
completed: 2026-08-13
linked_pr: "https://github.com/adamthede/slideshow-gen/pull/25"
effort: "~0.5d evaluation + whatever the history audit demands"
---

# Evaluate making slideshow-gen (Marquee) public

**Origin:** Adam, 2026-07-14 — published the v1.0.0 GitHub release and realized: private repo means nobody can ever see it. "Should we add evaluating whether to make Marquee a public repo to our list of to dos?"

## The question

Marquee v1.0.0 is published — to an audience of one. If Marquee is meant to be seen (the thedetech Marquee product page draft, PR #17, implies a public-facing product), distribution needs a decision.

## Options to evaluate

1. **Make the repo public.** Full open distribution; releases visible; potential community. Requires the checklist below.
2. **Lens pattern — repo stays private, artifact distributes publicly.** Publish the DMG/binaries via Cloudflare (as Lens does) + the thedetech product page as the download surface. No history audit needed; no source exposure decision forced.
3. **Public releases-only mirror** (empty public repo holding releases) — middle path, rarely worth the ceremony.

## Before going public — the audit checklist (option 1 only)

- [x] **Git history scrub:** secrets, tokens, absolute personal paths, any test fixtures containing family photos/media. If history is dirty, a fresh public repo (the larrys-letters precedent) beats history rewriting.
- [x] **License choice** — and check the open-core verdict: the 2026-07-04 GTM session ruled open-core out for T&S as passion-project-vs-business; decide whether Marquee (a tool, not the moat) reads differently.
- [x] **README as landing page** — the repo becomes marketing surface; align copy with the thedetech product page (venue rule: product copy leads there).
- [x] **Support posture** — public repo invites issues; decide the "hobby app, no spend" stance up front (per the standing quote-grabber/daily-calendar precedent).

## Recommendation seed (to pressure-test at evaluation)

Option 2 first: it ships public distribution this window with zero risk (product page + hosted DMG), and leaves option 1 open. Going repo-public is a one-way door that deserves its own sitting.

## Outcome (2026-08-13)

**Option 1 chosen — the repo went public on 2026-08-13.** Board card w33-18 ("Marquee: ship it public") drove the finish.

How each checklist item closed:

- **Git history scrub:** the 2026-08-03 public-readiness scan (`command-center/docs/research/2026-08-03-marquee-public-readiness.md`) swept all 205 commits on all branches — zero credentials, zero personal media. Re-verified 2026-08-13 across all 212 commits (including the post-scan remediation commits) before the flip. Verdict both times: history clean, no rewrite needed. Known accepted residual: absolute personal paths in three docs' *history* (stripped at HEAD in PR #25), including the old `design-pass.md` line referencing a then-private project path.
- **License choice:** MIT, `Copyright (c) 2026 Thede Technologies, LLC` — shipped in PR #25 with BMAD attribution (vendored trees) and the FFmpeg GPL posture intact. GitHub detects the license correctly.
- **README as landing page:** truth pass in PR #25 (dropped "private, all rights reserved", added Download quickstart and Support sections); product screenshot added in the follow-up README PR. Product copy leads at thedetech.com/marquee/ per the venue rule.
- **Support posture:** no-SLA hobby-project stance stated in the README Support section.

Post-flip verification: anonymous DMG download from the v1.0.0 release confirmed working; repo homepage set to https://thedetech.com/marquee/.
