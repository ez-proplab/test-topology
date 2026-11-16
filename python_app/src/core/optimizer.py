"""
SIMP Topology Optimization Algorithm.
Supports arbitrary geometries via voxel-based approach.
"""

import numpy as np
from scipy import ndimage
from typing import Callable, Optional, Tuple, Dict, Any
import logging
import time

from .fea import FEASolver
from .mesh_utils import MeshHandler

logger = logging.getLogger(__name__)


class TopologyOptimizer:
    """
    SIMP-based topology optimizer for arbitrary CAD geometries.
    
    The optimizer works on a voxel grid derived from the input mesh,
    ensuring sufficient hollowness for structural optimization.
    """
    
    def __init__(self, mesh_handler: MeshHandler, params: Dict[str, Any]):
        """
        Initialize optimizer.
        
        Args:
            mesh_handler: MeshHandler with loaded and voxelized geometry
            params: Optimization parameters dict with keys:
                - volfrac: Volume fraction constraint
                - penal: SIMP penalization power
                - rmin: Filter radius (in voxels)
                - max_iter: Maximum iterations
                - tol: Convergence tolerance
                - bc_type: Boundary condition type
                - min_wall_thickness: Minimum wall thickness (voxels)
        """
        self.mesh = mesh_handler
        self.params = params
        
        self.nx, self.ny, self.nz = mesh_handler.grid_shape
        self.ne = self.nx * self.ny * self.nz
        
        # Extract parameters
        self.volfrac = params.get('volfrac', 0.4)
        self.penal = params.get('penal', 3.0)
        self.rmin = params.get('rmin', 2.0)
        self.max_iter = params.get('max_iter', 50)
        self.tol = params.get('tol', 0.01)
        self.bc_type = params.get('bc_type', 'cantilever')
        
        # Initialize FEA solver
        self.fea = FEASolver(
            self.nx, self.ny, self.nz,
            voxel_size=mesh_handler.voxel_size
        )
        
        # Design variables
        self.x = None
        self.fixed_mask = None
        self.design_mask = None
        
        # History
        self.history = []
        self.convergence_data = []
        
        # Callbacks
        self.on_iteration: Optional[Callable] = None
        self.on_complete: Optional[Callable] = None
        
        self._is_running = False
        self._should_stop = False
    
    def setup(self) -> Dict[str, Any]:
        """
        Set up the optimization problem.
        Creates initial density field and identifies design space.
        
        Returns:
            Setup information dict
        """
        logger.info("Setting up optimization problem...")
        
        # Enforce hollowness
        self.mesh.enforce_hollowness(
            min_wall_thickness=self.params.get('min_wall_thickness', 2),
            target_hollow_fraction=self.params.get('hollow_fraction', 0.6)
        )
        
        # Get masks
        self.fixed_mask = self.mesh.get_fixed_dofs_mask()  # Surface shell
        self.design_mask = self.mesh.get_design_dofs_mask()  # Interior design space
        
        # Initial density
        self.x = self.mesh.get_initial_density(self.volfrac)
        
        # Build load vector
        F = self._build_load_vector()
        
        # Get fixed DOFs
        fixed_dofs = self._get_fixed_dofs()
        
        info = {
            'grid_shape': (self.nx, self.ny, self.nz),
            'num_elements': self.ne,
            'num_dofs': self.fea.ndof,
            'num_fixed_elements': int(np.sum(self.fixed_mask)),
            'num_design_elements': int(np.sum(self.design_mask)),
            'volume_fraction': self.volfrac,
            'initial_volume': float(np.sum(self.x) / self.ne),
        }
        
        logger.info(f"Setup complete: {info}")
        
        return info
    
    def _build_load_vector(self) -> np.ndarray:
        """Build the load vector based on boundary condition type."""
        F = np.zeros(self.fea.ndof)
        
        if self.bc_type == 'cantilever':
            # Load at far end, middle height
            node = self.fea.get_node_index(
                self.nx, self.ny // 2, self.nz // 2
            )
            self.fea.apply_load(F, node, direction=(0, 0, -1), magnitude=1.0)
            
        elif self.bc_type == 'bridge':
            # Load at center bottom
            node = self.fea.get_node_index(
                self.nx // 2, self.ny // 2, 0
            )
            self.fea.apply_load(F, node, direction=(0, 0, -1), magnitude=1.0)
            
        elif self.bc_type == '3point_bend':
            # Load at center top
            node = self.fea.get_node_index(
                self.nx // 2, self.ny // 2, self.nz
            )
            self.fea.apply_load(F, node, direction=(0, 0, -1), magnitude=1.0)
        
        elif self.bc_type == 'custom':
            # Custom load from params
            load_node = self.params.get('load_node', (self.nx, self.ny//2, self.nz//2))
            load_dir = self.params.get('load_direction', (0, 0, -1))
            load_mag = self.params.get('load_magnitude', 1.0)
            node = self.fea.get_node_index(*load_node)
            self.fea.apply_load(F, node, direction=load_dir, magnitude=load_mag)
        
        return F
    
    def _get_fixed_dofs(self) -> np.ndarray:
        """Get fixed DOFs based on boundary condition type."""
        if self.bc_type == 'cantilever':
            return self.fea.get_fixed_dofs_cantilever()
        elif self.bc_type == 'bridge':
            return self.fea.get_fixed_dofs_bridge()
        elif self.bc_type == '3point_bend':
            return self.fea.get_fixed_dofs_3point_bend()
        elif self.bc_type == 'custom':
            return np.array(self.params.get('fixed_dofs', []))
        else:
            return self.fea.get_fixed_dofs_cantilever()
    
    def optimize(self, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Run the topology optimization.
        
        Args:
            callback: Called each iteration with (iteration, density, compliance, volume)
            
        Returns:
            Results dict
        """
        self._is_running = True
        self._should_stop = False
        self.on_iteration = callback
        self.history = []
        self.convergence_data = []
        
        start_time = time.time()
        
        # Setup
        setup_info = self.setup()
        F = self._build_load_vector()
        fixed_dofs = self._get_fixed_dofs()
        
        x = self.x.flatten().copy()
        
        # Active elements mask (only optimize design space)
        active = self.design_mask.flatten()
        
        logger.info(f"Starting optimization: {self.max_iter} iterations")
        
        for iteration in range(1, self.max_iter + 1):
            if self._should_stop:
                logger.info("Optimization stopped by user")
                break
            
            iter_start = time.time()
            
            # Reshape density
            density = x.reshape(self.nx, self.ny, self.nz)
            
            # Assemble stiffness matrix
            K = self.fea.assemble_stiffness(density, self.penal, self.design_mask)
            
            # Solve FE system
            u, compliance = self.fea.solve(K, F, fixed_dofs)
            
            # Compute sensitivities
            dc = self.fea.compute_sensitivities(u, density, self.penal, self.design_mask)
            
            # Sensitivity filter
            dc = self._filter_sensitivities(dc, x)
            
            # OC update
            x, change = self._oc_update(x, dc, active)
            
            # Compute volume
            volume = float(np.sum(x * active) / max(1, np.sum(active)))
            
            iter_time = time.time() - iter_start
            
            # Store history
            self.convergence_data.append({
                'iteration': iteration,
                'compliance': compliance,
                'volume': volume,
                'change': change,
                'time': iter_time,
            })
            
            logger.info(
                f"Iter {iteration:3d}: compliance={compliance:.4e}, "
                f"volume={volume:.3f}, change={change:.4f}, time={iter_time:.2f}s"
            )
            
            # Callback
            if callback:
                callback(iteration, density, compliance, volume, change)
            
            # Check convergence
            if change < self.tol and iteration > 10:
                logger.info(f"Converged at iteration {iteration}")
                break
        
        # Final result
        final_density = x.reshape(self.nx, self.ny, self.nz)
        total_time = time.time() - start_time
        
        results = {
            'density': final_density,
            'iterations': iteration,
            'final_compliance': compliance,
            'final_volume': volume,
            'total_time': total_time,
            'converged': change < self.tol,
            'convergence_data': self.convergence_data,
        }
        
        self._is_running = False
        
        if self.on_complete:
            self.on_complete(results)
        
        logger.info(f"Optimization complete in {total_time:.1f}s")
        
        return results
    
    def _filter_sensitivities(self, dc: np.ndarray, x: np.ndarray) -> np.ndarray:
        """
        Apply sensitivity filter to prevent checkerboarding.
        Uses convolution-based approach for speed.
        """
        rmin_int = int(np.ceil(self.rmin))
        
        # Create filter kernel
        size = 2 * rmin_int + 1
        kernel = np.zeros((size, size, size))
        
        for k in range(size):
            for j in range(size):
                for i in range(size):
                    di = i - rmin_int
                    dj = j - rmin_int
                    dk = k - rmin_int
                    dist = np.sqrt(di**2 + dj**2 + dk**2)
                    if dist < self.rmin:
                        kernel[k, j, i] = self.rmin - dist
        
        # Compute filtered values using convolution
        xdc = (x * dc).reshape(self.nx, self.ny, self.nz)
        
        # Use scipy convolution for speed
        from scipy.ndimage import convolve
        numerator = convolve(xdc, kernel, mode='constant', cval=0.0)
        denominator = convolve(np.ones_like(xdc), kernel, mode='constant', cval=0.0)
        
        # Compute filtered sensitivities
        x_flat = x.copy()
        x_flat[x_flat < 1e-9] = 1e-9  # Avoid division by zero
        
        dcf = numerator.flatten() / (x_flat * denominator.flatten())
        
        # Where filter had no effect, keep original
        no_filter_mask = denominator.flatten() < 1e-12
        dcf[no_filter_mask] = dc[no_filter_mask]
        
        return dcf
    
    def _oc_update(self, x: np.ndarray, dc: np.ndarray, 
                   active: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Optimality Criteria update scheme (vectorized).
        """
        l1 = 0.0
        l2 = 1e9
        move = 0.2
        target_vol = self.volfrac
        n_active = max(1, np.sum(active))
        
        change = 1.0
        
        for _ in range(50):
            lmid = 0.5 * (l1 + l2)
            
            # Vectorized OC update
            # Be = sqrt(-dc / lmid) where dc < 0, else 0
            Be = np.zeros_like(dc)
            neg_mask = (dc < 0) & active
            Be[neg_mask] = np.sqrt(-dc[neg_mask] / lmid)
            
            # x_new = clip(x * Be, x - move, x + move)
            x_new = x.copy()
            x_updated = x * Be
            
            # Apply move limit and bounds
            x_new[active] = np.clip(x_updated[active], 
                                     np.maximum(0.001, x[active] - move),
                                     np.minimum(1.0, x[active] + move))
            
            # Check volume constraint
            current_vol = np.sum(x_new * active) / n_active
            
            if current_vol > target_vol:
                l1 = lmid
            else:
                l2 = lmid
            
            change = float(np.max(np.abs(x_new[active] - x[active])))
            x = x_new
            
            if (l2 - l1) < 1e-4 and change < 0.01:
                break
        
        return x, change
    
    def stop(self):
        """Stop the optimization."""
        self._should_stop = True
    
    @property
    def is_running(self) -> bool:
        return self._is_running
    
    def get_current_density(self) -> np.ndarray:
        """Get current density field."""
        if self.x is not None:
            return self.x.reshape(self.nx, self.ny, self.nz)
        return None
