# -*- mode: python ; coding: utf-8 -*-
import os
import customtkinter

# Get CTK path for themes
ctk_path = os.path.dirname(customtkinter.__file__)

block_cipher = None

a = Analysis(
    ['main4.py'],
    pathex=[],
    binaries=[],
    datas=[
        (ctk_path, 'customtkinter/'),
        ('Asset', 'Asset'),
        ('Dash.py', '.'),
        ('Custdash.py', '.')
    ],
    hiddenimports=['pandas', 'openpyxl', 'PIL', 'Dash', 'Custdash'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AptivInventory',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='AptivInventory',
)

app = BUNDLE(
    coll,
    name='Aptiv Inventory.app',
    icon=None,
    bundle_identifier='com.aptiv.inventory.manager',
)