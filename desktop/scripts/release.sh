#!/usr/bin/env bash
# Full release pipeline for Marquee:
#   1. Build + sign the PyInstaller sidecar
#   2. Build + sign the Tauri .app bundle and DMG
#   3. Submit the DMG to Apple notarytool
#   4. Staple the notarization ticket onto the DMG
#   5. Verify Gatekeeper acceptance with spctl
#
# Reference: distribution/build_release.sh in the user's LifesliceRedux
# project — the proven pattern for direct-download macOS notarization on
# this machine. Adapted to the Tauri/PyInstaller stack here.
#
# Credentials: notarytool reads the AC_PASSWORD keychain profile. Store
# it once with:
#   xcrun notarytool store-credentials AC_PASSWORD \
#     --apple-id adam@thedetech.com --team-id U85N54PC5J
# Then unlock the login keychain before running this script if it's not
# already unlocked in this terminal session.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

KEYCHAIN_PROFILE="${KEYCHAIN_PROFILE:-AC_PASSWORD}"

echo "[release] step 1/5 — build sidecar"
"$SCRIPT_DIR/build-sidecar.sh"

echo
echo "[release] step 2/5 — tauri build (signs .app + DMG)"
cd "$DESKTOP_DIR"
npm run tauri build -- --bundles app,dmg

APP="$DESKTOP_DIR/src-tauri/target/release/bundle/macos/Marquee.app"
DMG_DIR="$DESKTOP_DIR/src-tauri/target/release/bundle/dmg"

if [ ! -d "$APP" ]; then
  echo "[release] ERROR: $APP not found after build."
  exit 1
fi

# Resolve the DMG robustly under set -euo pipefail. Use nullglob so a
# missing match yields an empty array (instead of crashing the pipeline),
# then pick the newest by mtime so a stale prior build can't win.
shopt -s nullglob
dmg_candidates=("$DMG_DIR"/Marquee_*.dmg)
shopt -u nullglob

if [ "${#dmg_candidates[@]}" -eq 0 ]; then
  echo "[release] ERROR: No Marquee_*.dmg found in $DMG_DIR"
  exit 1
fi

# Pick the newest by mtime. Pure bash so paths with spaces (the repo
# parent is "Project - Slideshow Generator") survive intact — earlier
# `printf | xargs ls -t` whitespace-split the paths and broke the build.
DMG="${dmg_candidates[0]}"
for f in "${dmg_candidates[@]}"; do
  if [ "$f" -nt "$DMG" ]; then
    DMG="$f"
  fi
done

if [ ! -f "$DMG" ]; then
  echo "[release] ERROR: Resolved DMG path is not a regular file: $DMG"
  exit 1
fi

echo
echo "[release] verifying signing of bundle (deep, strict)..."
codesign --verify --deep --strict --verbose=2 "$APP"

echo
echo "[release] step 3/5 — notarytool submit ($DMG)"
echo "[release] (will wait until Apple returns a verdict; can take a few minutes)"
xcrun notarytool submit "$DMG" --keychain-profile "$KEYCHAIN_PROFILE" --wait

echo
echo "[release] step 4/5 — stapler staple"
xcrun stapler staple "$DMG"

echo
echo "[release] step 5/5 — spctl --assess (gatekeeper check)"
if spctl --assess --type install --verbose=4 "$DMG" 2>&1 | tee /tmp/marquee-spctl.log; then
  echo
  echo "[release] OK. Notarized DMG: $DMG"
else
  echo
  echo "[release] FAILED Gatekeeper assessment. Do NOT distribute this DMG."
  cat /tmp/marquee-spctl.log
  exit 1
fi
