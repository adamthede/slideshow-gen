---
title: E5.S3 — Hardened runtime + minimal entitlements
status: "In Progress"
linked_pr: ""
impl-model: sonnet
---

# E5.S3: Hardened Runtime + Minimal Entitlements

## Goal

Ensure every Mach-O binary in the `Marquee.app` bundle is signed with the
hardened runtime and carries **only the entitlements it actually needs** —
nothing blanket-granted. Document the rationale for every entitlement so the
notary log, when it eventually runs, has a clear baseline to compare against.

## Problem with current setup

A single `entitlements.plist` (containing `disable-library-validation`) is
applied to **three distinct binaries**:
- `Contents/MacOS/Marquee` (Tauri shell) — via `tauri.conf.json`
  `bundle.macOS.entitlements`
- `binaries/slideshow-gen` (PyInstaller sidecar) — via `--entitlements` in
  `release.yml`
- `resources/ffmpeg` + `resources/ffprobe` — via `--entitlements` in
  `release.yml`

The Tauri shell **does not need** `disable-library-validation`. It is a
self-contained, statically linked Tauri/WebKit binary that only loads
Apple-signed or Developer-ID-signed Tauri plugin libraries. Granting it
`disable-library-validation` is an unnecessary privilege that contradicts the
"minimal entitlements" principle.

The sidecar **does need** `disable-library-validation`: PyInstaller `--onefile`
extracts the PSF-signed `Python.framework` into a temp dir at launch and
`dlopen`s it. Under hardened runtime, loading a library signed by a different
team (PSF, not U85N54PC5J) is blocked unless this entitlement is granted.

The static FFmpeg/ffprobe binaries **do not strictly need** it (they only load
Apple-signed system frameworks at runtime), but applying it is harmless and
keeps signing uniform across nested binaries.

## Deliverables

### 1. Split entitlements into two files

`desktop/src-tauri/app-entitlements.plist` — empty plist (Tauri shell):
- No entitlements needed; the Tauri shell is a clean, hardened-runtime binary.

`desktop/src-tauri/binary-entitlements.plist` — for sidecar + FFmpeg:
- `com.apple.security.cs.disable-library-validation: true`
- Documents why each nested binary needs it.

### 2. Wire the split into tauri.conf.json and release.yml

- `tauri.conf.json`: `bundle.macOS.entitlements → "app-entitlements.plist"`
- `tauri.conf.json`: remove `exceptionDomain: ""` (empty, no-op artifact)
- `release.yml` sidecar signing step: `--entitlements … binary-entitlements.plist`
- `release.yml` FFmpeg/ffprobe signing step: same

### 3. Close "Known unknowns → Entitlements coverage" in release-pipeline.md

Replace the open question with a formal "Hardened Runtime & Entitlements" section
documenting:
- Which binary gets which entitlements file and why
- Why `disable-library-validation` is the only entitlement needed (no JIT, no
  sandbox, no network, child-process spawn is always allowed under hardened
  runtime, Apple-signed system frameworks are always allowed)
- Confirmation that child process spawn (sidecar → ffmpeg) needs no extra
  entitlement
- The "add only what the notary log names" principle, so the first real run has
  a clear action path if the notary rejects

## What does NOT change

- No new entitlements are added (no `allow-jit`, no `allow-unsigned-executable-memory`,
  no `network.client`)
- No sandboxing (Marquee is direct-download, not App Store)
- The `binary-entitlements.plist` content is identical to the current
  `entitlements.plist` — the split is structural, not additive
- Capabilities (`default.json`) are already minimal; no changes there

## Test plan

- `pytest tests/` (scoped) — no Python behavior changed; should be green
- Smoke-check tauri.conf.json parses correctly: `cd desktop && npm run tauri info`
  (or `cargo check --manifest-path desktop/src-tauri/Cargo.toml`)
