# Wrap-Up: Tauri bundler strips the sidecar's entitlements — v1.0.0 "Scan kills the engine" fix

**Date:** 2026-07-06
**Scope:** Marquee release pipeline (`.github/workflows/release.yml`)
**Identity:** `Developer ID Application: ADAM SPENCER THEDE (U85N54PC5J)` · Team `U85N54PC5J`
**Artifacts:** fix PR (`fix/release-sidecar-entitlements`) · shipped-v1.0.0 codesign forensics · workflow_dispatch verification run

---

## Problem

The shipped v1.0.0 DMG installs and launches cleanly — Gatekeeper accepts it,
the Tauri shell opens, the UI works. But clicking **Scan** kills the engine:
the PyInstaller onefile sidecar (`Contents/MacOS/slideshow-gen`) crashes at
launch with a dyld error:

> code signature … not valid for use in process: mapping process and mapped
> file (non-platform) have different Team IDs

Three green CI runs — signing, deep-verify, notarization, stapling, Gatekeeper
assessment all passing — shipped an app whose engine cannot start.

## Investigation

Forensics on the installed app (`/Applications/Marquee.app`):

- `codesign -d --entitlements :- …/Contents/MacOS/slideshow-gen` → **empty
  entitlements dict**, with `flags=0x10000(runtime)` (hardened runtime on).
  The sidecar was supposed to carry
  `com.apple.security.cs.disable-library-validation`.
- `…/Contents/Resources/ffmpeg` and `ffprobe` **still carry** the
  disable-library-validation entitlement — their pre-bundle signatures
  survived intact.

So the workflow's "Sign the PyInstaller sidecar" step did its job, and then
something later re-signed only the sidecar — with empty entitlements. The
differentiator: the sidecar is a `tauri.conf.json` `externalBin` (lands in
`Contents/MacOS/`), while ffmpeg/ffprobe are bundle `resources` (land in
`Contents/Resources/`).

## Root Cause

Tauri's bundler re-signs every `externalBin` during `npm run tauri build`,
using the entitlements configured in `tauri.conf.json` →
`app-entitlements.plist` — which is **intentionally empty** (it is the shell's
entitlements file). That re-sign silently replaced the sidecar's carefully
constructed signature, stripping `disable-library-validation`. Under the
hardened runtime, the sidecar then can't dlopen the PSF-signed
`Python.framework` it extracts at launch (different Team ID, not
Apple-signed), and dyld kills it.

Why every existing gate missed it:

- **Deep-verify** (`codesign --verify --deep --strict`) checks signature
  *validity*, not entitlement *content*. The bundler's re-sign is a perfectly
  valid signature — with the wrong entitlements.
- **Notarization** doesn't reject an app for *lacking* an entitlement.
- **Gatekeeper / spctl** and the manual double-click smoke test only exercise
  the Tauri shell, which needs no entitlements. The engine only launches when
  the user clicks Scan.

## Analogy

A courier seals a package with a tamper-evident seal listing its customs
declarations, and hands it to the shipping department. Shipping repacks it
into the branded box — and re-seals it with the *box's* blank declaration
form. Every checkpoint downstream verifies the seal is unbroken (it is!), but
nobody re-reads what the declaration actually says until customs at the
destination opens it and impounds the contents. The fix isn't a better seal —
it's a checkpoint that reads the declaration on the final box.

## What We Did

Two additions to `release.yml`, inserted after "Locate built Marquee.app" and
before the deep-verify gate / notarization:

1. **Post-bundle re-sign step.** Re-signs the bundled sidecar in place with
   `binary-entitlements.plist` (hardened runtime + timestamp, same identity),
   then re-seals the outer `.app` with `app-entitlements.plist` (modifying a
   nested binary invalidates the bundle seal), then re-runs
   `codesign --verify --deep --strict`. The outer re-sign is deliberately
   **not** `--deep` — a deep re-sign would push the app entitlements back
   onto every nested binary, recreating the exact bug.
2. **Entitlement assertion gate.** Extracts the entitlements *actually
   carried* by the final bundle's `slideshow-gen`, `ffmpeg`, and `ffprobe`,
   and hard-fails the job (`exit 1`) if any of them lacks
   `disable-library-validation`. This runs before notarization, so a
   regression can never again reach a notary submission, let alone a release
   — even if a future Tauri upgrade changes what the bundler re-signs.

Nothing else in the workflow was restructured; broader hygiene is deferred to
a separate PR.

