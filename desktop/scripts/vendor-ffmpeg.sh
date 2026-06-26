#!/usr/bin/env bash
# Vendor a license-clean static FFmpeg + ffprobe for aarch64-apple-darwin into
# Marquee's Tauri bundle-resource directory (E5.S7).
#
#   Output: <dest>/ffmpeg  and  <dest>/ffprobe   (default dest:
#           desktop/src-tauri/resources, matching `bundle.resources` in
#           tauri.conf.json -> Marquee.app/Contents/Resources/{ffmpeg,ffprobe})
#
# These binaries are NOT committed (see desktop/.gitignore). CI fetches them at
# build time, this script signs nothing — signing is a separate codesign step
# in release.yml so the E5.S2 deep-verify gate exercises the embedded copies.
#
# LICENSE POSTURE (see docs/release-pipeline.md): Marquee invokes FFmpeg as a
# **separate child process** (never linked), but we still prefer a clean
# LGPL/non-GPL build for a distributed product. This script FAILS CLOSED: if
# the fetched build advertises --enable-gpl / --enable-nonfree, or is missing a
# capability the engine actually uses, the build stops here rather than shipping
# a wrongly-licensed or broken FFmpeg.
#
# Source is overridable so Adam can pin an exact, verified build (recommended:
# pin a versioned URL + sha256 once the source is confirmed):
#   FFMPEG_VENDOR_URL   / FFPROBE_VENDOR_URL    (zip containing the binary)
#   FFMPEG_VENDOR_SHA256 / FFPROBE_VENDOR_SHA256 (optional; verified if set)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

DEST="${1:-$DESKTOP_DIR/src-tauri/resources}"
mkdir -p "$DEST"

# Default source: Martin Riedl's static macOS/arm64 build server. It exposes a
# stable redirect API and ships ffmpeg + ffprobe as separate static binaries.
# The license/feature guards below are the real contract — if this source ever
# serves a GPL build or drops a needed feature, the guard stops the build and
# Adam swaps FFMPEG_VENDOR_URL/FFPROBE_VENDOR_URL.
FFMPEG_VENDOR_URL="${FFMPEG_VENDOR_URL:-https://ffmpeg.martin-riedl.de/redirect/latest/macos/arm64/release/ffmpeg.zip}"
FFPROBE_VENDOR_URL="${FFPROBE_VENDOR_URL:-https://ffmpeg.martin-riedl.de/redirect/latest/macos/arm64/release/ffprobe.zip}"
FFMPEG_VENDOR_SHA256="${FFMPEG_VENDOR_SHA256:-}"
FFPROBE_VENDOR_SHA256="${FFPROBE_VENDOR_SHA256:-}"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

log() { echo "[vendor-ffmpeg] $*"; }
fail() { echo "[vendor-ffmpeg] ERROR: $*" >&2; exit 1; }

# Supply-chain guard. This script downloads a binary and then EXECUTES it
# (`-version`/`-encoders`/... guards). In CI that runner also holds the Apple
# Developer ID cert + passwords, so executing an unverified binary from a
# third-party host would be an arbitrary-code-execution / supply-chain risk if
# that host were compromised. In CI we therefore REFUSE to proceed unless both
# checksums are pinned (which also makes releases reproducible). Locally
# (no CI) checksums stay optional with a warning. Override the gate explicitly
# with REQUIRE_PINNED_SHA256=0 only for local experimentation.
REQUIRE_PINNED_SHA256="${REQUIRE_PINNED_SHA256:-${CI:-false}}"
if [ "$REQUIRE_PINNED_SHA256" = "true" ] || [ "$REQUIRE_PINNED_SHA256" = "1" ]; then
  if [ -z "$FFMPEG_VENDOR_SHA256" ] || [ -z "$FFPROBE_VENDOR_SHA256" ]; then
    fail "FFMPEG_VENDOR_SHA256 and FFPROBE_VENDOR_SHA256 must be pinned before fetching/executing FFmpeg in a secrets-bearing job. Pin a verified build (and ideally a versioned URL). See docs/release-pipeline.md."
  fi
