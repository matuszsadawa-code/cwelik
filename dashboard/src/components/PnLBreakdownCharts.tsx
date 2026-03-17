import { useEffect, useRef, useState } from 'react';
import { createChart, LineSeries, HistogramSeries } from 'lightweight-charts';
import type { IChartApi, HistogramData, LineData, Time } from 'lightweight-charts';
import type { TimeRange, PnLBreakdownData, PnLDisplayMode, PnLPeriod } from '../types/index';
import { fetchPnLBreakdown } from '../services/api';
import {
  optimizeChartData,
  createOptimizedChartOptions,
  createRenderTimeMeasurement,
  debounce,
} from '../utils/chartOptimization';

/**
 * PnLBreakdownCharts Component
 * 
 * Displays PnL breakdown by time period (daily, weekly, monthly) with bar charts
 * and cumulative PnL overlay.
 * 
 * Features:
 * - Daily PnL bar chart with color coding (green for positive, red for negative)
 * - Weekly PnL bar chart
 * - Monthly PnL bar chart
 * - Cumulative PnL line overlay on bar charts
 * - Best and worst day/week/month display
 * - Toggle between absolute PnL and percentage PnL
 * - Responsive design
 * - Dark mode optimized colors
 * 
 * Requirements: 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10
 */

interface PnLBreakdownChartsProps {
  timeRange?: TimeRange;
  onTimeRangeChange?: (range: TimeRange) => void;
}

const TIME_RANGES: { value: TimeRange; label: string }[] = [
  { value: '7d', label: '7D' },
  { value: '30d', label: '30D' },
  { value: '90d', label: '90D' },
  { value: '1y', label: '1Y' },
  { value: 'all', label: 'All' },
];

type PeriodType = 'daily' | 'weekly' | 'monthly';

// Helper function to parse time strings
const parseTimeString = (
  timeStr: string,
  timeKey: 'date' | 'week' | 'month'
): number | null => {
  try {
    if (timeKey === 'date') {
      // YYYY-MM-DD format
      return new Date(timeStr).getTime() / 1000;
    } else if (timeKey === 'week') {
      // YYYY-Www format (e.g., 2024-W01)
      const [year, week] = timeStr.split('-W');
      const date = getDateOfISOWeek(parseInt(week), parseInt(year));
      return date.getTime() / 1000;
    } else if (timeKey === 'month') {
      // YYYY-MM format
      return new Date(timeStr + '-01').getTime() / 1000;
    }
  } catch (e) {
    console.error('Error parsing time string:', e);
  }
  return null;
};

const getDateOfISOWeek = (week: number, year: number): Date => {
  const simple = new Date(year, 0, 1 + (week - 1) * 7);
  const dow = simple.getDay();
  const ISOweekStart = simple;
  if (dow <= 4) {
    ISOweekStart.setDate(simple.getDate() - simple.getDay() + 1);
  } else {
    ISOweekStart.setDate(simple.getDate() + 8 - simple.getDay());
  }
  return ISOweekStart;
};

