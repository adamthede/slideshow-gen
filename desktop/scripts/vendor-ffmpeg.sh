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
# LICENSE POSTURE (see docs/release-pipeline.md): GPL is ALLOWED, nonfree is
# NOT. Marquee invokes FFmpeg purely as a **separate child process** (subprocess
# via src/slideshow_gen/ffmpeg.py + media.py; it never links libav*), so under
# the well-established GPL aggregation / "mere exec" principle FFmpeg's copyleft
# reaches only the ffmpeg binary itself, not Marquee's own code. Distribution is
# a free, direct-download, notarized .app (NOT the Mac App Store, where GPL is
# incompatible), and we ship the FFmpeg GPLv2 text + a written offer for source
# (see THIRD-PARTY-LICENSES.md / the bundled THIRD-PARTY dir), so a GPL build is
# fine to ship. `--enable-nonfree` is a different animal: it produces a
# genuinely non-redistributable binary, so this script STILL FAILS CLOSED on it
# (and on any missing capability the engine actually uses) rather than shipping
# something we have no right to distribute or that is broken.
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
# His macOS/arm64 build is a GPL build (--enable-gpl --enable-libfreetype
# --enable-libx264) and his server offers no LGPL variant — which is fine under
# the posture above (GPL allowed for arm's-length subprocess distribution). The
# license/feature guards below are the real contract: a `--enable-nonfree` build
# or a build missing a needed feature still stops the build, and Adam swaps
# FFMPEG_VENDOR_URL/FFPROBE_VENDOR_URL.
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
    # `|| true`: under `set -euo pipefail`, a no-match `grep` exits non-zero and
    # would kill the script here, bypassing the descriptive error below. Swallow
    # it so an archive with no Mach-O falls through to the clear failure message.
    found="$(find "$ex" -type f -print0 | xargs -0 file | grep -i 'Mach-O' | head -n1 | cut -d: -f1 || true)"
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

# --- Executability smoke check: fail fast with a clear message on a corrupt /
# non-runnable download (arch or dynamic-linking issue). This must run BEFORE
# the license guard: if the binary can't execute, its `-version` is empty and
# the GPL-detection grep below would silently pass (a no-op), so the guard is
# only trustworthy once we know the binary actually runs. ---
"$FFMPEG" -hide_banner -version >/dev/null 2>&1 \
  || fail "vendored ffmpeg cannot execute on this host (corrupt download or arch/linking issue)"
"$DEST/ffprobe" -hide_banner -version >/dev/null 2>&1 \
  || fail "vendored ffprobe cannot execute on this host (corrupt download or arch/linking issue)"

# --- License guard: GPL is OK (arm's-length subprocess; see header + docs/
# release-pipeline.md), but a non-redistributable --enable-nonfree build is NOT.
# We print the exact configuration: line + -buildconf into the CI log either way
# so there's an auditable record of the license + feature set actually shipped
# (and so the GPLv2 obligation is anchored to the precise build). ---
CONFIG_LINE="$("$FFMPEG" -hide_banner -version 2>/dev/null | grep -i '^configuration:' || true)"
log "ffmpeg configuration: $CONFIG_LINE"
"$FFMPEG" -hide_banner -buildconf 2>/dev/null || true
# GPL (--enable-gpl) is intentionally ALLOWED: FFmpeg is invoked arm's-length as
# a separate child process, so its copyleft does not reach Marquee's own code,
# and we convey GPLv2 (text + written offer for source) with the .app. Only
# --enable-nonfree is refused — it yields a genuinely non-redistributable binary
# we'd have no right to ship.
if grep -q -- '--enable-nonfree' <<<"$CONFIG_LINE"; then
  fail "fetched FFmpeg is a non-redistributable build (--enable-nonfree). GPL is allowed for this product, but nonfree is not — pick a build without --enable-nonfree (set FFMPEG_VENDOR_URL/FFPROBE_VENDOR_URL)."
fi
log "License guard passed: no --enable-nonfree (GPL is allowed for arm's-length subprocess distribution)."

# --- Feature guards: every capability the engine actually invokes. ---
# Snapshot the tables ONCE, then match with a here-string (not a live
# `ffmpeg | grep -q` pipe). `grep -q` exits on first match; against a still-
# writing ffmpeg that closes the pipe early and SIGPIPEs ffmpeg (exit 141),
# which under `set -o pipefail` propagates and fails the pipeline even though
# the feature IS present — a real, timing-dependent false negative (it bit the
# earliest-listed filter, sidechaincompress, on a real vendor run). A here-
# string has no upstream writer process, so there's no SIGPIPE race.
FF_ENCODERS="$("$FFMPEG" -hide_banner -encoders 2>/dev/null || true)"
FF_FILTERS="$("$FFMPEG"  -hide_banner -filters  2>/dev/null || true)"
require_encoder() { grep -qw -- "$1" <<<"$FF_ENCODERS" || fail "FFmpeg build missing required encoder: $1"; }
require_filter()  { grep -qw -- "$1" <<<"$FF_FILTERS"  || fail "FFmpeg build missing required filter: $1"; }

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
