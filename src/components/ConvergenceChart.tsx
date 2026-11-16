import { useRef, useEffect } from 'react';

interface ConvergenceChartProps {
  history: number[];
  currentIteration: number;
}

export default function ConvergenceChart({ history, currentIteration }: ConvergenceChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || history.length < 2) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    
    const w = rect.width;
    const h = rect.height;
    const padding = { top: 10, right: 10, bottom: 20, left: 40 };
    const plotW = w - padding.left - padding.right;
    const plotH = h - padding.top - padding.bottom;
    
    // Clear
    ctx.clearRect(0, 0, w, h);
    
    // Find range
    const maxVal = Math.max(...history);
    const minVal = Math.min(...history);
    const range = maxVal - minVal || 1;
    
    // Draw grid
    ctx.strokeStyle = '#1f2937';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 4; i++) {
      const y = padding.top + (plotH * i) / 4;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(w - padding.right, y);
      ctx.stroke();
    }
    
    // Draw axes labels
    ctx.fillStyle = '#6b7280';
    ctx.font = '9px monospace';
    ctx.textAlign = 'right';
    for (let i = 0; i <= 4; i++) {
      const y = padding.top + (plotH * i) / 4;
      const val = maxVal - (range * i) / 4;
      ctx.fillText(val.toExponential(1), padding.left - 4, y + 3);
    }
    
    // X axis labels
    ctx.textAlign = 'center';
    const numLabels = Math.min(5, history.length);
    for (let i = 0; i < numLabels; i++) {
      const x = padding.left + (plotW * i) / (numLabels - 1);
      const iter = Math.round((history.length - 1) * i / (numLabels - 1));
      ctx.fillText(`${iter}`, x, h - 4);
    }
    
    // Draw line
    ctx.beginPath();
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    
    for (let i = 0; i < history.length; i++) {
      const x = padding.left + (plotW * i) / Math.max(1, history.length - 1);
      const y = padding.top + plotH * (1 - (history[i] - minVal) / range);
      
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    
    // Draw gradient fill
    const gradient = ctx.createLinearGradient(0, padding.top, 0, padding.top + plotH);
    gradient.addColorStop(0, 'rgba(59, 130, 246, 0.3)');
    gradient.addColorStop(1, 'rgba(59, 130, 246, 0.0)');
    
    ctx.lineTo(padding.left + plotW, padding.top + plotH);
    ctx.lineTo(padding.left, padding.top + plotH);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();
    
    // Draw current point
    if (history.length > 0) {
      const lastX = padding.left + plotW;
      const lastY = padding.top + plotH * (1 - (history[history.length - 1] - minVal) / range);
      
      ctx.beginPath();
      ctx.arc(lastX, lastY, 3, 0, Math.PI * 2);
      ctx.fillStyle = '#3b82f6';
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    
  }, [history]);
  
  return (
    <div className="w-full h-full">
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{ display: 'block' }}
      />
    </div>
  );
}
