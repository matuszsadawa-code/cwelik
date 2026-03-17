import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, type LineData, type Time } from 'lightweight-charts';
import type { IChartApi, ISeriesApi } from 'lightweight-charts';
import type { TimeRange, EquityCurveData } from '../types/index';
import { fetchEquityCurve } from '../services/api';
import {
  optimizeChartData,
  createOptimizedChartOptions,
  createRenderTimeMeasurement,
  debounce,
} from '../utils/chartOptimization';

/**
 * EquityCurveChart Component
 * 
 * Visualizes equity curve with drawdown periods using TradingView Lightweight Charts.
 * 
 * Features:
 * - Line chart showing equity over time
 * - Shaded drawdown periods (>5%) in red
 * - Peak equity marker on chart
 * - Current equity value display
 * - Time range selector (1d, 7d, 30d, 90d, 1y, all)
 * - Interactive tooltips showing exact values on hover
 * - Maximum drawdown depth and duration display
 * - Responsive chart sizing
 * - Dark mode optimized colors
 * 
 * Requirements: 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 8.10
 */

interface EquityCurveChartProps {
  timeRange?: TimeRange;
  onTimeRangeChange?: (range: TimeRange) => void;
}

const TIME_RANGES: { value: TimeRange; label: string }[] = [
  { value: '1d', label: '1D' },
  { value: '7d', label: '7D' },
  { value: '30d', label: '30D' },
  { value: '90d', label: '90D' },
  { value: '1y', label: '1Y' },
  { value: 'all', label: 'All' },
];

