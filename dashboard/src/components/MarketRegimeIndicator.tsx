import { useEffect, useRef, useMemo } from 'react';
import { createChart } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, LineData } from 'lightweight-charts';
import { useDashboardStore } from '../stores/dashboardStore';

interface MarketRegimeIndicatorProps {
  symbol: string;
}

interface RegimeHistoryPoint {
  time: number;
  regime: 'TRENDING' | 'RANGING' | 'VOLATILE' | 'QUIET';
  confidence: number;
}

/**
 * MarketRegimeIndicator Component
 * 
 * Displays market regime classification for a selected symbol with real-time updates.
 * 
 * Features:
 * - Regime badge with color coding (TRENDING: blue, RANGING: yellow, VOLATILE: red, QUIET: gray)
 * - Regime confidence score as percentage
 * - Volatility percentile display
 * - Trend strength indicator
 * - Regime history chart for past 24 hours
 * - Real-time updates via WebSocket
 * 
 * @param symbol - Trading pair symbol (e.g., 'BTCUSDT')
 * 
 * Requirements: 2.4, 2.5, 2.6, 2.7, 2.8
 */
export const MarketRegimeIndicator: React.FC<MarketRegimeIndicatorProps> = ({
  symbol,
}) => {
  const marketRegimes = useDashboardStore((state) => state.marketRegimes);
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  // Get current regime for the symbol
  const currentRegime = useMemo(() => {
    return marketRegimes.get(symbol) || null;
  }, [marketRegimes, symbol]);

  // Mock regime history data (in production, this would come from API)
  const regimeHistory = useMemo<RegimeHistoryPoint[]>(() => {
    const now = Date.now();
    const history: RegimeHistoryPoint[] = [];
    const regimes: Array<'TRENDING' | 'RANGING' | 'VOLATILE' | 'QUIET'> = [
      'TRENDING',
      'RANGING',
      'VOLATILE',
      'QUIET',
    ];

    // Generate 24 hours of history (1 point per hour)
    for (let i = 24; i >= 0; i--) {
      const timestamp = now - i * 60 * 60 * 1000;
      history.push({
        time: timestamp,
        regime: regimes[Math.floor(Math.random() * regimes.length)],
        confidence: 60 + Math.random() * 30,
      });
    }

    return history;
  }, []);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 200,
      layout: {
        background: { color: '#0F172A' },
        textColor: '#94A3B8',
      },
      grid: {
        vertLines: { color: '#1E293B' },
        horzLines: { color: '#1E293B' },
      },
      timeScale: {
        borderColor: '#334155',
        timeVisible: true,
      },
      rightPriceScale: {
        borderColor: '#334155',
      },
    });

    const lineSeries = chart.addSeries({
      type: 'Line',
      color: '#3B82F6',
      lineWidth: 2,
      priceFormat: {
        type: 'custom',
        formatter: (price: number) => {
          const regimes = ['QUIET', 'RANGING', 'VOLATILE', 'TRENDING'];
          return regimes[Math.floor(price)] || '';
        },
      },
    });

    // Convert regime history to chart data
    const chartData: LineData[] = regimeHistory.map((point) => {
      const regimeValue =
        point.regime === 'QUIET'
          ? 0
          : point.regime === 'RANGING'
          ? 1
          : point.regime === 'VOLATILE'
          ? 2
          : 3;

      return {
        time: Math.floor(point.time / 1000) as any,
        value: regimeValue,
      };
    });

    lineSeries.setData(chartData);
    chart.timeScale().fitContent();

    chartRef.current = chart;
    seriesRef.current = lineSeries;

    // Handle resize
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
    };
  }, [regimeHistory]);

  // Get regime color
  const getRegimeColor = (regime: string): string => {
    switch (regime) {
      case 'TRENDING':
        return 'bg-blue-500';
      case 'RANGING':
        return 'bg-yellow-500';
      case 'VOLATILE':
        return 'bg-red-500';
      case 'QUIET':
        return 'bg-gray-500';
      default:
        return 'bg-gray-500';
    }
  };

  // Get regime text color
  const getRegimeTextColor = (regime: string): string => {
    switch (regime) {
      case 'TRENDING':
        return 'text-blue-400';
      case 'RANGING':
        return 'text-yellow-400';
      case 'VOLATILE':
        return 'text-red-400';
      case 'QUIET':
        return 'text-gray-400';
      default:
        return 'text-gray-400';
    }
  };

  if (!currentRegime) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-8">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-slate-400">Loading market regime...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-950 px-6 py-4">
        <h3 className="text-lg font-semibold text-slate-100">Market Regime</h3>
        <p className="text-sm text-slate-400 mt-1">{symbol}</p>
      </div>

      {/* Current Regime */}
      <div className="p-6">
        {/* Regime Badge */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <div
              className={`${getRegimeColor(
                currentRegime.regime
              )} w-3 h-3 rounded-full`}
            />
            <span
              className={`text-2xl font-bold ${getRegimeTextColor(
                currentRegime.regime
              )}`}
            >
              {currentRegime.regime}
            </span>
          </div>

          {/* Confidence Score */}
          <div className="text-right">
            <p className="text-xs text-slate-400 uppercase tracking-wider">
              Confidence
            </p>
            <p className="text-2xl font-bold text-slate-100 mt-1">
              {currentRegime.confidence.toFixed(1)}%
            </p>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          {/* Volatility Percentile */}
          <div className="bg-slate-800/50 rounded-lg p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
              Volatility Percentile
            </p>
            <div className="flex items-end justify-between">
              <p className="text-xl font-semibold text-slate-100">
                {currentRegime.volatilityPercentile.toFixed(1)}%
              </p>
              <div className="flex items-center space-x-1">
                {currentRegime.volatilityPercentile > 70 ? (
                  <svg
                    className="w-5 h-5 text-red-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                    />
                  </svg>
                ) : currentRegime.volatilityPercentile < 30 ? (
                  <svg
                    className="w-5 h-5 text-green-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"
                    />
                  </svg>
                ) : (
                  <svg
                    className="w-5 h-5 text-yellow-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 12h14"
                    />
                  </svg>
                )}
              </div>
            </div>

            {/* Volatility Bar */}
            <div className="mt-3 bg-slate-700 rounded-full h-2 overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  currentRegime.volatilityPercentile > 70
                    ? 'bg-red-500'
                    : currentRegime.volatilityPercentile < 30
                    ? 'bg-green-500'
                    : 'bg-yellow-500'
                }`}
                style={{ width: `${currentRegime.volatilityPercentile}%` }}
              />
            </div>
          </div>

          {/* Trend Strength */}
          <div className="bg-slate-800/50 rounded-lg p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
              Trend Strength
            </p>
            <div className="flex items-end justify-between">
              <p className="text-xl font-semibold text-slate-100">
                {currentRegime.trendStrength.toFixed(1)}%
              </p>
              <div className="flex items-center space-x-1">
                {currentRegime.trendStrength > 60 ? (
                  <svg
                    className="w-5 h-5 text-blue-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                    />
                  </svg>
                ) : currentRegime.trendStrength < 30 ? (
                  <svg
                    className="w-5 h-5 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 12h14"
                    />
                  </svg>
                ) : (
                  <svg
                    className="w-5 h-5 text-yellow-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                    />
                  </svg>
                )}
              </div>
            </div>

            {/* Trend Strength Bar */}
            <div className="mt-3 bg-slate-700 rounded-full h-2 overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  currentRegime.trendStrength > 60
                    ? 'bg-blue-500'
                    : currentRegime.trendStrength < 30
                    ? 'bg-gray-500'
                    : 'bg-yellow-500'
                }`}
                style={{ width: `${currentRegime.trendStrength}%` }}
              />
            </div>
          </div>
        </div>

        {/* Regime History Chart */}
        <div className="bg-slate-800/50 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-3">
            Regime History (24 Hours)
          </p>
          <div ref={chartContainerRef} className="w-full" />
        </div>

        {/* Legend */}
        <div className="mt-4 flex flex-wrap gap-4 text-xs">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-blue-500" />
            <span className="text-slate-400">Trending</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <span className="text-slate-400">Ranging</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <span className="text-slate-400">Volatile</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-gray-500" />
            <span className="text-slate-400">Quiet</span>
          </div>
        </div>
      </div>
    </div>
  );
};
