"""
Export utilities for topology optimization results.
Supports STL, OBJ, and other formats.
"""

import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def export_density_to_stl(density: np.ndarray, voxel_size: float,
                          origin: np.ndarray, threshold: float = 0.5,
                          filepath: str = "output.stl") -> str:
    """
    Export density field as STL mesh using marching cubes.
    
    Args:
        density: 3D density array
        voxel_size: Size of each voxel
        origin: Origin of the voxel grid
        threshold: Density threshold for solid/void
        filepath: Output file path
        
    Returns:
        Path to exported file
    """
    import trimesh
    
    # Create binary mask
    mask = density > threshold
    
    if not np.any(mask):
        logger.warning("No elements above threshold - nothing to export")
        return filepath
    
    try:
        # Use trimesh's marching cubes
        mesh = trimesh.voxel.ops.matrix_to_marching_cubes(
            mask, pitch=voxel_size, origin=origin
        )
        
        if mesh is not None and len(mesh.faces) > 0:
            mesh.export(filepath)
            logger.info(f"Exported {len(mesh.faces)} faces to {filepath}")
        else:
            logger.warning("Generated mesh is empty")
    
    except Exception as e:
        logger.error(f"Failed to export STL: {e}")
        # Fallback: export as raw voxel data
        _export_voxel_obj(density, threshold, voxel_size, origin, filepath.replace('.stl', '.obj'))
    
    return filepath


def _export_voxel_obj(density: np.ndarray, threshold: float,
                      voxel_size: float, origin: np.ndarray,
                      filepath: str):
    """Fallback: export as voxel cubes in OBJ format."""
    mask = density > threshold
    
    nx, ny, nz = density.shape
    
    vertices = []
    faces = []
    
    for iz in range(nz):
        for iy in range(ny):
            for ix in range(nx):
                if mask[ix, iy, iz]:
                    # Add a cube at this position
                    base = len(vertices)
                    x0, y0, z0 = origin + np.array([ix, iy, iz]) * voxel_size
                    x1, y1, z1 = x0 + voxel_size, y0 + voxel_size, z0 + voxel_size
                    
                    # 8 vertices of cube
                    vertices.extend([
                        [x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                        [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1],
                    ])
                    
                    # 6 faces (12 triangles)
                    faces.extend([
                        [base+1, base+2, base+3], [base+1, base+3, base+4],  # bottom
                        [base+5, base+6, base+7], [base+5, base+7, base+8],  # top
                        [base+1, base+2, base+6], [base+1, base+6, base+5],  # front
                        [base+3, base+4, base+8], [base+3, base+8, base+7],  # back
                        [base+1, base+4, base+5], [base+1, base+5, base+8],  # left - fixed
                        [base+2, base+3, base+7], [base+2, base+7, base+6],  # right
                    ])
    
    # Write OBJ
    with open(filepath, 'w') as f:
        for v in vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for face in faces:
            f.write(f"f {face[0]} {face[1]} {face[2]}\n")
    
    logger.info(f"Exported {len(faces)} faces to {filepath}")


def export_density_field(density: np.ndarray, filepath: str = "density.npy"):
    """Export raw density field as numpy array."""
    np.save(filepath, density)
    logger.info(f"Exported density field to {filepath}")


def export_convergence_data(data: list, filepath: str = "convergence.csv"):
    """Export convergence history as CSV."""
    import csv
    
    if not data:
        return
    
    keys = data[0].keys()
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    
    logger.info(f"Exported convergence data to {filepath}")
