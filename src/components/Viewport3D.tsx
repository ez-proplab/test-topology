import { useRef, useMemo, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Grid } from '@react-three/drei';
import * as THREE from 'three';

interface DensityMeshProps {
  density: Float32Array;
  nelx: number;
  nely: number;
  threshold: number;
  colorMode: 'density' | 'stress';
}

function DensityMesh({ density, nelx, nely, threshold, colorMode }: DensityMeshProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const count = nelx * nely;
  
  const { matrices, colors } = useMemo(() => {
    const matrices: THREE.Matrix4[] = [];
    const colors: Float32Array = new Float32Array(count * 3);
    const matrix = new THREE.Matrix4();
    
    for (let ely = 0; ely < nely; ely++) {
      for (let elx = 0; elx < nelx; elx++) {
        const idx = ely * nelx + elx;
        const d = density[idx];
        
        if (d > threshold) {
          const scale = Math.max(0.1, d);
          matrix.makeScale(scale, scale, scale);
          matrix.setPosition(elx - nelx / 2 + 0.5, nely - ely - 0.5, 0);
          matrices.push(matrix.clone());
          
          // Color based on density
          if (colorMode === 'density') {
            // Cool blue to warm orange gradient
            const t = d;
            const r = 0.15 + 0.85 * t;
            const g = 0.3 + 0.5 * t * (1 - t) * 4;
            const b = 0.9 - 0.7 * t;
            colors[(matrices.length - 1) * 3] = r;
            colors[(matrices.length - 1) * 3 + 1] = g;
            colors[(matrices.length - 1) * 3 + 2] = b;
          } else {
            // Stress-like coloring (heat map)
            const stress = 1 - d;
            if (stress < 0.25) {
              colors[(matrices.length - 1) * 3] = 0.2;
              colors[(matrices.length - 1) * 3 + 1] = 0.3 + stress * 2.8;
              colors[(matrices.length - 1) * 3 + 2] = 0.8 - stress * 2;
            } else if (stress < 0.5) {
              const t = (stress - 0.25) * 4;
              colors[(matrices.length - 1) * 3] = 0.2 + t * 0.6;
              colors[(matrices.length - 1) * 3 + 1] = 0.8 + t * 0.2;
              colors[(matrices.length - 1) * 3 + 2] = 0.3 - t * 0.3;
            } else if (stress < 0.75) {
              const t = (stress - 0.5) * 4;
              colors[(matrices.length - 1) * 3] = 0.8 + t * 0.2;
              colors[(matrices.length - 1) * 3 + 1] = 1.0 - t * 0.5;
              colors[(matrices.length - 1) * 3 + 2] = 0.0;
            } else {
              const t = (stress - 0.75) * 4;
              colors[(matrices.length - 1) * 3] = 1.0;
              colors[(matrices.length - 1) * 3 + 1] = 0.5 - t * 0.5;
              colors[(matrices.length - 1) * 3 + 2] = 0.0;
            }
          }
        }
      }
    }
    
    return { matrices, colors };
  }, [density, nelx, nely, threshold, colorMode]);
  
  useEffect(() => {
    if (!meshRef.current) return;
    
    const color = new THREE.Color();
    matrices.forEach((mat, i) => {
      meshRef.current!.setMatrixAt(i, mat);
      color.setRGB(colors[i * 3], colors[i * 3 + 1], colors[i * 3 + 2]);
      meshRef.current!.setColorAt(i, color);
    });
    
    meshRef.current.instanceMatrix.needsUpdate = true;
    if (meshRef.current.instanceColor) {
      meshRef.current.instanceColor.needsUpdate = true;
    }
    meshRef.current.count = matrices.length;
  }, [matrices, colors]);
  
  if (matrices.length === 0) return null;
  
  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, matrices.length]}>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial vertexColors metalness={0.3} roughness={0.5} />
    </instancedMesh>
  );
}

