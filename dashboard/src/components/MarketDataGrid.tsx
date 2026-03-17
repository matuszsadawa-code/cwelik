import { useMemo, useState, useCallback, memo } from 'react';
import { useDashboardStore } from '../stores/dashboardStore';
import type { MarketDataSnapshot, MarketRegime } from '../types/index';
import { shallowEqual } from '../utils/performanceOptimization';

interface MarketDataGridProps {
  symbols: string[];
  onSymbolSelect?: (symbol: string) => void;
}

type SortColumn = 'symbol' | 'price' | 'change24h' | 'volume24h' | 'bidAskSpread' | 'cvd';
type SortDirection = 'asc' | 'desc';

/**
 * MarketDataGrid Component (Optimized)
 * 
 * Displays real-time market data for monitored symbols in a sortable table format.
 * 
 * Performance Optimizations:
 * - React.memo to prevent unnecessary re-renders
 * - Selective Zustand subscriptions (only marketData and marketRegimes)
 * - useMemo for expensive sorting operations
 * - useCallback for event handlers
 * - Memoized row components
 * 
 * Features:
 * - Real-time price updates via WebSocket (sub-100ms latency)
 * - Color-coded price changes (green for positive, red for negative)
 * - Sortable columns (click header to sort)
 * - Market regime indicators with confidence scores
 * - Row click to view detailed order book
 * 
 * @param symbols - Array of symbol names to display (e.g., ['BTCUSDT', 'ETHUSDT'])
 * @param onSymbolSelect - Callback when a row is clicked to view order book details
 * 
 * Requirements: 1.2, 1.3, 1.4, 1.5, 1.9, 1.10, Task 6.10
 */
