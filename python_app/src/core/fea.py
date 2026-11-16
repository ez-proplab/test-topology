"""
Finite Element Analysis solver for voxel-based topology optimization.
Uses 8-node hexahedral elements with SIMP material interpolation.
"""

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import cg, spsolve
from typing import Tuple, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class FEASolver:
    """
    Voxel-based FEA solver for topology optimization.
    
    Uses 8-node hexahedral (brick) elements on a regular voxel grid.
    Supports arbitrary boundary conditions and loading.
    """
    
    def __init__(self, nx: int, ny: int, nz: int, 
                 voxel_size: float = 1.0,
                 youngs_modulus: float = 1.0,
                 poisson_ratio: float = 0.3):
        """
        Initialize FEA solver.
        
        Args:
            nx, ny, nz: Grid dimensions
            voxel_size: Size of each voxel
            youngs_modulus: Young's modulus of solid material
            poisson_ratio: Poisson's ratio
        """
        self.nx = nx
        self.ny = ny
        self.nz = nz
        self.voxel_size = voxel_size
        self.E = youngs_modulus
        self.nu = poisson_ratio
        
        # Number of nodes and DOFs
        self.nnodes = (nx + 1) * (ny + 1) * (nz + 1)
        self.ndof = 3 * self.nnodes  # 3 DOFs per node (ux, uy, uz)
        
        # Compute element stiffness matrix
        self.KE = self._compute_hex8_stiffness()
        
        # Precompute element connectivity
        self._build_connectivity()
        
        logger.info(f"FEA Solver: {nx}x{ny}x{nz} grid, {self.ndof} DOFs")
    
    def _compute_hex8_stiffness(self) -> np.ndarray:
        """
        Compute the 24x24 stiffness matrix for a single hex8 element.
        Uses 2x2x2 Gauss quadrature for numerical integration.
        """
        E = self.E
        nu = self.nu
        h = self.voxel_size
        
        # Material matrix (constitutive relation) for 3D elasticity
        C = self._constitutive_matrix()
        
        # Gauss points (2x2x2)
        gp = 1.0 / np.sqrt(3)
        gauss_points = [
            (-gp, -gp, -gp), (gp, -gp, -gp),
            (-gp, gp, -gp), (gp, gp, -gp),
            (-gp, -gp, gp), (gp, -gp, gp),
            (-gp, gp, gp), (gp, gp, gp)
        ]
        weights = [1.0] * 8  # Weight = 1 for each point (h^3/8 factored in)
        
        # Node coordinates in reference element [-1, 1]^3
        node_coords = np.array([
            [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
            [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]
        ], dtype=np.float64)
        
        KE = np.zeros((24, 24))
        
        for xi, eta, zeta in gauss_points:
            # Shape function derivatives
            dN = self._shape_derivatives(xi, eta, zeta, node_coords)
            
            # Jacobian
            J = dN @ node_coords * (h / 2)
            detJ = np.linalg.det(J)
            Jinv = np.linalg.inv(J)
            
            # B matrix (strain-displacement)
            dN_global = dN @ Jinv
            B = self._B_matrix(dN_global)
            
            # Integrate
            KE += B.T @ C @ B * detJ
        
        return KE
    
    def _constitutive_matrix(self) -> np.ndarray:
        """Compute the 6x6 constitutive (material) matrix for 3D elasticity."""
        E = self.E
        nu = self.nu
        
        factor = E / ((1 + nu) * (1 - 2 * nu))
        
        C = np.zeros((6, 6))
        C[0, 0] = C[1, 1] = C[2, 2] = 1 - nu
        C[0, 1] = C[0, 2] = C[1, 0] = C[1, 2] = C[2, 0] = C[2, 1] = nu
        C[3, 3] = C[4, 4] = C[5, 5] = (1 - 2 * nu) / 2
        
        return C * factor
    
    def _shape_derivatives(self, xi, eta, zeta, node_coords):
        """Compute derivatives of shape functions at a point."""
        dN = np.zeros((8, 3))
        
        for i in range(8):
            xi_i, eta_i, zeta_i = node_coords[i]
            
            dN[i, 0] = xi_i * (1 + eta_i * eta) * (1 + zeta_i * zeta) / 8
            dN[i, 1] = eta_i * (1 + xi_i * xi) * (1 + zeta_i * zeta) / 8
            dN[i, 2] = zeta_i * (1 + xi_i * xi) * (1 + eta_i * eta) / 8
        
        return dN
    
    def _B_matrix(self, dN: np.ndarray) -> np.ndarray:
        """Build the strain-displacement B matrix from shape function derivatives."""
        B = np.zeros((6, 24))
        
        for i in range(8):
            col = i * 3
            dndx, dndy, dndz = dN[i]
            
            B[0, col] = dndx           # eps_xx
            B[1, col + 1] = dndy       # eps_yy
            B[2, col + 2] = dndz       # eps_zz
            B[3, col] = dndy           # gamma_xy
            B[3, col + 1] = dndx
            B[4, col + 1] = dndz       # gamma_yz
            B[4, col + 2] = dndy
            B[5, col] = dndz           # gamma_xz
            B[5, col + 2] = dndx
        
        return B
    
    def _build_connectivity(self):
        """Precompute element-to-node connectivity."""
        self.edof_matrix = np.zeros((self.nx * self.ny * self.nz, 24), dtype=np.int32)
        
        elem_idx = 0
        for iz in range(self.nz):
            for iy in range(self.ny):
                for ix in range(self.nx):
                    # 8 node indices for this element
                    n0 = ix * (self.ny + 1) * (self.nz + 1) + iy * (self.nz + 1) + iz
                    n1 = n0 + (self.ny + 1) * (self.nz + 1)
                    n2 = n1 + (self.nz + 1)
                    n3 = n0 + (self.nz + 1)
                    n4 = n0 + 1
                    n5 = n1 + 1
                    n6 = n2 + 1
                    n7 = n3 + 1
                    
                    nodes = [n0, n1, n2, n3, n4, n5, n6, n7]
                    
                    for j, node in enumerate(nodes):
                        self.edof_matrix[elem_idx, j*3:j*3+3] = [3*node, 3*node+1, 3*node+2]
                    
                    elem_idx += 1
    
    def assemble_stiffness(self, density: np.ndarray, penal: float = 3.0,
                           active_mask: Optional[np.ndarray] = None) -> sparse.csr_matrix:
        """
        Assemble global stiffness matrix using SIMP interpolation.
        Vectorized for performance.
        
        Args:
            density: Element density array (flattened, nx*ny*nz)
            penal: SIMP penalization power
            active_mask: Boolean mask of active elements (optional)
            
        Returns:
            Sparse global stiffness matrix
        """
        ne = self.nx * self.ny * self.nz
        
        # SIMP interpolation
        xPhys = density.flatten() ** penal
        
        if active_mask is not None:
            xPhys *= active_mask.flatten()
        
        # Find active elements
        active_elems = np.where(xPhys > 1e-9)[0]
        
        if len(active_elems) == 0:
            return sparse.csr_matrix((self.ndof, self.ndof))
        
        # Vectorized assembly
        # For each active element, we need to scatter KE * xPhys[e] into global matrix
        n_active = len(active_elems)
        
        # Repeat KE pattern for all active elements
        # KE is 24x24, we need 576 entries per element
        ke_flat = self.KE.flatten()  # 576 values
        
        # Scale by density
        x_active = xPhys[active_elems]  # (n_active,)
        
        # Build row/col/val arrays
        # edof_matrix[active_elems] has shape (n_active, 24)
        edof_active = self.edof_matrix[active_elems]  # (n_active, 24)
        
        # Create indices: for each element i, for each (j,k) in KE
        # row = edof_active[i, j], col = edof_active[i, k]
        # We use broadcasting: edof_active[:, :, None] and edof_active[:, None, :]
        
        rows = np.repeat(edof_active[:, :, None], 24, axis=2).flatten()  # (n_active * 24 * 24,)
        cols = np.repeat(edof_active[:, None, :], 24, axis=1).flatten()  # (n_active * 24 * 24,)
        
        # Values: ke_flat repeated and scaled
        vals = np.tile(ke_flat, n_active) * np.repeat(x_active, 576)
        
        K = sparse.coo_matrix(
            (vals, (rows, cols)),
            shape=(self.ndof, self.ndof)
        ).tocsr()
        
        return K
    
    def solve(self, K: sparse.csr_matrix, F: np.ndarray,
              fixed_dofs: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Solve the FE system Ku = F with boundary conditions.
        
        Args:
            K: Global stiffness matrix
            F: Load vector
            fixed_dofs: Indices of fixed DOFs
            
        Returns:
            Displacement vector and compliance
        """
        # Free DOFs
        all_dofs = np.arange(self.ndof)
        free_dofs = np.setdiff1d(all_dofs, fixed_dofs)
        
        if len(free_dofs) == 0:
            return np.zeros(self.ndof), 0.0
        
        # Extract sub-matrices
        K_ff = K[np.ix_(free_dofs, free_dofs)]
        F_f = F[free_dofs]
        
        # Solve using conjugate gradient
        u_f, info = cg(K_ff, F_f, tol=1e-8, maxiter=1000)
        
        if info != 0:
            logger.warning(f"CG solver did not converge (info={info}). Trying direct solver...")
            try:
                u_f = spsolve(K_ff, F_f)
            except Exception as e:
                logger.error(f"Direct solver also failed: {e}")
                u_f = np.zeros(len(free_dofs))
        
        # Assemble full displacement vector
        u = np.zeros(self.ndof)
        u[free_dofs] = u_f
        
        # Compute compliance
        compliance = float(F @ u)
        
        return u, compliance
    
    def compute_sensitivities(self, u: np.ndarray, density: np.ndarray,
                              penal: float = 3.0,
                              active_mask: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Compute sensitivity of compliance w.r.t. design variables.
        Vectorized for performance.
        
        dc/dx_e = -p * x_e^(p-1) * u_e^T * K_e * u_e
        
        Args:
            u: Displacement vector
            density: Element density array
            penal: SIMP penalization power
            active_mask: Boolean mask of active elements
            
        Returns:
            Sensitivity array (dc/dx for each element)
        """
        ne = self.nx * self.ny * self.nz
        x = density.flatten()
        
        if active_mask is not None:
            active = active_mask.flatten()
        else:
            active = np.ones(ne, dtype=bool)
        
        # Get DOFs for all active elements
        active_elems = np.where(active)[0]
        edof_active = self.edof_matrix[active_elems]  # (n_active, 24)
        
        # Extract displacements: u[edof_active] -> (n_active, 24)
        ue_all = u[edof_active]
        
        # Compute element strain energy: ue^T @ KE @ ue for each element
        # KE @ ue_all.T -> (24, n_active)
        # Then ue_all * (KE @ ue_all.T).T -> element-wise multiply and sum
        KE_ue = self.KE @ ue_all.T  # (24, n_active)
        ce = np.sum(ue_all * KE_ue.T, axis=1)  # (n_active,)
        
        # Compute sensitivities
        dc = np.zeros(ne)
        dc[active_elems] = -penal * (x[active_elems] ** (penal - 1)) * ce
        
        return dc
    
    def apply_load(self, F: np.ndarray, node_idx: int, 
                   direction: Tuple[float, float, float] = (0, -1, 0),
                   magnitude: float = 1.0):
        """
        Apply a point load at a specific node.
        
        Args:
            F: Load vector (modified in place)
            node_idx: Node index
            direction: Load direction (will be normalized)
            magnitude: Load magnitude
        """
        d = np.array(direction, dtype=np.float64)
        d = d / np.linalg.norm(d)
        
        dof_start = 3 * node_idx
        F[dof_start:dof_start + 3] += magnitude * d
    
    def get_node_index(self, ix: int, iy: int, iz: int) -> int:
        """Get node index from grid coordinates."""
        return ix * (self.ny + 1) * (self.nz + 1) + iy * (self.nz + 1) + iz
    
    def get_element_index(self, ix: int, iy: int, iz: int) -> int:
        """Get element index from grid coordinates."""
        return iz * self.nx * self.ny + iy * self.nx + ix
    
    def get_fixed_dofs_cantilever(self) -> np.ndarray:
        """Get fixed DOFs for cantilever BC (fix one face)."""
        fixed = []
        for iy in range(self.ny + 1):
            for iz in range(self.nz + 1):
                node = self.get_node_index(0, iy, iz)
                fixed.extend([3*node, 3*node+1, 3*node+2])
        return np.array(fixed)
    
    def get_fixed_dofs_bridge(self) -> np.ndarray:
        """Get fixed DOFs for simply-supported beam."""
        fixed = []
        
        # Fix bottom-left edge (x=0, z=0)
        for iy in range(self.ny + 1):
            node = self.get_node_index(0, iy, 0)
            fixed.extend([3*node, 3*node+1, 3*node+2])
        
        # Fix bottom-right edge (x=nx, z=0) - only y direction
        for iy in range(self.ny + 1):
            node = self.get_node_index(self.nx, iy, 0)
            fixed.extend([3*node+1, 3*node+2])  # fix y and z, allow x
        
        return np.array(fixed)
    
    def get_fixed_dofs_3point_bend(self) -> np.ndarray:
        """Get fixed DOFs for 3-point bending."""
        fixed = []
        
        # Two roller supports at bottom
        support_y = [self.ny // 4, 3 * self.ny // 4]
        
        for sy in support_y:
            node = self.get_node_index(0, sy, 0)
            fixed.extend([3*node+2])  # fix z only (roller)
        
        # Pin support
        node = self.get_node_index(0, self.ny // 2, 0)
        fixed.extend([3*node, 3*node+2])  # fix x and z
        
        return np.array(fixed)
