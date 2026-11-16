"""
Mesh handling utilities for arbitrary CAD geometry.
Supports STL, OBJ, STEP, and other formats via trimesh.
Provides voxelization and hollowness enforcement.
"""

import numpy as np
import trimesh
from scipy import ndimage
from typing import Tuple, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class MeshHandler:
    """Handles loading, processing, and voxelization of arbitrary CAD geometries."""
    
    def __init__(self):
        self.mesh: Optional[trimesh.Trimesh] = None
        self.voxel_grid: Optional[np.ndarray] = None
        self.design_mask: Optional[np.ndarray] = None
        self.surface_mask: Optional[np.ndarray] = None
        self.voxel_size: float = 1.0
        self.grid_shape: Tuple[int, int, int] = (0, 0, 0)
        self.origin: np.ndarray = np.zeros(3)
        
    def load_mesh(self, filepath: str) -> Dict[str, Any]:
        """
        Load a mesh from file. Supports STL, OBJ, OFF, PLY, and more.
        
        Returns dict with mesh info.
        """
        logger.info(f"Loading mesh from: {filepath}")
        
        try:
            self.mesh = trimesh.load(filepath, force='mesh')
        except Exception as e:
            raise ValueError(f"Failed to load mesh: {e}")
        
        if not isinstance(self.mesh, trimesh.Trimesh):
            raise ValueError("File does not contain a valid mesh")
        
        # Ensure mesh is watertight for voxelization
        if not self.mesh.is_watertight:
            logger.warning("Mesh is not watertight. Attempting to fix...")
            self.mesh = self._fix_mesh(self.mesh)
        
        info = {
            'vertices': len(self.mesh.vertices),
            'faces': len(self.mesh.faces),
            'is_watertight': self.mesh.is_watertight,
            'is_volume': self.mesh.is_volume,
            'bounds': self.mesh.bounds.tolist(),
            'extents': self.mesh.extents.tolist(),
            'volume': float(self.mesh.volume) if self.mesh.is_volume else 0.0,
            'area': float(self.mesh.area),
        }
        
        logger.info(f"Mesh loaded: {info['vertices']} vertices, {info['faces']} faces")
        return info
    
    def _fix_mesh(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Attempt to fix a non-watertight mesh."""
        # Fill holes
        trimesh.repair.fill_holes(mesh)
        # Fix winding
        trimesh.repair.fix_winding(mesh)
        # Fix normals
        trimesh.repair.fix_normals(mesh)
        
        if not mesh.is_watertight:
            logger.warning("Could not fully fix mesh. Voxelization may be approximate.")
        
        return mesh
    
    def voxelize(self, resolution: float = None, num_voxels: int = 40) -> np.ndarray:
        """
        Voxelize the mesh into a 3D binary grid.
        
        Args:
            resolution: Voxel size in model units. If None, computed from num_voxels.
            num_voxels: Target number of voxels along the longest axis.
            
        Returns:
            3D boolean array (True = inside mesh)
        """
        if self.mesh is None:
            raise ValueError("No mesh loaded")
        
        extents = self.mesh.extents
        max_extent = max(extents)
        
        if resolution is None:
            resolution = max_extent / num_voxels
        
        self.voxel_size = resolution
        
        # Compute grid dimensions
        nx = max(3, int(np.ceil(extents[0] / resolution)) + 2)
        ny = max(3, int(np.ceil(extents[1] / resolution)) + 2)
        nz = max(3, int(np.ceil(extents[2] / resolution)) + 2)
        
        self.grid_shape = (nx, ny, nz)
        
        # Origin offset (pad by 1 voxel on each side)
        self.origin = self.mesh.bounds[0] - resolution
        
        logger.info(f"Voxelizing: grid={self.grid_shape}, voxel_size={resolution:.4f}")
        
        # Create voxel grid
        pitch = [resolution, resolution, resolution]
        voxelized = self.mesh.voxelized(pitch=resolution)
        
        # Convert to dense array
        matrix = voxelized.matrix.astype(bool)
        
        # Pad to ensure consistent shape
        padded = np.zeros(self.grid_shape, dtype=bool)
        # Copy into padded array (centered)
        sx, sy, sz = matrix.shape
        px, py, pz = self.grid_shape
        ox = max(0, (px - sx) // 2)
        oy = max(0, (py - sy) // 2)
        oz = max(0, (pz - sz) // 2)
        
        copy_sx = min(sx, px - ox)
        copy_sy = min(sy, py - oy)
        copy_sz = min(sz, pz - oz)
        
        padded[ox:ox+copy_sx, oy:oy+copy_sy, oz:oz+copy_sz] = \
            matrix[:copy_sx, :copy_sy, :copy_sz]
        
        self.voxel_grid = padded
        
        logger.info(f"Voxelization complete: {np.sum(padded)} solid voxels out of {np.prod(self.grid_shape)}")
        
        return self.voxel_grid
    
    def enforce_hollowness(self, min_wall_thickness: int = 2, 
                           target_hollow_fraction: float = 0.5) -> np.ndarray:
        """
        Ensure the voxelized geometry has sufficient hollowness for optimization.
        
        This creates an interior void region so the optimizer has room to work.
        
        Args:
            min_wall_thickness: Minimum wall thickness in voxels.
            target_hollow_fraction: Target fraction of interior to hollow out (0-1).
            
        Returns:
            Design mask (True = can be optimized, False = fixed boundary)
        """
        if self.voxel_grid is None:
            raise ValueError("Must voxelize first")
        
        solid = self.voxel_grid.copy()
        
        # Identify surface voxels (voxels adjacent to empty space)
        surface = self._identify_surface(solid)
        self.surface_mask = surface
        
        # Erode to find interior
        interior = solid.copy()
        
        # Erode by min_wall_thickness to preserve outer shell
        for _ in range(min_wall_thickness):
            interior = ndimage.binary_erosion(interior, structure=np.ones((3, 3, 3)))
        
        # The design space is the interior region
        # Apply target_hollow_fraction to control how much to hollow
        if target_hollow_fraction < 1.0:
            # Keep some interior material for structural support
            interior_eroded = interior.copy()
            extra_erosion = int((1 - target_hollow_fraction) * min_wall_thickness * 2)
            for _ in range(extra_erosion):
                interior_eroded = ndimage.binary_erosion(
                    interior_eroded, structure=np.ones((3, 3, 3))
                )
            # Design space = interior minus the deeply eroded core
            design_space = interior & ~interior_eroded
        else:
            design_space = interior
        
        # Design mask: True where optimization can occur
        self.design_mask = design_space
        
        # Create initial density field
        # Solid shell = density 1.0
        # Design space = initial density (volfrac)
        # Outside = density 0.0
        
        hollow_fraction = 1.0 - (np.sum(interior) / max(1, np.sum(solid)))
        
        logger.info(f"Hollowness enforced:")
        logger.info(f"  Solid voxels: {np.sum(solid)}")
        logger.info(f"  Surface voxels: {np.sum(surface)}")
        logger.info(f"  Interior (design space): {np.sum(design_space)}")
        logger.info(f"  Hollow fraction: {hollow_fraction:.2%}")
        logger.info(f"  Min wall thickness: {min_wall_thickness} voxels")
        
        return self.design_mask
    
    def _identify_surface(self, solid: np.ndarray) -> np.ndarray:
        """Identify surface voxels (solid voxels adjacent to empty space)."""
        # A voxel is on the surface if any of its 6-connected neighbors is empty
        padded = np.pad(solid, 1, mode='constant', constant_values=False)
        
        # Check all 6 neighbors
        surface = np.zeros_like(solid)
        
        # +x, -x
        surface |= solid & ~padded[2:, 1:-1, 1:-1]
        surface |= solid & ~padded[:-2, 1:-1, 1:-1]
        # +y, -y
        surface |= solid & ~padded[1:-1, 2:, 1:-1]
        surface |= solid & ~padded[1:-1, :-2, 1:-1]
        # +z, -z
        surface |= solid & ~padded[1:-1, 1:-1, 2:]
        surface |= solid & ~padded[1:-1, 1:-1, :-2]
        
        return surface
    
    def get_initial_density(self, volfrac: float = 0.4) -> np.ndarray:
        """
        Create initial density field for optimization.
        
        - Non-design regions (outside mesh): density = 0
        - Surface shell: density = 1.0 (fixed)
        - Design space (interior): density = volfrac
        
        Returns:
            3D density array
        """
        if self.voxel_grid is None or self.design_mask is None:
            raise ValueError("Must voxelize and enforce hollowness first")
        
        density = np.zeros(self.grid_shape, dtype=np.float64)
        
        # Surface shell is solid
        surface = self.surface_mask
        density[surface] = 1.0
        
        # Design space starts at volfrac
        design = self.design_mask
        density[design] = volfrac
        
        return density
    
    def get_fixed_dofs_mask(self) -> np.ndarray:
        """
        Get mask of elements that should remain fixed (density = 1).
        These are the surface voxels that form the outer shell.
        """
        if self.surface_mask is None:
            raise ValueError("Must enforce hollowness first")
        return self.surface_mask
    
    def get_design_dofs_mask(self) -> np.ndarray:
        """Get mask of elements that can be optimized."""
        if self.design_mask is None:
            raise ValueError("Must enforce hollowness first")
        return self.design_mask
    
    def export_result(self, density: np.ndarray, threshold: float = 0.5,
                      filepath: str = "optimized.stl") -> str:
        """
        Export optimization result as an STL mesh.
        
        Args:
            density: Final density field
            threshold: Density threshold for solid/void
            filepath: Output file path
            
        Returns:
            Path to exported file
        """
        if self.voxel_grid is None:
            raise ValueError("No voxel grid available")
        
        # Create binary mask from density
        solid_mask = density > threshold
        
        # Convert voxel grid to mesh
        result_mesh = self._voxels_to_mesh(solid_mask)
        
        if result_mesh is not None and len(result_mesh.faces) > 0:
            result_mesh.export(filepath)
            logger.info(f"Exported result to: {filepath}")
        else:
            logger.warning("No geometry to export (all elements below threshold)")
        
        return filepath
    
    def _voxels_to_mesh(self, mask: np.ndarray) -> Optional[trimesh.Trimesh]:
        """Convert a 3D boolean mask to a triangle mesh."""
        # Use marching cubes via trimesh
        # First create a smooth scalar field
        from scipy.ndimage import gaussian_filter
        
        # Smooth the mask slightly for better mesh quality
        smooth = gaussian_filter(mask.astype(np.float64), sigma=0.5)
        
        try:
            # Use trimesh's marching cubes
            mesh = trimesh.voxel.ops.matrix_to_marching_cubes(
                mask, pitch=self.voxel_size, origin=self.origin
            )
            return mesh
        except Exception as e:
            logger.error(f"Failed to convert voxels to mesh: {e}")
            return None
    
    def get_bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get the bounding box of the voxel grid."""
        if self.voxel_grid is None:
            raise ValueError("Must voxelize first")
        
        min_corner = self.origin
        max_corner = self.origin + np.array(self.grid_shape) * self.voxel_size
        return min_corner, max_corner
    
    def get_mesh_summary(self) -> str:
        """Get a text summary of the current mesh state."""
        lines = []
        if self.mesh is not None:
            lines.append(f"Vertices: {len(self.mesh.vertices):,}")
            lines.append(f"Faces: {len(self.mesh.faces):,}")
            lines.append(f"Bounds: {self.mesh.bounds[0].round(3)} to {self.mesh.bounds[1].round(3)}")
            lines.append(f"Extents: {self.mesh.extents.round(3)}")
        
        if self.voxel_grid is not None:
            lines.append(f"Voxel Grid: {self.grid_shape}")
            lines.append(f"Voxel Size: {self.voxel_size:.4f}")
            lines.append(f"Solid Voxels: {np.sum(self.voxel_grid):,}")
            lines.append(f"Fill Ratio: {np.sum(self.voxel_grid) / np.prod(self.grid_shape):.2%}")
        
        if self.design_mask is not None:
            lines.append(f"Design Voxels: {np.sum(self.design_mask):,}")
            lines.append(f"Surface Voxels: {np.sum(self.surface_mask):,}")
        
        return "\n".join(lines)


def create_test_geometry(shape: str = "beam", **kwargs) -> MeshHandler:
    """
    Create a test geometry for demonstration.
    
    Shapes: 'beam', 'l_bracket', 'plate', 'cylinder'
    """
    handler = MeshHandler()
    
    if shape == "beam":
        # Simple rectangular beam
        length = kwargs.get('length', 60)
        height = kwargs.get('height', 20)
        depth = kwargs.get('depth', 10)
        handler.mesh = trimesh.creation.box(extents=[length, height, depth])
        
    elif shape == "l_bracket":
        # L-shaped bracket
        t = kwargs.get('thickness', 5)
        l1 = kwargs.get('length1', 40)
        l2 = kwargs.get('length2', 30)
        depth = kwargs.get('depth', 10)
        
        box1 = trimesh.creation.box(extents=[l1, t, depth])
        box1.apply_translation([l1/2, t/2, 0])
        
        box2 = trimesh.creation.box(extents=[t, l2, depth])
        box2.apply_translation([t/2, l2/2, 0])
        
        handler.mesh = trimesh.boolean.union([box1, box2])
        
    elif shape == "plate":
        # Plate with hole
        size = kwargs.get('size', 40)
        thickness = kwargs.get('thickness', 5)
        hole_radius = kwargs.get('hole_radius', 8)
        
        plate = trimesh.creation.box(extents=[size, size, thickness])
        plate.apply_translation([0, 0, thickness/2])
        
        hole = trimesh.creation.cylinder(
            radius=hole_radius, height=thickness * 2
        )
        hole.apply_translation([0, 0, thickness/2])
        
        handler.mesh = trimesh.boolean.difference([plate, hole])
        
    elif shape == "cylinder":
        # Hollow cylinder
        outer_r = kwargs.get('outer_radius', 15)
        inner_r = kwargs.get('inner_radius', 10)
        height = kwargs.get('height', 30)
        
        outer = trimesh.creation.cylinder(radius=outer_r, height=height)
        inner = trimesh.creation.cylinder(radius=inner_r, height=height * 1.1)
        
        handler.mesh = trimesh.boolean.difference([outer, inner])
    
    else:
        raise ValueError(f"Unknown shape: {shape}")
    
    return handler