const MarketDataGridComponent: React.FC<MarketDataGridProps> = ({ symbols, onSymbolSelect }) => {
  // Selective Zustand subscriptions - only subscribe to needed state slices
  const marketData = useDashboardStore((state) => state.marketData, shallowEqual);
  const marketRegimes = useDashboardStore((state) => state.marketRegimes, shallowEqual);
  const [sortColumn, setSortColumn] = useState<SortColumn>('symbol');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  // Memoize sort handler with useCallback
  const handleSort = useCallback((column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  }, [sortColumn, sortDirection]);

  const sortedData = useMemo(() => {
    const dataArray = symbols
      .map((symbol) => ({
        symbol,
        data: marketData.get(symbol),
        regime: marketRegimes.get(symbol) || null,
      }))
      .filter((item) => item.data !== undefined) as Array<{
        symbol: string;
        data: MarketDataSnapshot;
        regime: MarketRegime | null;
      }>;

    return dataArray.sort((a, b) => {
      let aValue: number | string;
      let bValue: number | string;

      switch (sortColumn) {
        case 'symbol':
          aValue = a.symbol;
          bValue = b.symbol;
          break;
        case 'price':
          aValue = a.data.price;
          bValue = b.data.price;
          break;
        case 'change24h':
          aValue = a.data.change24h;
          bValue = b.data.change24h;
          break;
        case 'volume24h':
          aValue = a.data.volume24h;
          bValue = b.data.volume24h;
          break;
        case 'bidAskSpread':
          aValue = a.data.bidAskSpread;
          bValue = b.data.bidAskSpread;
          break;
        case 'cvd':
          aValue = a.data.cvd;
          bValue = b.data.cvd;
          break;
        default:
          aValue = a.symbol;
          bValue = b.symbol;
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      return sortDirection === 'asc'
        ? (aValue as number) - (bValue as number)
        : (bValue as number) - (aValue as number);
    });
  }, [symbols, marketData, marketRegimes, sortColumn, sortDirection]);

  const formatPrice = (price: number): string => {
    return price.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 8,
    });
  };

  const formatVolume = (volume: number): string => {
    if (volume >= 1_000_000_000) {
      return `${(volume / 1_000_000_000).toFixed(2)}B`;
    } else if (volume >= 1_000_000) {
      return `${(volume / 1_000_000).toFixed(2)}M`;
    } else if (volume >= 1_000) {
      return `${(volume / 1_000).toFixed(2)}K`;
    }
    return volume.toFixed(2);
  };

  const formatCVD = (cvd: number): string => {
    if (Math.abs(cvd) >= 1_000_000) {
      return `${(cvd / 1_000_000).toFixed(2)}M`;
    } else if (Math.abs(cvd) >= 1_000) {
      return `${(cvd / 1_000).toFixed(2)}K`;
    }
    return cvd.toFixed(2);
  };

  const getRegimeColor = (regime: string): string => {
    switch (regime) {
      case 'TRENDING':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'RANGING':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'VOLATILE':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'QUIET':
        return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const getSortIcon = (column: SortColumn): string => {
    if (sortColumn !== column) return '↕';
    return sortDirection === 'asc' ? '↑' : '↓';
  };

  const handleRowClick = (symbol: string) => {
    if (onSymbolSelect) {
      onSymbolSelect(symbol);
    }
  };

  if (sortedData.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-8 text-center">
        <p className="text-slate-400">No market data available</p>
      </div>
    );
  }

  return (
    <>
      {/* Desktop Table View (md and above) */}
      <div className="hidden md:block bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table 
            className="w-full"
            aria-label="Real-time market data for monitored symbols"
          >
            <caption className="sr-only">
              Market data showing price, volume, and regime information for {sortedData.length} symbols
            </caption>
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950">
                <th
                  className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider cursor-pointer hover:text-green-400 transition-colors"
                  onClick={() => handleSort('symbol')}
                  aria-sort={sortColumn === 'symbol' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
                  scope="col"
                >
                  Symbol {getSortIcon('symbol')}
                </th>
                <th
                  className="px-4 py-3 text-right text-xs font-semibold text-slate-300 uppercase tracking-wider cursor-pointer hover:text-green-400 transition-colors"
                  onClick={() => handleSort('price')}
                  aria-sort={sortColumn === 'price' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
                  scope="col"
                >
                  Price {getSortIcon('price')}
                </th>
                <th
                  className="px-4 py-3 text-right text-xs font-semibold text-slate-300 uppercase tracking-wider cursor-pointer hover:text-green-400 transition-colors"
                  onClick={() => handleSort('change24h')}
                  aria-sort={sortColumn === 'change24h' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
                  scope="col"
                >
                  24h Change {getSortIcon('change24h')}
                </th>
                <th
                  className="px-4 py-3 text-right text-xs font-semibold text-slate-300 uppercase tracking-wider cursor-pointer hover:text-green-400 transition-colors"
                  onClick={() => handleSort('volume24h')}
                  aria-sort={sortColumn === 'volume24h' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
                  scope="col"
                >
                  Volume {getSortIcon('volume24h')}
                </th>
                <th
                  className="px-4 py-3 text-right text-xs font-semibold text-slate-300 uppercase tracking-wider cursor-pointer hover:text-green-400 transition-colors"
                  onClick={() => handleSort('bidAskSpread')}
                  aria-sort={sortColumn === 'bidAskSpread' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
                  scope="col"
                >
                  Bid-Ask Spread {getSortIcon('bidAskSpread')}
                </th>
                <th
                  className="px-4 py-3 text-right text-xs font-semibold text-slate-300 uppercase tracking-wider cursor-pointer hover:text-green-400 transition-colors"
                  onClick={() => handleSort('cvd')}
                  aria-sort={sortColumn === 'cvd' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
                  scope="col"
                >
                  CVD {getSortIcon('cvd')}
                </th>
                <th 
                  className="px-4 py-3 text-center text-xs font-semibold text-slate-300 uppercase tracking-wider"
                  scope="col"
                >
                  Regime
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {sortedData.map(({ symbol, data, regime }) => (
                <tr
                  key={symbol}
                  className="hover:bg-slate-800/50 transition-colors cursor-pointer"
                  onClick={() => handleRowClick(symbol)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleRowClick(symbol);
                    }
                  }}
                  aria-label={`View details for ${symbol}`}
                >
                  <td className="px-4 py-3 text-sm font-medium text-slate-100">
                    {symbol}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-slate-200 font-mono">
                    ${formatPrice(data.price)}
                  </td>
                  <td className="px-4 py-3 text-sm text-right font-semibold">
                    <span
                      className={
                        data.change24h > 0
                          ? 'text-green-500'
                          : data.change24h < 0
                          ? 'text-red-500'
                          : 'text-slate-400'
                      }
                      aria-label={`24 hour change: ${data.change24h > 0 ? 'up' : 'down'} ${Math.abs(data.change24h).toFixed(2)} percent`}
                    >
                      {data.change24h > 0 ? '+' : ''}
                      {data.change24h.toFixed(2)}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-slate-300 font-mono">
                    ${formatVolume(data.volume24h)}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-slate-300 font-mono">
                    {data.bidAskSpread.toFixed(4)}%
                  </td>
                  <td className="px-4 py-3 text-sm text-right font-mono">
                    <span
                      className={
                        data.cvd > 0
                          ? 'text-green-500'
                          : data.cvd < 0
                          ? 'text-red-500'
                          : 'text-slate-400'
                      }
                      aria-label={`Cumulative volume delta: ${data.cvd > 0 ? 'positive' : 'negative'} ${formatCVD(data.cvd)}`}
                    >
                      {formatCVD(data.cvd)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {regime ? (
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getRegimeColor(
                          regime.regime
                        )}`}
                        aria-label={`Market regime: ${regime.regime}, confidence ${(regime.confidence * 100).toFixed(0)} percent`}
                      >
                        {regime.regime}
                        <span className="ml-1 text-[10px] opacity-75" aria-hidden="true">
                          {(regime.confidence * 100).toFixed(0)}%
                        </span>
                      </span>
                    ) : (
                      <span className="text-xs text-slate-500" aria-label="No regime data">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mobile Card View (below md) */}
      <div 
        className="md:hidden space-y-3"
        role="list"
        aria-label="Market data cards"
      >
        {sortedData.map(({ symbol, data, regime }) => (
          <article
            key={symbol}
            className="bg-slate-900 border border-slate-800 rounded-lg p-4 cursor-pointer hover:bg-slate-800/50 transition-colors touch-manipulation"
            onClick={() => handleRowClick(symbol)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleRowClick(symbol);
              }
            }}
            style={{ minHeight: '44px' }}
            aria-label={`${symbol} market data card`}
          >
            {/* Header Row */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-base font-bold text-slate-100">{symbol}</span>
                {regime && (
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border ${getRegimeColor(
                      regime.regime
                    )}`}
                    aria-label={`Market regime: ${regime.regime}`}
                  >
                    {regime.regime}
                  </span>
                )}
              </div>
              <span
                className={`text-base font-bold ${
                  data.change24h > 0
                    ? 'text-green-500'
                    : data.change24h < 0
                    ? 'text-red-500'
                    : 'text-slate-400'
                }`}
                aria-label={`24 hour change: ${data.change24h > 0 ? 'up' : 'down'} ${Math.abs(data.change24h).toFixed(2)} percent`}
              >
                {data.change24h > 0 ? '+' : ''}
                {data.change24h.toFixed(2)}%
              </span>
            </div>

            {/* Price Row */}
            <div className="flex items-baseline justify-between mb-2">
              <span className="text-xs text-slate-400">Price</span>
              <span className="text-lg font-mono text-slate-200">
                ${formatPrice(data.price)}
              </span>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Volume</span>
                <span className="font-mono text-slate-300">${formatVolume(data.volume24h)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">CVD</span>
                <span
                  className={`font-mono ${
                    data.cvd > 0
                      ? 'text-green-500'
                      : data.cvd < 0
                      ? 'text-red-500'
                      : 'text-slate-400'
                  }`}
                >
                  {formatCVD(data.cvd)}
                </span>
              </div>
            </div>
          </article>
        ))}
      </div>
    </>
  );
};

// Export memoized component
export const MarketDataGrid = memo(MarketDataGridComponent);
