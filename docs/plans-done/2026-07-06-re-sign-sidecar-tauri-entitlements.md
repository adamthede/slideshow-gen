---
title: "Re-sign sidecar after Tauri bundler strips its entitlements"
status: "Done"
completed: 2026-07-06
linked_pr: "https://github.com/adamthede/slideshow-gen/pull/22"
---

Shipped via PR #22. Post-v1.0.0 release-pipeline bugfix: Tauri's bundler re-signs
`externalBin` with the shell's empty entitlements, silently stripping
`com.apple.security.cs.disable-library-validation` from the PyInstaller sidecar so
**Scan** killed the engine under the hardened runtime. Fix adds two `release.yml`
steps — re-sign the bundled sidecar with `binary-entitlements.plist` + re-seal the
outer `.app`, then a hard assertion gate that fails the build if the entitlement is
missing from `slideshow-gen`/`ffmpeg`/`ffprobe`.

No backing plan file existed — this was a bug discovered against the shipped v1.0.0
DMG, distinct from the signed-DMG epic (`2026-07-04-e5-s4-signed-dmg.md`, PR #18).
Recorded via /shipped interactive fallback.
