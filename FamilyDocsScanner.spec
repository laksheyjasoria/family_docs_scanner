# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

datas = [
    ('ui', 'ui'),
    ('core', 'core'),
]

binaries = [
    ('libs/ScannerEngine.dll', '.'),
]

hiddenimports = [
    'customtkinter',
    'PIL',
    'PIL._tkinter_finder',
    'cv2',
    'numpy',
    'numpy.core',
    'numpy.core._multiarray_tests',
    'numpy.core._multiarray_umath',
    'numpy.linalg',
    'numpy.linalg._umath_linalg'
]

tmp_ret = collect_all('numpy')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

tmp_ret = collect_all('cv2')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'numpy.distutils',
        'numpy.f2py',
        'numpy.tests',
        'matplotlib',
        'tensorflow',
        'torch',
        'scipy',
        'pandas'
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FamilyDocsScanner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon='assets/app_icon.ico'
)