# ADR 0001 — Desktop app stack

- **Status:** Accepted
- **Date:** 2026-05-23
- **Deciders:** Adam
- **Supersedes:** the SwiftUI-rewrite assumption baked into the initial PRD scaffold

## Context

The PRD targets a standalone macOS desktop app wrapping the proven Python rendering engine (~1,700 LOC). The original scaffold assumed a SwiftUI rewrite porting every engine module (`pipeline`, `ffmpeg`, `kenburns`, `metadata`, `overlay`, `discovery`, `heic`) to Swift. That assumption needs to be revisited against the actual constraints:

- **Personal-tool-first, but public distribution is in scope.** The app will be offered as a GitHub release download.
- **Performance and speed-to-market matter more than native look-and-feel.** The render perf ceiling is FFmpeg, not the UI framework.
- **The Python engine is proven and stable.** Rewriting it is the expensive part of any plan that involves rewriting it.
- **Single maintainer (the model + Adam).** The maintenance surface should be minimized.
- **Prior experience:** a similar pywebview + PyInstaller app exists in the author's portfolio (`adafruit-clue`). Lessons learned: pywebview ships, but hand-rolled HTML/CSS feels homemade, and PyInstaller-based macOS notarization is folklore-grade painful.

## Options Considered

### Option A — SwiftUI rewrite (original PRD assumption)
Port the entire engine to Swift, build a SwiftUI app, ship a single native binary.
- **Pros:** Genuinely native look and feel, smallest install, cleanest notarization story, AVKit preview is trivial, no Python runtime to ship.
- **Cons:** Months of work porting 1,700 LOC of FFmpeg filter-graph construction, Ken Burns supersampling math, and three-phase pipeline orchestration. Two codebases to keep in lockstep forever (Python CLI and Swift core). Output-parity testing is its own subproject. Single-platform from day one.

### Option B — pywebview + Tailwind/shadcn UI, packaged with PyInstaller / py2app
Keep the engine as-is, import `RenderPipeline` directly, render a web UI in a native WKWebView.
- **Pros:** Fastest weekend-of-shipping path. Direct Python import of the engine — no IPC. Author has built this pattern before. Adopting a real design system (Tailwind + shadcn-style components) fixes the "homemade" aesthetic of the prior project.
- **Cons:** PyInstaller-based notarization for a Python *GUI* app is a known pain (signing every bundled `.so`/`.dylib`, hidden-import breakage, dmg quirks). Bundles are large (~50–150 MB). Auto-update is roll-your-own. pywebview's menu, window-chrome, and event integration are thin. Public-distribution operational cost is high.

### Option C — Tauri + React + shadcn/ui + Python sidecar (selected)
Rust shell hosting a web UI (React + Tailwind + shadcn/ui). The Python engine is frozen as a sidecar CLI binary (PyInstaller-frozen `slideshow-gen`) that Tauri spawns and talks to via stdin/stdout (JSON events) for render orchestration and progress.
- **Pros:**
  - Notarization is first-class in Tauri's tooling, including signing the sidecar binary.
  - Built-in signed auto-updater (Sparkle-equivalent) — table stakes for public releases.
  - ~10 MB shell vs. ~50–150 MB for pywebview/PyInstaller.
  - Modern frontend dev loop (Vite, HMR, real React tooling) → fast iteration.
  - Tauri IPC fits the app's shape: frontend calls "start render," receives a stream of progress events.
  - Freezing a *CLI* with PyInstaller (the sidecar) is dramatically simpler than freezing a Python GUI app. Most of PyInstaller's signing folklore is GUI-app folklore.
  - Engine stays Python — zero rewrite, the CLI stays useful as the engine surface and as a power-user tool.
  - shadcn/ui ceiling for polish is high without any custom design work.
- **Cons:**
  - Rust + JS + Python — three languages, though the Rust touch is shallow (Tauri's defaults handle most of it) and Python work is the existing engine.
  - Sidecar IPC adds a layer vs. pywebview's direct Python import — but JSON-line events over stdio is a well-understood pattern.
  - A day or two of upfront scaffolding (sidecar packaging, signing pipeline, IPC contract) before any UI work pays off.

### Option D — Flet (pure Python, Flutter UI)
Single-language, Material Design components, packages to `.app`.
- **Pros:** Zero web stack, zero Rust, native-feeling Flutter widgets, decent default polish.
- **Cons:** Flutter aesthetic doesn't feel Mac-native. Smaller ecosystem than React/Tailwind. Standalone packaging works but is younger than Tauri's. Auto-update story weaker.

### Option E — Electron + React + Python sidecar
Same UI ceiling as Tauri, more familiar JS toolchain, no Rust.
- **Pros:** Most familiar stack on Earth. Same sidecar pattern works.
- **Cons:** ~150 MB shell vs. Tauri's ~10 MB. Heavier runtime. No real win over Tauri for this app.

## Decision

**Option C — Tauri + React + shadcn/ui + Tailwind, with the existing Python engine frozen as a sidecar CLI.**

## Rationale

Public distribution flips this decision from "weekend project" optimization to "what can I maintain and update for years" optimization. Tauri's built-in auto-updater and first-class notarization tooling are not optional features for a downloadable Mac app — they're the floor. The cost of building those manually on a pywebview/PyInstaller stack is higher than the cost of learning Tauri's defaults, and recurs every release.

Keeping the Python engine intact is the single largest speed-to-market win. The Swift rewrite was the most expensive line item in the original PRD; deleting it shortens the critical path by months. The sidecar pattern lets the existing `slideshow-gen` CLI keep being the engine's surface, which means CLI improvements (estimates, ducking tests, future overlay customization) automatically benefit the app.

shadcn/ui + Tailwind addresses the author's specific concern about the prior project — that hand-rolled CSS in a webview felt homemade. Adopting a design system means the visual ceiling is set by component-library quality, not by hand-craftsmanship-on-deadline.

## Consequences

### Positive
- Engine port is eliminated from the roadmap. Epics 1–5 simplify substantially.
- The CLI and the app share one render core, automatically and forever.
- Auto-update + notarization on the critical path from day one.
- Frontend stack (React + Tailwind + shadcn) is industry standard, easy to evolve, easy to find references for.

### Negative
- Three languages in the build (Rust, TypeScript, Python). Most of the Rust is generated by Tauri scaffolding.
- IPC contract between sidecar and shell must be designed and versioned.
- PyInstaller still applies — to the sidecar CLI. Lower-risk than GUI freezing, but not free.

### Operational
- Cross-platform optional. Tauri builds Linux and Windows targets at low marginal cost if ever wanted; macOS-only for v1.
- Open the door to a Linux build for users running the CLI on a NAS or workstation, if it ever becomes interesting.

## Follow-ups

- Define the sidecar IPC contract (commands, event schema, cancellation semantics) → owned by Epic 1.
- Stand up the signing + notarization pipeline early — before significant UI work — so release mechanics are proven on a "Hello, world" build.
- Pin Python version for the frozen sidecar and capture the freeze recipe in `docs/`.
- Decide whether shadcn/ui (React) or daisyUI (Svelte) is the component baseline. Default to shadcn/React unless a strong reason emerges in Epic 2.
