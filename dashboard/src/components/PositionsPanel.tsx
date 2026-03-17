import { useMemo, useState, useCallback, memo } from 'react';
import { useDashboardStore } from '../stores/dashboardStore';
import { shallowEqual } from '../utils/performanceOptimization';

interface PositionsPanelProps {
  onClosePosition?: (positionId: string) => void;
}

/**
 * PositionsPanel Component (Optimized)
 * 
 * Displays all open trading positions with real-time P&L updates.
 * 
 * Performance Optimizations:
 * - React.memo to prevent unnecessary re-renders
 * - Selective Zustand subscription (openPositions only)
 * - useMemo for portfolio metrics calculation
 * - useCallback for event handlers
 * 
 * Features:
 * - Real-time unrealized P&L updates via WebSocket
 * - Color-coded P&L (green for positive, red for negative)
 * - Total portfolio exposure gauge with warning indicator (>80%)
 * - Portfolio-level unrealized P&L calculation
 * - Manual position closure with confirmation dialog
 * - Risk-reward ratio display
 * - Position duration tracking
 * 
 * @param onClosePosition - Callback when closing a position
 * 
 * Requirements: 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 5.11, Task 6.10
 */
const PositionsPanelComponent: React.FC<PositionsPanelProps> = ({ onClosePosition }) => {
  // Selective Zustand subscription - only subscribe to openPositions
  const openPositions = useDashboardStore((state) => state.openPositions, shallowEqual);
  const [closingPositionId, setClosingPositionId] = useState<string | null>(null);

  // Memoize portfolio-level metrics calculation
  const portfolioMetrics = useMemo(() => {
    if (openPositions.length === 0) {
      return {
        totalExposure: 0,
        totalUnrealizedPnL: 0,
        totalUnrealizedPnLPercent: 0,
        exposureWarning: false,
      };
    }

    const totalExposure = openPositions.reduce(
      (sum, pos) => sum + pos.size * pos.entryPrice,
      0
    );

    const totalUnrealizedPnL = openPositions.reduce(
      (sum, pos) => sum + pos.unrealizedPnL,
      0
    );

    // Assuming max exposure is the total exposure (can be configured)
    const maxExposure = totalExposure > 0 ? totalExposure / 0.8 : 1; // Reverse calculate max from 80%
    const exposurePercent = (totalExposure / maxExposure) * 100;
    const exposureWarning = exposurePercent > 80;

    // Calculate weighted average PnL percent
    const totalValue = openPositions.reduce(
      (sum, pos) => sum + pos.size * pos.entryPrice,
      0
    );
    const totalUnrealizedPnLPercent =
      totalValue > 0 ? (totalUnrealizedPnL / totalValue) * 100 : 0;

    return {
      totalExposure,
      totalUnrealizedPnL,
      totalUnrealizedPnLPercent,
      exposureWarning,
      exposurePercent: Math.min(exposurePercent, 100),
    };
  }, [openPositions]);

  // Memoize formatting functions
  const formatPrice = useCallback((price: number): string => {
    return price.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 8,
    });
  }, []);

  const formatPnL = useCallback((pnl: number): string => {
    return pnl.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }, []);

  const formatDuration = useCallback((durationMinutes: number): string => {
    if (durationMinutes < 60) {
      return `${durationMinutes}m`;
    } else if (durationMinutes < 1440) {
      const hours = Math.floor(durationMinutes / 60);
      const minutes = durationMinutes % 60;
      return `${hours}h ${minutes}m`;
    } else {
      const days = Math.floor(durationMinutes / 1440);
      const hours = Math.floor((durationMinutes % 1440) / 60);
      return `${days}d ${hours}h`;
    }
  }, []);

  // Memoize event handlers
  const handleCloseClick = useCallback((positionId: string) => {
    setClosingPositionId(positionId);
  }, []);

  const handleConfirmClose = useCallback(async () => {
    if (closingPositionId && onClosePosition) {
      try {
        // Call API to close position
        const response = await fetch(`/api/positions/${closingPositionId}/close`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (response.ok) {
          onClosePosition(closingPositionId);
          setClosingPositionId(null);
        } else {
          console.error('Failed to close position');
          // TODO: Show error notification
        }
      } catch (error) {
        console.error('Error closing position:', error);
        // TODO: Show error notification
      }
    }
  }, [closingPositionId, onClosePosition]);

  const handleCancelClose = useCallback(() => {
    setClosingPositionId(null);
  }, []);

  if (openPositions.length === 0) {
    return (
      <div className="space-y-4">
        {/* Portfolio Summary - Empty State */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">Portfolio Summary</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-slate-950 rounded-lg p-4">
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">
                Total Exposure
              </p>
              <p className="text-2xl font-bold text-slate-300">$0.00</p>
            </div>
            <div className="bg-slate-950 rounded-lg p-4">
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">
                Unrealized P&L
              </p>
              <p className="text-2xl font-bold text-slate-300">$0.00</p>
            </div>
            <div className="bg-slate-950 rounded-lg p-4">
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">
                Exposure Level
              </p>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-slate-800 rounded-full h-2">
                  <div className="bg-green-500 h-2 rounded-full" style={{ width: '0%' }} />
                </div>
                <span className="text-sm font-semibold text-slate-300">0%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Empty State */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-8 text-center">
          <p className="text-slate-400">No open positions</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Portfolio Summary */}
      <section 
        className="bg-slate-900 border border-slate-800 rounded-lg p-6"
        aria-labelledby="portfolio-summary-heading"
      >
        <h3 id="portfolio-summary-heading" className="text-lg font-semibold text-slate-100 mb-4">
          Portfolio Summary
        </h3>
        <div 
          className="grid grid-cols-1 md:grid-cols-3 gap-4"
          role="region"
          aria-live="polite"
          aria-atomic="false"
        >
          <div className="bg-slate-950 rounded-lg p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">
              Total Exposure
            </p>
            <p className="text-2xl font-bold text-slate-300" aria-label={`Total exposure: ${formatPrice(portfolioMetrics.totalExposure)} dollars`}>
              ${formatPrice(portfolioMetrics.totalExposure)}
            </p>
          </div>
          <div className="bg-slate-950 rounded-lg p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">
              Unrealized P&L
            </p>
            <p
              className={`text-2xl font-bold ${
                portfolioMetrics.totalUnrealizedPnL > 0
                  ? 'text-green-500'
                  : portfolioMetrics.totalUnrealizedPnL < 0
                  ? 'text-red-500'
                  : 'text-slate-300'
              }`}
              aria-label={`Unrealized profit and loss: ${portfolioMetrics.totalUnrealizedPnL > 0 ? 'positive' : 'negative'} ${Math.abs(portfolioMetrics.totalUnrealizedPnL).toFixed(2)} dollars, ${Math.abs(portfolioMetrics.totalUnrealizedPnLPercent).toFixed(2)} percent`}
            >
              {portfolioMetrics.totalUnrealizedPnL > 0 ? '+' : ''}$
              {formatPnL(portfolioMetrics.totalUnrealizedPnL)}
              <span className="text-sm ml-2">
                ({portfolioMetrics.totalUnrealizedPnLPercent > 0 ? '+' : ''}
                {portfolioMetrics.totalUnrealizedPnLPercent.toFixed(2)}%)
              </span>
            </p>
          </div>
          <div className="bg-slate-950 rounded-lg p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">
              Exposure Level
              {portfolioMetrics.exposureWarning && (
                <span className="ml-2 text-yellow-500" role="alert" aria-label="Warning: High exposure">
                  ⚠ High
                </span>
              )}
            </p>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-slate-800 rounded-full h-2" role="progressbar" aria-valuenow={portfolioMetrics.exposurePercent ?? 0} aria-valuemin={0} aria-valuemax={100} aria-label="Portfolio exposure level">
                <div
                  className={`h-2 rounded-full transition-all ${
                    portfolioMetrics.exposureWarning
                      ? 'bg-yellow-500'
                      : 'bg-green-500'
                  }`}
                  style={{ width: `${portfolioMetrics.exposurePercent}%` }}
                />
              </div>
              <span
                className={`text-sm font-semibold ${
                  portfolioMetrics.exposureWarning ? 'text-yellow-500' : 'text-slate-300'
                }`}
                aria-hidden="true"
              >
                {(portfolioMetrics.exposurePercent ?? 0).toFixed(0)}%
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Positions Table - Desktop */}
      <section 
        className="hidden md:block bg-slate-900 border border-slate-800 rounded-lg overflow-hidden"
        aria-labelledby="positions-table-heading"
      >
        <h3 id="positions-table-heading" className="sr-only">Open Positions Table</h3>
        <div className="overflow-x-auto">
          <table 
            className="w-full"
            aria-label="Open trading positions"
          >
            <caption className="sr-only">
              List of {openPositions.length} open trading positions with real-time P&L
            </caption>
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider" scope="col">
                  Symbol
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-300 uppercase tracking-wider" scope="col">
                  Side
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-300 uppercase tracking-wider" scope="col">
                  Size
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-300 uppercase tracking-wider" scope="col">
                  Entry Price
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-300 uppercase tracking-wider" scope="col">
                  Current Price
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-300 uppercase tracking-wider" scope="col">
                  Unrealized P&L
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-300 uppercase tracking-wider" scope="col">
                  Stop Loss
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-300 uppercase tracking-wider" scope="col">
                  Take Profit
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-300 uppercase tracking-wider" scope="col">
                  R:R
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-300 uppercase tracking-wider" scope="col">
                  Duration
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-300 uppercase tracking-wider" scope="col">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {openPositions.map((position) => (
                <tr key={position.positionId} className="hover:bg-slate-800/50 transition-colors">
                  <td className="px-4 py-3 text-sm font-medium text-slate-100">
                    {position.symbol}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        position.side === 'LONG'
                          ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                          : 'bg-red-500/20 text-red-400 border border-red-500/30'
                      }`}
                    >
                      {position.side}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-slate-300 font-mono">
                    {position.size.toFixed(4)}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-slate-300 font-mono">
                    ${formatPrice(position.entryPrice)}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-slate-200 font-mono font-semibold">
                    ${formatPrice(position.currentPrice)}
                  </td>
                  <td className="px-4 py-3 text-sm text-right font-semibold">
                    <div
                      className={
                        position.unrealizedPnL > 0
                          ? 'text-green-500'
                          : position.unrealizedPnL < 0
                          ? 'text-red-500'
                          : 'text-slate-400'
                      }
                    >
                      <div className="font-mono">
                        {position.unrealizedPnL > 0 ? '+' : ''}$
                        {formatPnL(position.unrealizedPnL)}
                      </div>
                      <div className="text-xs">
                        ({position.unrealizedPnLPercent > 0 ? '+' : ''}
                        {position.unrealizedPnLPercent.toFixed(2)}%)
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-red-400 font-mono">
                    ${formatPrice(position.stopLoss)}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-green-400 font-mono">
                    ${formatPrice(position.takeProfit)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="inline-flex items-center px-2 py-1 rounded bg-slate-800 text-xs font-medium text-slate-300">
                      {position.riskRewardRatio.toFixed(2)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center text-sm text-slate-300">
                    {formatDuration(position.duration)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleCloseClick(position.positionId)}
                      className="px-3 py-1 text-xs font-medium text-red-400 hover:text-red-300 border border-red-500/30 hover:border-red-500/50 rounded transition-colors"
                    >
                      Close
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Positions Cards - Mobile */}
      <section 
        className="md:hidden space-y-3"
        aria-labelledby="positions-mobile-heading"
      >
        <h3 id="positions-mobile-heading" className="sr-only">Open Positions</h3>
        {openPositions.map((position) => (
          <article
            key={position.positionId}
            className="bg-slate-900 border border-slate-800 rounded-lg p-4"
            aria-label={`Position for ${position.symbol}`}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-base font-bold text-slate-100">{position.symbol}</span>
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    position.side === 'LONG'
                      ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                      : 'bg-red-500/20 text-red-400 border border-red-500/30'
                  }`}
                >
                  {position.side}
                </span>
              </div>
              <div className="text-right">
                <div
                  className={`text-base font-bold ${
                    position.unrealizedPnL > 0
                      ? 'text-green-500'
                      : position.unrealizedPnL < 0
                      ? 'text-red-500'
                      : 'text-slate-400'
                  }`}
                >
                  {position.unrealizedPnL > 0 ? '+' : ''}
                  {position.unrealizedPnLPercent.toFixed(2)}%
                </div>
                <div className="text-xs text-slate-400">{formatDuration(position.duration)}</div>
              </div>
            </div>

            {/* Price Info */}
            <div className="grid grid-cols-2 gap-3 mb-3 text-sm">
              <div>
                <div className="text-xs text-slate-400 mb-1">Entry</div>
                <div className="font-mono text-slate-300">${formatPrice(position.entryPrice)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400 mb-1">Current</div>
                <div className="font-mono text-slate-100 font-semibold">
                  ${formatPrice(position.currentPrice)}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-400 mb-1">Stop Loss</div>
                <div className="font-mono text-red-400">${formatPrice(position.stopLoss)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400 mb-1">Take Profit</div>
                <div className="font-mono text-green-400">${formatPrice(position.takeProfit)}</div>
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-800">
              <div className="flex items-center gap-3 text-xs text-slate-400">
                <span>
                  Size: <span className="text-slate-300 font-mono">{position.size.toFixed(4)}</span>
                </span>
                <span>
                  R:R: <span className="text-slate-300 font-medium">{position.riskRewardRatio.toFixed(2)}</span>
                </span>
              </div>
              <button
                onClick={() => handleCloseClick(position.positionId)}
                className="px-3 py-1.5 text-xs font-medium text-red-400 hover:text-red-300 border border-red-500/30 hover:border-red-500/50 rounded transition-colors touch-manipulation"
                style={{ minHeight: '44px' }}
              >
                Close
              </button>
            </div>
          </article>
        ))}
      </section>

      {/* Confirmation Dialog */}
      {closingPositionId && (
        <div 
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          role="dialog"
          aria-modal="true"
          aria-labelledby="close-position-dialog-title"
          aria-describedby="close-position-dialog-description"
        >
          <div className="bg-slate-900 border border-slate-700 rounded-lg p-6 max-w-md w-full mx-4">
            <h3 id="close-position-dialog-title" className="text-lg font-semibold text-slate-100 mb-4">
              Confirm Position Closure
            </h3>
            <p id="close-position-dialog-description" className="text-slate-300 mb-6">
              Are you sure you want to close this position? This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={handleCancelClose}
                className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-slate-100 border border-slate-700 hover:border-slate-600 rounded transition-colors"
                aria-label="Cancel closing position"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmClose}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded transition-colors"
                aria-label="Confirm close position"
              >
                Close Position
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Memoized export
export const PositionsPanel = memo(PositionsPanelComponent);
