// Simplified SIMP (Solid Isotropic Material with Penalization) Topology Optimization
// Based on the 99-line topology optimization code by Sigmund (2001)

export interface OptimizationParams {
  nelx: number; // Number of elements in x direction
  nely: number; // Number of elements in y direction
  volfrac: number; // Volume fraction constraint
  penal: number; // Penalization power
  rmin: number; // Filter radius
  loadX: number; // Load application point X (fraction)
  loadY: number; // Load application point Y (fraction)
  bcType: 'cantilever' | 'bridge' | 'mbb'; // Boundary condition type
}

export interface OptimizationResult {
  density: Float32Array;
  iteration: number;
  compliance: number;
  converged: boolean;
}

// Build stiffness matrix for a single element
function lk(): number[] {
  const E = 1.0;
  const nu = 0.3;
  const k = [
    1/2 + nu/6, 1/8 + nu/8, -1/4 - nu/12, -1/8 + 3*nu/8,
    -1/4 + nu/12, -1/8 - nu/8, nu/6, 1/8 - 3*nu/8
  ];
  
  const KE = new Array(64).fill(0);
  const indices = [0, 1, 2, 3, 4, 5, 6, 7];
  
  for (let i = 0; i < 8; i++) {
    for (let j = 0; j < 8; j++) {
      // Simplified plane stress element stiffness
      const row = indices[i];
      const col = indices[j];
      KE[row * 8 + col] = E / (1 - nu * nu) * k[i] * (j === i ? 1 : 0.1);
    }
  }
  
  // Use a proper 2D quad element stiffness matrix
  const k11 = 1/2 + nu/6;
  const k12 = 1/8 + nu/8;
  const k13 = -1/4 - nu/12;
  const k14 = -1/8 + 3*nu/8;
  const k15 = -1/4 + nu/12;
  const k16 = -1/8 - nu/8;
  const k17 = nu/6;
  const k18 = 1/8 - 3*nu/8;
  
  const KE2D = [
    k11, k12, k13, k14, k15, k16, k17, k18,
    k12, k11, k18, k17, k16, k15, k14, k13,
    k13, k18, k11, k12, k17, k14, k15, k16,
    k14, k17, k12, k11, k18, k13, k16, k15,
    k15, k16, k17, k18, k11, k12, k13, k14,
    k16, k15, k14, k13, k12, k11, k18, k17,
    k17, k14, k15, k16, k13, k18, k11, k12,
    k18, k13, k16, k15, k14, k17, k12, k11
  ];
  
  return KE2D.map(v => v * E / (1 - nu * nu));
}

// Sparse matrix operations
class SparseMatrix {
  rows: number;
  cols: number;
  data: Map<number, number>;
  
  constructor(rows: number, cols: number) {
    this.rows = rows;
    this.cols = cols;
    this.data = new Map();
  }
  
  set(i: number, j: number, val: number) {
    const key = i * this.cols + j;
    this.data.set(key, (this.data.get(key) || 0) + val);
  }
  
  get(i: number, j: number): number {
    return this.data.get(i * this.cols + j) || 0;
  }
  
  multiply(x: Float64Array): Float64Array {
    const result = new Float64Array(this.rows);
    for (const [key, val] of this.data) {
      const i = Math.floor(key / this.cols);
      const j = key % this.cols;
      result[i] += val * x[j];
    }
    return result;
  }
}

// Conjugate gradient solver
function solveCG(K: SparseMatrix, f: Float64Array, maxIter: number = 200): Float64Array {
  const n = f.length;
  const x = new Float64Array(n);
  const r = new Float64Array(n);
  const p = new Float64Array(n);
  
  // r = f - K*x (x is initially zero, so r = f)
  for (let i = 0; i < n; i++) {
    r[i] = f[i];
    p[i] = r[i];
  }
  
  let rsold = 0;
  for (let i = 0; i < n; i++) rsold += r[i] * r[i];
  
  for (let iter = 0; iter < maxIter; iter++) {
    const Kp = K.multiply(p);
    let pKp = 0;
    for (let i = 0; i < n; i++) pKp += p[i] * Kp[i];
    
    if (Math.abs(pKp) < 1e-30) break;
    const alpha = rsold / pKp;
    
    for (let i = 0; i < n; i++) {
      x[i] += alpha * p[i];
      r[i] -= alpha * Kp[i];
    }
    
    let rsnew = 0;
    for (let i = 0; i < n; i++) rsnew += r[i] * r[i];
    
    if (Math.sqrt(rsnew) < 1e-6) break;
    
    const beta = rsnew / rsold;
    for (let i = 0; i < n; i++) {
      p[i] = r[i] + beta * p[i];
    }
    rsold = rsnew;
  }
  
  return x;
}

