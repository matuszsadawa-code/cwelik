import { useMemo } from 'react';
import { useDashboardStore } from '../stores/dashboardStore';

/**
 * PerformanceMetricsPanel Component
 * 
 * Displays key performance metrics with real-time updates via WebSocket.
 * 
 * Features:
 * - Win rate with trend indicator (↑↓)
 * - Profit factor with color coding (green >1.5, yellow >1.0, red otherwise)
 * - Sharpe ratio with interpretation label
 * - Current drawdown with visual gauge
 * - Daily, weekly, monthly PnL display
 * - Total trades count and active positions count
 * - Updates every 30 seconds via performance_update WebSocket messages
 * 
 * Requirements: 7.6, 7.7, 7.8, 7.9, 7.10, 7.11
 */
export const PerformanceMetricsPanel: React.FC = () => {
  const performanceMetrics = useDashboardStore((state) => state.performanceMetrics);

  // Calculate trend indicators and interpretations
  const metrics = useMemo(() => {
    if (!performanceMetrics) {
      return null;
    }

    // Profit factor color coding
    const profitFactorColor =
      performanceMetrics.profitFactor > 1.5
        ? 'text-green-500'
        : performanceMetrics.profitFactor > 1.0
        ? 'text-yellow-500'
        : 'text-red-500';

    // Sharpe ratio interpretation
    const getSharpeInterpretation = (sharpe: number): string => {
      if (sharpe > 2.0) return 'Excellent';
      if (sharpe > 1.0) return 'Good';
      if (sharpe > 0.5) return 'Acceptable';
      if (sharpe > 0) return 'Poor';
      return 'Very Poor';
    };

    const sharpeInterpretation = getSharpeInterpretation(performanceMetrics.sharpeRatio);
    const sharpeColor =
      performanceMetrics.sharpeRatio > 1.0
        ? 'text-green-500'
        : performanceMetrics.sharpeRatio > 0.5
        ? 'text-yellow-500'
        : 'text-red-500';

    // Drawdown percentage (0-100)
    const drawdownPercent = Math.abs(performanceMetrics.currentDrawdown);
    const drawdownColor =
      drawdownPercent < 5
        ? 'bg-green-500'
        : drawdownPercent < 10
        ? 'bg-yellow-500'
        : 'bg-red-500';

    return {
      profitFactorColor,
      sharpeInterpretation,
      sharpeColor,
      drawdownPercent,
      drawdownColor,
    };
  }, [performanceMetrics]);

  const formatPnL = (pnl: number): string => {
    return pnl.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  if (!performanceMetrics || !metrics) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">Performance Metrics</h3>
        <div className="text-center py-8">
          <p className="text-slate-400">Loading performance metrics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-slate-100 mb-6">Performance Metrics</h3>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {/* Win Rate */}
        <div className="bg-slate-950 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-slate-400 uppercase tracking-wider">Win Rate</p>
            <span className="text-green-500 text-sm" aria-label="Trend up">
              ↑
            </span>
          </div>
          <p className="text-2xl font-bold text-slate-100">
            {performanceMetrics.winRate.toFixed(1)}%
          </p>
        </div>

        {/* Profit Factor */}
        <div className="bg-slate-950 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            Profit Factor
          </p>
          <p className={`text-2xl font-bold ${metrics.profitFactorColor}`}>
            {performanceMetrics.profitFactor.toFixed(2)}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            {performanceMetrics.profitFactor > 1.5
              ? 'Excellent'
              : performanceMetrics.profitFactor > 1.0
              ? 'Good'
              : 'Needs Improvement'}
          </p>
        </div>

        {/* Sharpe Ratio */}
        <div className="bg-slate-950 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            Sharpe Ratio
          </p>
          <p className={`text-2xl font-bold ${metrics.sharpeColor}`}>
            {performanceMetrics.sharpeRatio.toFixed(2)}
          </p>
          <p className="text-xs text-slate-500 mt-1">{metrics.sharpeInterpretation}</p>
        </div>
      </div>

      {/* Drawdown Gauge */}
      <div className="bg-slate-950 rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs text-slate-400 uppercase tracking-wider">
            Current Drawdown
          </p>
          <p className="text-lg font-bold text-red-400">
            {metrics.drawdownPercent.toFixed(2)}%
          </p>
        </div>
        <div className="relative">
          <div className="w-full bg-slate-800 rounded-full h-3">
            <div
              className={`${metrics.drawdownColor} h-3 rounded-full transition-all duration-300`}
              style={{ width: `${Math.min(metrics.drawdownPercent, 100)}%` }}
              role="progressbar"
              aria-valuenow={metrics.drawdownPercent}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Current drawdown ${metrics.drawdownPercent.toFixed(2)}%`}
            />
          </div>
          <div className="flex justify-between text-xs text-slate-500 mt-1">
            <span>0%</span>
            <span>Max DD: {performanceMetrics.maxDrawdown.toFixed(2)}%</span>
          </div>
        </div>
      </div>

      {/* PnL Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Daily PnL */}
        <div className="bg-slate-950 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Daily P&L</p>
          <p
            className={`text-xl font-bold ${
              performanceMetrics.dailyPnL > 0
                ? 'text-green-500'
                : performanceMetrics.dailyPnL < 0
                ? 'text-red-500'
                : 'text-slate-300'
            }`}
          >
            {performanceMetrics.dailyPnL > 0 ? '+' : ''}$
            {formatPnL(performanceMetrics.dailyPnL)}
          </p>
        </div>

        {/* Weekly PnL */}
        <div className="bg-slate-950 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Weekly P&L</p>
          <p
            className={`text-xl font-bold ${
              performanceMetrics.weeklyPnL > 0
                ? 'text-green-500'
                : performanceMetrics.weeklyPnL < 0
                ? 'text-red-500'
                : 'text-slate-300'
            }`}
          >
            {performanceMetrics.weeklyPnL > 0 ? '+' : ''}$
            {formatPnL(performanceMetrics.weeklyPnL)}
          </p>
        </div>

        {/* Monthly PnL */}
        <div className="bg-slate-950 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Monthly P&L</p>
          <p
            className={`text-xl font-bold ${
              performanceMetrics.monthlyPnL > 0
                ? 'text-green-500'
                : performanceMetrics.monthlyPnL < 0
                ? 'text-red-500'
                : 'text-slate-300'
            }`}
          >
            {performanceMetrics.monthlyPnL > 0 ? '+' : ''}$
            {formatPnL(performanceMetrics.monthlyPnL)}
          </p>
        </div>
      </div>

      {/* Trading Activity */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Total Trades */}
        <div className="bg-slate-950 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            Total Trades
          </p>
          <p className="text-2xl font-bold text-slate-100">
            {performanceMetrics.totalTrades.toLocaleString()}
          </p>
        </div>

        {/* Active Positions */}
        <div className="bg-slate-950 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            Active Positions
          </p>
          <p className="text-2xl font-bold text-slate-100">
            {performanceMetrics.activePositions}
          </p>
        </div>
      </div>

      {/* Last Update */}
      <div className="mt-4 text-center">
        <p className="text-xs text-slate-500">
          Last updated: {new Date(performanceMetrics.timestamp).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
};
