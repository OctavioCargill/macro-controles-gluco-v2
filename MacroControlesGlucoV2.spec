# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()

block_cipher = None

datas = [
    (str(ROOT / "assets" / "icons" / "placeholder.ico"), "assets/icons"),
    (str(ROOT / "config" / "app_settings.json"), "config"),
    (str(ROOT / "icon" / "placeholder.ico"), "icon"),
    (str(ROOT / "README.txt"), "."),
    (str(ROOT / "logs"), "logs"),
    (str(ROOT / "data"), "data"),
]

analysis = Analysis(
    [str(ROOT / "gui" / "app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "customtkinter",
        "pandas",
        "openpyxl",
        "pyxlsb",
        "tkinter",
        "pywin32",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="MacroControlesGlucoV2.exe",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ROOT / "assets" / "icons" / "placeholder.ico"),
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MacroControlesGlucoV2",
)