export function runOptimization(params: OptimizationParams, onProgress?: (iter: number, density: Float32Array, compliance: number) => void): OptimizationResult {
  const { nelx, nely, volfrac, penal, rmin, bcType } = params;
  
  const ndof = 2 * (nelx + 1) * (nely + 1);
  const KE = lk();
  
  // Initialize design variables
  let x = new Float32Array(nelx * nely);
  x.fill(volfrac);
  
  // Build load vector
  const F = new Float64Array(ndof);
  
  if (bcType === 'cantilever') {
    // Cantilever beam: fixed on left, load on right middle
    const loadNode = Math.floor((nely + 1) / 2);
    F[2 * (nelx * (nely + 1) + loadNode) + 1] = -1;
  } else if (bcType === 'bridge') {
    // Simply supported beam with center load
    const midX = Math.floor(nelx / 2);
    F[2 * (midX * (nely + 1) + nely) + 1] = -1;
  } else {
    // MBB beam
    const loadNode = nely;
    F[2 * (0 * (nely + 1) + loadNode) + 1] = -1;
  }
  
  // Fixed DOFs
  const fixedDofs: number[] = [];
  
  if (bcType === 'cantilever') {
    // Fix left edge
    for (let i = 0; i <= nely; i++) {
      fixedDofs.push(2 * i);
      fixedDofs.push(2 * i + 1);
    }
  } else if (bcType === 'bridge') {
    // Fix bottom-left corner (x and y) and bottom-right corner (y)
    fixedDofs.push(0, 1); // bottom-left
    fixedDofs.push(2 * nely + 1); // bottom-right y
  } else {
    // MBB beam: fix bottom-left (x,y) and bottom-right (y)
    fixedDofs.push(2 * nely, 2 * nely + 1);
    fixedDofs.push(2 * (nelx * (nely + 1) + nely) + 1);
  }
  
  const freeDofs: number[] = [];
  const isFixed = new Set(fixedDofs);
  for (let i = 0; i < ndof; i++) {
    if (!isFixed.has(i)) freeDofs.push(i);
  }
  
  let compliance = 0;
  const maxIter = 30;
  
  for (let loop = 0; loop < maxIter; loop++) {
    // Assemble stiffness matrix
    const K = new SparseMatrix(ndof, ndof);
    
    for (let ely = 0; ely < nely; ely++) {
      for (let elx = 0; elx < nelx; elx++) {
        const ne = ely * nelx + elx;
        const xPhys = Math.pow(x[ne], penal);
        
        const n1 = elx * (nely + 1) + ely;
        const n2 = (elx + 1) * (nely + 1) + ely;
        const edof = [2*n1, 2*n1+1, 2*n2, 2*n2+1, 2*(n2+1), 2*(n2+1)+1, 2*(n1+1), 2*(n1+1)+1];
        
        for (let i = 0; i < 8; i++) {
          for (let j = 0; j < 8; j++) {
            K.set(edof[i], edof[j], xPhys * KE[i * 8 + j]);
          }
        }
      }
    }
    
    // Solve system
    const U = solveCG(K, F, 100);
    
    // Compute objective and sensitivities
    const dc = new Float64Array(nelx * nely);
    compliance = 0;
    
    for (let ely = 0; ely < nely; ely++) {
      for (let elx = 0; elx < nelx; elx++) {
        const ne = ely * nelx + elx;
        const xPhys = Math.pow(x[ne], penal);
        
        const n1 = elx * (nely + 1) + ely;
        const n2 = (elx + 1) * (nely + 1) + ely;
        const edof = [2*n1, 2*n1+1, 2*n2, 2*n2+1, 2*(n2+1), 2*(n2+1)+1, 2*(n1+1), 2*(n1+1)+1];
        
        let ce = 0;
        for (let i = 0; i < 8; i++) {
          for (let j = 0; j < 8; j++) {
            ce += U[edof[i]] * KE[i * 8 + j] * U[edof[j]];
          }
        }
        
        compliance += xPhys * ce;
        dc[ne] = -penal * Math.pow(x[ne], penal - 1) * ce;
      }
    }
    
    // Sensitivity filter
    const dcf = new Float64Array(nelx * nely);
    for (let ely = 0; ely < nely; ely++) {
      for (let elx = 0; elx < nelx; elx++) {
        const ne = ely * nelx + elx;
        let sum = 0;
        for (let i = Math.max(0, elx - Math.floor(rmin)); i <= Math.min(nelx - 1, elx + Math.floor(rmin)); i++) {
          for (let j = Math.max(0, ely - Math.floor(rmin)); j <= Math.min(nely - 1, ely + Math.floor(rmin)); j++) {
            const dist = Math.sqrt(Math.pow(elx - i, 2) + Math.pow(ely - j, 2));
            if (dist < rmin) {
              const fac = rmin - dist;
              const nf = j * nelx + i;
              sum += fac * x[nf] * dc[nf];
            }
          }
        }
        dcf[ne] = sum / (x[ne] * Math.PI * rmin * rmin / 4);
      }
    }
    
    // OC update
    let l1 = 0, l2 = 1e9;
    let lmid = (l1 + l2) / 2;
    const move = 0.2;
    
    for (let iter = 0; iter < 50; iter++) {
      lmid = (l1 + l2) / 2;
      let change = 0;
      
      for (let ne = 0; ne < nelx * nely; ne++) {
        const xnew = Math.max(
          0.001,
          Math.max(
            x[ne] - move,
            Math.min(
              1.0,
              Math.min(
                x[ne] + move,
                x[ne] * Math.sqrt(-dcf[ne] / lmid)
              )
            )
          )
        );
        change = Math.max(change, Math.abs(xnew - x[ne]));
        x[ne] = xnew;
      }
      
      const vol = x.reduce((a, b) => a + b, 0) / (nelx * nely);
      
      if (vol > volfrac) {
        l1 = lmid;
      } else {
        l2 = lmid;
      }
      
      if (l2 - l1 < 1e-4 && change < 0.01) break;
    }
    
    if (onProgress) {
      onProgress(loop + 1, new Float32Array(x), compliance);
    }
  }
  
  return {
    density: x,
    iteration: maxIter,
    compliance,
    converged: true
  };
}

