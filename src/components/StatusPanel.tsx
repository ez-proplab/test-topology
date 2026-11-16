interface StatusPanelProps {
  isRunning: boolean;
  currentIteration: number;
  maxIterations: number;
  compliance: number;
  density: Float32Array | null;
  nelx: number;
  nely: number;
  volfrac: number;
}

export default function StatusPanel({
  isRunning,
  currentIteration,
  maxIterations,
  compliance,
  density,
  nelx,
  nely,
  volfrac,
}: StatusPanelProps) {
  const actualVol = density
    ? density.reduce((a, b) => a + b, 0) / (nelx * nely)
    : 0;
  
  const progress = maxIterations > 0 ? (currentIteration / maxIterations) * 100 : 0;
  
  return (
    <div className="bg-gray-900/95 backdrop-blur-sm border-t border-gray-700/50 px-4 py-2">
      <div className="flex items-center justify-between gap-4">
        {/* Status indicator */}
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-green-400 animate-pulse' : 'bg-gray-500'}`} />
          <span className="text-xs text-gray-400">
            {isRunning ? 'Optimizing...' : density ? 'Complete' : 'Ready'}
          </span>
        </div>
        
        {/* Progress bar */}
        {isRunning && (
          <div className="flex-1 max-w-xs">
            <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
        
        {/* Stats */}
        <div className="flex items-center gap-4">
          <div className="text-center">
            <div className="text-xs text-gray-500">Iteration</div>
            <div className="text-xs text-white font-mono">{currentIteration}/{maxIterations}</div>
          </div>
          
          <div className="text-center">
            <div className="text-xs text-gray-500">Compliance</div>
            <div className="text-xs text-white font-mono">
              {compliance > 0 ? compliance.toExponential(2) : '—'}
            </div>
          </div>
          
          <div className="text-center">
            <div className="text-xs text-gray-500">Volume</div>
            <div className="text-xs text-white font-mono">
              {actualVol > 0 ? (actualVol * 100).toFixed(1) + '%' : '—'}
            </div>
          </div>
          
          <div className="text-center">
            <div className="text-xs text-gray-500">Mesh</div>
            <div className="text-xs text-white font-mono">{nelx}×{nely}</div>
          </div>
          
          <div className="text-center">
            <div className="text-xs text-gray-500">DOFs</div>
            <div className="text-xs text-white font-mono">
              {(2 * (nelx + 1) * (nely + 1)).toLocaleString()}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