## Files Changed

- `.github/workflows/release.yml` — the two new steps above.
- `docs/wrap-ups/2026-07-06-sidecar-entitlement-stripping-fix.md` — this doc.

## Impact / Before & After

| | Before | After |
|---|---|---|
| Sidecar entitlements in shipped app | Empty (stripped by Tauri bundler) | `disable-library-validation` present |
| Clicking Scan | Engine killed by dyld at launch | Engine launches (Python.framework loads) |
| CI protection against this class of bug | None — all gates check validity, not content | Hard `exit 1` assertion on final-bundle entitlements, pre-notarization |
| Release artifacts | v1.0.0 draft assets broken | Rebuild via tag re-push after merge produces fixed DMG/zip |

## Lessons Learned

- **A report is a snapshot; only a live check is a gate.** The signing step's
  own verification passed — at the moment it ran. The artifact was mutated
  afterward. Turn release lessons into CI assertions that run against the
  *final* artifact, not the intermediate one.
- **Verify entitlement content, not just signature validity.** `codesign
  --verify --deep --strict` says "validly signed," not "signed with what you
  intended."
- **Test the path the user takes.** Every smoke test exercised app launch;
  none clicked Scan. The one unexercised process was the broken one. The
  post-merge runbook now requires a real Scan before publishing.
- **Bundlers re-sign.** Treat any packaging step that holds a signing
  identity as a potential re-signer, and assert your invariants after it.

## Open Items

- **Release runbook (Adam):** after merge, delete and re-push the `v1.0.0`
  tag to rebuild the draft release with fixed artifacts; install the new DMG
  and click **Scan** on a real folder *before* publishing the release.
- **Workflow hygiene PR (deferred):** unused env vars and other cleanup in
  `release.yml` — explicitly out of scope here.
- **No planning file exists for this fix** — `/shipped` creates the stub at
  merge time.

---

# Round 2 (same day): the DMG bundling pass resurrected the bug in one artifact

## Problem

After Round 1 merged and the `v1.0.0` tag was re-pushed, the rebuilt draft
release was asymmetric: the sidecar inside `Marquee-stapled.zip` carried
`disable-library-validation`, but the sidecar inside
`Marquee_1.0.0_aarch64.dmg` had **zero entitlements**. Adam installed from
the DMG and hit the identical dlopen Team-ID failure.

## Root Cause

`npm run tauri bundle -- --bundles dmg` does not just wrap the existing .app
— the bundler re-runs its **entire signing pass** first. Run 28766929210's
log proves it with timestamps: during the DMG step, Tauri logs
`Signing …/Contents/MacOS/slideshow-gen`, then the shell, then the .app —
all with the empty app entitlements — before packing the DMG. So the Round 1
re-sign fix was undone *inside the DMG* (and the .app's staple invalidated),
while the zip stayed correct only because commit 0228859 had already moved
zip creation before the DMG step. The Round 1 assertion gate passed honestly
— against the intermediate .app, which was the wrong artifact to assert.

## What We Did (Round 2)

1. **Replaced the Tauri DMG step with pure hdiutil packaging** — a staging
   copy (`ditto`) of the notarized + stapled .app plus an `/Applications`
   symlink, `hdiutil create -format UDZO`, then codesign the DMG. The bundler
   is never re-entered after signatures are final; the app inside the DMG is
   byte-identical to the zip's. Trade-off: default Finder layout (no custom
   icon positions) — cosmetic, deferred to hygiene.
2. **Moved the assertion gate to the very end** and pointed it at the
   shipped artifacts: it unzips the final zip and mounts the final DMG, then
   asserts the parsed entitlement on sidecar/ffmpeg/ffprobe inside **both**,
   plus `stapler validate` on the app inside the DMG. It runs after all
   signing/notarization/stapling and before upload/attach.

## Lessons Learned (Round 2)

- **Assert the artifact you ship, not the intermediate.** Round 1's gate was
  live and honest — and aimed at a bundle that a later step quietly rebuilt.
  The gate must sit at the last edge before publication.
- **"Bundlers re-sign" is not a one-time lesson — it re-applies per
  invocation.** Every `tauri build`/`tauri bundle` call re-signs; the fix is
  to stop re-entering the bundler, not to chase each pass with another
  re-sign.
- **A per-artifact asymmetry is a diagnosis.** zip good + DMG bad immediately
  isolated the fault to the only step that touches one and not the other.
