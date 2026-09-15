# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('Asset', 'Asset'), ('Dash.py', '.'), ('Custdash.py', '.')],
    hiddenimports=['openpyxl'],
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
    name='ACS_inv_4.3.8',
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
    name='ACS_inv_4.3.8',
)
app = BUNDLE(
    coll,
    name='ACS_inv_4.3.8.app',
    icon='/Users/gourab.palui/Desktop/Projects/Asset/checklist.icns',
    bundle_identifier='com.aptiv.inventory.acs',
    info_plist={
        'CFBundleShortVersionString': '4.3.8',
        'CFBundleVersion': '4.3.8',
    },
)
