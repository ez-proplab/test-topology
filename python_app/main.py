#!/usr/bin/env python3
"""
Topology Optimization for CAD Models
=====================================

A Python executable for performing SIMP-based topology optimization
on arbitrary CAD geometries with automatic hollowness enforcement.

Usage:
    python main.py                  # Launch GUI
    python main.py --cli            # Command-line mode
    python main.py --help           # Show help

Author: Topology Optimization Tool
License: MIT
"""

import sys
import os
import argparse
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def run_gui():
    """Launch the GUI application."""
    # Must set QT_API before importing pyvista
    os.environ['QT_API'] = 'pyqt5'
    
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    
    # Enable high DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("Topology Optimization")
    app.setOrganizationName("TopOpt")
    
    from src.gui.main_window import MainWindow
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


def run_cli(args):
    """Run optimization in command-line mode."""
    from src.core.mesh_utils import MeshHandler, create_test_geometry
    from src.core.optimizer import TopologyOptimizer
    
    # Load or create geometry
    if args.input:
        handler = MeshHandler()
        info = handler.load_mesh(args.input)
        logger.info(f"Loaded mesh: {info}")
    else:
        handler = create_test_geometry(args.test_shape)
        logger.info(f"Created test geometry: {args.test_shape}")
    
    # Voxelize
    handler.voxelize(num_voxels=args.resolution)
    handler.enforce_hollowness(
        min_wall_thickness=args.wall_thickness,
        target_hollow_fraction=args.hollow_fraction
    )
    
    logger.info(handler.get_mesh_summary())
    
    # Setup optimizer
    params = {
        'volfrac': args.volfrac,
        'penal': args.penal,
        'rmin': args.filter_radius,
        'max_iter': args.max_iter,
        'bc_type': args.bc_type,
        'min_wall_thickness': args.wall_thickness,
        'hollow_fraction': args.hollow_fraction,
    }
    
    optimizer = TopologyOptimizer(handler, params)
    
    # Progress callback
    def progress(iteration, density, compliance, volume, change):
        bar_len = 30
        filled = int(bar_len * iteration / args.max_iter)
        bar = '█' * filled + '░' * (bar_len - filled)
        print(f"\r  [{bar}] {iteration}/{args.max_iter} | "
              f"C={compliance:.2e} | V={volume:.3f} | Δ={change:.4f}", end='', flush=True)
    
    print(f"\n{'='*60}")
    print(f"  Topology Optimization - SIMP Method")
    print(f"{'='*60}")
    print(f"  Grid: {handler.grid_shape}")
    print(f"  Design voxels: {handler.design_mask.sum():,}")
    print(f"  Volume fraction: {args.volfrac}")
    print(f"  Penalization: {args.penal}")
    print(f"  Filter radius: {args.filter_radius}")
    print(f"  BC type: {args.bc_type}")
    print(f"{'='*60}\n")
    
    # Run
    results = optimizer.optimize(callback=progress)
    
    print(f"\n\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    print(f"  Iterations: {results['iterations']}")
    print(f"  Final compliance: {results['final_compliance']:.4e}")
    print(f"  Final volume: {results['final_volume']:.3f}")
    print(f"  Total time: {results['total_time']:.1f}s")
    print(f"  Converged: {results['converged']}")
    print(f"{'='*60}\n")
    
    # Export
    output = args.output or "optimized_result.stl"
    handler.export_result(results['density'], threshold=args.threshold, filepath=output)
    print(f"  Result exported to: {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Topology Optimization for CAD Models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          Launch GUI
  python main.py --input model.stl        Load and optimize STL file
  python main.py --test beam --bc cantilever   Optimize test beam
  python main.py --input part.obj --volfrac 0.3 --penal 3.0
        """
    )
    
    parser.add_argument('--cli', action='store_true',
                       help='Run in command-line mode (no GUI)')
    parser.add_argument('--input', '-i', type=str, default=None,
                       help='Input CAD file (STL, OBJ, etc.)')
    parser.add_argument('--output', '-o', type=str, default=None,
                       help='Output file path (default: optimized_result.stl)')
    parser.add_argument('--test', dest='test_shape', type=str, default='beam',
                       choices=['beam', 'l_bracket', 'plate', 'cylinder'],
                       help='Test geometry shape (default: beam)')
    
    # Optimization parameters
    parser.add_argument('--volfrac', type=float, default=0.4,
                       help='Volume fraction constraint (default: 0.4)')
    parser.add_argument('--penal', type=float, default=3.0,
                       help='SIMP penalization power (default: 3.0)')
    parser.add_argument('--filter-radius', '--rmin', type=float, default=2.0,
                       help='Sensitivity filter radius in voxels (default: 2.0)')
    parser.add_argument('--max-iter', type=int, default=50,
                       help='Maximum optimization iterations (default: 50)')
    parser.add_argument('--resolution', type=int, default=30,
                       help='Voxel resolution (voxels along longest axis)')
    parser.add_argument('--wall-thickness', type=int, default=2,
                       help='Minimum wall thickness in voxels (default: 2)')
    parser.add_argument('--hollow-fraction', type=float, default=0.6,
                       help='Fraction of interior to hollow out (default: 0.6)')
    parser.add_argument('--threshold', type=float, default=0.5,
                       help='Density threshold for export (default: 0.5)')
    parser.add_argument('--bc-type', type=str, default='cantilever',
                       choices=['cantilever', 'bridge', '3point_bend', 'custom'],
                       help='Boundary condition type (default: cantilever)')
    
    args = parser.parse_args()
    
    if args.cli or args.input:
        run_cli(args)
    else:
        run_gui()


if __name__ == '__main__':
    main()
