---
title: "fix(release): build DMG with hdiutil — Tauri's DMG pass re-strips the sidecar"
status: "Done"
completed: 2026-07-06
linked_pr: "https://github.com/adamthede/slideshow-gen/pull/23"
---

Shipped via PR #23. No backing plan file existed — round 2 of the sidecar-entitlement
saga: PR #22 fixed the .app but the workflow's DMG step ran a second Tauri bundling
pass that re-stripped `disable-library-validation` from the sidecar inside the DMG
(zip asset good, DMG broken — caught by Adam's install + Scan test 2026-07-06).
Fix: build the DMG with `hdiutil` around the already re-signed, notarized, stapled
.app, and relocate the CI entitlement gate to assert INSIDE both final artifacts
(mounted DMG + extracted zip). Lesson encoded: assert the artifact you ship, not
the intermediate.
