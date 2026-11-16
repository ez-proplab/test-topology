"""
Main GUI window for Topology Optimization application.
Uses PyQt5 with pyvista for 3D visualization.
"""

import sys
import os
import numpy as np
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QSlider, QSpinBox, QDoubleSpinBox,
    QComboBox, QGroupBox, QFileDialog, QTextEdit, QProgressBar,
    QMessageBox, QStatusBar, QTabWidget, QCheckBox, QFormLayout,
    QApplication, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon

import pyvista as pv
from pyvistaqt import QtInteractor

from ..core.mesh_utils import MeshHandler, create_test_geometry
from ..core.optimizer import TopologyOptimizer

import logging
logger = logging.getLogger(__name__)


class OptimizationWorker(QThread):
    """Worker thread for running optimization without blocking GUI."""
    
    progress = pyqtSignal(int, object, float, float, float)  # iter, density, compliance, volume, change
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, optimizer: TopologyOptimizer):
        super().__init__()
        self.optimizer = optimizer
    
    def run(self):
        try:
            results = self.optimizer.optimize(callback=self._callback)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))
    
    def _callback(self, iteration, density, compliance, volume, change):
        self.progress.emit(iteration, density.copy(), compliance, volume, change)
    
    def stop(self):
        self.optimizer.stop()


