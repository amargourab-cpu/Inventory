# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['MAIN4.py'],
    pathex=[],
    binaries=[],
    datas=[('Asset/Launchpage.jpg', '.'), ('Dash.py', '.'), ('Custdash.py', '.')],
    hiddenimports=['customtkinter', 'PIL._tkinter_finder', 'pandas'],
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
    [],
    exclude_binaries=True,
    name='AptivInventorySystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AptivInventorySystem',
)
app = BUNDLE(
    coll,
    name='AptivInventorySystem.app',
    icon=None,
    bundle_identifier=None,
)
