import { OptimizationParams } from '../utils/topologyOptimization';

interface ControlPanelProps {
  params: OptimizationParams;
  onParamsChange: (params: OptimizationParams) => void;
  isRunning: boolean;
  onRun: () => void;
  onStop: () => void;
  onReset: () => void;
  threshold: number;
  onThresholdChange: (val: number) => void;
  colorMode: 'density' | 'stress';
  onColorModeChange: (mode: 'density' | 'stress') => void;
  showBounds: boolean;
  onShowBoundsChange: (val: boolean) => void;
  autoRotate: boolean;
  onAutoRotateChange: (val: boolean) => void;
}

export default function ControlPanel({
  params,
  onParamsChange,
  isRunning,
  onRun,
  onStop,
  onReset,
  threshold,
  onThresholdChange,
  colorMode,
  onColorModeChange,
  showBounds,
  onShowBoundsChange,
  autoRotate,
  onAutoRotateChange,
}: ControlPanelProps) {
  const updateParam = (key: keyof OptimizationParams, value: number | string) => {
    onParamsChange({ ...params, [key]: value });
  };

  return (
    <div className="h-full overflow-y-auto bg-gray-900/95 backdrop-blur-sm border-r border-gray-700/50">
      <div className="p-4 space-y-5">
        {/* Header */}
        <div className="flex items-center gap-2 pb-3 border-b border-gray-700/50">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
          </div>
          <div>
            <h1 className="text-sm font-bold text-white">Topology Optimization</h1>
            <p className="text-xs text-gray-400">SIMP Method</p>
          </div>
        </div>

        {/* Presets */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
            Quick Presets
          </label>
          <div className="grid grid-cols-2 gap-1">
            <button
              onClick={() => onParamsChange({
                nelx: 40, nely: 20, volfrac: 0.4, penal: 3.0, rmin: 2.0,
                loadX: 1.0, loadY: 0.5, bcType: 'cantilever'
              })}
              className="px-2 py-1.5 text-xs rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors border border-gray-700/50"
            >
              🔧 Cantilever
            </button>
            <button
              onClick={() => onParamsChange({
                nelx: 60, nely: 20, volfrac: 0.4, penal: 3.0, rmin: 2.5,
                loadX: 0.5, loadY: 1.0, bcType: 'bridge'
              })}
              className="px-2 py-1.5 text-xs rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors border border-gray-700/50"
            >
              🌉 Bridge
            </button>
            <button
              onClick={() => onParamsChange({
                nelx: 60, nely: 20, volfrac: 0.5, penal: 3.0, rmin: 2.0,
                loadX: 0.0, loadY: 0.0, bcType: 'mbb'
              })}
              className="px-2 py-1.5 text-xs rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors border border-gray-700/50"
            >
              📐 MBB Beam
            </button>
            <button
              onClick={() => onParamsChange({
                nelx: 30, nely: 30, volfrac: 0.3, penal: 3.0, rmin: 2.0,
                loadX: 1.0, loadY: 0.5, bcType: 'cantilever'
              })}
              className="px-2 py-1.5 text-xs rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors border border-gray-700/50"
            >
              🎨 Fine Mesh
            </button>
          </div>
        </div>

        {/* Boundary Conditions */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
            Boundary Condition
          </label>
          <div className="grid grid-cols-3 gap-1">
            {(['cantilever', 'bridge', 'mbb'] as const).map((type) => (
              <button
                key={type}
                onClick={() => updateParam('bcType', type)}
                className={`px-2 py-2 text-xs rounded-lg font-medium transition-all ${
                  params.bcType === type
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'
                }`}
              >
                {type === 'cantilever' ? 'Cantilever' : type === 'bridge' ? 'Bridge' : 'MBB Beam'}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-500 italic">
            {params.bcType === 'cantilever' && 'Fixed on left edge, load at right middle'}
            {params.bcType === 'bridge' && 'Supported at bottom corners, load at center'}
            {params.bcType === 'mbb' && 'Simply supported, load at top-left'}
          </p>
        </div>

        {/* Mesh Resolution */}
        <div className="space-y-3">
          <label className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
            Mesh Resolution
          </label>
          
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-400">Elements X</span>
              <span className="text-xs text-blue-400 font-mono">{params.nelx}</span>
            </div>
            <input
              type="range"
              min="10"
              max="80"
              step="5"
              value={params.nelx}
              onChange={(e) => updateParam('nelx', parseInt(e.target.value))}
              disabled={isRunning}
              className="w-full h-1.5 bg-gray-700 rounded-full appearance-none cursor-pointer accent-blue-500 disabled:opacity-50"
            />
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-400">Elements Y</span>
              <span className="text-xs text-blue-400 font-mono">{params.nely}</span>
            </div>
            <input
              type="range"
              min="5"
              max="50"
              step="5"
              value={params.nely}
              onChange={(e) => updateParam('nely', parseInt(e.target.value))}
              disabled={isRunning}
              className="w-full h-1.5 bg-gray-700 rounded-full appearance-none cursor-pointer accent-blue-500 disabled:opacity-50"
            />
          </div>
        </div>

        {/* Optimization Parameters */}
        <div className="space-y-3">
          <label className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
            Optimization Parameters
          </label>
          
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-400">Volume Fraction</span>
              <span className="text-xs text-green-400 font-mono">{params.volfrac.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.1"
              max="0.8"
              step="0.05"
              value={params.volfrac}
              onChange={(e) => updateParam('volfrac', parseFloat(e.target.value))}
              disabled={isRunning}
              className="w-full h-1.5 bg-gray-700 rounded-full appearance-none cursor-pointer accent-green-500 disabled:opacity-50"
            />
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-400">Penalization (p)</span>
              <span className="text-xs text-yellow-400 font-mono">{params.penal.toFixed(1)}</span>
            </div>
            <input
              type="range"
              min="1"
              max="5"
              step="0.5"
              value={params.penal}
              onChange={(e) => updateParam('penal', parseFloat(e.target.value))}
              disabled={isRunning}
              className="w-full h-1.5 bg-gray-700 rounded-full appearance-none cursor-pointer accent-yellow-500 disabled:opacity-50"
            />
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-400">Filter Radius</span>
              <span className="text-xs text-purple-400 font-mono">{params.rmin.toFixed(1)}</span>
            </div>
            <input
              type="range"
              min="1"
              max="5"
              step="0.5"
              value={params.rmin}
              onChange={(e) => updateParam('rmin', parseFloat(e.target.value))}
              disabled={isRunning}
              className="w-full h-1.5 bg-gray-700 rounded-full appearance-none cursor-pointer accent-purple-500 disabled:opacity-50"
            />
          </div>
        </div>

        {/* Display Options */}
        <div className="space-y-3">
          <label className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
            Display Options
          </label>
          
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-400">Density Threshold</span>
              <span className="text-xs text-orange-400 font-mono">{threshold.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.01"
              max="0.9"
              step="0.01"
              value={threshold}
              onChange={(e) => onThresholdChange(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-gray-700 rounded-full appearance-none cursor-pointer accent-orange-500"
            />
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400">Color Mode:</span>
            <button
              onClick={() => onColorModeChange(colorMode === 'density' ? 'stress' : 'density')}
              className="px-2 py-1 text-xs rounded bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors"
            >
              {colorMode === 'density' ? '🌊 Density' : '🔥 Stress'}
            </button>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400">Show BCs</span>
            <button
              onClick={() => onShowBoundsChange(!showBounds)}
              className={`w-10 h-5 rounded-full transition-colors ${showBounds ? 'bg-blue-600' : 'bg-gray-700'}`}
            >
              <div className={`w-4 h-4 rounded-full bg-white transition-transform ${showBounds ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </button>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400">Auto Rotate</span>
            <button
              onClick={() => onAutoRotateChange(!autoRotate)}
              className={`w-10 h-5 rounded-full transition-colors ${autoRotate ? 'bg-blue-600' : 'bg-gray-700'}`}
            >
              <div className={`w-4 h-4 rounded-full bg-white transition-transform ${autoRotate ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </button>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="space-y-2 pt-3 border-t border-gray-700/50">
          {!isRunning ? (
            <button
              onClick={onRun}
              className="w-full py-2.5 px-4 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 text-white text-sm font-semibold rounded-lg shadow-lg shadow-blue-600/20 transition-all hover:shadow-blue-600/40 active:scale-95"
            >
              ▶ Run Optimization
            </button>
          ) : (
            <button
              onClick={onStop}
              className="w-full py-2.5 px-4 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white text-sm font-semibold rounded-lg shadow-lg shadow-red-600/20 transition-all active:scale-95"
            >
              ■ Stop
            </button>
          )}
          <button
            onClick={onReset}
            className="w-full py-2 px-4 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium rounded-lg transition-colors"
          >
            ↺ Reset
          </button>
        </div>

        {/* Algorithm Info */}
        <div className="space-y-2 pt-3 border-t border-gray-700/50">
          <details className="group">
            <summary className="text-xs font-semibold text-gray-300 uppercase tracking-wider cursor-pointer hover:text-white transition-colors list-none flex items-center gap-1">
              <span className="group-open:rotate-90 transition-transform">▶</span>
              About SIMP Algorithm
            </summary>
            <div className="mt-2 text-xs text-gray-500 space-y-1.5 leading-relaxed">
              <p>
                <strong className="text-gray-400">SIMP</strong> (Solid Isotropic Material with Penalization) is a widely-used topology optimization method.
              </p>
              <p>
                <strong className="text-gray-400">Volume Fraction:</strong> Target ratio of material in the design domain.
              </p>
              <p>
                <strong className="text-gray-400">Penalization (p):</strong> Controls the black-and-white nature of the solution. Higher values push densities toward 0 or 1.
              </p>
              <p>
                <strong className="text-gray-400">Filter Radius:</strong> Ensures mesh-independent solutions and controls minimum member size.
              </p>
              <p className="text-gray-600 pt-1 border-t border-gray-800">
                Based on Sigmund (2001). Uses OC (Optimality Criteria) update scheme with sensitivity filtering.
              </p>
            </div>
          </details>
        </div>
      </div>
    </div>
  );
}
