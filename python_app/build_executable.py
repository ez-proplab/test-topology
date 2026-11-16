#!/usr/bin/env python3
"""
Build script for creating standalone executable.
Uses PyInstaller to bundle the application.
"""

import subprocess
import sys
import os
import platform


def build_executable():
    """Build the standalone executable using PyInstaller."""
    
    print("=" * 60)
    print("  Building Topology Optimization Executable")
    print("=" * 60)
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("\nPyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Determine platform-specific options
    system = platform.system()
    
    if system == "Windows":
        icon_path = "assets/icon.ico"
        name = "TopologyOptimizer"
    elif system == "Darwin":
        icon_path = "assets/icon.icns"
        name = "TopologyOptimizer"
    else:
        icon_path = "assets/icon.png"
        name = "TopologyOptimizer"
    
    # PyInstaller arguments
    args = [
        sys.executable, "-m", "PyInstaller",
        "--name", name,
        "--onefile",           # Single executable
        "--windowed",          # No console window (GUI app)
        "--noconfirm",         # Overwrite without asking
        "--clean",             # Clean build
        "--collect-all", "pyvista",
        "--collect-all", "trimesh",
        "--hidden-import", "scipy.sparse.csgraph._shortest_path",
        "--hidden-import", "scipy.sparse.csgraph._traversal",
        "--hidden-import", "scipy.spatial",
        "--hidden-import", "scipy.spatial.transform",
        "--hidden-import", "vtk",
        "--hidden-import", "vtkmodules.all",
        "--hidden-import", "pyvistaqt",
        "--hidden-import", "PyQt5",
        "--hidden-import", "PyQt5.QtWidgets",
        "--hidden-import", "PyQt5.QtCore",
        "--hidden-import", "PyQt5.QtGui",
        "--hidden-import", "trimesh",
        "--hidden-import", "trimesh.exchange",
        "--hidden-import", "trimesh.voxel",
        "--hidden-import", "trimesh.boolean",
        "--hidden-import", "trimesh.creation",
        "--hidden-import", "trimesh.repair",
        "--hidden-import", "numpy",
        "--hidden-import", "scipy",
        "main.py"
    ]
    
    # Add icon if exists
    if os.path.exists(icon_path):
        args.extend(["--icon", icon_path])
    
    print(f"\nPlatform: {system}")
    print(f"Output: dist/{name}")
    print(f"\nRunning PyInstaller...\n")
    
    try:
        result = subprocess.run(args, check=True)
        print(f"\n{'='*60}")
        print(f"  BUILD SUCCESSFUL!")
        print(f"  Executable: dist/{name}")
        if system == "Windows":
            print(f"  Full path: {os.path.abspath(f'dist/{name}.exe')}")
        print(f"{'='*60}")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error code: {e.returncode}")
        sys.exit(1)
    except FileNotFoundError:
        print("\nError: PyInstaller not found. Install with: pip install pyinstaller")
        sys.exit(1)


def create_simple_spec():
    """Create a PyInstaller spec file for advanced configuration."""
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Topology Optimization.
Build with: pyinstaller TopologyOptimizer.spec
"""

import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all pyvista data
datas_pyvista, binaries_pyvista, hiddenimports_pyvista = collect_all('pyvista')
datas_trimesh, binaries_trimesh, hiddenimports_trimesh = collect_all('trimesh')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries_pyvista + binaries_trimesh,
    datas=datas_pyvista + datas_trimesh,
    hiddenimports=[
        *hiddenimports_pyvista,
        *hiddenimports_trimesh,
        'scipy.sparse.csgraph._shortest_path',
        'scipy.sparse.csgraph._traversal',
        'scipy.spatial',
        'pyvistaqt',
        'PyQt5',
        'PyQt5.QtWidgets',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.sip',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'pandas', 'PIL', 'IPython'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TopologyOptimizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
    
    with open('TopologyOptimizer.spec', 'w') as f:
        f.write(spec_content)
    
    print("Created TopologyOptimizer.spec")
    print("Build with: pyinstaller TopologyOptimizer.spec")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--spec':
        create_simple_spec()
    else:
        build_executable()
