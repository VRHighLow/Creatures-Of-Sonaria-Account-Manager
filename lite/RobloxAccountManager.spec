# -*- mode: python ; coding: utf-8 -*-

import os
spec_root = os.path.abspath(SPECPATH)

block_cipher = None

a = Analysis(
    ['main.py', 'gui.py', 'account_manager.py', 'game_launcher.py'],
    pathex=[spec_root],
    binaries=[],
    datas=[('RobloxAccountManager.manifest', '.')],
    hiddenimports=[
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.common',
        'selenium.webdriver.chrome',
        'selenium.webdriver.chrome.service',
        'webdriver_manager',
        'webdriver_manager.chrome',
        'psutil',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['win32api', 'win32con', 'window_controller'],
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
    name='CosManagerLite',
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
