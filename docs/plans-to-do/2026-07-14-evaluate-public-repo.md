---
title: "Evaluate making slideshow-gen (Marquee) a public repo"
status: "Up Next"
priority: "P3"
project: "slideshow-gen"
created: 2026-07-14
linked_pr: ""
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

- [ ] **Git history scrub:** secrets, tokens, absolute personal paths, any test fixtures containing family photos/media. If history is dirty, a fresh public repo (the larrys-letters precedent) beats history rewriting.
- [ ] **License choice** — and check the open-core verdict: the 2026-07-04 GTM session ruled open-core out for T&S as passion-project-vs-business; decide whether Marquee (a tool, not the moat) reads differently.
- [ ] **README as landing page** — the repo becomes marketing surface; align copy with the thedetech product page (venue rule: product copy leads there).
- [ ] **Support posture** — public repo invites issues; decide the "hobby app, no spend" stance up front (per the standing quote-grabber/daily-calendar precedent).

## Recommendation seed (to pressure-test at evaluation)

Option 2 first: it ships public distribution this window with zero risk (product page + hosted DMG), and leaves option 1 open. Going repo-public is a one-way door that deserves its own sitting.
