---
title: "Epic 1: Tauri shell + Python sidecar + signed DMG"
status: "Done"
completed: 2026-05-24
linked_pr: "https://github.com/adamthede/slideshow-gen/pull/1"
---

Shipped via PR #1. No backing plan file existed — confirmed via /shipped interactive fallback.

## Summary

Stands up the **Marquee** macOS desktop app skeleton end-to-end: Tauri 2 shell, React+TS+Tailwind+shadcn frontend, `slideshow-gen` Python CLI frozen as a signed PyInstaller sidecar, JSON-line IPC contract live across all layers, signed `.app` + DMG produced by `npm run tauri build`.

All verification steps completed:
- Smoke test: notarized DMG launched from Finder, scanned real 142-file folder (120 images + 22 videos)
- IPC pipeline fully functional: event log shows discovery → estimate → exit
- Rust tests: 16/16 passing
- TypeScript strict + Vite build: clean
- FFmpeg preflight deferred to E5.S1 (estimate-only doesn't require it)
- multiprocessing.freeze_support() eliminated 2204 stderr lines

Status: **Production-ready E1 build.** Ready to merge and move to Epic 2 (real ingestion + summary UI).
