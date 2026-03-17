/**
 * BacktestViewer Component
 * 
 * Displays backtest runs with detailed results, equity curves, and performance comparison.
 * Requirements: 22.3, 22.4, 22.5, 22.6, 22.7, 22.8, 22.9, 22.10
 */

import { useState, useEffect, useRef } from 'react';
import { createChart, LineStyle } from 'lightweight-charts';
import type { IChartApi } from 'lightweight-charts';
import type { BacktestRun, BacktestResults } from '../types';
import { fetchBacktestRuns, fetchBacktestResults, fetchBacktestComparison } from '../services/api';

export default function BacktestViewer() {
  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<BacktestResults | null>(null);
  const [comparisonRuns, setComparisonRuns] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  // Fetch backtest runs
  useEffect(() => {
    const loadRuns = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchBacktestRuns();
        setRuns(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load backtest runs');
      } finally {
        setLoading(false);
      }
    };

    loadRuns();
  }, []);

  // Fetch selected run details
  useEffect(() => {
    if (!selectedRun) return;

    const loadRunDetails = async () => {
      try {
        const data = await fetchBacktestResults(selectedRun.runId);
        setSelectedRun(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load backtest details');
      }
    };

    loadRunDetails();
  }, [selectedRun?.runId]);

  // Render equity curve chart
  useEffect(() => {
    if (!selectedRun || !chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { color: '#111827' },
        textColor: '#9CA3AF',
      },
      grid: {
        vertLines: { color: '#1F2937' },
        horzLines: { color: '#1F2937' },
      },
      timeScale: {
        borderColor: '#374151',
      },
      rightPriceScale: {
        borderColor: '#374151',
      },
    });

    chartRef.current = chart;

    const lineSeries = chart.addLineSeries({
      color: '#3B82F6',
      lineWidth: 2,
    });

    // Convert equity curve data
    const equityData = selectedRun.equityCurve.timestamps.map((timestamp, index) => ({
      time: (timestamp / 1000) as any,
      value: selectedRun.equityCurve.equityValues[index],
    }));

    lineSeries.setData(equityData);

    // Add drawdown periods
    selectedRun.equityCurve.drawdownPeriods.forEach((period) => {
      const startTime = period.startDate / 1000;
      const endTime = period.endDate / 1000;
      
      // Add shaded area for drawdown (simplified - in production use area series)
      lineSeries.createPriceLine({
        price: period.peakEquity,
        color: '#EF4444',
        lineWidth: 1,
        lineStyle: LineStyle.Dotted,
        axisLabelVisible: false,
      });
    });

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [selectedRun]);

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const handleRunSelect = async (runId: string) => {
    try {
      const data = await fetchBacktestResults(runId);
      setSelectedRun(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load backtest details');
    }
  };

  const toggleComparison = (runId: string) => {
    setComparisonRuns(prev => 
      prev.includes(runId) 
        ? prev.filter(id => id !== runId)
        : prev.length < 4 ? [...prev, runId] : prev
    );
  };

  if (loading) {
    return (
      <div className="bg-gray-900 rounded-lg p-6">
        <div className="flex items-center justify-center h-96">
          <div className="text-gray-400">Loading backtest runs...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-900 rounded-lg p-6">
        <div className="text-red-400">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Backtest Runs List */}
      <div className="bg-gray-900 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Backtest Runs</h2>
          {comparisonRuns.length > 0 && (
            <button
              onClick={() => setComparisonRuns([])}
              className="text-sm text-gray-400 hover:text-white"
            >
              Clear comparison ({comparisonRuns.length})
            </button>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800 text-left text-sm text-gray-400">
                <th className="pb-3 pr-4">Date</th>
                <th className="pb-3 pr-4">Win Rate</th>
                <th className="pb-3 pr-4">Profit Factor</th>
                <th className="pb-3 pr-4">Sharpe Ratio</th>
                <th className="pb-3 pr-4">Max DD</th>
                <th className="pb-3 pr-4">Total Trades</th>
                <th className="pb-3 pr-4">Total PnL</th>
                <th className="pb-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr
                  key={run.runId}
                  className={`border-b border-gray-800 hover:bg-gray-800/50 cursor-pointer ${
                    selectedRun?.runId === run.runId ? 'bg-gray-800/50' : ''
                  }`}
                  onClick={() => handleRunSelect(run.runId)}
                >
                  <td className="py-3 pr-4 text-sm">{formatDate(run.date)}</td>
                  <td className="py-3 pr-4 text-sm">{run.winRate.toFixed(1)}%</td>
                  <td className="py-3 pr-4 text-sm">{run.profitFactor.toFixed(2)}</td>
                  <td className="py-3 pr-4 text-sm">{run.sharpeRatio.toFixed(2)}</td>
                  <td className="py-3 pr-4 text-sm text-red-400">{run.maxDrawdown.toFixed(1)}%</td>
                  <td className="py-3 pr-4 text-sm">{run.totalTrades}</td>
                  <td className={`py-3 pr-4 text-sm font-semibold ${
                    run.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {run.totalPnL >= 0 ? '+' : ''}{run.totalPnL.toFixed(2)}%
                  </td>
                  <td className="py-3">
                    <input
                      type="checkbox"
                      checked={comparisonRuns.includes(run.runId)}
                      onChange={(e) => {
                        e.stopPropagation();
                        toggleComparison(run.runId);
                      }}
                      disabled={!comparisonRuns.includes(run.runId) && comparisonRuns.length >= 4}
                      className="w-4 h-4 rounded border-gray-700 bg-gray-800 text-blue-600 focus:ring-blue-500"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Selected Run Details */}
      {selectedRun && (
        <div className="bg-gray-900 rounded-lg p-6">
          <h2 className="text-xl font-bold mb-4">
            Backtest Results - {formatDate(selectedRun.date)}
          </h2>

          {/* Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-800 p-4 rounded-lg">
              <div className="text-sm text-gray-400">Win Rate</div>
              <div className="text-2xl font-bold mt-1">{selectedRun.metrics.winRate.toFixed(1)}%</div>
            </div>
            <div className="bg-gray-800 p-4 rounded-lg">
              <div className="text-sm text-gray-400">Profit Factor</div>
              <div className="text-2xl font-bold mt-1">{selectedRun.metrics.profitFactor.toFixed(2)}</div>
            </div>
            <div className="bg-gray-800 p-4 rounded-lg">
              <div className="text-sm text-gray-400">Sharpe Ratio</div>
              <div className="text-2xl font-bold mt-1">{selectedRun.metrics.sharpeRatio.toFixed(2)}</div>
            </div>
            <div className="bg-gray-800 p-4 rounded-lg">
              <div className="text-sm text-gray-400">Max Drawdown</div>
              <div className="text-2xl font-bold text-red-400 mt-1">{selectedRun.metrics.maxDrawdown.toFixed(1)}%</div>
            </div>
            <div className="bg-gray-800 p-4 rounded-lg">
              <div className="text-sm text-gray-400">Sortino Ratio</div>
              <div className="text-2xl font-bold mt-1">{selectedRun.metrics.sortinoRatio.toFixed(2)}</div>
            </div>
            <div className="bg-gray-800 p-4 rounded-lg">
              <div className="text-sm text-gray-400">Calmar Ratio</div>
              <div className="text-2xl font-bold mt-1">{selectedRun.metrics.calmarRatio.toFixed(2)}</div>
            </div>
            <div className="bg-gray-800 p-4 rounded-lg">
              <div className="text-sm text-gray-400">Total Trades</div>
              <div className="text-2xl font-bold mt-1">{selectedRun.metrics.totalTrades}</div>
            </div>
            <div className="bg-gray-800 p-4 rounded-lg">
              <div className="text-sm text-gray-400">Total PnL</div>
              <div className={`text-2xl font-bold mt-1 ${
                selectedRun.metrics.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'
              }`}>
                {selectedRun.metrics.totalPnL >= 0 ? '+' : ''}{selectedRun.metrics.totalPnL.toFixed(2)}%
              </div>
            </div>
          </div>

          {/* Equity Curve */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-3">Equity Curve</h3>
            <div ref={chartContainerRef} className="w-full h-[400px] bg-gray-800 rounded-lg" />
          </div>

          {/* Parameters */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-3">Parameters</h3>
            <div className="bg-gray-800 p-4 rounded-lg">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {Object.entries(selectedRun.parameters).map(([key, value]) => (
                  <div key={key}>
                    <div className="text-sm text-gray-400">{key}</div>
                    <div className="text-sm font-medium mt-1">{String(value)}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Trade List Summary */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Trade Summary</h3>
            <div className="bg-gray-800 p-4 rounded-lg">
              <div className="text-sm text-gray-400">
                {selectedRun.trades.length} trades executed during backtest period
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Comparison View */}
      {comparisonRuns.length > 1 && (
        <div className="bg-gray-900 rounded-lg p-6">
          <h2 className="text-xl font-bold mb-4">Backtest Comparison</h2>
          <div className="text-sm text-gray-400">
            Comparing {comparisonRuns.length} backtest runs side-by-side
          </div>
          {/* Comparison implementation would go here */}
        </div>
      )}
    </div>
  );
}
