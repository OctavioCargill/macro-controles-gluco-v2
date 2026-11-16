# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

ROOT = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()

block_cipher = None

datas = [
    (str(ROOT / "assets" / "icons" / "glucovil.ico"), "assets/icons"),
    (str(ROOT / "assets" / "icons" / "glucovil.png"), "assets/icons"),
    (str(ROOT / "config" / "app_settings.json"), "config"),
    (str(ROOT / "icon" / "glucovil.ico"), "icon"),
    (str(ROOT / "README.txt"), "."),
    # data y logs NO se empaquetan: la app usa las carpetas que están al lado del .exe, y empaquetar data
    # metería en el ejecutable los reportes e históricos de quien lo genera.
]

# Validación con la Power App: el OCR (RapidOCR) lleva sus modelos y su configuración adentro, y usa onnxruntime.
# Solo se incluye el motor onnxruntime (no torch / paddle / openvino, que no se usan).
_MOTORES_NO_USADOS = ("torch", "paddle", "openvino", "tensorrt", "mnn")
datas += collect_data_files("rapidocr")
binaries_ocr = collect_dynamic_libs("onnxruntime")
hidden_ocr = collect_submodules("rapidocr", filter=lambda nombre: not any(m in nombre for m in _MOTORES_NO_USADOS))
hidden_ocr += collect_submodules("onnxruntime.capi") + ["pypdf", "validacion"]

analysis = Analysis(
    [str(ROOT / "gui" / "app.py")],
    pathex=[str(ROOT)],
    binaries=binaries_ocr,
    datas=datas,
    hiddenimports=[
        "customtkinter",
        "pandas",
        "openpyxl",
        "pyxlsb",
        "xlsxwriter",
        "netting",
        "liberacion",
        "asistente",
        "tkinter",
        "pywin32",
    ] + hidden_ocr,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["torch", "paddle", "openvino", "tensorflow"],
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
    icon=str(ROOT / "assets" / "icons" / "glucovil.ico"),
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
