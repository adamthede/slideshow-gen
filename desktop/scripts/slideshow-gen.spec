# PyInstaller spec for the slideshow-gen sidecar binary embedded in Marquee.
#
# Tradeoffs (see ADR-0002):
#   - onefile=True: ~simpler signing surface (one binary to sign), slower
#     cold start (~1–2s for self-extract), bigger memory peak. Chosen here
#     because the sidecar is short-lived per invocation and the signing
#     simplicity is worth it for E1.
#
# Bundled data:
#   - reverse_geocoder/rg_cities1000.csv — the offline geocoding dataset.
#     Required at runtime; the package looks it up via __file__.
#
# Hidden imports:
#   - reverse_geocoder.cKDTree_MP, pillow_heif — both imported lazily by
#     slideshow_gen and not always picked up by PyInstaller's analysis.

import os
import sys
from pathlib import Path

import reverse_geocoder

# PyInstaller injects SPECPATH; fall back to cwd for direct invocation.
SPECPATH = globals().get("SPECPATH") or os.getcwd()
ROOT = Path(SPECPATH).resolve().parent.parent  # desktop/scripts -> repo root
ENTRY = Path(SPECPATH) / "sidecar_entry.py"

if not ENTRY.exists():
    sys.exit(f"Entry point not found: {ENTRY}")

RG_DATA = Path(reverse_geocoder.__file__).parent / "rg_cities1000.csv"
if not RG_DATA.exists():
    sys.exit(f"reverse_geocoder dataset not found at {RG_DATA}")

block_cipher = None

a = Analysis(
    [str(ENTRY)],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[(str(RG_DATA), "reverse_geocoder")],
    hiddenimports=[
        "reverse_geocoder",
        "reverse_geocoder.cKDTree_MP",
        "pillow_heif",
        "PIL._tkinter_finder",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim some weight; sidecar is headless.
        "tkinter",
        "matplotlib",
        "pytest",
        "IPython",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="slideshow-gen",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="arm64",
    codesign_identity=None,  # We sign after the fact in build-sidecar.sh
    entitlements_file=None,
)
