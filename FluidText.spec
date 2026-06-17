# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_all

datas = [('C:\\Users\\muell\\Desktop\\FluidText-src\\execution\\assets', 'assets')]
binaries = []
hiddenimports = ['gui_dashboard', 'gui_overlay', 'transcriber', 'audio_capture', 'injector', 'settings_manager', 'utils', 'generate_logo', 'customtkinter', 'faster_whisper', 'huggingface_hub', 'huggingface_hub.utils', 'huggingface_hub.file_download', 'tqdm', 'tqdm.auto', 'keyboard', 'appdirs', 'pystray', 'PIL', 'PIL._tkinter_finder', 'platform_support', 'platform_support.hotkey_windows', 'platform_support.autostart_windows', 'sounddevice', 'certifi', 'requests', 'urllib3', 'filelock', 'fsspec', 'packaging', 'packaging.version', 'packaging.requirements']
datas += collect_data_files('certifi')
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('faster_whisper')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('huggingface_hub')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pystray')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['execution\\main.py'],
    pathex=['C:\\Users\\muell\\Desktop\\FluidText-src\\execution'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='FluidText',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\muell\\Desktop\\FluidText-src\\execution\\assets\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='FluidText',
)