export const PnLBreakdownCharts: React.FC<PnLBreakdownChartsProps> = ({
  timeRange = 'all',
  onTimeRangeChange,
}) => {
  const dailyChartRef = useRef<HTMLDivElement>(null);
  const weeklyChartRef = useRef<HTMLDivElement>(null);
  const monthlyChartRef = useRef<HTMLDivElement>(null);
  
  const dailyChartInstanceRef = useRef<IChartApi | null>(null);
  const weeklyChartInstanceRef = useRef<IChartApi | null>(null);
  const monthlyChartInstanceRef = useRef<IChartApi | null>(null);
  
  const renderMeasurement = useRef(createRenderTimeMeasurement('PnLBreakdownCharts'));
  
  const [pnlData, setPnlData] = useState<PnLBreakdownData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [displayMode, setDisplayMode] = useState<PnLDisplayMode>('percentage');
  const [activePeriod, setActivePeriod] = useState<PeriodType>('daily');
  const [renderTime, setRenderTime] = useState<number | null>(null);

  // Fetch PnL breakdown data
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetchPnLBreakdown(timeRange);
        setPnlData(data);
      } catch (err) {
        console.error('Error fetching PnL breakdown:', err);
        setError(err instanceof Error ? err.message : 'Failed to load PnL breakdown');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [timeRange]);

  const createChartInstance = (container: HTMLDivElement): IChartApi => {
    return createChart(
      container,
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
        height: 300,
      })
    );
  };

  const updateChart = (
    chart: IChartApi,
    data: PnLPeriod[],
    timeKey: 'date' | 'week' | 'month'
  ) => {
    // Start render time measurement
    renderMeasurement.current.start();

    // Create histogram series for PnL
    const histogramSeriesInstance = chart.addSeries(HistogramSeries, {
      color: '#22C55E',
      priceFormat: {
        type: 'custom',
        formatter: (price: number) => `${price.toFixed(2)}%`,
      },
    });

    // Create line series for cumulative PnL
    const lineSeriesInstance = chart.addSeries(LineSeries, {
      color: '#3B82F6', // blue-500
      lineWidth: 2,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 4,
      priceScaleId: 'right',
    });

    // Convert data to chart format
    const histogramData: HistogramData[] = [];
    const lineData: LineData[] = [];

    data.forEach((period) => {
      const timeValue = period[timeKey];
      if (!timeValue) return;

      // Convert time string to timestamp
      const timestamp = parseTimeString(timeValue, timeKey);
      if (!timestamp) return;

      // Histogram data with color based on positive/negative
      histogramData.push({
        time: timestamp as Time,
        value: period.pnl,
        color: period.pnl >= 0 ? '#22C55E' : '#EF4444',
      });

      // Line data (cumulative PnL)
      lineData.push({
        time: timestamp as Time,
        value: period.cumulativePnL,
      });
    });

    // Optimize data by limiting to 1000 points
    const optimizedHistogramData = optimizeChartData(histogramData);
    const optimizedLineData = optimizeChartData(lineData);

    histogramSeriesInstance.setData(optimizedHistogramData);
    lineSeriesInstance.setData(optimizedLineData);

    // Fit content
    chart.timeScale().fitContent();

    // End render time measurement
    const time = renderMeasurement.current.end();
    if (time !== null) {
      setRenderTime(time);
    }
  };

  // Initialize and update charts
  useEffect(() => {
    if (!pnlData || loading || error) return;

    // Initialize daily chart
    if (dailyChartRef.current && !dailyChartInstanceRef.current) {
      dailyChartInstanceRef.current = createChartInstance(dailyChartRef.current);
    }

    // Initialize weekly chart
    if (weeklyChartRef.current && !weeklyChartInstanceRef.current) {
      weeklyChartInstanceRef.current = createChartInstance(weeklyChartRef.current);
    }

    // Initialize monthly chart
    if (monthlyChartRef.current && !monthlyChartInstanceRef.current) {
      monthlyChartInstanceRef.current = createChartInstance(monthlyChartRef.current);
    }

    // Update charts with data
    if (dailyChartInstanceRef.current && pnlData.daily.length > 0) {
      updateChart(dailyChartInstanceRef.current, pnlData.daily, 'date');
    }

    if (weeklyChartInstanceRef.current && pnlData.weekly.length > 0) {
      updateChart(weeklyChartInstanceRef.current, pnlData.weekly, 'week');
    }

    if (monthlyChartInstanceRef.current && pnlData.monthly.length > 0) {
      updateChart(monthlyChartInstanceRef.current, pnlData.monthly, 'month');
    }

    // Handle resize
    const handleResize = debounce(() => {
      const resizeChart = (chart: IChartApi | null, container: HTMLDivElement | null) => {
        if (chart && container) {
          chart.applyOptions({
            width: container.clientWidth,
          });
        }
      };

      resizeChart(dailyChartInstanceRef.current, dailyChartRef.current);
      resizeChart(weeklyChartInstanceRef.current, weeklyChartRef.current);
      resizeChart(monthlyChartInstanceRef.current, monthlyChartRef.current);
    }, 150);

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [pnlData, loading, error, displayMode]);

  // Cleanup charts on unmount
  useEffect(() => {
    return () => {
      if (dailyChartInstanceRef.current) {
        dailyChartInstanceRef.current.remove();
        dailyChartInstanceRef.current = null;
      }
      if (weeklyChartInstanceRef.current) {
        weeklyChartInstanceRef.current.remove();
        weeklyChartInstanceRef.current = null;
      }
      if (monthlyChartInstanceRef.current) {
        monthlyChartInstanceRef.current.remove();
        monthlyChartInstanceRef.current = null;
      }
    };
  }, []);

  const handleTimeRangeChange = (range: TimeRange) => {
    if (onTimeRangeChange) {
      onTimeRangeChange(range);
    }
  };

  const formatPnL = (value: number): string => {
    if (displayMode === 'percentage') {
      return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
    } else {
      // For absolute mode, we'd need the actual dollar amount
      // For now, we'll just show percentage
      return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
    }
  };

  const renderBestWorst = (
    best: PnLPeriod | null,
    worst: PnLPeriod | null,
    label: string
  ) => {
    if (!best && !worst) return null;

    return (
      <div className="grid grid-cols-2 gap-4">
        {best && (
          <div className="bg-slate-950 rounded-lg p-4 border border-green-500/20">
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
              Best {label}
            </p>
            <p className="text-lg font-bold text-green-500">
              {formatPnL(best.pnl)}
            </p>
            <p className="text-xs text-slate-500 mt-1">
              {best.date || best.week || best.month}
            </p>
          </div>
        )}
        {worst && (
          <div className="bg-slate-950 rounded-lg p-4 border border-red-500/20">
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
              Worst {label}
            </p>
            <p className="text-lg font-bold text-red-400">
              {formatPnL(worst.pnl)}
            </p>
            <p className="text-xs text-slate-500 mt-1">
              {worst.date || worst.week || worst.month}
            </p>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-slate-100">PnL Breakdown</h3>
        
        <div className="flex gap-4">
          {/* Display Mode Toggle */}
          <div className="flex gap-1 bg-slate-950 rounded-lg p-1">
            <button
              onClick={() => setDisplayMode('percentage')}
              className={`px-3 py-1 text-sm font-medium rounded transition-colors ${
                displayMode === 'percentage'
                  ? 'bg-green-500 text-white'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
              aria-label="Show percentage PnL"
            >
              %
            </button>
            <button
              onClick={() => setDisplayMode('absolute')}
              className={`px-3 py-1 text-sm font-medium rounded transition-colors ${
                displayMode === 'absolute'
                  ? 'bg-green-500 text-white'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
              aria-label="Show absolute PnL"
            >
              $
            </button>
          </div>

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
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center h-96">
          <p className="text-slate-400">Loading PnL breakdown...</p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="flex items-center justify-center h-96">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Charts and Metrics */}
      {!loading && !error && pnlData && (
        <>
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

          {/* Period Tabs */}
          <div className="flex gap-2 mb-6">
            <button
              onClick={() => setActivePeriod('daily')}
              className={`px-4 py-2 text-sm font-medium rounded transition-colors ${
                activePeriod === 'daily'
                  ? 'bg-slate-800 text-slate-100'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              Daily
            </button>
            <button
              onClick={() => setActivePeriod('weekly')}
              className={`px-4 py-2 text-sm font-medium rounded transition-colors ${
                activePeriod === 'weekly'
                  ? 'bg-slate-800 text-slate-100'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              Weekly
            </button>
            <button
              onClick={() => setActivePeriod('monthly')}
              className={`px-4 py-2 text-sm font-medium rounded transition-colors ${
                activePeriod === 'monthly'
                  ? 'bg-slate-800 text-slate-100'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              Monthly
            </button>
          </div>

          {/* Daily Chart */}
          {activePeriod === 'daily' && (
            <div className="space-y-4">
              {pnlData.daily.length > 0 ? (
                <>
                  <div
                    ref={dailyChartRef}
                    className="w-full bg-slate-950 rounded-lg"
                  />
                  {renderBestWorst(pnlData.bestDay, pnlData.worstDay, 'Day')}
                </>
              ) : (
                <div className="flex items-center justify-center h-64 bg-slate-950 rounded-lg">
                  <p className="text-slate-400">No daily data available</p>
                </div>
              )}
            </div>
          )}

          {/* Weekly Chart */}
          {activePeriod === 'weekly' && (
            <div className="space-y-4">
              {pnlData.weekly.length > 0 ? (
                <>
                  <div
                    ref={weeklyChartRef}
                    className="w-full bg-slate-950 rounded-lg"
                  />
                  {renderBestWorst(pnlData.bestWeek, pnlData.worstWeek, 'Week')}
                </>
              ) : (
                <div className="flex items-center justify-center h-64 bg-slate-950 rounded-lg">
                  <p className="text-slate-400">No weekly data available</p>
                </div>
              )}
            </div>
          )}

          {/* Monthly Chart */}
          {activePeriod === 'monthly' && (
            <div className="space-y-4">
              {pnlData.monthly.length > 0 ? (
                <>
                  <div
                    ref={monthlyChartRef}
                    className="w-full bg-slate-950 rounded-lg"
                  />
                  {renderBestWorst(pnlData.bestMonth, pnlData.worstMonth, 'Month')}
                </>
              ) : (
                <div className="flex items-center justify-center h-64 bg-slate-950 rounded-lg">
                  <p className="text-slate-400">No monthly data available</p>
                </div>
              )}
            </div>
          )}

          {/* Legend */}
          <div className="flex items-center justify-center gap-6 mt-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-green-500 rounded"></div>
              <span className="text-slate-400">Positive PnL</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-red-500 rounded"></div>
              <span className="text-slate-400">Negative PnL</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-0.5 bg-blue-500"></div>
              <span className="text-slate-400">Cumulative PnL</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
