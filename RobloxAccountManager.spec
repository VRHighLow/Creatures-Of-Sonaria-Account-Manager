# -*- mode: python ; coding: utf-8 -*-

import os
spec_root = os.path.abspath(SPECPATH)
dist_dir = os.path.join(spec_root, 'dist', 'lite')

block_cipher = None

a = Analysis(
    ['main_lite.py', 'gui_lite.py', 'account_manager.py', 'game_launcher.py', 'window_controller.py'],
    pathex=[spec_root],
    binaries=[],
    datas=[('RobloxBotCOS.manifest', '.')],
    hiddenimports=[
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.common',
        'selenium.webdriver.chrome',
        'selenium.webdriver.chrome.service',
        'webdriver_manager',
        'webdriver_manager.chrome',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RobloxAccountManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Hide console window (looks more professional)
    target_arch='x64',  # Explicitly target 64-bit
    disable_windowed_traceback=False,
    argv_emulation=False,
    codesign_identity=None,
    entitlements_file=None,
    win_private_assemblies=False,
)
