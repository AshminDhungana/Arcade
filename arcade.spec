# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

# -------------------------------------------------------------------------
# Path setup
# -------------------------------------------------------------------------
import sys
ROOT = Path(sys.argv[0]).parent.resolve() if "__file__" not in dir() else Path(__file__).parent.resolve()
BACKEND = ROOT / "backend"
FRONTEND_DIST = ROOT / "frontend" / "dist"
ALEMBIC_DIR = BACKEND / "alembic"
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
    "machineid",
    "tinytuya",
    "escpos",
    "fastapi",
    "fastapi.security",
    "fastapi.middleware.cors",
    "uvicorn",
    "uvicorn.config",
    "uvicorn.main",
    "starlette",
    "starlette.applications",
    "starlette.routing",
    "starlette.middleware",
    "pydantic",
    "pydantic.main",
    "pydantic.fields",
    "pydantic.validators",
    "pydantic.networks",
    "email_validator",
    "passlib",
    "passlib.context",
    "passlib.handlers.argon2",
    "python_jose",
    "python_jose.jwt",
    "python_jose.exceptions",
    "setuptools._vendor.jaraco.text",
    "setuptools._vendor.jaraco",
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
    "*.pem", "*.key", "venv", "*.spec",
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

# NOTE: arcade.config.json is created by SetupWizard on first run.
# Do NOT bundle it — PyInstaller extracts data files with restrictive
# permissions on Windows. The launcher checks for its presence to
# decide between SetupWizard and MainScreen.

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
    vs = versioninfo.VarStruct('Translation', [0x0409, 0x04B0])
    ss = versioninfo.StringTable('040904B0', [
        versioninfo.StringStruct('CompanyName', 'Neurotech Biratnagar'),
        versioninfo.StringStruct('FileDescription', 'Arcade Launcher'),
        versioninfo.StringStruct('FileVersion', VERSION),
        versioninfo.StringStruct('InternalName', 'Arcade Launcher'),
        versioninfo.StringStruct('LegalCopyright', 'Copyright (C) 2026 Neurotech Biratnagar'),
        versioninfo.StringStruct('OriginalFilename', 'Arcade Launcher.exe'),
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
    versioninfo_path = ROOT / "file_version_info.txt"
    with open(versioninfo_path, "w", encoding="utf-8") as f:
        f.write(str(vvi))
else:
    versioninfo_path = None

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
    version=versioninfo_path,
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