// Generate async optimization with yielding
export async function* runOptimizationAsync(
  params: OptimizationParams
): AsyncGenerator<{ iteration: number; density: Float32Array; compliance: number }> {
  const { nelx, nely, volfrac, penal, rmin, bcType } = params;
  
  const ndof = 2 * (nelx + 1) * (nely + 1);
  const KE = lk();
  
  let x = new Float32Array(nelx * nely);
  x.fill(volfrac);
  
  const F = new Float64Array(ndof);
  
  if (bcType === 'cantilever') {
    const loadNode = Math.floor((nely + 1) / 2);
    F[2 * (nelx * (nely + 1) + loadNode) + 1] = -1;
  } else if (bcType === 'bridge') {
    const midX = Math.floor(nelx / 2);
    F[2 * (midX * (nely + 1) + nely) + 1] = -1;
  } else {
    const loadNode = nely;
    F[2 * (0 * (nely + 1) + loadNode) + 1] = -1;
  }
  
  const fixedDofs: number[] = [];
  
  if (bcType === 'cantilever') {
    for (let i = 0; i <= nely; i++) {
      fixedDofs.push(2 * i);
      fixedDofs.push(2 * i + 1);
    }
  } else if (bcType === 'bridge') {
    fixedDofs.push(0, 1);
    fixedDofs.push(2 * nely + 1);
  } else {
    fixedDofs.push(2 * nely, 2 * nely + 1);
    fixedDofs.push(2 * (nelx * (nely + 1) + nely) + 1);
  }
  
  const isFixed = new Set(fixedDofs);
  const maxIter = 40;
  
  for (let loop = 0; loop < maxIter; loop++) {
    const K = new SparseMatrix(ndof, ndof);
    
    for (let ely = 0; ely < nely; ely++) {
      for (let elx = 0; elx < nelx; elx++) {
        const ne = ely * nelx + elx;
        const xPhys = Math.pow(x[ne], penal);
        
        const n1 = elx * (nely + 1) + ely;
        const n2 = (elx + 1) * (nely + 1) + ely;
        const edof = [2*n1, 2*n1+1, 2*n2, 2*n2+1, 2*(n2+1), 2*(n2+1)+1, 2*(n1+1), 2*(n1+1)+1];
        
        for (let i = 0; i < 8; i++) {
          for (let j = 0; j < 8; j++) {
            K.set(edof[i], edof[j], xPhys * KE[i * 8 + j]);
          }
        }
      }
    }
    
    const U = solveCG(K, F, 150);
    
    const dc = new Float64Array(nelx * nely);
    let compliance = 0;
    
    for (let ely = 0; ely < nely; ely++) {
      for (let elx = 0; elx < nelx; elx++) {
        const ne = ely * nelx + elx;
        const xPhys = Math.pow(x[ne], penal);
        
        const n1 = elx * (nely + 1) + ely;
        const n2 = (elx + 1) * (nely + 1) + ely;
        const edof = [2*n1, 2*n1+1, 2*n2, 2*n2+1, 2*(n2+1), 2*(n2+1)+1, 2*(n1+1), 2*(n1+1)+1];
        
        let ce = 0;
        for (let i = 0; i < 8; i++) {
          for (let j = 0; j < 8; j++) {
            ce += U[edof[i]] * KE[i * 8 + j] * U[edof[j]];
          }
        }
        
        compliance += xPhys * ce;
        dc[ne] = -penal * Math.pow(x[ne], penal - 1) * ce;
      }
    }
    
    // Sensitivity filter
    const dcf = new Float64Array(nelx * nely);
    for (let ely = 0; ely < nely; ely++) {
      for (let elx = 0; elx < nelx; elx++) {
        const ne = ely * nelx + elx;
        let sum = 0;
        for (let i = Math.max(0, elx - Math.floor(rmin)); i <= Math.min(nelx - 1, elx + Math.floor(rmin)); i++) {
          for (let j = Math.max(0, ely - Math.floor(rmin)); j <= Math.min(nely - 1, ely + Math.floor(rmin)); j++) {
            const dist = Math.sqrt(Math.pow(elx - i, 2) + Math.pow(ely - j, 2));
            if (dist < rmin) {
              const fac = rmin - dist;
              const nf = j * nelx + i;
              sum += fac * x[nf] * dc[nf];
            }
          }
        }
        dcf[ne] = sum / (x[ne] * Math.PI * rmin * rmin / 4);
      }
    }
    
    // OC update
    let l1 = 0, l2 = 1e9;
    const move = 0.2;
    
    for (let iter = 0; iter < 50; iter++) {
      let lmid = (l1 + l2) / 2;
      let change = 0;
      
      for (let ne = 0; ne < nelx * nely; ne++) {
        const xnew = Math.max(
          0.001,
          Math.max(
            x[ne] - move,
            Math.min(1.0, Math.min(x[ne] + move, x[ne] * Math.sqrt(-dcf[ne] / lmid)))
          )
        );
        change = Math.max(change, Math.abs(xnew - x[ne]));
        x[ne] = xnew;
      }
      
      const vol = x.reduce((a, b) => a + b, 0) / (nelx * nely);
      
      if (vol > volfrac) l1 = lmid;
      else l2 = lmid;
      
      if (l2 - l1 < 1e-4 && change < 0.01) break;
    }
    
    yield { iteration: loop + 1, density: new Float32Array(x), compliance };
    
    // Yield to UI thread
    await new Promise(resolve => setTimeout(resolve, 10));
  }
}