fi

# fetch_one <url> <sha256-or-empty> <expected-binary-name> <dest-path>
fetch_one() {
  local url="$1" want_sha="$2" name="$3" dest="$4"
  local zip="$WORK/$name.zip" ex="$WORK/$name.d"

  log "Fetching $name from: $url"
  curl --fail --location --silent --show-error --retry 3 -o "$zip" "$url"

  if [ -n "$want_sha" ]; then
    local got_sha
    got_sha="$(shasum -a 256 "$zip" | awk '{print $1}')"
    [ "$got_sha" = "$want_sha" ] || fail "$name sha256 mismatch: got $got_sha want $want_sha"
    log "$name sha256 verified."
  else
    log "$name sha256 not pinned (got $(shasum -a 256 "$zip" | awk '{print $1}')). Consider pinning for reproducible releases."
  fi

  mkdir -p "$ex"
  ditto -x -k "$zip" "$ex" 2>/dev/null || unzip -qo "$zip" -d "$ex"

  # Locate the extracted executable: prefer an exact name match, else the first
  # Mach-O regular file in the archive.
  local found
  found="$(find "$ex" -type f -name "$name" | head -n1)"
  if [ -z "$found" ]; then
    found="$(find "$ex" -type f -print0 | xargs -0 file | grep -i 'Mach-O' | head -n1 | cut -d: -f1)"
  fi
  [ -n "$found" ] || fail "could not find the $name executable inside $url"

  install -m 0755 "$found" "$dest"
  log "Installed $name -> $dest"

  # Architecture guard: must be a native arm64 Mach-O.
  file "$dest" | grep -q 'arm64' || fail "$dest is not an arm64 Mach-O: $(file "$dest")"
}

fetch_one "$FFMPEG_VENDOR_URL"  "$FFMPEG_VENDOR_SHA256"  "ffmpeg"  "$DEST/ffmpeg"
fetch_one "$FFPROBE_VENDOR_URL" "$FFPROBE_VENDOR_SHA256" "ffprobe" "$DEST/ffprobe"

FFMPEG="$DEST/ffmpeg"

# --- License guard: refuse GPL / nonfree builds for a distributed product. ---
CONFIG_LINE="$("$FFMPEG" -hide_banner -version 2>/dev/null | grep -i '^configuration:' || true)"
log "ffmpeg configuration: $CONFIG_LINE"
"$FFMPEG" -hide_banner -buildconf 2>/dev/null || true
if echo "$CONFIG_LINE" | grep -q -- '--enable-gpl'; then
  fail "fetched FFmpeg is a GPL build (--enable-gpl). Pick an LGPL/non-GPL build for distribution (set FFMPEG_VENDOR_URL/FFPROBE_VENDOR_URL)."
fi
if echo "$CONFIG_LINE" | grep -q -- '--enable-nonfree'; then
  fail "fetched FFmpeg is a non-redistributable build (--enable-nonfree)."
fi
log "License guard passed: no --enable-gpl / --enable-nonfree."

# --- Feature guards: every capability the engine actually invokes. ---
require_encoder() { "$FFMPEG" -hide_banner -encoders 2>/dev/null | grep -qw "$1" || fail "FFmpeg build missing required encoder: $1"; }
require_filter()  { "$FFMPEG" -hide_banner -filters  2>/dev/null | grep -qw "$1" || fail "FFmpeg build missing required filter: $1"; }

require_encoder "h264_videotoolbox"   # all encodes use the Apple HW encoder
require_encoder "aac"                 # silent + music audio tracks
require_filter  "zoompan"             # Ken Burns motion
require_filter  "drawtext"            # date/location overlays (needs libfreetype)
require_filter  "sidechaincompress"   # music ducking under narration
require_filter  "overlay"
log "Feature guards passed: h264_videotoolbox, aac, zoompan, drawtext, sidechaincompress, overlay."

echo
log "OK. Vendored:"
ls -lh "$DEST/ffmpeg" "$DEST/ffprobe"
