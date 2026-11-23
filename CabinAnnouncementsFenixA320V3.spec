# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = ['imageio_ffmpeg']
datas += collect_data_files('certifi')
hiddenimports += collect_submodules('imageio_ffmpeg')
tmp_ret = collect_all('num2words')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('edge_tts')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('SimConnect')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
datas += [('avatar_cleardeck.png', '.')]
datas += [('mobiflight_module/layout.json', 'mobiflight_module')]
datas += [('mobiflight_module/manifest.json', 'mobiflight_module')]
datas += [('mobiflight_module/ContentInfo/mobiflight-event-module/Thumbnail.jpg', 'mobiflight_module/ContentInfo/mobiflight-event-module')]
datas += [('mobiflight_module/modules/MobiFlightWasmModule.wasm', 'mobiflight_module/modules')]


a = Analysis(
    ['cabin_announcements_fenix_a320_v3.py'],
    pathex=[],
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
    a.binaries,
    a.datas,
    [],
    name='CabinAnnouncementsFenixA320V3',
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
    icon='cleardeck_icon.ico',
)