function BoundaryConditions({ nelx, nely, bcType }: { nelx: number; nely: number; bcType: string }) {
  const arrowLength = 1.5;
  const arrowColor = '#ef4444';
  const constraintColor = '#3b82f6';
  
  const constraints: JSX.Element[] = [];
  const loads: JSX.Element[] = [];
  
  if (bcType === 'cantilever') {
    // Constraints on left edge
    for (let i = 0; i <= nely; i += Math.max(1, Math.floor(nely / 4))) {
      constraints.push(
        <mesh key={`c-${i}`} position={[-nelx / 2 - 0.5, nely - i - 0.5, 0]}>
          <sphereGeometry args={[0.3, 8, 8]} />
          <meshStandardMaterial color={constraintColor} />
        </mesh>
      );
    }
    // Load on right middle
    const loadY = nely - Math.floor((nely + 1) / 2) - 0.5;
    loads.push(
      <group key="load" position={[nelx / 2 + 0.5, loadY, 0]}>
        <mesh position={[0, arrowLength / 2, 0]}>
          <cylinderGeometry args={[0.1, 0.1, arrowLength, 8]} />
          <meshStandardMaterial color={arrowColor} />
        </mesh>
        <mesh position={[0, arrowLength, 0]}>
          <coneGeometry args={[0.3, 0.5, 8]} />
          <meshStandardMaterial color={arrowColor} />
        </mesh>
      </group>
    );
  } else if (bcType === 'bridge') {
    // Support at bottom corners
    constraints.push(
      <mesh key="c-left" position={[-nelx / 2 - 0.5, -0.5, 0]}>
        <sphereGeometry args={[0.3, 8, 8]} />
        <meshStandardMaterial color={constraintColor} />
      </mesh>
    );
    constraints.push(
      <mesh key="c-right" position={[nelx / 2 + 0.5, -0.5, 0]}>
        <sphereGeometry args={[0.3, 8, 8]} />
        <meshStandardMaterial color={constraintColor} />
      </mesh>
    );
    // Load at center bottom
    const midX = Math.floor(nelx / 2) - nelx / 2 + 0.5;
    loads.push(
      <group key="load" position={[midX, -1.5, 0]}>
        <mesh position={[0, arrowLength / 2, 0]}>
          <cylinderGeometry args={[0.1, 0.1, arrowLength, 8]} />
          <meshStandardMaterial color={arrowColor} />
        </mesh>
        <mesh position={[0, arrowLength, 0]}>
          <coneGeometry args={[0.3, 0.5, 8]} />
          <meshStandardMaterial color={arrowColor} />
        </mesh>
      </group>
    );
  } else {
    // MBB beam
    constraints.push(
      <mesh key="c-left" position={[-nelx / 2 - 0.5, -0.5, 0]}>
        <sphereGeometry args={[0.3, 8, 8]} />
        <meshStandardMaterial color={constraintColor} />
      </mesh>
    );
    constraints.push(
      <mesh key="c-right" position={[nelx / 2 + 0.5, -0.5, 0]}>
        <sphereGeometry args={[0.3, 8, 8]} />
        <meshStandardMaterial color={constraintColor} />
      </mesh>
    );
    // Load at top-left
    loads.push(
      <group key="load" position={[-nelx / 2 + 0.5, nely + 1.5, 0]}>
        <mesh position={[0, -arrowLength / 2, 0]}>
          <cylinderGeometry args={[0.1, 0.1, arrowLength, 8]} />
          <meshStandardMaterial color={arrowColor} />
        </mesh>
        <mesh position={[0, -arrowLength, 0]} rotation={[Math.PI, 0, 0]}>
          <coneGeometry args={[0.3, 0.5, 8]} />
          <meshStandardMaterial color={arrowColor} />
        </mesh>
      </group>
    );
  }
  
  return (
    <group>
      {constraints}
      {loads}
    </group>
  );
}

function RotatingGroup({ children, autoRotate }: { children: React.ReactNode; autoRotate: boolean }) {
  const groupRef = useRef<THREE.Group>(null);
  
  useFrame((_, delta) => {
    if (autoRotate && groupRef.current) {
      groupRef.current.rotation.y += delta * 0.2;
    }
  });
  
  return <group ref={groupRef}>{children}</group>;
}

interface Viewport3DProps {
  density: Float32Array | null;
  nelx: number;
  nely: number;
  threshold: number;
  colorMode: 'density' | 'stress';
  bcType: string;
  showBounds: boolean;
  autoRotate: boolean;
}

export default function Viewport3D({ density, nelx, nely, threshold, colorMode, bcType, showBounds, autoRotate }: Viewport3DProps) {
  const cameraDistance = Math.max(nelx, nely) * 1.5;
  const centerY = nely / 2 - 0.5;
  
  return (
    <div className="w-full h-full relative">
      <Canvas
        camera={{ position: [0, centerY, cameraDistance], fov: 50 }}
        gl={{ antialias: true }}
      >
        <ambientLight intensity={0.4} />
        <directionalLight position={[10, 10, 10]} intensity={1} />
        <directionalLight position={[-5, -5, 5]} intensity={0.3} />
        
        <RotatingGroup autoRotate={autoRotate}>
          {density && (
            <DensityMesh
              density={density}
              nelx={nelx}
              nely={nely}
              threshold={threshold}
              colorMode={colorMode}
            />
          )}
          
          {showBounds && (
            <BoundaryConditions nelx={nelx} nely={nely} bcType={bcType} />
          )}
          
          {/* Design space outline */}
          <lineSegments position={[0, nely / 2 - 0.5, -0.1]}>
            <edgesGeometry args={[new THREE.BoxGeometry(nelx, nely, 0.01)]} />
            <lineBasicMaterial color="#666" />
          </lineSegments>
        </RotatingGroup>
        
        <Grid
          position={[0, -1, 0]}
          args={[50, 50]}
          cellSize={1}
          cellThickness={0.5}
          cellColor="#404040"
          sectionSize={5}
          sectionThickness={1}
          sectionColor="#606060"
          fadeDistance={50}
          infiniteGrid
        />
        
        <OrbitControls
          enableDamping
          dampingFactor={0.1}
          minDistance={5}
          maxDistance={200}
        />
      </Canvas>
      
      {/* Color legend */}
      <div className="absolute bottom-4 right-4 bg-gray-900/80 backdrop-blur-sm rounded-lg p-2 border border-gray-700/50">
        <div className="text-xs text-gray-400 mb-1 font-medium">
          {colorMode === 'density' ? 'Relative Density' : 'Stress Level'}
        </div>
        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-500">Low</span>
          <div className="w-20 h-3 rounded-sm" style={{
            background: colorMode === 'density' 
              ? 'linear-gradient(to right, #cc4444, #44cc66, #4488ee)' 
              : 'linear-gradient(to right, #44cc44, #cccc44, #cc4444)'
          }} />
          <span className="text-xs text-gray-500">High</span>
        </div>
      </div>
      
      {/* Axis indicator */}
      <div className="absolute bottom-4 left-4 text-xs text-gray-400 font-mono">
        <div className="flex items-center gap-2">
          <span className="text-red-400">X</span>
          <span className="text-green-400">Y</span>
          <span className="text-blue-400">Z</span>
        </div>
      </div>
    </div>
  );
}
