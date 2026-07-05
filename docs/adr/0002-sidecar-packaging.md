# ADR 0002 — Sidecar packaging (PyInstaller)

- **Status:** Accepted
- **Date:** 2026-05-23
- **Deciders:** Adam
- **Context:** Epic 1, Story E1.S2 — freeze the `slideshow-gen` Python CLI as a sidecar binary for Marquee.
- **Supersedes:** the "decide in E1.S2" placeholder in [ADR-0001](0001-app-stack.md) under "Open Questions" → "Sidecar packaging tradeoffs".

## Context

The Tauri shell embeds the Python engine as a sidecar binary it spawns per invocation. PyInstaller offers two modes:

- **onefile** — single executable that self-extracts the bundled Python + deps into a temp dir at launch.
- **onedir** — a directory of binaries, dylibs, and data files. The "executable" is the entry script with everything sitting next to it.

The Tauri-side mechanics (`externalBin` convention: `binaries/<name>-<target-triple>`) work with either, but the **signing** and **distribution** surfaces differ sharply.

## Decision

**Use PyInstaller `onefile` mode for E1.**

The spec is at `desktop/scripts/slideshow-gen.spec`. The build script is `desktop/scripts/build-sidecar.sh`. Output: `desktop/src-tauri/binaries/slideshow-gen-aarch64-apple-darwin` (~37 MB).

## Rationale

The decisive factor for E1 was signing surface complexity:

- **onefile:** Exactly one binary to sign. `codesign --sign … <binary>` and you're done. The embedded Python framework and dylibs are inside the binary's PKG archive — they don't need separate signing because they're not exposed as files at signing time.
- **onedir:** Every nested `.so` and `.dylib` in the directory must be signed individually before the outer binary can be sealed. PyInstaller produces 100+ nested dylibs for the slideshow-gen dependency set. Tauri's `externalBin` is designed for a single binary, not a directory — you'd have to copy the whole tree into `.app/Contents/Resources/` and route the entry point differently.

The cost of onefile is cold-start latency: ~1–2 seconds while the bootloader extracts the bundle to `/var/folders/.../T/_MEI…`. This is acceptable because:

- The sidecar runs per-invocation, not per-keystroke. A user only ever sees the extraction cost when they click "Scan" or "Render".
- The extraction is cached by the OS for the rest of the session.
- The alternative (onedir) trades 1–2s cold start for hours of signing-pipeline complexity, and recurs every release.

If cold start becomes a measurable UX problem (likely never — render times are minutes-to-hours), onedir is a future migration. For E1, simplicity wins.

## Bundled data

The reverse geocoder ships its dataset as a data file (`rg_cities1000.csv`) inside the `reverse_geocoder` package. PyInstaller does not pick this up automatically because the package looks for it via `__file__` at runtime. The spec includes it via:

```python
datas=[(str(RG_DATA), "reverse_geocoder")]
```

so it lands at `reverse_geocoder/rg_cities1000.csv` inside the bundle.

Hidden imports declared because PyInstaller's static analysis misses them:

- `reverse_geocoder.cKDTree_MP` — lazy-imported inside `reverse_geocoder.__init__`
- `pillow_heif` — registered via PIL plugin protocol, not a normal import
- `PIL._tkinter_finder` — PIL stub that's sometimes needed for image loaders

## FFmpeg — deferred to E5.S1

FFmpeg is **not bundled** in the E1 sidecar. The frozen binary expects to find FFmpeg on `PATH` — typically `/opt/homebrew/bin/ffmpeg` on the developer's Mac. This is fine for:

- Local development on a machine that has Homebrew + ffmpeg
- The E1 smoke test (which uses `--estimate-only` and never invokes FFmpeg)

This is **not** fine for distribution. A notarized direct-download build on a Mac without Homebrew FFmpeg will fail any real render with `FFmpeg not found`. Bundling FFmpeg inside `Marquee.app/Contents/Resources/` and teaching the engine to prefer the bundled binary over PATH is tracked as **Epic 5, story E5.S1** in the PRD. Surfaced in `desktop/README.md` so it can't be missed.

The reason it's deferred:

- The E1 mandate is "prove every layer that matters for distribution." Notarization, signing, sidecar IPC, frontend event handling — all of those exercise on a non-rendering build via `--estimate-only`.
- Bundling FFmpeg adds nontrivial signing complexity (FFmpeg itself is a nested binary that needs its own signature inside the app bundle).
- It's better to ship the signing/notarization pipeline first against a minimal sidecar, then layer FFmpeg bundling on top once the chain is proven.

## Signing under hardened runtime

The sidecar binary needs `com.apple.security.cs.disable-library-validation` because the PyInstaller onefile bootloader extracts an Apple-signed `Python.framework` and dlopens it. Under hardened runtime, dlopen normally rejects libraries whose Team ID doesn't match the parent process. Without this entitlement, the sidecar fails with:

```
code signature in 'Python' not valid for use in process:
mapping process and mapped file (non-platform) have different Team IDs
```

The entitlement lives in `desktop/src-tauri/binary-entitlements.plist` and is applied to the **sidecar** (and the vendored FFmpeg/ffprobe). Since E5.S3 the entitlements are split: the Tauri shell binary gets a separate, **empty** `app-entitlements.plist` — it is a clean hardened-runtime binary that needs no entitlement. (Originally a single `entitlements.plist` was applied to both; E5.S3 removed the unnecessary grant from the shell. See `docs/release-pipeline.md` → "Hardened Runtime & Entitlements".)

## Consequences

### Positive

- One binary to sign, one to notarize. The signing pipeline is `codesign` + the Tauri-bundled re-sign of the `.app` — no nested loops over dylibs.
- The sidecar can be tested in isolation: `./scripts/build-sidecar.sh` produces a runnable binary that you can hand-invoke with any CLI flags, including `--ipc`. Easy to debug.
- ~37 MB sidecar fits comfortably inside a Tauri shell that's <100 MB total even with the Python framework embedded.

### Negative

- 1–2s cold start per invocation. Mitigated by the per-invocation nature of the sidecar and by the OS-level extraction cache within a session.
- `--add-data` / hiddenimports must be hand-curated. If a transitive dep starts using a runtime data file, the spec needs an update or the bundle will be broken in a way the unit tests can't catch. Build script smoke-tests `--help` and `render --help` to catch trivially broken bundles; broader runtime coverage will land with E2.

### Operational

- The sidecar binary is `.gitignored` — every build produces it locally or in CI (E5.S1). Source of truth is the spec file + build script, both checked in.
- Before `cargo check`, `npm run tauri dev`, or `npm run tauri build`, run `./scripts/build-sidecar.sh` once so the expected `desktop/src-tauri/binaries/slideshow-gen-aarch64-apple-darwin` path exists. No stub is checked in — the build script is fast enough that materializing the real binary is the right default.

## Follow-ups (carried into later epics)

- **E5.S1** — Bundle FFmpeg inside the `.app`; teach the engine to prefer it over PATH.
- **E5.S1** — Build the sidecar in CI (GitHub Actions) so the release pipeline doesn't require a developer machine.
- **Universal binary** — currently arm64-only. Intel support would mean a second sidecar build + Tauri's `--target universal-apple-darwin`.
- **Reconsider onedir** if cold-start becomes a UX issue (unlikely; sidecar is not in any tight UI loop).
