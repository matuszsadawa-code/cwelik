import { useEffect, useState, useRef } from 'react';
import { createChart, type IChartApi, type HistogramData, type Time, HistogramSeries } from 'lightweight-charts';
import {
  createOptimizedChartOptions,
  createRenderTimeMeasurement,
  debounce,
} from '../utils/chartOptimization';

/**
 * RRDistributionChart Component
 * 
 * Displays the distribution of risk-reward (R:R) ratios achieved across all trades.
 * 
 * Features:
 * - R:R distribution histogram with buckets (<0.5, 0.5-1.0, 1.0-1.5, 1.5-2.0, >2.0)
 * - Percentage of trades in each bucket
 * - Average and median R:R achieved
 * - Comparison of actual vs. target R:R distribution
 * - Warning indicator when average R:R < 1.0
 * - Dark Mode OLED optimized design
 * 
 * Requirements: 14.3, 14.4, 14.5, 14.6, 14.7, 14.8
 */

interface RRDistributionData {
  buckets: {
    label: string;
    count: number;
    percentage: number;
  }[];
  avgRR: number;
  medianRR: number;
  targetRR?: number; // Optional since it might not be provided by API
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Bucket colors based on R:R quality
const BUCKET_COLORS: Record<string, string> = {
  '<0.5': '#EF4444', // red-500 - very poor
  '0.5-1.0': '#F97316', // orange-500 - poor
  '1.0-1.5': '#EAB308', // yellow-500 - acceptable
  '1.5-2.0': '#84CC16', // lime-500 - good
  '>2.0': '#22C55E', // green-500 - excellent
};

export const RRDistributionChart: React.FC = () => {
  const [data, setData] = useState<RRDistributionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [renderTime, setRenderTime] = useState<number | null>(null);
  
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<IChartApi | null>(null);
  const renderMeasurement = useRef(createRenderTimeMeasurement('RRDistributionChart'));

  // Fetch R:R distribution data
  useEffect(() => {
    const fetchRRDistribution = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`${API_BASE_URL}/api/analytics/rr-distribution`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch R:R distribution: ${response.statusText}`);
        }
        
        const responseData = await response.json();
        setData(responseData);
      } catch (err) {
        console.error('Error fetching R:R distribution:', err);
        setError(err instanceof Error ? err.message : 'Failed to load R:R distribution');
      } finally {
        setLoading(false);
      }
    };

    fetchRRDistribution();
    
    // Refresh every 60 seconds
    const interval = setInterval(fetchRRDistribution, 60000);
    
    return () => clearInterval(interval);
  }, []);

  // Initialize histogram chart
  useEffect(() => {
    if (!chartRef.current || !data || data.buckets.length === 0) {
      return;
    }

    // Start render time measurement
    renderMeasurement.current.start();

    // Create chart if it doesn't exist
    if (!chartInstance.current) {
      const chart = createChart(
        chartRef.current,
        createOptimizedChartOptions({
          layout: {
            background: { color: '#020617' }, // slate-950
            textColor: '#94A3B8', // slate-400
          },
          grid: {
            vertLines: { color: '#1E293B' }, // slate-800
            horzLines: { color: '#1E293B' },
          },
          rightPriceScale: {
            borderColor: '#334155',
          },
          timeScale: {
            borderColor: '#334155',
            visible: false, // Hide time scale for categorical data
          },
        })
      );

      chartInstance.current = chart;

      const histogramSeries = chart.addSeries(HistogramSeries, {
        priceFormat: {
          type: 'custom',
          formatter: (price: number) => `${price.toFixed(1)}%`,
        },
      });

      // Convert data to chart format
      const chartData: HistogramData[] = data.buckets.map((bucket, index) => ({
        time: (index + 1) as Time,
        value: bucket.percentage,
        color: BUCKET_COLORS[bucket.label] || '#64748B', // slate-500 fallback
      }));

      histogramSeries.setData(chartData);
      chart.timeScale().fitContent();

      // End render time measurement
      const time = renderMeasurement.current.end();
      if (time !== null) {
        setRenderTime(time);
      }
    }

    // Debounced resize handler
    const handleResize = debounce(() => {
      if (chartInstance.current && chartRef.current) {
        chartInstance.current.applyOptions({
          width: chartRef.current.clientWidth,
          height: chartRef.current.clientHeight,
        });
      }
    }, 150);

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [data]);

  // Cleanup chart on unmount
  useEffect(() => {
    return () => {
      if (chartInstance.current) {
        chartInstance.current.remove();
        chartInstance.current = null;
      }
    };
  }, []);

  if (loading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">R:R Distribution</h3>
        <div className="text-center py-8">
          <p className="text-slate-400">Loading R:R distribution...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">R:R Distribution</h3>
        <div className="text-center py-8">
          <p className="text-red-400">{error || 'No R:R distribution data available'}</p>
        </div>
      </div>
    );
  }

  // Check if average R:R is below 1.0
  const showWarning = data.avgRR < 1.0;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-slate-100">R:R Distribution</h3>
        
        {/* Warning Indicator */}
        {showWarning && (
          <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
            <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span className="text-sm text-red-400 font-medium">
              Average R:R below 1.0 - Risk management needs improvement
            </span>
          </div>
        )}
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Average R:R */}
        <div className="bg-slate-950 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            Average R:R
          </p>
          <p
            className={`text-2xl font-bold ${
              data.avgRR >= 1.5
                ? 'text-green-500'
                : data.avgRR >= 1.0
                ? 'text-yellow-500'
                : 'text-red-400'
            }`}
          >
            {data.avgRR.toFixed(2)}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            {data.avgRR >= 1.5
              ? 'Excellent'
              : data.avgRR >= 1.0
              ? 'Acceptable'
              : 'Needs Improvement'}
          </p>
        </div>

        {/* Median R:R */}
        <div className="bg-slate-950 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            Median R:R
          </p>
          <p
            className={`text-2xl font-bold ${
              data.medianRR >= 1.5
                ? 'text-green-500'
                : data.medianRR >= 1.0
                ? 'text-yellow-500'
                : 'text-red-400'
            }`}
          >
            {data.medianRR.toFixed(2)}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Middle value
          </p>
        </div>

        {/* Target R:R */}
        <div className="bg-slate-950 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            Target R:R
          </p>
          <p className="text-2xl font-bold text-slate-100">
            {data.targetRR?.toFixed(2) ?? 'N/A'}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Strategy goal
          </p>
        </div>
      </div>

      {/* Histogram Chart */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-slate-200">
            Distribution by R:R Bucket
          </h4>
          <p className="text-xs text-slate-500">
            Percentage of trades in each range
          </p>
        </div>
        {data.buckets.length > 0 ? (
          <>
            <div
              ref={chartRef}
              className="w-full h-64 bg-slate-950 rounded-lg mb-3"
              style={{ minHeight: '256px' }}
            />
            {/* Bucket Labels */}
            <div className="flex justify-around text-xs text-slate-400 px-4">
              {data.buckets.map((bucket) => (
                <div key={bucket.label} className="text-center">
                  <div
                    className="w-3 h-3 rounded-full mx-auto mb-1"
                    style={{ backgroundColor: BUCKET_COLORS[bucket.label] || '#64748B' }}
                  />
                  <p className="font-medium">{bucket.label}</p>
                  <p className="text-slate-500 mt-1">{bucket.percentage.toFixed(1)}%</p>
                  <p className="text-slate-600 text-xs mt-1">({bucket.count} trades)</p>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="bg-slate-950 rounded-lg p-8 text-center">
            <p className="text-slate-400 text-sm">No R:R distribution data available</p>
          </div>
        )}
      </div>

      {/* Comparison Table */}
      <div>
        <h4 className="text-sm font-semibold text-slate-200 mb-3">
          Actual vs. Target Distribution
        </h4>
        <div className="bg-slate-950 rounded-lg p-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
                Actual Average
              </p>
              <p
                className={`text-xl font-bold ${
                  data.targetRR && data.avgRR >= data.targetRR ? 'text-green-500' : 'text-red-400'
                }`}
              >
                {data.avgRR.toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
                Target Average
              </p>
              <p className="text-xl font-bold text-slate-100">
                {data.targetRR?.toFixed(2) ?? 'N/A'}
              </p>
            </div>
          </div>
          {data.targetRR && (
            <div className="mt-4 pt-4 border-t border-slate-800">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Performance vs. Target</span>
                <span
                  className={`text-sm font-medium ${
                    data.avgRR >= data.targetRR ? 'text-green-500' : 'text-red-400'
                  }`}
                >
                  {data.avgRR >= data.targetRR ? '✓ Meeting Target' : '✗ Below Target'}
                </span>
              </div>
              {data.avgRR < data.targetRR && (
                <p className="text-xs text-slate-500 mt-2">
                  Improve by {((data.targetRR - data.avgRR) / data.targetRR * 100).toFixed(1)}% to reach target
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Interpretation Guide */}
      <div className="mt-6 bg-slate-950 rounded-lg p-4">
        <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">
          R:R Interpretation Guide
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="flex items-start gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-slate-300 font-medium">&lt;0.5: Very Poor</p>
              <p className="text-slate-500">Losses exceed gains significantly</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-3 h-3 rounded-full bg-orange-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-slate-300 font-medium">0.5-1.0: Poor</p>
              <p className="text-slate-500">Losses still larger than gains</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-3 h-3 rounded-full bg-yellow-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-slate-300 font-medium">1.0-1.5: Acceptable</p>
              <p className="text-slate-500">Gains match or slightly exceed losses</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-3 h-3 rounded-full bg-lime-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-slate-300 font-medium">1.5-2.0: Good</p>
              <p className="text-slate-500">Gains significantly exceed losses</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-slate-300 font-medium">&gt;2.0: Excellent</p>
              <p className="text-slate-500">Gains far exceed losses</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
