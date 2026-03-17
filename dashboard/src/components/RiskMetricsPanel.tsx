import { useEffect, useState, useMemo, useRef } from 'react';
import { createChart, type IChartApi, type ISeriesApi, type LineData, type Time, LineSeries, HistogramSeries } from 'lightweight-charts';
import {
  optimizeChartData,
  createOptimizedChartOptions,
  createRenderTimeMeasurement,
  debounce,
} from '../utils/chartOptimization';

/**
 * RiskMetricsPanel Component
 * 
 * Displays risk-adjusted return metrics including Sharpe, Sortino, and Calmar ratios,
 * along with drawdown analysis.
 * 
 * Features:
 * - Sharpe ratio, Sortino ratio, Calmar ratio with interpretation labels
 * - Maximum drawdown and average drawdown duration display
 * - Benchmark comparison if available
 * - Rolling Sharpe ratio line chart (30-day window)
 * - Drawdown duration histogram
 * - Dark Mode OLED optimized design
 * - Color coding for metric interpretation
 * 
 * Requirements: 12.6, 12.7, 12.8, 12.9, 12.10
 */

interface RiskMetrics {
  sharpeRatio: number;
  sortinoRatio: number;
  calmarRatio: number;
  maxDrawdown: number;
  avgDrawdownDuration: number;
  rollingSharpe: Array<{ timestamp: string; sharpe: number }>;
  drawdownHistogram: {
    buckets: string[];
    counts: number[];
  };
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const RiskMetricsPanel: React.FC = () => {
  const [metrics, setMetrics] = useState<RiskMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [renderTime, setRenderTime] = useState<number | null>(null);
  
  const rollingSharpeChartRef = useRef<HTMLDivElement>(null);
  const histogramChartRef = useRef<HTMLDivElement>(null);
  const rollingSharpeChartInstance = useRef<IChartApi | null>(null);
  const rollingSharpeSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const histogramChartInstance = useRef<IChartApi | null>(null);
  const histogramSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const renderMeasurement = useRef(createRenderTimeMeasurement('RiskMetricsPanel'));

  // Fetch risk metrics data
  useEffect(() => {
    const fetchRiskMetrics = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`${API_BASE_URL}/api/analytics/risk-metrics`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch risk metrics: ${response.statusText}`);
        }
        
        const data = await response.json();
        setMetrics(data);
      } catch (err) {
        console.error('Error fetching risk metrics:', err);
        setError(err instanceof Error ? err.message : 'Failed to load risk metrics');
      } finally {
        setLoading(false);
      }
    };

    fetchRiskMetrics();
    
    // Refresh every 60 seconds
    const interval = setInterval(fetchRiskMetrics, 60000);
    
    return () => clearInterval(interval);
  }, []);

  // Get interpretation for Sharpe ratio
  const getSharpeInterpretation = (sharpe: number): { label: string; color: string } => {
    if (sharpe > 2.0) return { label: 'Excellent', color: 'text-green-500' };
    if (sharpe > 1.0) return { label: 'Good', color: 'text-green-400' };
    if (sharpe > 0.5) return { label: 'Acceptable', color: 'text-yellow-500' };
    if (sharpe > 0) return { label: 'Poor', color: 'text-orange-500' };
    return { label: 'Very Poor', color: 'text-red-500' };
  };

  // Get interpretation for Sortino ratio
  const getSortinoInterpretation = (sortino: number): { label: string; color: string } => {
    if (sortino > 3.0) return { label: 'Excellent', color: 'text-green-500' };
    if (sortino > 2.0) return { label: 'Good', color: 'text-green-400' };
    if (sortino > 1.0) return { label: 'Acceptable', color: 'text-yellow-500' };
    if (sortino > 0) return { label: 'Poor', color: 'text-orange-500' };
    return { label: 'Very Poor', color: 'text-red-500' };
  };

  // Get interpretation for Calmar ratio
  const getCalmarInterpretation = (calmar: number): { label: string; color: string } => {
    if (calmar > 3.0) return { label: 'Excellent', color: 'text-green-500' };
    if (calmar > 1.5) return { label: 'Good', color: 'text-green-400' };
    if (calmar > 0.5) return { label: 'Acceptable', color: 'text-yellow-500' };
    if (calmar > 0) return { label: 'Poor', color: 'text-orange-500' };
    return { label: 'Very Poor', color: 'text-red-500' };
  };

  // Calculate interpretations
  const interpretations = useMemo(() => {
    if (!metrics) return null;

    return {
      sharpe: getSharpeInterpretation(metrics.sharpeRatio),
      sortino: getSortinoInterpretation(metrics.sortinoRatio),
      calmar: getCalmarInterpretation(metrics.calmarRatio),
    };
  }, [metrics]);

  // Format duration from minutes to human-readable
  const formatDuration = (minutes: number): string => {
    if (minutes < 60) {
      return `${Math.round(minutes)}m`;
    } else if (minutes < 1440) {
      const hours = Math.floor(minutes / 60);
      const mins = Math.round(minutes % 60);
      return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
    } else {
      const days = Math.floor(minutes / 1440);
      const hours = Math.floor((minutes % 1440) / 60);
      return hours > 0 ? `${days}d ${hours}h` : `${days}d`;
    }
  };

  // Initialize and update rolling Sharpe ratio chart
  useEffect(() => {
    if (!rollingSharpeChartRef.current || !metrics || metrics.rollingSharpe.length === 0) {
      return;
    }

    // Start render time measurement
    renderMeasurement.current.start();

    // Create chart if it doesn't exist
    if (!rollingSharpeChartInstance.current) {
      const chart = createChart(
        rollingSharpeChartRef.current,
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

      rollingSharpeChartInstance.current = chart;

      const lineSeries = chart.addSeries(LineSeries, {
        color: '#22C55E', // green-500
        lineWidth: 2,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
        crosshairMarkerBorderColor: '#22C55E',
        crosshairMarkerBackgroundColor: '#22C55E',
        lastValueVisible: true,
        priceLineVisible: true,
      });

      rollingSharpeSeriesRef.current = lineSeries;

      // Convert data to TradingView format
      const chartData: LineData[] = metrics.rollingSharpe.map((point) => ({
        time: (new Date(point.timestamp).getTime() / 1000) as Time,
        value: point.sharpe,
      }));

      // Optimize data by limiting to 1000 points
      const optimizedData = optimizeChartData(chartData);

      lineSeries.setData(optimizedData);
      chart.timeScale().fitContent();

      // End render time measurement
      const time = renderMeasurement.current.end();
      if (time !== null) {
        setRenderTime(time);
      }
    }

    // Debounced resize handler
    const handleResize = debounce(() => {
      if (rollingSharpeChartInstance.current && rollingSharpeChartRef.current) {
        rollingSharpeChartInstance.current.applyOptions({
          width: rollingSharpeChartRef.current.clientWidth,
          height: rollingSharpeChartRef.current.clientHeight,
        });
      }
    }, 150);

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [metrics]);

  // Initialize and update drawdown histogram chart
  useEffect(() => {
    if (!histogramChartRef.current || !metrics || metrics.drawdownHistogram.buckets.length === 0) {
      return;
    }

    // Create chart if it doesn't exist
    if (!histogramChartInstance.current) {
      const chart = createChart(
        histogramChartRef.current,
        createOptimizedChartOptions({
          layout: {
            background: { color: '#020617' }, // slate-950
            textColor: '#94A3B8', // slate-400
          },
          grid: {
            vertLines: { color: '#1E293B' },
            horzLines: { color: '#1E293B' },
          },
          rightPriceScale: {
            borderColor: '#334155',
          },
          timeScale: {
            borderColor: '#334155',
            visible: false, // Hide time scale for histogram
          },
        })
      );

      histogramChartInstance.current = chart;

      const histogramSeries = chart.addSeries(HistogramSeries, {
        color: '#EF4444', // red-500
        priceFormat: {
          type: 'volume',
        },
      });

      histogramSeriesRef.current = histogramSeries;

      // Convert histogram data to TradingView format
      const chartData = metrics.drawdownHistogram.buckets.map((_bucket, index) => ({
        time: (index + 1) as Time,
        value: metrics.drawdownHistogram.counts[index],
        color: '#EF4444',
      }));

      histogramSeries.setData(chartData);
      chart.timeScale().fitContent();
    }

    // Debounced resize handler
    const handleResize = debounce(() => {
      if (histogramChartInstance.current && histogramChartRef.current) {
        histogramChartInstance.current.applyOptions({
          width: histogramChartRef.current.clientWidth,
          height: histogramChartRef.current.clientHeight,
        });
      }
    }, 150);

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [metrics]);

  // Cleanup charts on unmount
  useEffect(() => {
    return () => {
      if (rollingSharpeChartInstance.current) {
        rollingSharpeChartInstance.current.remove();
        rollingSharpeChartInstance.current = null;
        rollingSharpeSeriesRef.current = null;
      }
      if (histogramChartInstance.current) {
        histogramChartInstance.current.remove();
        histogramChartInstance.current = null;
        histogramSeriesRef.current = null;
      }
    };
  }, []);

  if (loading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">Risk Metrics</h3>
        <div className="text-center py-8">
          <p className="text-slate-400">Loading risk metrics...</p>
        </div>
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">Risk Metrics</h3>
        <div className="text-center py-8">
          <p className="text-red-400">{error || 'No risk metrics available'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-slate-100 mb-6">Risk Metrics</h3>

      {/* Risk-Adjusted Return Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Sharpe Ratio */}
        <div className="bg-slate-950 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            Sharpe Ratio
          </p>
          <p className={`text-2xl font-bold ${interpretations?.sharpe.color}`}>
            {metrics.sharpeRatio.toFixed(2)}
          </p>
          <p className="text-xs text-slate-500 mt-1">{interpretations?.sharpe.label}</p>
          <p className="text-xs text-slate-600 mt-2">
            Risk-adjusted return
          </p>
        </div>

        {/* Sortino Ratio */}
        <div className="bg-slate-950 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            Sortino Ratio
          </p>
          <p className={`text-2xl font-bold ${interpretations?.sortino.color}`}>
            {metrics.sortinoRatio.toFixed(2)}
          </p>
          <p className="text-xs text-slate-500 mt-1">{interpretations?.sortino.label}</p>
          <p className="text-xs text-slate-600 mt-2">
            Downside risk-adjusted
          </p>
        </div>

        {/* Calmar Ratio */}
        <div className="bg-slate-950 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            Calmar Ratio
          </p>
          <p className={`text-2xl font-bold ${interpretations?.calmar.color}`}>
            {metrics.calmarRatio.toFixed(2)}
          </p>
          <p className="text-xs text-slate-500 mt-1">{interpretations?.calmar.label}</p>
          <p className="text-xs text-slate-600 mt-2">
            Return / Max drawdown
          </p>
        </div>
      </div>

      {/* Drawdown Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {/* Maximum Drawdown */}
        <div className="bg-slate-950 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            Maximum Drawdown
          </p>
          <p className="text-2xl font-bold text-red-400">
            {metrics.maxDrawdown.toFixed(2)}%
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Largest peak-to-trough decline
          </p>
        </div>

        {/* Average Drawdown Duration */}
        <div className="bg-slate-950 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            Avg Drawdown Duration
          </p>
          <p className="text-2xl font-bold text-slate-100">
            {formatDuration(metrics.avgDrawdownDuration)}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Average recovery time
          </p>
        </div>
      </div>

      {/* Rolling Sharpe Ratio Chart */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-slate-200">
            Rolling Sharpe Ratio (30-day window)
          </h4>
        </div>
        {metrics.rollingSharpe.length > 0 ? (
          <div
            ref={rollingSharpeChartRef}
            className="w-full h-64 bg-slate-950 rounded-lg"
            style={{ minHeight: '256px' }}
          />
        ) : (
          <div className="bg-slate-950 rounded-lg p-8 text-center">
            <p className="text-slate-400 text-sm">
              Insufficient data for rolling Sharpe ratio
            </p>
          </div>
        )}
      </div>

      {/* Drawdown Duration Histogram */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-slate-200">
            Drawdown Duration Distribution
          </h4>
        </div>
        {metrics.drawdownHistogram.buckets.length > 0 ? (
          <>
            <div
              ref={histogramChartRef}
              className="w-full h-48 bg-slate-950 rounded-lg mb-3"
              style={{ minHeight: '192px' }}
            />
            {/* Bucket Labels */}
            <div className="flex justify-around text-xs text-slate-400 px-4">
              {metrics.drawdownHistogram.buckets.map((bucket, index) => (
                <div key={index} className="text-center">
                  <p className="font-medium">{bucket}</p>
                  <p className="text-slate-500 mt-1">
                    {metrics.drawdownHistogram.counts[index]}
                  </p>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="bg-slate-950 rounded-lg p-8 text-center">
            <p className="text-slate-400 text-sm">
              No drawdown periods detected
            </p>
          </div>
        )}
      </div>

      {/* Benchmark Comparison (placeholder for future implementation) */}
      {/* Uncomment when benchmark data is available */}
      {/* <div className="mt-6 bg-slate-950 rounded-lg p-4">
        <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
          Benchmark Comparison
        </p>
        <p className="text-sm text-slate-300">
          Coming soon: Compare against BTC buy-and-hold strategy
        </p>
      </div> */}
    </div>
  );
};
