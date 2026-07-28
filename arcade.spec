# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

# -------------------------------------------------------------------------
# Path setup
# -------------------------------------------------------------------------
ROOT = Path(__file__).parent.resolve()
BACKEND = ROOT / "backend"
FRONTEND_DIST = ROOT / "frontend" / "dist"
ALEMBIC_DIR = ROOT / "alembic"
ALEMBIC_INI = BACKEND / "alembic.ini"
LICENSING_PUBKEY = BACKEND / "licensing" / "public_key.py"

# -------------------------------------------------------------------------
# Version (from pyproject.toml)
# -------------------------------------------------------------------------
try:
    import tomllib
except ImportError:
    import tomli as tomllib

def _get_version() -> str:
    pyproject = ROOT / "pyproject.toml"
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
    "aiosqlite",
    "sqlalchemy.dialects.sqlite",
    "alembic",
    "nacl",
    "argon2",
    "cryptography.hazmat.primitives",
    "pydantic_core._pydantic_core",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "starlette.middleware.cors",
    "customtkinter",
    "PIL._tkinter_finder",
    "machineid",
    "tinytuya",
    "escpos",
]

# Auto-collect heavy packages
for pkg in [
    "sqlalchemy", "alembic", "pydantic", "fastapi", "starlette",
    "uvicorn", "argon2", "cryptography", "nacl", "customtkinter",
]:
    hiddenimports.extend(collect_submodules(pkg))

# Deduplicate
hiddenimports = sorted(set(hiddenimports))

# -------------------------------------------------------------------------
# Excludes
# -------------------------------------------------------------------------
excludes = [
    "pytest", "pytest_asyncio", "pytest_cov",
    "ruff", "mypy", "black", "bandit", "pip_audit", "locust", "faker",
    "tools", "tools.keygen", "tools.keygen.generate_license",
    "backend.tests", "backend.tests.*",
    "*.tests", "*.tests.*",
    "setuptools", "pip", "wheel", "virtualenv",
]

# -------------------------------------------------------------------------
# Data files
# -------------------------------------------------------------------------
def _exists(p: Path) -> bool:
    return p.exists()

datas = []

if _exists(FRONTEND_DIST):
    datas.append((str(FRONTEND_DIST), "frontend/dist"))
else:
    print("WARNING: frontend/dist not found. Run `npm run build` in frontend/ first.")

if _exists(ALEMBIC_DIR):
    datas.append((str(ALEMBIC_DIR), "alembic"))

if _exists(ALEMBIC_INI):
    datas.append((str(ALEMBIC_INI), "alembic.ini"))

if _exists(LICENSING_PUBKEY):
    datas.append((str(LICENSING_PUBKEY), "backend/licensing/public_key.py"))

# Platform-specific icons
if sys.platform == "win32":
    icon_path = ROOT / "assets" / "icon.ico"
    icon = str(icon_path) if _exists(icon_path) else None
elif sys.platform == "darwin":
    icon_path = ROOT / "assets" / "icon.icns"
    icon = str(icon_path) if _exists(icon_path) else None
else:
    icon = None

# -------------------------------------------------------------------------
# Windows version info (embedded in EXE)
# -------------------------------------------------------------------------
if sys.platform == "win32":
    from PyInstaller.utils.win32 import versioninfo
    versioninfo.CreateVersionInfo(
        versioninfo.FixedFileInfo(
            filevers=tuple(map(int, VERSION.split('.'))) + (0,),
            prodvers=tuple(map(int, VERSION.split('.'))) + (0,),
            fileflags=0,
            fileos=0x40004,
            filetype=0x1,
            filesubtype=0x0,
        ),
        [
            versioninfo.StringFileInfo([
                versioninfo.StringTable('040904B0', {
                    'CompanyName': 'Neurotech Biratnagar',
                    'FileDescription': 'Arcade Launcher',
                    'FileVersion': VERSION,
                    'InternalName': 'Arcade Launcher',
                    'LegalCopyright': 'Copyright (C) 2026 Neurotech Biratnagar',
                    'OriginalFilename': 'Arcade Launcher.exe',
                    'ProductName': 'Arcade',
                    'ProductVersion': VERSION,
                })
            ]),
            versioninfo.VarFileInfo([versioninfo.VarStruct('Translation', [0x0409, 0x04B0])])
        ],
        str(ROOT / "file_version_info.txt")
    )

# -------------------------------------------------------------------------
# Analysis
# -------------------------------------------------------------------------
a = Analysis(
    ["launcher.py"],
    pathex=[str(ROOT), str(BACKEND)],
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
    name="Arcade Launcher",
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
    version="file_version_info.txt" if sys.platform == "win32" else None,
)

# -------------------------------------------------------------------------
# COLLECT (onedir output)
# -------------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="arcade",
)
