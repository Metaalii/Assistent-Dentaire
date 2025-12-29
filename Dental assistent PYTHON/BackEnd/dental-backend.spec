# dental-backend.spec
# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import copy_metadata
import sys
import os

block_cipher = None

# 1. Collect metadata for packages that use 'importlib.metadata'
#    This prevents "Package not found" errors at runtime.
datas = []
datas += copy_metadata('tqdm')
datas += copy_metadata('regex')
datas += copy_metadata('requests')
datas += copy_metadata('packaging')
datas += copy_metadata('filelock')
datas += copy_metadata('numpy')
datas += copy_metadata('tokenizers')

# 2. Add Faster-Whisper and Llama-cpp binaries
#    Note: These libraries often load DLLs/dylibs dynamically.
#    We ensure the entire package directory is included.
import faster_whisper
import llama_cpp

faster_whisper_path = os.path.dirname(faster_whisper.__file__)
llama_cpp_path = os.path.dirname(llama_cpp.__file__)

datas += [(faster_whisper_path, 'faster_whisper')]
datas += [(llama_cpp_path, 'llama_cpp')]

# 3. Main Analysis
a = Analysis(
    ['app/main.py'],  # Your entry point
    pathex=[],
    binaries=[],
    datas=datas,
    # Hidden imports are critical for these AI libraries
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'faster_whisper',
        'llama_cpp',
        'sklearn.utils._typedefs', # Common missing dependency for some AI libs
        'sklearn.neighbors._partition_nodes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'PyQt5', 'PySide2'], # Exclude GUI libs to save space
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='dental-backend', # This is the executable name
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Keep True for debugging MVP (False checks VRAM in bg)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='dental-backend',
)