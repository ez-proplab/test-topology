import { useState, useRef, useCallback } from 'react';
import Viewport3D from './components/Viewport3D';
import ControlPanel from './components/ControlPanel';
import StatusPanel from './components/StatusPanel';
import ConvergenceChart from './components/ConvergenceChart';
import { OptimizationParams, runOptimizationAsync } from './utils/topologyOptimization';

function App() {
  const [params, setParams] = useState<OptimizationParams>({
    nelx: 40,
    nely: 20,
    volfrac: 0.4,
    penal: 3.0,
    rmin: 2.0,
    loadX: 1.0,
    loadY: 0.5,
    bcType: 'cantilever',
  });

  const [density, setDensity] = useState<Float32Array | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [currentIteration, setCurrentIteration] = useState(0);
  const [compliance, setCompliance] = useState(0);
  const [complianceHistory, setComplianceHistory] = useState<number[]>([]);
  const [threshold, setThreshold] = useState(0.3);
  const [colorMode, setColorMode] = useState<'density' | 'stress'>('density');
  const [showBounds, setShowBounds] = useState(true);
  const [autoRotate, setAutoRotate] = useState(false);
  const [showChart, setShowChart] = useState(true);
  
  const stopRef = useRef(false);

  const handleRun = useCallback(async () => {
    setIsRunning(true);
    stopRef.current = false;
    setCurrentIteration(0);
    setCompliance(0);
    setComplianceHistory([]);
    setDensity(null);

    try {
      const gen = runOptimizationAsync(params);
      
      for await (const result of gen) {
        if (stopRef.current) break;
        
        setDensity(result.density);
        setCurrentIteration(result.iteration);
        setCompliance(result.compliance);
        setComplianceHistory(prev => [...prev, result.compliance]);
      }
    } catch (err) {
      console.error('Optimization error:', err);
    } finally {
      setIsRunning(false);
    }
  }, [params]);

  const handleStop = useCallback(() => {
    stopRef.current = true;
  }, []);

  const handleReset = useCallback(() => {
    stopRef.current = true;
    setIsRunning(false);
    setDensity(null);
    setCurrentIteration(0);
    setCompliance(0);
    setComplianceHistory([]);
  }, []);

  return (
    <div className="h-screen w-screen flex flex-col bg-gray-950 overflow-hidden">
      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left sidebar - Controls */}
        <div className="w-72 flex-shrink-0">
          <ControlPanel
            params={params}
            onParamsChange={setParams}
            isRunning={isRunning}
            onRun={handleRun}
            onStop={handleStop}
            onReset={handleReset}
            threshold={threshold}
            onThresholdChange={setThreshold}
            colorMode={colorMode}
            onColorModeChange={setColorMode}
            showBounds={showBounds}
            onShowBoundsChange={setShowBounds}
            autoRotate={autoRotate}
            onAutoRotateChange={setAutoRotate}
          />
        </div>

        {/* Center - 3D Viewport */}
        <div className="flex-1 relative flex flex-col">
          <div className="flex-1 relative">
            <Viewport3D
              density={density}
              nelx={params.nelx}
              nely={params.nely}
              threshold={threshold}
              colorMode={colorMode}
              bcType={params.bcType}
              showBounds={showBounds}
              autoRotate={autoRotate}
            />
            
            {/* Overlay info when no result */}
            {!density && !isRunning && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="text-center space-y-4 bg-gray-900/80 backdrop-blur-sm rounded-2xl p-8 border border-gray-700/50 max-w-md">
                  <div className="w-16 h-16 mx-auto rounded-full bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center border border-blue-500/30">
                    <svg className="w-8 h-8 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
                    </svg>
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-white">Topology Optimization</h2>
                    <p className="text-sm text-gray-400 mt-2">
                      Configure parameters in the left panel and click <strong className="text-blue-400">Run Optimization</strong> to generate an optimal material layout using the SIMP method.
                    </p>
                  </div>
                  <div className="flex items-center gap-6 text-xs text-gray-500 justify-center pt-2">
                    <span className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-blue-500"></span>
                      Constraints (fixed)
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
                      Applied loads
                    </span>
                  </div>
                  <div className="text-xs text-gray-600 pt-2 border-t border-gray-700/50">
                    <p>🖱️ Left-click drag to orbit • Scroll to zoom • Right-click to pan</p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Loading overlay */}
            {isRunning && (
              <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-gray-900/90 backdrop-blur-sm rounded-lg px-4 py-2 border border-gray-700/50">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                  <span className="text-xs text-gray-300">
                    Iteration {currentIteration} — Compliance: {compliance.toExponential(2)}
                  </span>
                </div>
              </div>
            )}
          </div>
          
          {/* Convergence chart */}
          {showChart && complianceHistory.length > 1 && (
            <div className="h-32 bg-gray-900/95 border-t border-gray-700/50 p-2">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-400 font-medium">Convergence History</span>
                <button
                  onClick={() => setShowChart(false)}
                  className="text-xs text-gray-500 hover:text-gray-300"
                >
                  ✕
                </button>
              </div>
              <div className="h-24">
                <ConvergenceChart history={complianceHistory} currentIteration={currentIteration} />
              </div>
            </div>
          )}
          
          {!showChart && complianceHistory.length > 1 && (
            <button
              onClick={() => setShowChart(true)}
              className="absolute bottom-14 right-4 bg-gray-800/90 text-gray-400 hover:text-white text-xs px-3 py-1.5 rounded-lg border border-gray-700/50 hover:border-gray-600 transition-colors"
            >
              📈 Show Convergence
            </button>
          )}
        </div>
      </div>

      {/* Bottom status bar */}
      <StatusPanel
        isRunning={isRunning}
        currentIteration={currentIteration}
        maxIterations={40}
        compliance={compliance}
        density={density}
        nelx={params.nelx}
        nely={params.nely}
        volfrac={params.volfrac}
      />
    </div>
  );
}

export default App;
