# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# -------------------------------------------------------------------------
# Path setup - __file__ is not defined when PyInstaller executes the spec.
# Use sys.argv[0] which is the spec file path.
# -------------------------------------------------------------------------
SPEC_PATH = Path(sys.argv[0]).resolve()
ROOT = SPEC_PATH.parent
TOOLS_DIR = ROOT.parent
REPO_ROOT = TOOLS_DIR.parent
BACKEND = REPO_ROOT / "backend"
KEYGEN_DIR = ROOT
ICON_DIR = KEYGEN_DIR / "icon"

# -------------------------------------------------------------------------
# Version (from pyproject.toml)
# -------------------------------------------------------------------------
try:
    import tomllib
except ImportError:
    import tomli as tomllib

def _get_version() -> str:
    pyproject = REPO_ROOT / "pyproject.toml"
    if pyproject.exists():
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        return data.get("project", {}).get("version", "1.0.0")
    return "1.0.0"

VERSION = _get_version()

# -------------------------------------------------------------------------
# Hidden imports — auto-collect + manual
# -------------------------------------------------------------------------
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = [
    "customtkinter",
    "nacl",
    "nacl.signing",
    "nacl.encoding",
    "PIL",
    "PIL.Image",
    "PIL.ImageTk",
    "tkinter",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "argon2",
    "argon2.low_level",
]

# Auto-collect heavy packages
for pkg in [
    "customtkinter",
    "nacl",
    "PIL",
    "argon2",
]:
    hiddenimports.extend(collect_submodules(pkg))

# Deduplicate
hiddenimports = sorted(set(hiddenimports))

# -------------------------------------------------------------------------
# Excludes - exclude everything outside tools directory
# -------------------------------------------------------------------------
excludes = [
    "pytest", "pytest_asyncio", "pytest_cov",
    "ruff", "mypy", "black", "bandit", "pip_audit", "locust", "faker",
    "backend", "backend.*",
    "frontend", "frontend.*",
    "agent", "agent.*",
    "launcher", "launcher.*",
    "tools.launcher", "tools.launcher.*",
    "tests", "tests.*",
    "*.tests", "*.tests.*",
    "setuptools", "pip", "wheel", "virtualenv",
    "*.pem", "*.key", "venv", "*.spec",
    "notebook", "jupyter", "ipython",
    "matplotlib", "numpy", "pandas", "scipy",
]

# -------------------------------------------------------------------------
# Data files
# -------------------------------------------------------------------------
def _exists(p: Path) -> bool:
    return p.exists()

datas = []

# Include icon assets
for icon_file in [
    ICON_DIR / "arcade_logo_64.png",
    ICON_DIR / "arcade_logo_128.png",
    ICON_DIR / "arcade_icon.svg",
    ICON_DIR / "arcade_gradient_3px.png",
]:
    if _exists(icon_file):
        datas.append((str(icon_file), "icon"))

# Include the private key for license generation (internal tool only)
private_key = KEYGEN_DIR / "private_key.pem"
if _exists(private_key):
    datas.append((str(private_key), "."))

# Platform-specific icons
if sys.platform == "win32":
    icon_path = ICON_DIR / "arcade_icon.ico"
    icon = str(icon_path) if _exists(icon_path) else None
elif sys.platform == "darwin":
    icon_path = ICON_DIR / "arcade_icon.icns"
    icon = str(icon_path) if _exists(icon_path) else None
else:
    icon = None

# -------------------------------------------------------------------------
# Windows version info (embedded in EXE)
# -------------------------------------------------------------------------
if sys.platform == "win32":
    from PyInstaller.utils.win32 import versioninfo
    vs = versioninfo.VarStruct('Translation', [0x0409, 0x04B0])
    ss = versioninfo.StringTable('040904B0', [
        versioninfo.StringStruct('CompanyName', 'Neurotech Biratnagar'),
        versioninfo.StringStruct('FileDescription', 'Arcade License Key Generator'),
        versioninfo.StringStruct('FileVersion', VERSION),
        versioninfo.StringStruct('InternalName', 'Arcade Keygen'),
        versioninfo.StringStruct('LegalCopyright', 'Copyright (C) 2026 Neurotech Biratnagar'),
        versioninfo.StringStruct('OriginalFilename', 'Arcade Keygen.exe'),
        versioninfo.StringStruct('ProductName', 'Arcade'),
        versioninfo.StringStruct('ProductVersion', VERSION),
    ])
    sfi = versioninfo.StringFileInfo([ss])
    vffi = versioninfo.FixedFileInfo(
        tuple(map(int, VERSION.split('.'))) + (0,),
        tuple(map(int, VERSION.split('.'))) + (0,),
        0x3f, 0, 0x40004, 0x1, 0x0, (0, 0)
    )
    vvi = versioninfo.VSVersionInfo(vffi, [sfi, versioninfo.VarFileInfo([vs])])
    versioninfo_path = KEYGEN_DIR / "file_version_info.txt"
    with open(versioninfo_path, "w", encoding="utf-8") as f:
        f.write(str(vvi))
else:
    versioninfo_path = None

# -------------------------------------------------------------------------
# Analysis
# -------------------------------------------------------------------------
a = Analysis(
    [str(KEYGEN_DIR / "generate_license.py")],
    pathex=[str(KEYGEN_DIR), str(BACKEND)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# -------------------------------------------------------------------------
# PYZ (compressed archive)
# -------------------------------------------------------------------------
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# -------------------------------------------------------------------------
# EXE (onedir)
# -------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Arcade Keygen",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
    version=versioninfo_path,
)

# -------------------------------------------------------------------------
# COLLECT (onedir output) - build directory inside tools/keygen/dist
# -------------------------------------------------------------------------
DIST_PATH = str(KEYGEN_DIR / "dist")
WORK_PATH = str(KEYGEN_DIR / "build")

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="arcade-keygen",
    distpath=DIST_PATH,
    workpath=WORK_PATH,
)