class Viewport3D(QtInteractor):
    """3D viewport using pyvista."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_background('#1a1a2e')
        self.add_axes()
        self.reset_camera()
    
    def update_density_visualization(self, density: np.ndarray, threshold: float = 0.3,
                                      mesh_handler: MeshHandler = None):
        """Update the 3D visualization with density data."""
        self.clear()
        
        if density is None:
            return
        
        # Create binary mask
        mask = density > threshold
        
        if not np.any(mask):
            return
        
        # Convert to mesh
        if mesh_handler is not None:
            try:
                result_mesh = mesh_handler._voxels_to_mesh(mask)
                if result_mesh is not None and len(result_mesh.faces) > 0:
                    self.add_mesh(result_mesh, color='lightblue', opacity=0.9,
                                 show_edges=False, smooth_shading=True)
                else:
                    self._add_voxel_cloud(density, threshold, mesh_handler)
            except Exception:
                self._add_voxel_cloud(density, threshold, mesh_handler)
        else:
            self._add_voxel_cloud(density, threshold, mesh_handler)
        
        self.reset_camera()
    
    def _add_voxel_cloud(self, density, threshold, mesh_handler):
        """Fallback: add as point cloud with color mapping."""
        nx, ny, nz = density.shape
        x, y, z = np.meshgrid(
            np.arange(nx), np.arange(ny), np.arange(nz), indexing='ij'
        )
        
        mask = density > threshold
        points = np.column_stack([
            x[mask].ravel(), y[mask].ravel(), z[mask].ravel()
        ])
        values = density[mask].ravel()
        
        if len(points) > 0:
            cloud = pv.PolyData(points)
            cloud['density'] = values
            self.add_mesh(cloud, scalars='density', cmap='coolwarm',
                         point_size=3, render_points_as_spheres=True)
    
    def show_mesh(self, mesh_handler: MeshHandler):
        """Display the input mesh."""
        self.clear()
        if mesh_handler.mesh is not None:
            self.add_mesh(mesh_handler.mesh, color='gray', opacity=0.5,
                         show_edges=True)
            self.reset_camera()
    
    def show_voxels(self, mesh_handler: MeshHandler):
        """Display the voxelized geometry."""
        self.clear()
        if mesh_handler.voxel_grid is not None:
            self._add_voxel_cloud(
                mesh_handler.voxel_grid.astype(float), 0.5, mesh_handler
            )
            self.reset_camera()


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Topology Optimization for CAD Models")
        self.setMinimumSize(1200, 800)
        
        # State
        self.mesh_handler = MeshHandler()
        self.optimizer = None
        self.worker = None
        self.current_density = None
        self.is_optimizing = False
        
        # Setup UI
        self._setup_ui()
        self._create_menus()
        self._setup_statusbar()
        
        # Apply dark theme
        self._apply_stylesheet()
    
    def _setup_ui(self):
        """Setup the main UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Splitter for left panel and viewport
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - controls
        left_panel = self._create_control_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - 3D viewport + info
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 3D Viewport
        self.viewport = Viewport3D()
        right_layout.addWidget(self.viewport, stretch=3)
        
        # Info panel below viewport
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(150)
        self.info_text.setFont(QFont("Consolas", 9))
        right_layout.addWidget(self.info_text, stretch=1)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 900])
    
    def _create_control_panel(self) -> QWidget:
        """Create the left control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("Topology Optimization")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # File group
        file_group = QGroupBox("Input Geometry")
        file_layout = QVBoxLayout(file_group)
        
        self.btn_load = QPushButton("📁 Load CAD Model")
        self.btn_load.clicked.connect(self._load_file)
        file_layout.addWidget(self.btn_load)
        
        self.btn_test = QPushButton("🧪 Use Test Geometry")
        self.btn_test.clicked.connect(self._use_test_geometry)
        file_layout.addWidget(self.btn_test)
        
        self.lbl_mesh_info = QLabel("No mesh loaded")
        self.lbl_mesh_info.setWordWrap(True)
        self.lbl_mesh_info.setStyleSheet("color: #888; font-size: 10px;")
        file_layout.addWidget(self.lbl_mesh_info)
        
        layout.addWidget(file_group)
        
        # Parameters group
        param_group = QGroupBox("Optimization Parameters")
        param_layout = QFormLayout(param_group)
        
        # Volume fraction
        self.spin_volfrac = QDoubleSpinBox()
        self.spin_volfrac.setRange(0.1, 0.9)
        self.spin_volfrac.setValue(0.4)
        self.spin_volfrac.setSingleStep(0.05)
        self.spin_volfrac.setDecimals(2)
        param_layout.addRow("Volume Fraction:", self.spin_volfrac)
        
        # Penalization
        self.spin_penal = QDoubleSpinBox()
        self.spin_penal.setRange(1.0, 5.0)
        self.spin_penal.setValue(3.0)
        self.spin_penal.setSingleStep(0.5)
        self.spin_penal.setDecimals(1)
        param_layout.addRow("Penalization (p):", self.spin_penal)
        
        # Filter radius
        self.spin_rmin = QDoubleSpinBox()
        self.spin_rmin.setRange(1.0, 10.0)
        self.spin_rmin.setValue(2.0)
        self.spin_rmin.setSingleStep(0.5)
        param_layout.addRow("Filter Radius:", self.spin_rmin)
        
        # Max iterations
        self.spin_maxiter = QSpinBox()
        self.spin_maxiter.setRange(10, 200)
        self.spin_maxiter.setValue(50)
        self.spin_maxiter.setSingleStep(10)
        param_layout.addRow("Max Iterations:", self.spin_maxiter)
        
        # Voxel resolution
        self.spin_resolution = QSpinBox()
        self.spin_resolution.setRange(10, 80)
        self.spin_resolution.setValue(30)
        self.spin_resolution.setSingleStep(5)
        param_layout.addRow("Voxel Resolution:", self.spin_resolution)
        
        # Min wall thickness
        self.spin_wall = QSpinBox()
        self.spin_wall.setRange(1, 5)
        self.spin_wall.setValue(2)
        param_layout.addRow("Wall Thickness:", self.spin_wall)
        
        # Boundary condition
        self.combo_bc = QComboBox()
        self.combo_bc.addItems(["Cantilever", "Bridge", "3-Point Bend", "Custom"])
        param_layout.addRow("Boundary Condition:", self.combo_bc)
        
        layout.addWidget(param_group)
        
        # Display group
        display_group = QGroupBox("Display")
        display_layout = QFormLayout(display_group)
        
        self.slider_threshold = QSlider(Qt.Horizontal)
        self.slider_threshold.setRange(1, 90)
        self.slider_threshold.setValue(30)
        self.slider_threshold.valueChanged.connect(self._update_display)
        display_layout.addRow("Density Threshold:", self.slider_threshold)
        
        self.lbl_threshold = QLabel("0.30")
        display_layout.addRow("", self.lbl_threshold)
        
        layout.addWidget(display_group)
        
        # Action buttons
        action_group = QGroupBox("Actions")
        action_layout = QVBoxLayout(action_group)
        
        self.btn_voxelize = QPushButton("🔲 Voxelize Geometry")
        self.btn_voxelize.clicked.connect(self._voxelize)
        action_layout.addWidget(self.btn_voxelize)
        
        self.btn_optimize = QPushButton("▶ Run Optimization")
        self.btn_optimize.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 8px;")
        self.btn_optimize.clicked.connect(self._run_optimization)
        action_layout.addWidget(self.btn_optimize)
        
        self.btn_stop = QPushButton("■ Stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_optimization)
        action_layout.addWidget(self.btn_stop)
        
        self.btn_export = QPushButton("💾 Export Result (STL)")
        self.btn_export.clicked.connect(self._export_result)
        self.btn_export.setEnabled(False)
        action_layout.addWidget(self.btn_export)
        
        layout.addWidget(action_group)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("color: #4ade80;")
        layout.addWidget(self.lbl_status)
        
        layout.addStretch()
        
        return panel
    
    def _create_menus(self):
        """Create menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        file_menu.addAction("&Open CAD Model...", self._load_file, "Ctrl+O")
        file_menu.addAction("&Export Result...", self._export_result, "Ctrl+E")
        file_menu.addSeparator()
        file_menu.addAction("E&xit", self.close, "Ctrl+Q")
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("&About", self._show_about)
        help_menu.addAction("&Algorithm Info", self._show_algorithm_info)
    
    def _setup_statusbar(self):
        """Setup status bar."""
        self.statusBar().showMessage("Ready - Load a CAD model to begin")
    
    def _apply_stylesheet(self):
        """Apply dark theme stylesheet."""
        self.setStyleSheet("""
            QMainWindow { background-color: #0f0f1a; }
            QWidget { 
                background-color: #1a1a2e; 
                color: #e0e0e0; 
                font-family: 'Segoe UI', sans-serif;
            }
            QGroupBox { 
                border: 1px solid #333; 
                border-radius: 5px; 
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px;
                color: #60a5fa;
            }
            QPushButton {
                background-color: #2d2d44;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 6px 12px;
                color: #e0e0e0;
            }
            QPushButton:hover { background-color: #3d3d5c; border-color: #60a5fa; }
            QPushButton:pressed { background-color: #1d1d34; }
            QPushButton:disabled { color: #666; background-color: #1a1a2e; }
            QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #2d2d44;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 3px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #444;
                height: 6px;
                background: #2d2d44;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #60a5fa;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QProgressBar {
                border: 1px solid #444;
                border-radius: 3px;
                text-align: center;
                background-color: #2d2d44;
            }
            QProgressBar::chunk {
                background-color: #2563eb;
                border-radius: 2px;
            }
            QTextEdit {
                background-color: #0f0f1a;
                border: 1px solid #333;
                border-radius: 3px;
            }
            QStatusBar { background-color: #0f0f1a; color: #888; }
            QMenuBar { background-color: #1a1a2e; color: #e0e0e0; }
            QMenuBar::item:selected { background-color: #2d2d44; }
            QMenu { background-color: #1a1a2e; border: 1px solid #333; }
            QMenu::item:selected { background-color: #2563eb; }
        """)
    
    def _load_file(self):
        """Load a CAD model from file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open CAD Model", "",
            "CAD Files (*.stl *.obj *.off *.ply *.3mf);;All Files (*)"
        )
        
        if not filepath:
            return
        
        try:
            info = self.mesh_handler.load_mesh(filepath)
            self._update_mesh_info(info)
            self.viewport.show_mesh(self.mesh_handler)
            self.log(f"Loaded: {os.path.basename(filepath)}")
            self.statusBar().showMessage(f"Loaded: {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{e}")
    
    def _use_test_geometry(self):
        """Create a test geometry."""
        items = ["Beam (Cantilever)", "L-Bracket", "Plate with Hole", "Hollow Cylinder"]
        
        from PyQt5.QtWidgets import QInputDialog
        item, ok = QInputDialog.getItem(
            self, "Test Geometry", "Select geometry:", items, 0, False
        )
        
        if not ok:
            return
        
        shape_map = {
            "Beam (Cantilever)": "beam",
            "L-Bracket": "l_bracket",
            "Plate with Hole": "plate",
            "Hollow Cylinder": "cylinder",
        }
        
        try:
            self.mesh_handler = create_test_geometry(shape_map[item])
            info = {
                'vertices': len(self.mesh_handler.mesh.vertices),
                'faces': len(self.mesh_handler.mesh.faces),
                'is_watertight': True,
                'bounds': self.mesh_handler.mesh.bounds.tolist(),
                'extents': self.mesh_handler.mesh.extents.tolist(),
            }
            self._update_mesh_info(info)
            self.viewport.show_mesh(self.mesh_handler)
            self.log(f"Created test geometry: {item}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create geometry:\n{e}")
    
    def _update_mesh_info(self, info: dict):
        """Update mesh info display."""
        text = f"Vertices: {info['vertices']:,}\n"
        text += f"Faces: {info['faces']:,}\n"
        text += f"Extents: {info['extents'][0]:.1f} × {info['extents'][1]:.1f} × {info['extents'][2]:.1f}\n"
        text += f"Watertight: {'Yes' if info.get('is_watertight') else 'No'}"
        self.lbl_mesh_info.setText(text)
    
    def _voxelize(self):
        """Voxelize the current mesh."""
        if self.mesh_handler.mesh is None:
            QMessageBox.warning(self, "Warning", "Please load a mesh first.")
            return
        
        try:
            resolution = self.spin_resolution.value()
            self.mesh_handler.voxelize(num_voxels=resolution)
            
            # Enforce hollowness
            wall_thickness = self.spin_wall.value()
            self.mesh_handler.enforce_hollowness(
                min_wall_thickness=wall_thickness,
                target_hollow_fraction=0.6
            )
            
            self.viewport.show_voxels(self.mesh_handler)
            self.log(self.mesh_handler.get_mesh_summary())
            self.statusBar().showMessage(
                f"Voxelized: {self.mesh_handler.grid_shape}, "
                f"{np.sum(self.mesh_handler.design_mask)} design voxels"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Voxelization failed:\n{e}")
    
    def _run_optimization(self):
        """Start the optimization."""
        if self.mesh_handler.voxel_grid is None:
            # Auto-voxelize
            self._voxelize()
            if self.mesh_handler.voxel_grid is None:
                return
        
        # Create optimizer
        params = {
            'volfrac': self.spin_volfrac.value(),
            'penal': self.spin_penal.value(),
            'rmin': self.spin_rmin.value(),
            'max_iter': self.spin_maxiter.value(),
            'bc_type': self.combo_bc.currentText().lower().replace('-', '_').replace(' ', '_'),
            'min_wall_thickness': self.spin_wall.value(),
            'hollow_fraction': 0.6,
        }
        
        # Map combo box text to bc_type
        bc_map = {
            "cantilever": "cantilever",
            "bridge": "bridge",
            "3_point_bend": "3point_bend",
            "custom": "custom",
        }
        params['bc_type'] = bc_map.get(
            self.combo_bc.currentText().lower().replace('-', '_').replace(' ', '_'),
            "cantilever"
        )
        
        self.optimizer = TopologyOptimizer(self.mesh_handler, params)
        
        # Setup worker
        self.worker = OptimizationWorker(self.optimizer)
        self.worker.progress.connect(self._on_iteration)
        self.worker.finished.connect(self._on_complete)
        self.worker.error.connect(self._on_error)
        
        # Update UI
        self.is_optimizing = True
        self.btn_optimize.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_voxelize.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(params['max_iter'])
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Optimizing...")
        self.lbl_status.setStyleSheet("color: #fbbf24;")
        
        # Start
        self.worker.start()
        self.log(f"Starting optimization: {params}")
    
    def _stop_optimization(self):
        """Stop the optimization."""
        if self.worker:
            self.worker.stop()
            self.lbl_status.setText("Stopping...")
    
    def _on_iteration(self, iteration, density, compliance, volume, change):
        """Handle iteration update."""
        self.current_density = density
        self.progress_bar.setValue(iteration)
        self.lbl_status.setText(
            f"Iter {iteration}: C={compliance:.2e}, V={volume:.3f}"
        )
        
        # Update visualization every few iterations
        if iteration % 3 == 0 or iteration == 1:
            threshold = self.slider_threshold.value() / 100.0
            self.viewport.update_density_visualization(
                density, threshold, self.mesh_handler
            )
        
        # Update info
        self.info_text.setPlainText(
            f"Iteration: {iteration}\n"
            f"Compliance: {compliance:.4e}\n"
            f"Volume: {volume:.3f}\n"
            f"Change: {change:.4f}"
        )
    
    def _on_complete(self, results):
        """Handle optimization complete."""
        self.is_optimizing = False
        self.btn_optimize.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_voxelize.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.lbl_status.setText("Complete!")
        self.lbl_status.setStyleSheet("color: #4ade80;")
        
        self.current_density = results['density']
        
        # Final visualization
        threshold = self.slider_threshold.value() / 100.0
        self.viewport.update_density_visualization(
            self.current_density, threshold, self.mesh_handler
        )
        
        # Log results
        self.log(
            f"\n{'='*50}\n"
            f"OPTIMIZATION COMPLETE\n"
            f"{'='*50}\n"
            f"Iterations: {results['iterations']}\n"
            f"Final Compliance: {results['final_compliance']:.4e}\n"
            f"Final Volume: {results['final_volume']:.3f}\n"
            f"Total Time: {results['total_time']:.1f}s\n"
            f"Converged: {results['converged']}\n"
            f"{'='*50}"
        )
        
        self.statusBar().showMessage(
            f"Optimization complete: {results['iterations']} iterations, "
            f"{results['total_time']:.1f}s"
        )
    
    def _on_error(self, error_msg):
        """Handle optimization error."""
        self.is_optimizing = False
        self.btn_optimize.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_voxelize.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.lbl_status.setText("Error!")
        self.lbl_status.setStyleSheet("color: #ef4444;")
        
        QMessageBox.critical(self, "Optimization Error", error_msg)
        self.log(f"ERROR: {error_msg}")
    
    def _update_display(self):
        """Update display when threshold changes."""
        threshold = self.slider_threshold.value() / 100.0
        self.lbl_threshold.setText(f"{threshold:.2f}")
        
        if self.current_density is not None:
            self.viewport.update_density_visualization(
                self.current_density, threshold, self.mesh_handler
            )
    
    def _export_result(self):
        """Export the optimization result."""
        if self.current_density is None:
            QMessageBox.warning(self, "Warning", "No result to export.")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Result", "optimized.stl",
            "STL Files (*.stl);;OBJ Files (*.obj);;All Files (*)"
        )
        
        if not filepath:
            return
        
        try:
            threshold = self.slider_threshold.value() / 100.0
            self.mesh_handler.export_result(
                self.current_density, threshold, filepath
            )
            self.log(f"Exported result to: {filepath}")
            QMessageBox.information(self, "Export", f"Result exported to:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed:\n{e}")
    
    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self, "About",
            "<h2>Topology Optimization for CAD Models</h2>"
            "<p>Interactive topology optimization tool using the SIMP method.</p>"
            "<p>Supports arbitrary CAD geometries (STL, OBJ, etc.)</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>Automatic mesh voxelization</li>"
            "<li>Hollowness enforcement for structural optimization</li>"
            "<li>Sensitivity filtering to prevent checkerboarding</li>"
            "<li>Multiple boundary conditions</li>"
            "<li>Real-time 3D visualization</li>"
            "<li>Export to STL/OBJ</li>"
            "</ul>"
            "<p>Based on Sigmund (2001) SIMP algorithm.</p>"
        )
    
    def _show_algorithm_info(self):
        """Show algorithm information."""
        QMessageBox.information(
            self, "Algorithm Information",
            "<h3>SIMP Method</h3>"
            "<p><b>Solid Isotropic Material with Penalization</b></p>"
            "<p>The SIMP method interpolates material properties using:</p>"
            "<p align='center'>E(x) = x<sup>p</sup> · E₀</p>"
            "<p>where x is the relative density (0-1) and p is the penalization power.</p>"
            "<p><b>Key Parameters:</b></p>"
            "<ul>"
            "<li><b>Volume Fraction:</b> Target amount of material in design space</li>"
            "<li><b>Penalization (p):</b> Higher values → clearer solid/void (typical: 3)</li>"
            "<li><b>Filter Radius:</b> Controls minimum feature size</li>"
            "<li><b>Wall Thickness:</b> Minimum shell thickness preserved</li>"
            "</ul>"
            "<p><b>Hollowness:</b> The tool automatically creates an interior void "
            "region so the optimizer can redistribute material efficiently.</p>"
        )
    
    def log(self, message: str):
        """Log message to info panel."""
        self.info_text.append(message)
        self.info_text.verticalScrollBar().setValue(
            self.info_text.verticalScrollBar().maximum()
        )
    
    def closeEvent(self, event):
        """Handle window close."""
        if self.is_optimizing:
            reply = QMessageBox.question(
                self, "Confirm Exit",
                "Optimization is running. Stop and exit?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            
            if self.worker:
                self.worker.stop()
                self.worker.wait(2000)
        
        event.accept()
