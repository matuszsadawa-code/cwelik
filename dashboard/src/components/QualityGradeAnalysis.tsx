import { useEffect, useState, useMemo, useRef } from 'react';
import { createChart, type IChartApi, type HistogramData, type Time, HistogramSeries, LineSeries } from 'lightweight-charts';

/**
 * QualityGradeAnalysis Component
 * 
 * Displays performance analysis broken down by signal quality grade (A+, A, B, C).
 * 
 * Features:
 * - Quality grade performance bar chart showing win rate by grade
 * - Performance table with detailed metrics per grade
 * - Highlight best performing quality grade
 * - Confidence vs. actual win rate scatter plot
 * - Calibration warning when performance deviates significantly from expected
 * - Dark Mode OLED optimized design
 * 
 * Requirements: 13.5, 13.6, 13.7, 13.8, 13.9
 */

interface QualityMetrics {
  quality: 'A+' | 'A' | 'B' | 'C';
  totalTrades: number;
  winRate: number;
  avgPnL: number;
  totalPnL: number;
  avgConfidence: number;
}

interface QualityAnalysisData {
  qualityMetrics: QualityMetrics[];
  calibrationWarning: boolean;
  calibrationMessage?: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Quality grade colors
const QUALITY_COLORS: Record<string, string> = {
  'A+': '#22C55E', // green-500
  'A': '#84CC16', // lime-500
  'B': '#EAB308', // yellow-500
  'C': '#EF4444', // red-500
};

export const QualityGradeAnalysis: React.FC = () => {
  const [data, setData] = useState<QualityAnalysisData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const barChartRef = useRef<HTMLDivElement>(null);
  const scatterChartRef = useRef<HTMLDivElement>(null);
  const barChartInstance = useRef<IChartApi | null>(null);
  const scatterChartInstance = useRef<IChartApi | null>(null);

  // Fetch quality analysis data
  useEffect(() => {
    const fetchQualityAnalysis = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`${API_BASE_URL}/api/analytics/quality-analysis`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch quality analysis: ${response.statusText}`);
        }
        
        const responseData = await response.json();
        setData(responseData);
      } catch (err) {
        console.error('Error fetching quality analysis:', err);
        setError(err instanceof Error ? err.message : 'Failed to load quality analysis');
      } finally {
        setLoading(false);
      }
    };

    fetchQualityAnalysis();
    
    // Refresh every 60 seconds
    const interval = setInterval(fetchQualityAnalysis, 60000);
    
    return () => clearInterval(interval);
  }, []);

  // Find best performing quality grade
  const bestGrade = useMemo(() => {
    if (!data || data.qualityMetrics.length === 0) return null;
    return data.qualityMetrics.reduce((best, current) =>
      current.winRate > best.winRate ? current : best
    );
  }, [data]);

  // Initialize bar chart
  useEffect(() => {
    if (!barChartRef.current || !data || data.qualityMetrics.length === 0) {
      return;
    }

    // Create chart if it doesn't exist
    if (!barChartInstance.current) {
      const chart = createChart(barChartRef.current, {
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
        crosshair: {
          mode: 1,
        },
      });

      barChartInstance.current = chart;

      const histogramSeries = chart.addSeries(HistogramSeries, {
        priceFormat: {
          type: 'custom',
          formatter: (price: number) => `${price.toFixed(1)}%`,
        },
      });

      // Convert data to chart format
      const chartData: HistogramData[] = data.qualityMetrics.map((metric, index) => ({
        time: (index + 1) as Time,
        value: metric.winRate,
        color: QUALITY_COLORS[metric.quality],
      }));

      histogramSeries.setData(chartData);
      chart.timeScale().fitContent();
    }

    // Handle resize
    const handleResize = () => {
      if (barChartInstance.current && barChartRef.current) {
        barChartInstance.current.applyOptions({
          width: barChartRef.current.clientWidth,
          height: barChartRef.current.clientHeight,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [data]);

  // Initialize scatter plot (confidence vs. win rate)
  useEffect(() => {
    if (!scatterChartRef.current || !data || data.qualityMetrics.length === 0) {
      return;
    }

    // Create chart if it doesn't exist
    if (!scatterChartInstance.current) {
      const chart = createChart(scatterChartRef.current, {
        layout: {
          background: { color: '#020617' },
          textColor: '#94A3B8',
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
          visible: false,
        },
      });

      scatterChartInstance.current = chart;

      // Add a line series for each quality grade (simulating scatter plot)
      data.qualityMetrics.forEach((metric) => {
        const lineSeries = chart.addSeries(LineSeries, {
          color: QUALITY_COLORS[metric.quality],
          pointMarkersVisible: true,
          crosshairMarkerVisible: true,
          crosshairMarkerRadius: 6,
          crosshairMarkerBorderColor: QUALITY_COLORS[metric.quality],
          crosshairMarkerBackgroundColor: QUALITY_COLORS[metric.quality],
        });

        // Plot confidence vs. win rate
        lineSeries.setData([
          {
            time: (metric.avgConfidence * 100) as Time,
            value: metric.winRate,
          },
        ]);
      });

      chart.timeScale().fitContent();
    }

    // Handle resize
    const handleResize = () => {
      if (scatterChartInstance.current && scatterChartRef.current) {
        scatterChartInstance.current.applyOptions({
          width: scatterChartRef.current.clientWidth,
          height: scatterChartRef.current.clientHeight,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [data]);

  // Cleanup charts on unmount
  useEffect(() => {
    return () => {
      if (barChartInstance.current) {
        barChartInstance.current.remove();
        barChartInstance.current = null;
      }
      if (scatterChartInstance.current) {
        scatterChartInstance.current.remove();
        scatterChartInstance.current = null;
      }
    };
  }, []);

  if (loading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">Quality Grade Analysis</h3>
        <div className="text-center py-8">
          <p className="text-slate-400">Loading quality grade analysis...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">Quality Grade Analysis</h3>
        <div className="text-center py-8">
          <p className="text-red-400">{error || 'No quality grade data available'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-slate-100">Quality Grade Analysis</h3>
        
        {/* Calibration Warning */}
        {data.calibrationWarning && (
          <div className="flex items-center gap-2 bg-yellow-500/10 border border-yellow-500/30 rounded-lg px-3 py-2">
            <svg className="w-5 h-5 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span className="text-sm text-yellow-500 font-medium">
              {data.calibrationMessage || 'Calibration Warning: Performance deviates from expected'}
            </span>
          </div>
        )}
      </div>

      {/* Win Rate Bar Chart */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-slate-200">Win Rate by Quality Grade</h4>
        </div>
        {data.qualityMetrics.length > 0 ? (
          <>
            <div
              ref={barChartRef}
              className="w-full h-64 bg-slate-950 rounded-lg mb-3"
              style={{ minHeight: '256px' }}
            />
            {/* Grade Labels */}
            <div className="flex justify-around text-xs text-slate-400 px-4">
              {data.qualityMetrics.map((metric) => (
                <div key={metric.quality} className="text-center">
                  <div
                    className="w-3 h-3 rounded-full mx-auto mb-1"
                    style={{ backgroundColor: QUALITY_COLORS[metric.quality] }}
                  />
                  <p className="font-medium">{metric.quality}</p>
                  <p className="text-slate-500 mt-1">{metric.winRate.toFixed(1)}%</p>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="bg-slate-950 rounded-lg p-8 text-center">
            <p className="text-slate-400 text-sm">No quality grade data available</p>
          </div>
        )}
      </div>

      {/* Performance Table */}
      <div className="mb-6">
        <h4 className="text-sm font-semibold text-slate-200 mb-3">Performance Metrics by Grade</h4>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Grade
                </th>
                <th className="text-right py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Trades
                </th>
                <th className="text-right py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Win Rate
                </th>
                <th className="text-right py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Avg PnL
                </th>
                <th className="text-right py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Total PnL
                </th>
                <th className="text-right py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Avg Confidence
                </th>
              </tr>
            </thead>
            <tbody>
              {data.qualityMetrics.map((metric) => {
                const isBest = bestGrade && metric.quality === bestGrade.quality;
                return (
                  <tr
                    key={metric.quality}
                    className={`border-b border-slate-800/50 ${
                      isBest ? 'bg-green-500/5 border-l-4 border-l-green-500' : ''
                    }`}
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: QUALITY_COLORS[metric.quality] }}
                        />
                        <span className="text-sm font-medium text-slate-100">
                          {metric.quality}
                        </span>
                        {isBest && (
                          <span className="text-xs text-green-500 font-medium">BEST</span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-sm text-right text-slate-300">
                      {metric.totalTrades}
                    </td>
                    <td className="py-3 px-4 text-sm text-right">
                      <span
                        className={
                          metric.winRate >= 60
                            ? 'text-green-500'
                            : metric.winRate >= 50
                            ? 'text-yellow-500'
                            : 'text-red-400'
                        }
                      >
                        {metric.winRate.toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-3 px-4 text-sm text-right">
                      <span className={metric.avgPnL >= 0 ? 'text-green-500' : 'text-red-400'}>
                        {metric.avgPnL >= 0 ? '+' : ''}
                        {metric.avgPnL.toFixed(2)}%
                      </span>
                    </td>
                    <td className="py-3 px-4 text-sm text-right font-medium">
                      <span className={metric.totalPnL >= 0 ? 'text-green-500' : 'text-red-400'}>
                        {metric.totalPnL >= 0 ? '+' : ''}
                        {metric.totalPnL.toFixed(2)}%
                      </span>
                    </td>
                    <td className="py-3 px-4 text-sm text-right text-slate-300">
                      {(metric.avgConfidence * 100).toFixed(1)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confidence vs. Win Rate Scatter Plot */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-slate-200">
            Confidence vs. Actual Win Rate
          </h4>
          <p className="text-xs text-slate-500">
            Ideal: Points should align with expected win rates
          </p>
        </div>
        {data.qualityMetrics.length > 0 ? (
          <div
            ref={scatterChartRef}
            className="w-full h-64 bg-slate-950 rounded-lg"
            style={{ minHeight: '256px' }}
          />
        ) : (
          <div className="bg-slate-950 rounded-lg p-8 text-center">
            <p className="text-slate-400 text-sm">Insufficient data for scatter plot</p>
          </div>
        )}
      </div>
    </div>
  );
};
