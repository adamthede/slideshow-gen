# Wrap-Up: Developer ID signing certificate — loss, Time Machine recovery, and CI hardening

**Date:** 2026-06-29
**Scope:** Thede Technologies code-signing identity (shared by Lens / LifesliceRedux and Marquee / slideshow-gen)
**Identity:** `Developer ID Application: ADAM SPENCER THEDE (U85N54PC5J)` · Team `U85N54PC5J`
**Artifacts:** slideshow-gen PR #17 (CI intermediate install) · Lens local signing restored · GitHub Actions secrets set

---

## Problem

While wiring up Marquee's CI release pipeline (`slideshow-gen/.github/workflows/release.yml`)
to sign + notarize on a clean GitHub `macos-14` runner, two problems surfaced in
sequence:

1. **The signing identity was gone.** The **Developer ID Application certificate
   and its private key** were missing from the login keychain on the Mac Studio.
   `security find-identity -v -p codesigning` did not list the identity — which
   meant **Lens could no longer be signed locally either**, not just Marquee in CI.
2. **Even after recovery, imports showed "0 valid identities."** Re-importing the
   recovered `.p12` reported `14 identities imported … 0 valid identities found`,
   and Lens's `xcodebuild -exportArchive` failed with **exit 70**.

A Developer ID private key is generated locally and **never held by Apple**. If it
is lost with no backup, the only path is to revoke the certificate, issue a new
one, and re-sign + re-notarize everything ever shipped under it. So this was a
genuine "can we recover it or do we start over?" moment.

## Investigation

- **Confirmed the loss**, not a search-path quirk: the identity was absent from
  `find-identity` across the default keychain search list, not merely unlisted.
- **Time Machine archaeology.** The backup volume was attached, but the obvious
  paths didn't work:
  - The `.timemachine` automount paths are **not browsable** (`ls` →
    "No such file or directory") even with Full Disk Access — this is **not** an
    FDA problem, which sent us down a false trail initially.
  - The materialized latest backup lives at `/Volumes/Time Machine/`.
  - Older states are **APFS snapshots** (`com.apple.TimeMachine.<ts>.backup`) that
    must be mounted explicitly with `mount_apfs -s <snapshot> <device> <mountpoint>`
    (requires root; mounts read-only).
- **Mounted the May 6, 2026 snapshot** and recovered the old
  `login.keychain-db` to a scratch copy.
- **Diagnosed the "0 valid" mystery.** The cert inside the recovered keychain was
  *not* expired (valid 2026–2031) and the keychain was unlocked — so neither usual
  suspect applied. The real cause: a `.p12` exported via
  `security export -t identities -f pkcs12` contains **only the leaf certificate +
  private key**, *not* the **"Developer ID Certification Authority" intermediate**.
  On a keychain that lacks that intermediate, `codesign`/`find-identity` cannot
  build leaf → intermediate → Apple Root, so the identity is reported **invalid**
  ("0 valid") even though the import succeeded.

## Root Cause

Two distinct root causes, one per problem:

1. **Loss:** the Developer ID leaf cert + private key had dropped out of the active
   login keychain (keychain reset / migration at some prior point; no local export
   backup existed). Recoverable *only* because Time Machine had a snapshot
   predating the loss.
2. **"0 valid identities":** a code-signing identity is only valid when its **full
   certificate chain** is present and chains to a trusted root. The leaf alone is
   not enough — the **G2 intermediate** is required, and it is **not** a built-in
   macOS root, nor is it carried in a `-t identities` PKCS#12 export.

## Analogy

Apple keeps the **design of your ID card** (it can re-issue the certificate), but
**you hold the only stamp that makes a signature** (the private key) — lose the
stamp with no spare and no one can re-cut it; you start over.

The **intermediate certificate** is the **notary's seal-of-office** that proves
your stamp chains up to an authority everyone recognizes. You can have a perfectly
good stamp and still be turned away at a *fresh* desk (an empty CI keychain, or a
freshly-restored keychain) that has never seen the notary's seal — which is exactly
why the import said "0 valid" until the seal was added.

## What We Did

1. **Recovered the identity** from the Time Machine May-6 APFS snapshot
   (`mount_apfs` → copy `login.keychain-db` → import).
2. **Restored a valid identity** by also importing the two intermediates extracted
   from the recovered keychain → `find-identity -v` then reported **1 valid**.
3. **Restored Lens local signing** — `xcodebuild -exportArchive` went from
   **exit 70 → EXPORT SUCCEEDED**, producing a `Lens.app` signed with the full
   chain. (No Lens code changed; this was an environment/keychain restoration.)
