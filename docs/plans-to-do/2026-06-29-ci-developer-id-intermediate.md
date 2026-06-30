---
title: CI signing — install Developer ID G2 intermediate so codesign embeds the full chain
status: "In Progress"
completed:
linked_pr:
impl-model: opus
---

# CI signing — install the Developer ID G2 intermediate

Follow-on to E5.S2 codesign hygiene (`2026-06-25-epic-5-s2-codesign-hygiene.md`)
and the Developer ID cert recovery (see command-center session 2026-06-26/29).

## Problem

The release pipeline (`.github/workflows/release.yml`, "Import Developer ID
Application certificate" step) imports a single-identity `.p12` into a fresh
temporary keychain on a clean `macos-14` runner. That `.p12` carries only the
**leaf** certificate + private key. Apple's **"Developer ID Certification
Authority (G2)"** intermediate is *not* a built-in macOS root, so on the empty
CI keychain `codesign` cannot assemble the chain:

- `security find-identity -v -p codesigning` reports **"0 valid identities"**
  even though the import succeeded (this is exactly the failure reproduced
  locally during the cert recovery — the `.p12` exported via
  `security export -t identities` omits the intermediate).
- Any signature `codesign` does produce is leaf-only and can fail Gatekeeper on
  user Macs that have never cached the G2 intermediate.

## Fix

In the import step, after the `.p12` import + `set-key-partition-list`:

1. `curl` Apple's canonical intermediate from
   `https://www.apple.com/certificateauthority/DeveloperIDG2CA.cer` (DER, ~1 KB).
2. Verify the fetched cert's subject contains
   `Developer ID Certification Authority` — **fail closed** if Apple serves
   anything else.
3. `security import … -t cert -f x509 -k "$KEYCHAIN_PATH"`.

Also harden the existing sanity check: assert `find-identity -v` actually lists
a `Developer ID Application` identity, so a broken chain fails the job *early*
(before notarization) instead of silently producing an unsigned/leaf-only build.

## Why fetch at build time (not bundle the .cer)

The intermediate is public, stable (valid to 2031-09-17), and served by Apple
over HTTPS; fetching keeps the repo free of vendored Apple certs and always
matches the issuer Apple is currently chaining to. The subject-check + `--fail`
+ `--retry 3` make the fetch safe and deterministic enough for CI.

## Acceptance criteria

```gherkin
Given the release workflow runs on a clean macos-14 runner
When the "Import Developer ID Application certificate" step completes
Then "security find-identity -v -p codesigning" lists exactly one valid
  "Developer ID Application: ADAM SPENCER THEDE (U85N54PC5J)" identity
And the step fails the job if no valid identity is present
And the produced .app is signed with the full leaf -> G2 -> Apple Root chain
```

## Verification

Local proof that the chain is the missing piece is already in hand: importing
the G2 intermediate into the recovered keychain flipped Lens's
`xcodebuild -exportArchive` from exit 70 to **EXPORT SUCCEEDED**. CI validation:
trigger the release workflow (`workflow_dispatch`) after merge and confirm the
import step's sanity check prints one valid identity and the signed `.app`
notarizes + staples.

## Out of scope

- The `.p12` secret itself (`APPLE_CERTIFICATE_P12_BASE64`) is already set in the
  repo's Actions secrets (single-identity export, under GitHub's 48 KB limit).
- No change to the notarization or sidecar-signing steps.
