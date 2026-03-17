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

// Memoized row component to prevent unnecessary re-renders
interface MarketDataRowProps {
  symbol: string;
  data: MarketDataSnapshot;
  regime: MarketRegime | null;
  onRowClick: (symbol: string) => void;
}

const MarketDataRow = memo<MarketDataRowProps>(({ symbol, data, regime, onRowClick }) => {
  const formatPrice = useCallback((price: number): string => {
    return price.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 8,
    });
  }, []);

  const formatVolume = useCallback((volume: number): string => {
    if (volume >= 1_000_000_000) {
      return `${(volume / 1_000_000_000).toFixed(2)}B`;
    } else if (volume >= 1_000_000) {
      return `${(volume / 1_000_000).toFixed(2)}M`;
    } else if (volume >= 1_000) {
      return `${(volume / 1_000).toFixed(2)}K`;
    }
    return volume.toFixed(2);
  }, []);

  const formatCVD = useCallback((cvd: number): string => {
    if (Math.abs(cvd) >= 1_000_000) {
      return `${(cvd / 1_000_000).toFixed(2)}M`;
    } else if (Math.abs(cvd) >= 1_000) {
      return `${(cvd / 1_000).toFixed(2)}K`;
    }
    return cvd.toFixed(2);
  }, []);

  const getRegimeColor = useCallback((regime: string): string => {
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
  }, []);

  const handleClick = useCallback(() => {
    onRowClick(symbol);
  }, [symbol, onRowClick]);

  return (
    <tr
      className="hover:bg-slate-800/50 transition-colors cursor-pointer"
      onClick={handleClick}
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
          >
            {regime.regime}
            <span className="ml-1 text-[10px] opacity-75">
              {(regime.confidence * 100).toFixed(0)}%
            </span>
          </span>
        ) : (
          <span className="text-xs text-slate-500">-</span>
        )}
      </td>
    </tr>
  );
});

MarketDataRow.displayName = 'MarketDataRow';

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
    setSortColumn((prevColumn) => {
      if (prevColumn === column) {
        setSortDirection((prevDirection) => prevDirection === 'asc' ? 'desc' : 'asc');
      } else {
        setSortDirection('asc');
      }
      return column;
    });
  }, []);

  // Memoize sorted data - only recalculate when dependencies change
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

  // Memoize getSortIcon function
  const getSortIcon = useCallback((column: SortColumn): string => {
    if (sortColumn !== column) return '↕';
    return sortDirection === 'asc' ? '↑' : '↓';
  }, [sortColumn, sortDirection]);

  // Memoize row click handler
  const handleRowClick = useCallback((symbol: string) => {
    if (onSymbolSelect) {
      onSymbolSelect(symbol);
    }
  }, [onSymbolSelect]);

  if (sortedData.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-8 text-center">
        <p className="text-slate-400">No market data available</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-950">
              <th
                className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider cursor-pointer hover:text-green-400 transition-colors"
                onClick={() => handleSort('symbol')}
              >
                Symbol {getSortIcon('symbol')}
              </th>
              <th
                className="px-4 py-3 text-right text-xs font-semibold text-slate-300 uppercase tracking-wider cursor-pointer hover:text-green-400 transition-colors"
                onClick={() => handleSort('price')}
              >
                Price {getSortIcon('price')}
              </th>
              <th
                className="px-4 py-3 text-right text-xs font-semibold text-slate-300 uppercase tracking-wider cursor-pointer hover:text-green-400 transition-colors"
                onClick={() => handleSort('change24h')}
              >
                24h Change {getSortIcon('change24h')}
              </th>
              <th
                className="px-4 py-3 text-right text-xs font-semibold text-slate-300 uppercase tracking-wider cursor-pointer hover:text-green-400 transition-colors"
                onClick={() => handleSort('volume24h')}
              >
                Volume {getSortIcon('volume24h')}
              </th>
              <th
                className="px-4 py-3 text-right text-xs font-semibold text-slate-300 uppercase tracking-wider cursor-pointer hover:text-green-400 transition-colors"
                onClick={() => handleSort('bidAskSpread')}
              >
                Bid-Ask Spread {getSortIcon('bidAskSpread')}
              </th>
              <th
                className="px-4 py-3 text-right text-xs font-semibold text-slate-300 uppercase tracking-wider cursor-pointer hover:text-green-400 transition-colors"
                onClick={() => handleSort('cvd')}
              >
                CVD {getSortIcon('cvd')}
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Regime
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {sortedData.map(({ symbol, data, regime }) => (
              <MarketDataRow
                key={symbol}
                symbol={symbol}
                data={data}
                regime={regime}
                onRowClick={handleRowClick}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Export memoized component
export const MarketDataGrid = memo(MarketDataGridComponent);
