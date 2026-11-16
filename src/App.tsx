import { useState } from 'react';

function App() {
  const [activeTab, setActiveTab] = useState<'overview' | 'install' | 'usage' | 'algorithm'>('overview');
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const copyCode = (code: string, id: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(id);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Hero Section */}
      <header className="relative overflow-hidden border-b border-gray-800">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-900/20 via-purple-900/10 to-transparent" />
        <div className="absolute inset-0">
          <div className="absolute top-10 left-10 w-72 h-72 bg-blue-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-10 right-10 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
        </div>
        
        <div className="relative max-w-6xl mx-auto px-6 py-16">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
              </svg>
            </div>
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                Topology Optimization
              </h1>
              <p className="text-sm text-gray-400">for CAD Models • Python Executable</p>
            </div>
          </div>
          
          <p className="text-lg text-gray-300 max-w-2xl mt-6 leading-relaxed">
            A standalone Python application for performing <strong className="text-blue-400">SIMP-based topology optimization</strong> on 
            arbitrary CAD geometries. Automatically handles mesh voxelization, hollowness enforcement, 
            and structural optimization with real-time 3D visualization.
          </p>
          
          <div className="flex flex-wrap gap-3 mt-8">
            <a href="#install" className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors shadow-lg shadow-blue-600/20">
              Get Started
            </a>
            <a href="#overview" className="px-5 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg font-medium transition-colors border border-gray-700">
              View Documentation
            </a>
          </div>
          
          {/* Feature badges */}
          <div className="flex flex-wrap gap-2 mt-8">
            {['Arbitrary Geometry', 'Auto Hollowness', 'SIMP Algorithm', '3D Visualization', 'STL Export', 'Cross-Platform'].map((feat) => (
              <span key={feat} className="px-3 py-1 text-xs bg-gray-800/80 border border-gray-700/50 rounded-full text-gray-300">
                {feat}
              </span>
            ))}
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="sticky top-0 z-10 bg-gray-950/95 backdrop-blur-sm border-b border-gray-800">
        <div className="max-w-6xl mx-auto px-6">
          <div className="flex gap-1 py-2">
            {[
              { id: 'overview', label: 'Overview', icon: '📋' },
              { id: 'install', label: 'Installation', icon: '📦' },
              { id: 'usage', label: 'Usage', icon: '🚀' },
              { id: 'algorithm', label: 'Algorithm', icon: '🧮' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
                }`}
              >
                <span className="mr-1.5">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-6 py-12">
        {activeTab === 'overview' && <OverviewSection />}
        {activeTab === 'install' && <InstallSection copyCode={copyCode} copiedCode={copiedCode} />}
        {activeTab === 'usage' && <UsageSection copyCode={copyCode} copiedCode={copiedCode} />}
        {activeTab === 'algorithm' && <AlgorithmSection />}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-8">
        <div className="max-w-6xl mx-auto px-6 text-center text-sm text-gray-500">
          <p>Topology Optimization for CAD Models • SIMP Method • Python Executable</p>
          <p className="mt-1">Based on Sigmund (2001) • MIT License</p>
        </div>
      </footer>
    </div>
  );
}

function OverviewSection() {
  return (
    <div className="space-y-10">
      <section id="overview">
        <h2 className="text-2xl font-bold text-white mb-6">What It Does</h2>
        <div className="grid md:grid-cols-2 gap-6">
          <FeatureCard
            icon="🔲"
            title="Arbitrary Geometry Input"
            description="Import any CAD model in STL, OBJ, PLY, or OFF format. The tool automatically voxelizes the mesh and prepares it for optimization."
          />
          <FeatureCard
            icon="🕳️"
            title="Automatic Hollowness"
            description="Ensures sufficient interior void space so the optimizer can redistribute material. Preserves minimum wall thickness for structural integrity."
          />
          <FeatureCard
            icon="🧮"
            title="SIMP Algorithm"
            description="Industry-standard Solid Isotropic Material with Penalization method with sensitivity filtering and Optimality Criteria update."
          />
          <FeatureCard
            icon="🎨"
            title="3D Visualization"
            description="Real-time pyvista-based viewport showing optimization progress with density coloring and boundary condition display."
          />
          <FeatureCard
            icon="⚙️"
            title="Configurable Parameters"
            description="Volume fraction, penalization power, filter radius, wall thickness, boundary conditions — all adjustable in GUI or CLI."
          />
          <FeatureCard
            icon="💾"
            title="Export Results"
            description="Save optimized geometry as STL or OBJ. Also export raw density fields and convergence history as CSV."
          />
        </div>
      </section>

      <section>
        <h2 className="text-2xl font-bold text-white mb-6">Architecture</h2>
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 font-mono text-sm">
          <pre className="text-gray-300 overflow-x-auto">{`python_app/
├── main.py                    # Entry point (GUI + CLI)
├── requirements.txt           # Dependencies
├── build_executable.py        # PyInstaller build script
├── README.md                  # Documentation
└── src/
    ├── core/
    │   ├── mesh_utils.py      # Mesh loading, voxelization, hollowness
    │   ├── fea.py             # Finite element analysis (hex8 elements)
    │   └── optimizer.py       # SIMP topology optimization
    ├── gui/
    │   └── main_window.py     # PyQt5 GUI with pyvista viewport
    └── utils/
        └── exporters.py       # STL/OBJ export utilities`}</pre>
        </div>
      </section>

      <section>
        <h2 className="text-2xl font-bold text-white mb-6">How Hollowness Works</h2>
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="space-y-4">
            <Step num={1} title="Voxelize Input Mesh" desc="Convert the CAD geometry into a 3D boolean grid at user-specified resolution." />
            <Step num={2} title="Identify Surface Shell" desc="Find voxels adjacent to empty space — these form the fixed outer boundary." />
            <Step num={3} title="Erode Interior" desc="Remove interior voxels (erode by min_wall_thickness) to create the design space." />
            <Step num={4} title="Initialize Densities" desc="Shell = density 1.0 (fixed), Design space = volfrac (optimizable), Outside = 0.0" />
            <Step num={5} title="Optimize" desc="SIMP algorithm redistributes material within the design space while preserving the shell." />
          </div>
        </div>
      </section>
    </div>
  );
}

function InstallSection({ copyCode, copiedCode }: { copyCode: (code: string, id: string) => void; copiedCode: string | null }) {
  return (
    <div className="space-y-8" id="install">
      <section>
        <h2 className="text-2xl font-bold text-white mb-6">Installation</h2>
        
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-200 mb-3">Prerequisites</h3>
            <ul className="space-y-2 text-gray-400">
              <li className="flex items-center gap-2"><span className="text-green-400">✓</span> Python 3.9 or higher</li>
              <li className="flex items-center gap-2"><span className="text-green-400">✓</span> pip package manager</li>
              <li className="flex items-center gap-2"><span className="text-green-400">✓</span> (Optional) PyInstaller for building executables</li>
            </ul>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-200 mb-3">1. Install Dependencies</h3>
            <CodeBlock
              id="install-deps"
              code={`cd python_app
pip install -r requirements.txt`}
              copyCode={copyCode}
              copiedCode={copiedCode}
            />
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-200 mb-3">2. Run the Application</h3>
            <CodeBlock
              id="run-app"
              code={`# Launch GUI
python main.py

# Or run in CLI mode
python main.py --cli --test beam`}
              copyCode={copyCode}
              copiedCode={copiedCode}
            />
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-200 mb-3">3. Build Executable (Optional)</h3>
            <CodeBlock
              id="build-exe"
              code={`# Build standalone executable
python build_executable.py

# Output:
#   Windows: dist/TopologyOptimizer.exe
#   macOS:   dist/TopologyOptimizer
#   Linux:   dist/TopologyOptimizer`}
              copyCode={copyCode}
              copiedCode={copiedCode}
            />
          </div>

          <div className="bg-yellow-900/20 border border-yellow-700/30 rounded-lg p-4">
            <h4 className="text-yellow-400 font-medium mb-2">⚠️ Troubleshooting</h4>
            <div className="text-sm text-gray-400 space-y-2">
              <p><code className="text-yellow-300 bg-gray-800 px-1 rounded">pip install pyvistaqt</code> — if pyvistaqt is not found</p>
              <p><code className="text-yellow-300 bg-gray-800 px-1 rounded">pip install vtk --upgrade</code> — if VTK issues occur</p>
              <p><code className="text-yellow-300 bg-gray-800 px-1 rounded">pip install manifold3d</code> — if boolean operations fail</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function UsageSection({ copyCode, copiedCode }: { copyCode: (code: string, id: string) => void; copiedCode: string | null }) {
  return (
    <div className="space-y-8" id="usage">
      <section>
        <h2 className="text-2xl font-bold text-white mb-6">Usage Guide</h2>
        
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-200 mb-3">GUI Mode</h3>
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
              <ol className="space-y-3 text-gray-300">
                <li className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600/20 text-blue-400 flex items-center justify-center text-xs font-bold">1</span>
                  <span><strong>Load Geometry</strong> — Click "Load CAD Model" to import STL/OBJ, or "Test Geometry" for built-in examples</span>
                </li>
                <li className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600/20 text-blue-400 flex items-center justify-center text-xs font-bold">2</span>
                  <span><strong>Configure Parameters</strong> — Set volume fraction, penalization, filter radius, wall thickness, BC type</span>
                </li>
                <li className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600/20 text-blue-400 flex items-center justify-center text-xs font-bold">3</span>
                  <span><strong>Voxelize</strong> — Click "Voxelize Geometry" to convert mesh to voxel grid with hollowness</span>
                </li>
                <li className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600/20 text-blue-400 flex items-center justify-center text-xs font-bold">4</span>
                  <span><strong>Optimize</strong> — Click "Run Optimization" to start the SIMP algorithm</span>
                </li>
                <li className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600/20 text-blue-400 flex items-center justify-center text-xs font-bold">5</span>
                  <span><strong>Export</strong> — Save optimized result as STL with adjustable density threshold</span>
                </li>
              </ol>
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-200 mb-3">Command-Line Mode</h3>
            <CodeBlock
              id="cli-basic"
              code={`# Optimize an imported CAD file
python main.py --cli --input model.stl --volfrac 0.4 --penal 3.0

# Use built-in test geometry
python main.py --cli --test beam --bc-type cantilever --max-iter 50

# L-bracket with bridge supports
python main.py --cli --test l_bracket --bc-type bridge --volfrac 0.3

# High resolution optimization
python main.py --cli --input part.stl --resolution 50 --max-iter 80 --wall-thickness 3`}
              copyCode={copyCode}
              copiedCode={copiedCode}
            />
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-200 mb-3">All CLI Options</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Option</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Default</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Description</th>
                  </tr>
                </thead>
                <tbody className="text-gray-300">
                  <tr className="border-b border-gray-800/50">
                    <td className="py-2 px-3 font-mono text-blue-400">--input, -i</td>
                    <td className="py-2 px-3 text-gray-500">None</td>
                    <td className="py-2 px-3">Input CAD file (STL, OBJ, etc.)</td>
                  </tr>
                  <tr className="border-b border-gray-800/50">
                    <td className="py-2 px-3 font-mono text-blue-400">--output, -o</td>
                    <td className="py-2 px-3 text-gray-500">optimized_result.stl</td>
                    <td className="py-2 px-3">Output file path</td>
                  </tr>
                  <tr className="border-b border-gray-800/50">
                    <td className="py-2 px-3 font-mono text-blue-400">--volfrac</td>
                    <td className="py-2 px-3 text-gray-500">0.4</td>
                    <td className="py-2 px-3">Volume fraction constraint (0.1–0.9)</td>
                  </tr>
                  <tr className="border-b border-gray-800/50">
                    <td className="py-2 px-3 font-mono text-blue-400">--penal</td>
                    <td className="py-2 px-3 text-gray-500">3.0</td>
                    <td className="py-2 px-3">SIMP penalization power</td>
                  </tr>
                  <tr className="border-b border-gray-800/50">
                    <td className="py-2 px-3 font-mono text-blue-400">--filter-radius</td>
                    <td className="py-2 px-3 text-gray-500">2.0</td>
                    <td className="py-2 px-3">Sensitivity filter radius (voxels)</td>
                  </tr>
                  <tr className="border-b border-gray-800/50">
                    <td className="py-2 px-3 font-mono text-blue-400">--max-iter</td>
                    <td className="py-2 px-3 text-gray-500">50</td>
                    <td className="py-2 px-3">Maximum optimization iterations</td>
                  </tr>
                  <tr className="border-b border-gray-800/50">
                    <td className="py-2 px-3 font-mono text-blue-400">--resolution</td>
                    <td className="py-2 px-3 text-gray-500">30</td>
                    <td className="py-2 px-3">Voxel resolution along longest axis</td>
                  </tr>
                  <tr className="border-b border-gray-800/50">
                    <td className="py-2 px-3 font-mono text-blue-400">--wall-thickness</td>
                    <td className="py-2 px-3 text-gray-500">2</td>
                    <td className="py-2 px-3">Minimum wall thickness (voxels)</td>
                  </tr>
                  <tr className="border-b border-gray-800/50">
                    <td className="py-2 px-3 font-mono text-blue-400">--hollow-fraction</td>
                    <td className="py-2 px-3 text-gray-500">0.6</td>
                    <td className="py-2 px-3">Interior hollow fraction (0–1)</td>
                  </tr>
                  <tr className="border-b border-gray-800/50">
                    <td className="py-2 px-3 font-mono text-blue-400">--threshold</td>
                    <td className="py-2 px-3 text-gray-500">0.5</td>
                    <td className="py-2 px-3">Density threshold for STL export</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-mono text-blue-400">--bc-type</td>
                    <td className="py-2 px-3 text-gray-500">cantilever</td>
                    <td className="py-2 px-3">Boundary condition type</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function AlgorithmSection() {
  return (
    <div className="space-y-8" id="algorithm">
      <section>
        <h2 className="text-2xl font-bold text-white mb-6">SIMP Algorithm</h2>
        
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 space-y-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-200 mb-3">Material Interpolation</h3>
            <p className="text-gray-400 mb-4">
              The SIMP method uses power-law interpolation of material stiffness:
            </p>
            <div className="bg-gray-800 rounded-lg p-4 text-center font-mono text-lg text-blue-400">
              E(x) = x<sup>p</sup> · E₀
            </div>
            <p className="text-gray-500 text-sm mt-2">
              where x ∈ [0,1] is relative density, p is penalization power (typically 3), and E₀ is solid Young's modulus.
            </p>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-200 mb-3">Optimization Problem</h3>
            <div className="bg-gray-800 rounded-lg p-4 font-mono text-sm text-gray-300">
              <pre>{`minimize:  c(x) = FᵀU = UᵀKU    (compliance)
subject to: V(x)/V₀ ≤ f          (volume constraint)
            KU = F                  (equilibrium)
            0 < x_min ≤ x ≤ 1      (density bounds)`}</pre>
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-200 mb-3">Iteration Loop</h3>
            <div className="space-y-3">
              <Step num={1} title="Assemble K" desc="Build global stiffness matrix using SIMP: K = Σ x_e^p · K_e" />
              <Step num={2} title="Solve FE" desc="Solve Ku = F using Conjugate Gradient solver" />
              <Step num={3} title="Sensitivities" desc="Compute ∂c/∂x_e = -p·x_e^(p-1)·u_e^T·K_e·u_e" />
              <Step num={4} title="Filter" desc="Apply sensitivity filter to prevent checkerboarding" />
              <Step num={5} title="OC Update" desc="Update densities using Optimality Criteria method" />
              <Step num={6} title="Converge?" desc="Check if change < tolerance, repeat if not" />
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-200 mb-3">Hollowness Enforcement</h3>
            <p className="text-gray-400 mb-4">
              For arbitrary geometries, the tool ensures sufficient interior void:
            </p>
            <div className="bg-gray-800 rounded-lg p-4 font-mono text-sm text-gray-300">
              <pre>{`1. Voxelize mesh → binary 3D grid
2. Surface detection → identify shell voxels (6-connected neighbors)
3. Erosion → remove interior by min_wall_thickness
4. Design space = interior - eroded_core
5. Initialize: shell=1.0, design=volfrac, outside=0.0`}</pre>
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-200 mb-3">FEA Details</h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="bg-gray-800 rounded-lg p-4">
                <h4 className="text-blue-400 font-medium mb-2">Element Type</h4>
                <p className="text-sm text-gray-400">8-node hexahedral (hex8) with 2×2×2 Gauss quadrature</p>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <h4 className="text-blue-400 font-medium mb-2">Solver</h4>
                <p className="text-sm text-gray-400">Scipy sparse CG with fallback to direct solver</p>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <h4 className="text-blue-400 font-medium mb-2">Material</h4>
                <p className="text-sm text-gray-400">3D isotropic elasticity (E=1, ν=0.3)</p>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <h4 className="text-blue-400 font-medium mb-2">Filter</h4>
                <p className="text-sm text-gray-400">Sensitivity filter with radius r_min</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-2xl font-bold text-white mb-6">Parameter Guide</h2>
        <div className="grid md:grid-cols-2 gap-4">
          <ParamCard
            name="Volume Fraction"
            value="0.3 – 0.5"
            description="Lower = lighter structure, more optimization freedom. Higher = more material retained."
          />
          <ParamCard
            name="Penalization (p)"
            value="3.0"
            description="Controls solid/void clarity. p=1 gives grayscale, p=3+ gives clear black/white. Max recommended: 5."
          />
          <ParamCard
            name="Filter Radius"
            value="1.5 – 3.0"
            description="Controls minimum feature size. Larger = smoother, bigger features. Must be ≥ 1.5 to prevent checkerboarding."
          />
          <ParamCard
            name="Wall Thickness"
            value="2 – 3 voxels"
            description="Minimum preserved shell thickness. Ensures structural integrity of outer boundary."
          />
          <ParamCard
            name="Resolution"
            value="20 – 50"
            description="Voxels along longest axis. Higher = more detail but slower. Start with 25 for quick tests."
          />
          <ParamCard
            name="Hollow Fraction"
            value="0.5 – 0.7"
            description="How much interior to hollow out. Higher = more room for optimization, thinner internal structures."
          />
        </div>
      </section>
    </div>
  );
}

// Reusable components

function FeatureCard({ icon, title, description }: { icon: string; title: string; description: string }) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-5 hover:border-gray-700 transition-colors">
      <div className="text-2xl mb-3">{icon}</div>
      <h3 className="text-white font-semibold mb-2">{title}</h3>
      <p className="text-sm text-gray-400 leading-relaxed">{description}</p>
    </div>
  );
}

function Step({ num, title, desc }: { num: number; title: string; desc: string }) {
  return (
    <div className="flex gap-4 items-start">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600/20 text-blue-400 flex items-center justify-center text-sm font-bold border border-blue-500/30">
        {num}
      </div>
      <div>
        <h4 className="text-white font-medium">{title}</h4>
        <p className="text-sm text-gray-400 mt-0.5">{desc}</p>
      </div>
    </div>
  );
}

function CodeBlock({ id, code, copyCode, copiedCode }: { id: string; code: string; copyCode: (code: string, id: string) => void; copiedCode: string | null }) {
  return (
    <div className="relative bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800/50 border-b border-gray-800">
        <span className="text-xs text-gray-500 font-mono">bash</span>
        <button
          onClick={() => copyCode(code, id)}
          className="text-xs text-gray-400 hover:text-white transition-colors px-2 py-1 rounded hover:bg-gray-700"
        >
          {copiedCode === id ? '✓ Copied!' : '📋 Copy'}
        </button>
      </div>
      <pre className="p-4 text-sm text-gray-300 font-mono overflow-x-auto">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function ParamCard({ name, value, description }: { name: string; value: string; description: string }) {
  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-white font-medium text-sm">{name}</h4>
        <span className="text-xs font-mono text-blue-400 bg-blue-600/10 px-2 py-0.5 rounded">{value}</span>
      </div>
      <p className="text-xs text-gray-400 leading-relaxed">{description}</p>
    </div>
  );
}

export default App;
