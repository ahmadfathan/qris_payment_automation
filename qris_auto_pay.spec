# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app3.py'],
    pathex=[],
    binaries=[('embed/adb/windows/adb.exe', 'embed/adb/windows'), ('embed/adb/windows/AdbWinApi.dll', 'embed/adb/windows'), ('embed/adb/windows/AdbWinUsbApi.dll', 'embed/adb/windows')],
    datas=[('.env', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='qris_auto_pay',
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
)
