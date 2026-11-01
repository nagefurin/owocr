# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files('rapidocr', include_py_files=False)
datas += collect_data_files('unidic_lite', include_py_files=False)
datas += collect_data_files('manga_ocr', include_py_files=True)
datas += collect_data_files('manga_ocr_cpt', include_py_files=True)
datas += [( 'third_party_licenses/manga-ocr-CPT-LICENSE', 'third_party_licenses' )]
datas += [( 'third_party_licenses/manga-ocr-CPT-NOTICE.md', 'third_party_licenses' )]
datas += [( 'owocr/data', 'owocr/data' )]
datas += [( 'owocr_config.ini', '.' )]
datas += [( 'ndlocr_lite/config', 'ndlocr_lite/config' )]
hiddenimports = collect_submodules('pynputfix')
hiddenimports += collect_submodules('manga_ocr_cpt')
hiddenimports += collect_submodules('pystrayfix')
hiddenimports += collect_submodules('desktop_notifier')
hiddenimports += collect_submodules('PIL')

a = Analysis(
    ['owocr/__main__.py'],
    pathex=[],
    binaries=[],
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
    name='owocr',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory='data',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=False,
    upx_exclude=[],
    name='owocr',
)
