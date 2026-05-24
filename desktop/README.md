# Marquee — macOS desktop app for slideshow-gen

Tauri 2 (Rust shell) + React + TypeScript + Tailwind + shadcn/ui, wrapping the `slideshow-gen` Python CLI as a PyInstaller-frozen sidecar binary.

See [ADR-0001](../docs/adr/0001-app-stack.md) for the stack decision, [ADR-0002](../docs/adr/0002-sidecar-packaging.md) for sidecar packaging, [docs/sidecar-protocol.md](../docs/sidecar-protocol.md) for the IPC contract, and [docs/architecture-app.md](../docs/architecture-app.md) for the layering overview.

## Identity

| | |
|---|---|
| App name | Marquee |
| Bundle ID | `com.thedetech.marquee` |
| Apple Team | `U85N54PC5J` (Thede Technologies, LLC) |
| Signing cert | `Developer ID Application: ADAM SPENCER THEDE (U85N54PC5J)` |
| Notarytool profile | `AC_PASSWORD` |

## Prerequisites

- macOS 12+ on Apple Silicon
- Node 22.12+ (or 20.19+)
- Rust toolchain (`rustup install stable`)
- Python 3.11 with the project's `.venv` activated (`source ../.venv/bin/activate`)
- PyInstaller (`pip install pyinstaller`)
- `xcrun` / Xcode command-line tools

## Dev loop

```bash
cd desktop
npm install
# Build the sidecar at least once so Tauri can resolve it:
./scripts/build-sidecar.sh
npm run tauri dev
```

`npm run tauri dev` runs Vite + the Tauri shell. The Rust shell expects the sidecar binary at `src-tauri/binaries/slideshow-gen-aarch64-apple-darwin`. That path is gitignored — run `./scripts/build-sidecar.sh` before `cargo check` / `npm run tauri dev` / `npm run tauri build` so the binary exists.

## Sidecar build

```bash
./scripts/build-sidecar.sh
```

Writes `src-tauri/binaries/slideshow-gen-aarch64-apple-darwin`, signs it with the Developer ID cert, and verifies. See [ADR-0002](../docs/adr/0002-sidecar-packaging.md) for packaging tradeoffs.

### FFmpeg — deferred to E5.S1

The sidecar shells out to **system FFmpeg at `/opt/homebrew/bin/ffmpeg`** for v1. This is fine for local dev and the E1 smoke test (which uses `--estimate-only` and never invokes FFmpeg). For distribution, FFmpeg must be bundled inside `Marquee.app/Contents/Resources/` and the engine taught to prefer the bundled binary. This is tracked as **Epic 5, story E5.S1** in the PRD.

If you ship the current E1 build to a Mac without Homebrew FFmpeg, the app will appear to work for "scan + estimate" but any real render will fail with `FFmpeg not found`.

## Release build (signed + notarized DMG)

```bash
./scripts/release.sh
```

End-to-end: builds the sidecar, builds the Tauri bundle, signs everything, packages a DMG, submits to Apple notarytool, staples the ticket, and runs `spctl --assess` to confirm Gatekeeper acceptance.

Manual breakdown of what `release.sh` does:

1. `scripts/build-sidecar.sh` — produces signed sidecar binary
2. `npm run tauri build` — builds the Tauri app bundle (includes signing via `signingIdentity` in `tauri.conf.json`)
3. `xcrun notarytool submit … --keychain-profile AC_PASSWORD --wait`
4. `xcrun stapler staple …`
5. `spctl --assess --type install --verbose=4 …`

## Project layout

```
desktop/
├── src/                      # React frontend
│   ├── App.tsx               # Minimal "Hello, Marquee" UI for E1.S6
│   ├── components/ui/        # shadcn baseline (button, card)
│   ├── hooks/useSidecar.ts   # Typed hook over the sidecar event stream
│   └── lib/
│       ├── sidecar-events.ts # TS mirror of the IPC protocol
│       └── utils.ts          # cn() helper
├── src-tauri/                # Rust shell
│   ├── src/
│   │   ├── main.rs           # Entry point
│   │   ├── lib.rs            # Tauri builder + `start_scan` command
│   │   └── sidecar.rs        # JSON-line parser + event forwarder
│   ├── binaries/             # PyInstaller output (gitignored)
│   ├── capabilities/         # Tauri 2 permission grants
│   ├── entitlements.plist    # Hardened-runtime entitlements
│   └── tauri.conf.json       # Bundle config, signing identity, externalBin
├── scripts/
│   ├── build-sidecar.sh      # PyInstaller + codesign
│   └── release.sh            # Full sign + notarize + DMG
└── test-fixtures/            # Tiny synthetic JPGs for the smoke test
```

## Known follow-ups (carried into later epics)

- **E5.S1** — Bundle FFmpeg inside the `.app`; remove dependency on system Homebrew.
- **E2** — Real UI (drag-and-drop, summary card with shadcn primitives).
- **E5.S5** — Auto-updater via Tauri's signed update manifest.

## Troubleshooting

### "resource path `binaries/slideshow-gen-aarch64-apple-darwin` doesn't exist"

You haven't built the sidecar yet. Run `./scripts/build-sidecar.sh`.

### Tauri dev fails with permission denied spawning sidecar

Check `src-tauri/capabilities/default.json` — `shell:allow-execute` must list the sidecar.

### Notarization fails with "package does not have a signature"

Verify the signing identity in `tauri.conf.json` matches `security find-identity -p codesigning -v` output exactly.

### `spctl --assess` rejects after notarization

Run `codesign --verify --deep --strict --verbose=2 path/to/Marquee.app` and look for unsigned nested dylibs — most commonly an un-signed file inside the PyInstaller sidecar bundle.
