/**
 * Performance Monitor Component
 * 
 * Developer tool for monitoring real-time performance metrics.
 * Only visible in development mode.
 */

import React, { useState, useEffect } from 'react';
import { performanceMetrics } from '../utils/performanceMetrics';

export const PerformanceMonitor: React.FC = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [metrics, setMetrics] = useState<any>(null);

  useEffect(() => {
    // Only show in development
    if (import.meta.env.MODE !== 'development') {
      return;
    }

    // Update metrics every 2 seconds
    const interval = setInterval(() => {
      const report = performanceMetrics.getPerformanceReport();
      setMetrics(report);
    }, 2000);

    // Listen for keyboard shortcut (Ctrl+Shift+P)
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'P') {
        setIsVisible((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyPress);

    return () => {
      clearInterval(interval);
      window.removeEventListener('keydown', handleKeyPress);
    };
  }, []);

  if (!isVisible || !metrics) {
    return null;
  }

  const { summary, targets } = metrics;

  return (
    <div className="fixed bottom-4 right-4 z-50 w-96 bg-slate-900 border border-slate-700 rounded-lg shadow-2xl p-4 text-xs font-mono">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-white">Performance Monitor</h3>
        <button
          onClick={() => setIsVisible(false)}
          className="text-slate-400 hover:text-white"
        >
          ✕
        </button>
      </div>

      <div className="space-y-2">
        {/* Page Load Time */}
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Page Load:</span>
          <span className={targets.pageLoadTime.passed ? 'text-green-400' : 'text-red-400'}>
            {summary.pageLoadTime.toFixed(0)}ms
            {targets.pageLoadTime.passed ? ' ✅' : ' ❌'}
          </span>
        </div>

        {/* Time to Interactive */}
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Time to Interactive:</span>
          <span className={targets.timeToInteractive.passed ? 'text-green-400' : 'text-red-400'}>
            {summary.timeToInteractive.toFixed(0)}ms
            {targets.timeToInteractive.passed ? ' ✅' : ' ❌'}
          </span>
        </div>

        {/* Chart Render Time */}
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Avg Chart Render:</span>
          <span className={targets.chartRenderTime.passed ? 'text-green-400' : 'text-red-400'}>
            {summary.avgChartRenderTime.toFixed(2)}ms
            {targets.chartRenderTime.passed ? ' ✅' : ' ❌'}
          </span>
        </div>

        {/* WebSocket Latency */}
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Avg WS Latency:</span>
          <span className={targets.websocketLatency.passed ? 'text-green-400' : 'text-red-400'}>
            {summary.avgWebSocketLatency.toFixed(2)}ms
            {targets.websocketLatency.passed ? ' ✅' : ' ❌'}
          </span>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-slate-700">
        <div className="flex gap-2">
          <button
            onClick={() => performanceMetrics.logPerformanceReport()}
            className="flex-1 px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs"
          >
            Log Report
          </button>
          <button
            onClick={() => {
              const json = performanceMetrics.exportMetrics();
              const blob = new Blob([json], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `performance-metrics-${Date.now()}.json`;
              a.click();
            }}
            className="flex-1 px-2 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-xs"
          >
            Export
          </button>
          <button
            onClick={() => performanceMetrics.reset()}
            className="flex-1 px-2 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs"
          >
            Reset
          </button>
        </div>
      </div>

      <div className="mt-2 text-slate-500 text-center">
        Press Ctrl+Shift+P to toggle
      </div>
    </div>
  );
};