export const EquityCurveChart: React.FC<EquityCurveChartProps> = ({
  timeRange = '7d',
  onTimeRangeChange,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const renderMeasurement = useRef(createRenderTimeMeasurement('EquityCurveChart'));
  
  const [equityData, setEquityData] = useState<EquityCurveData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredValue, setHoveredValue] = useState<{ equity: number; time: string } | null>(null);
  const [renderTime, setRenderTime] = useState<number | null>(null);

  // Fetch equity curve data
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetchEquityCurve(timeRange);
        setEquityData(data);
      } catch (err) {
        console.error('Error fetching equity curve:', err);
        setError(err instanceof Error ? err.message : 'Failed to load equity curve');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [timeRange]);

  // Initialize and update chart
  useEffect(() => {
    if (!chartContainerRef.current || !equityData || equityData.timestamps.length === 0) {
      return;
    }

    // Start render time measurement
    renderMeasurement.current.start();

    // Create chart if it doesn't exist
    if (!chartRef.current) {
      const chart = createChart(
        chartContainerRef.current,
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
            timeVisible: true,
            secondsVisible: false,
          },
        })
      );

      chartRef.current = chart;

      // Create line series
      const lineSeries = chart.addLineSeries({
        color: '#22C55E', // green-500
        lineWidth: 2,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
        crosshairMarkerBorderColor: '#22C55E',
        crosshairMarkerBackgroundColor: '#22C55E',
        lastValueVisible: true,
        priceLineVisible: true,
      });

      seriesRef.current = lineSeries;

      // Subscribe to crosshair move for hover tooltips
      chart.subscribeCrosshairMove((param) => {
        if (param.time && param.seriesData.get(lineSeries)) {
          const data = param.seriesData.get(lineSeries) as LineData;
          const timestamp = (param.time as number) * 1000; // Convert to milliseconds
          const date = new Date(timestamp);
          
          setHoveredValue({
            equity: data.value,
            time: date.toLocaleString('en-US', {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            }),
          });
        } else {
          setHoveredValue(null);
        }
      });
    }

    // Update chart data
    if (chartRef.current && seriesRef.current) {
      // Convert data to TradingView format
      const chartData: LineData[] = equityData.timestamps.map((timestamp, index) => ({
        time: (timestamp / 1000) as Time, // Convert milliseconds to seconds
        value: equityData.equityValues[index],
      }));

      // Optimize data by limiting to 1000 points
      const optimizedData = optimizeChartData(chartData);

      seriesRef.current.setData(optimizedData);

      // Add drawdown period markers (limit to avoid performance issues)
      if (equityData.drawdownPeriods.length > 0) {
        const maxMarkers = 10; // Limit markers for performance
        const markersToShow = equityData.drawdownPeriods.slice(0, maxMarkers);
        
        markersToShow.forEach((period) => {
          seriesRef.current?.createPriceLine({
            price: period.troughEquity,
            color: '#EF4444', // red-500
            lineWidth: 1,
            lineStyle: 2, // Dashed
            axisLabelVisible: false,
            title: `DD: ${period.depth.toFixed(2)}%`,
          });
        });
      }

      // Mark peak equity point
      if (equityData.peakEquity > 0) {
        seriesRef.current.createPriceLine({
          price: equityData.peakEquity,
          color: '#22C55E', // green-500
          lineWidth: 1,
          lineStyle: 2, // Dashed
          axisLabelVisible: true,
          title: 'Peak',
        });
      }

      // Fit content to visible range
      chartRef.current.timeScale().fitContent();

      // End render time measurement
      const time = renderMeasurement.current.end();
      if (time !== null) {
        setRenderTime(time);
      }
    }

    // Debounced resize handler for better performance
    const handleResize = debounce(() => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    }, 150);

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [equityData]);

  // Cleanup chart on unmount
  useEffect(() => {
    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
        seriesRef.current = null;
      }
    };
  }, []);

  const handleTimeRangeChange = (range: TimeRange) => {
    if (onTimeRangeChange) {
      onTimeRangeChange(range);
    }
  };

  const formatCurrency = (value: number): string => {
    return value.toLocaleString('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  const formatDuration = (minutes: number): string => {
    if (minutes < 60) {
      return `${minutes}m`;
    } else if (minutes < 1440) {
      return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
    } else {
      return `${Math.floor(minutes / 1440)}d ${Math.floor((minutes % 1440) / 60)}h`;
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-slate-100">Equity Curve</h3>
        
        {/* Time Range Selector */}
        <div className="flex gap-1 bg-slate-950 rounded-lg p-1">
          {TIME_RANGES.map((range) => (
            <button
              key={range.value}
              onClick={() => handleTimeRangeChange(range.value)}
              className={`px-3 py-1 text-sm font-medium rounded transition-colors ${
                timeRange === range.value
                  ? 'bg-green-500 text-white'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
              aria-label={`Select ${range.label} time range`}
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center h-96">
          <p className="text-slate-400">Loading equity curve...</p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="flex items-center justify-center h-96">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Chart and Metrics */}
      {!loading && !error && equityData && (
        <>
          {/* Current Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            {/* Current Equity */}
            <div className="bg-slate-950 rounded-lg p-4">
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
                Current Equity
              </p>
              <p className="text-xl font-bold text-slate-100">
                {formatCurrency(equityData.currentEquity)}
              </p>
            </div>

            {/* Peak Equity */}
            <div className="bg-slate-950 rounded-lg p-4">
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
                Peak Equity
              </p>
              <p className="text-xl font-bold text-green-500">
                {formatCurrency(equityData.peakEquity)}
              </p>
            </div>

            {/* Max Drawdown */}
            <div className="bg-slate-950 rounded-lg p-4">
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
                Max Drawdown
              </p>
              <p className="text-xl font-bold text-red-400">
                {equityData.maxDrawdown.toFixed(2)}%
              </p>
            </div>

            {/* Max DD Duration */}
            <div className="bg-slate-950 rounded-lg p-4">
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
                Max DD Duration
              </p>
              <p className="text-xl font-bold text-slate-100">
                {formatDuration(equityData.maxDrawdownDuration)}
              </p>
            </div>
          </div>

          {/* Hover Tooltip */}
          {hoveredValue && (
            <div className="mb-4 bg-slate-950 rounded-lg p-3 border border-slate-700">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">{hoveredValue.time}</span>
                <span className="text-sm font-semibold text-slate-100">
                  {formatCurrency(hoveredValue.equity)}
                </span>
              </div>
            </div>
          )}

          {/* Performance Indicator */}
          {renderTime !== null && (
            <div className="mb-4 text-xs text-slate-500">
              <span>Chart render time: {renderTime.toFixed(2)}ms</span>
              {renderTime > 100 && (
                <span className="ml-2 text-yellow-500">
                  (exceeds 100ms target)
                </span>
              )}
            </div>
          )}

          {/* Chart Container */}
          <div
            ref={chartContainerRef}
            className="w-full h-96 bg-slate-950 rounded-lg"
            style={{ minHeight: '384px' }}
          />

          {/* Drawdown Periods Info */}
          {equityData.drawdownPeriods.length > 0 && (
            <div className="mt-4 text-xs text-slate-500">
              <p>
                {equityData.drawdownPeriods.length} drawdown period(s) exceeding 5% detected
              </p>
            </div>
          )}

          {/* No Data Message */}
          {equityData.timestamps.length === 0 && (
            <div className="flex items-center justify-center h-96">
              <p className="text-slate-400">No equity data available for selected time range</p>
            </div>
          )}
        </>
      )}
    </div>
  );
};
