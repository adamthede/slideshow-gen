#!/usr/bin/env bash
# Build, sign, and verify the slideshow-gen sidecar binary for Marquee.
#
# Output: desktop/src-tauri/binaries/slideshow-gen-aarch64-apple-darwin
#
# Tauri's externalBin convention: a per-target-triple suffix on the
# binary name. We're macOS arm64 only for v1 (NFR6, ADR-0001).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$DESKTOP_DIR/.." && pwd)"

SIGNING_IDENTITY="Developer ID Application: ADAM SPENCER THEDE (U85N54PC5J)"
TARGET_TRIPLE="aarch64-apple-darwin"
OUTPUT_NAME="slideshow-gen-${TARGET_TRIPLE}"
OUTPUT_DIR="$DESKTOP_DIR/src-tauri/binaries"
OUTPUT_PATH="$OUTPUT_DIR/$OUTPUT_NAME"

BUILD_DIR="$DESKTOP_DIR/sidecar-build"
DIST_DIR="$DESKTOP_DIR/sidecar-dist"

echo "[build-sidecar] Repo root: $REPO_ROOT"
echo "[build-sidecar] Output:    $OUTPUT_PATH"

# Activate the project's venv so PyInstaller sees the engine deps.
if [ -z "${VIRTUAL_ENV:-}" ]; then
  if [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
    # shellcheck source=/dev/null
    source "$REPO_ROOT/.venv/bin/activate"
  else
    echo "[build-sidecar] ERROR: no virtualenv active and $REPO_ROOT/.venv not found."
    echo "Create it with: python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ."
    exit 1
  fi
fi

# Sanity-check core deps before we burn cycles.
python -c "import slideshow_gen; import reverse_geocoder; import PIL; import pillow_heif" \
  || { echo "[build-sidecar] ERROR: engine deps not installed in venv."; exit 1; }

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "[build-sidecar] Installing PyInstaller into venv..."
  pip install --quiet pyinstaller
fi

echo "[build-sidecar] Cleaning previous build..."
rm -rf "$BUILD_DIR" "$DIST_DIR"

echo "[build-sidecar] Running PyInstaller..."
pyinstaller \
  --clean \
  --noconfirm \
  --workpath "$BUILD_DIR" \
  --distpath "$DIST_DIR" \
  "$SCRIPT_DIR/slideshow-gen.spec"

BUILT="$DIST_DIR/slideshow-gen"
if [ ! -f "$BUILT" ]; then
  echo "[build-sidecar] ERROR: expected output $BUILT not produced."
  ls -la "$DIST_DIR"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
cp "$BUILT" "$OUTPUT_PATH"
chmod +x "$OUTPUT_PATH"

echo "[build-sidecar] Signing with: $SIGNING_IDENTITY"
# Hardened runtime + entitlements. The PyInstaller-onefile bootloader
# extracts a Python framework to a temp dir and dlopens it at startup.
# Under hardened runtime, dlopen rejects libraries whose Team ID doesn't
# match the parent process unless `disable-library-validation` is granted.
# Python.framework as bundled by PyInstaller is signed with the PSF's
# Team ID, so without this entitlement, the sidecar fails to launch.
#
# Uses binary-entitlements.plist (E5.S3): the nested-binary entitlements
# file granting only disable-library-validation. This mirrors the sidecar
# signing step in release.yml exactly. See docs/release-pipeline.md
# "Hardened Runtime & Entitlements".
codesign \
  --force \
  --options runtime \
  --timestamp \
  --entitlements "$DESKTOP_DIR/src-tauri/binary-entitlements.plist" \
  --sign "$SIGNING_IDENTITY" \
  "$OUTPUT_PATH"

echo "[build-sidecar] Verifying signature..."
codesign --verify --verbose=2 "$OUTPUT_PATH"

echo "[build-sidecar] Smoke test: --help"
"$OUTPUT_PATH" --help >/dev/null

echo "[build-sidecar] Smoke test: render --help"
"$OUTPUT_PATH" render --help >/dev/null

echo
echo "[build-sidecar] OK. Sidecar at: $OUTPUT_PATH"
ls -lh "$OUTPUT_PATH"