4. **Set up Marquee CI signing secrets.** The recovered `.p12` had 14 identities →
   its base64 was ~53 KB, over **GitHub's 48 KB per-secret limit** (HTTP 422). Fixed
   by exporting a **clean single-identity `.p12`** (3,265 bytes) via Keychain Access.
   `APPLE_CERTIFICATE_P12_BASE64` + `APPLE_CERTIFICATE_PASSWORD` (plus the existing
   `APPLE_ID`, `APPLE_TEAM_ID`, `APPLE_APP_SPECIFIC_PASSWORD`) were set by Adam
   directly — the autonomous-agent guard correctly refuses to upload a private
   signing key as a CI secret.
5. **Hardened CI against the same root cause (PR #17).** A clean `macos-14` runner
   has the *same* empty-keychain problem the restored Mac had. The release
   workflow now downloads Apple's **Developer ID G2 intermediate**
   (SHA256-pinned: `f16cd3c5…d2df3a`, fail-closed), imports it, and asserts a
   valid `Developer ID Application` identity is present before building — so a
   broken chain fails the job *early* rather than producing an unsigned/leaf-only
   build that dies in notarization. Guards use snapshot-then-match rather than
   `… | grep -q` under `pipefail` (SIGPIPE false-negative class, per the repo's
   `vendor-ffmpeg.sh` convention).

## Files Changed

| File | Repo | Change |
|------|------|--------|
| `.github/workflows/release.yml` | slideshow-gen | Install + SHA256-pin the G2 intermediate in the keychain step; assert a valid identity; pipefail-safe guards |
| `docs/plans-to-do/2026-06-29-ci-developer-id-intermediate.md` | slideshow-gen | Plan for the CI intermediate work (PR #17) |
| GitHub Actions secrets | slideshow-gen | `APPLE_CERTIFICATE_P12_BASE64`, `APPLE_CERTIFICATE_PASSWORD` set (single-identity export) |
| login keychain (environment) | local Mac Studio | Recovered leaf + key + intermediates → 1 valid identity (no repo file) |

## Impact / Before & After

| | Before | After |
|--|--------|-------|
| Lens local signing | `xcodebuild -exportArchive` → **exit 70** | **EXPORT SUCCEEDED**, full chain |
| `find-identity -v` | identity absent → recovered but **0 valid** | **1 valid** Developer ID Application |
| Marquee CI secrets | none / oversized `.p12` (HTTP 422) | 5 secrets present, single-identity `.p12` (3.2 KB) |
| Marquee CI chain | would report "0 valid" on empty keychain | G2 intermediate installed + pinned; valid-identity assertion gates the build |
| Disaster recoverability | **unrecoverable if Time Machine lacked it** | identity in hand; **1Password stash pending** |

## Lessons Learned

1. **A Developer ID private key is a single point of failure for the whole
   portfolio.** It is unrecoverable from Apple. Back it up *out of band* — this is
   why the 1Password stash (Open Item) is non-negotiable, not a nicety.
2. **"0 valid identities" almost always means a missing intermediate, not an
   expired cert or a locked keychain.** Check the chain before assuming the worst.
3. **`security export -t identities` does not carry the intermediate.** Any `.p12`
   you stash for disaster recovery should be verified to produce a *valid* identity
   on a *fresh* keychain — export the chain, or re-add the intermediate on import.
4. **Time Machine internals:** the browsable backup is `/Volumes/Time Machine/`;
   `.timemachine` automount paths are a dead end; older states need
   `mount_apfs -s <snapshot>` as root. FDA is necessary but not sufficient.
5. **GitHub Actions secrets cap at 48 KB.** A multi-identity `.p12` blows past it;
   export exactly the one identity CI needs.
6. **Empty-keychain == clean CI runner == freshly-restored Mac.** The same
   intermediate-chain failure shows up in all three. Fixing it once in CI
   (PR #17) closes the gap that this whole incident exposed.

## Open Items

- [ ] **Stash the recovered single-identity `.p12` + its password in 1Password**
      (Adam). The recovery worked *this time* because Time Machine had it; the
      backup makes the next time a non-event.
- [ ] **Clean up scratch material holding private keys** (Adam, runs as root):
      `sudo umount /tmp/tm-may06`; remove `/tmp/recovered-login.keychain-db` and the
      exported `.p12` scratch copies.
- [ ] **Merge PR #17, then run the Marquee release dry run**
      (`gh workflow run "Release (sign + notarize)" -R adamthede/slideshow-gen`) to
      validate the full chain end-to-end (import → sidecar sign → Tauri build →
      notarize → staple).
- [ ] **Watch for Apple rotating the G2 intermediate** (valid to 2031-09-17). If it
      rotates, the SHA256 pin in `release.yml` fails closed with a clear message —
      update the pin then.
