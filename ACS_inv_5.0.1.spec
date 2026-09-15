# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main4.py'],
    pathex=[],
    binaries=[],
    datas=[('Asset', 'Asset')],
    hiddenimports=['Dash', 'Custdash'],
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
    name='ACS_inv_5.0.1',
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
    icon=['/Users/gourab.palui/Desktop/Projects/Asset/checklist.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ACS_inv_5.0.1',
)
app = BUNDLE(
    coll,
    name='ACS_inv_5.0.1.app',
    icon='/Users/gourab.palui/Desktop/Projects/Asset/checklist.icns',
    bundle_identifier=None,
)
