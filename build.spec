# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Get the project root directory (current working directory)
project_root = Path.cwd()

# Add the project root to Python path
sys.path.insert(0, str(project_root))

# Define the main script
main_script = str(project_root / "localcaption" / "main.py")

# Define data files to include
datas = []

# Include models directory if it exists
models_dir = project_root / "models"
if models_dir.exists():
    datas.append((str(models_dir), "models"))

# Include configuration files
readme_file = project_root / "README.md"
if readme_file.exists():
    datas.append((str(readme_file), "."))

license_file = project_root / "LICENSE"
if license_file.exists():
    datas.append((str(license_file), "."))

# Define hidden imports
hiddenimports = [
    'sherpa_onnx',
    'sounddevice',
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'numpy',
    'psutil',
    'localcaption',
    'localcaption.audio',
    'localcaption.asr',
    'localcaption.ui',
    'localcaption.utils',
]

# Define excluded modules
excludes = [
    'tkinter',
    'matplotlib',
    'scipy',
    'pandas',
    'jupyter',
    'IPython',
    'notebook',
]

# Create the Analysis object
a = Analysis(
    [main_script],
    pathex=[str(project_root)],
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

# Remove duplicate files
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Create the executable (single file)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LocalCaption',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path if you have one
)
