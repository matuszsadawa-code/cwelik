import { useEffect, useState, useMemo } from 'react';
import type { SymbolMetrics } from '../types/index';
import { fetchSymbolPerformance } from '../services/api';
import { useDebounce } from '../hooks';

/**
 * SymbolPerformanceTable Component
 * 
 * Displays detailed performance statistics for each trading symbol in a sortable table.
 * 
 * Features:
 * - Sortable columns (click header to sort)
 * - Display columns: Symbol, Win Rate, Profit Factor, Avg PnL, Total PnL, Trade Count, Avg Hold Time, Best Trade, Worst Trade
 * - Highlight best performing symbol in green border
 * - Highlight worst performing symbol in red border
 * - Click row to open detailed symbol analysis chart
 * - Dark mode OLED optimized colors
 * - Responsive design
 * 
 * Requirements: 10.7, 10.8, 10.9, 10.10, 10.11, 10.12
 */

interface SymbolPerformanceTableProps {
  onSymbolClick?: (symbol: string) => void;
}

type SortColumn = keyof SymbolMetrics;
type SortDirection = 'asc' | 'desc';

const formatDuration = (minutes: number): string => {
  if (minutes < 60) {
    return `${Math.round(minutes)}m`;
  } else if (minutes < 1440) {
    return `${(minutes / 60).toFixed(1)}h`;
  } else {
    return `${(minutes / 1440).toFixed(1)}d`;
  }
};

export const SymbolPerformanceTable: React.FC<SymbolPerformanceTableProps> = ({
  onSymbolClick,
}) => {
  const [symbolMetrics, setSymbolMetrics] = useState<SymbolMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortColumn, setSortColumn] = useState<SortColumn>('totalPnL');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Debounce search query (300ms delay)
  const debouncedSearchQuery = useDebounce(searchQuery, 300);

  // Fetch symbol performance data
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetchSymbolPerformance();
        setSymbolMetrics(data);
      } catch (err) {
        console.error('Error fetching symbol performance:', err);
        setError(err instanceof Error ? err.message : 'Failed to load symbol performance');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Filter and sort data
  const sortedData = useMemo(() => {
    if (symbolMetrics.length === 0) return [];

    // Filter by search query
    let filtered = symbolMetrics;
    if (debouncedSearchQuery) {
      const query = debouncedSearchQuery.toLowerCase();
      filtered = symbolMetrics.filter(metric => 
        metric.symbol.toLowerCase().includes(query)
      );
    }

    // Sort filtered data
    const sorted = [...filtered].sort((a, b) => {
      const aValue = a[sortColumn];
      const bValue = b[sortColumn];

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      const aNum = Number(aValue);
      const bNum = Number(bValue);

      return sortDirection === 'asc' ? aNum - bNum : bNum - aNum;
    });

    return sorted;
  }, [symbolMetrics, sortColumn, sortDirection, debouncedSearchQuery]);

  // Find best and worst performing symbols (by total PnL)
  const bestSymbol = useMemo(() => {
    if (symbolMetrics.length === 0) return null;
    return symbolMetrics.reduce((best, current) =>
      current.totalPnL > best.totalPnL ? current : best
    );
  }, [symbolMetrics]);

  const worstSymbol = useMemo(() => {
    if (symbolMetrics.length === 0) return null;
    return symbolMetrics.reduce((worst, current) =>
      current.totalPnL < worst.totalPnL ? current : worst
    );
  }, [symbolMetrics]);

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      // Toggle direction if same column
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // Set new column with default descending
      setSortColumn(column);
      setSortDirection('desc');
    }
  };

  const handleRowClick = (symbol: string) => {
    if (onSymbolClick) {
      onSymbolClick(symbol);
    }
  };

  const getSortIcon = (column: SortColumn) => {
    if (sortColumn !== column) {
      return (
        <svg className="w-4 h-4 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      );
    }

    return sortDirection === 'asc' ? (
      <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
      </svg>
    ) : (
      <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    );
  };

  const getRowClassName = (symbol: SymbolMetrics) => {
    const baseClass = 'cursor-pointer transition-colors hover:bg-slate-800/50';
    
    if (bestSymbol && symbol.symbol === bestSymbol.symbol) {
      return `${baseClass} border-l-4 border-green-500 bg-green-500/5`;
    }
    
    if (worstSymbol && symbol.symbol === worstSymbol.symbol) {
      return `${baseClass} border-l-4 border-red-500 bg-red-500/5`;
    }
    
    return baseClass;
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-slate-100">Symbol Performance</h3>
        <div className="flex items-center gap-4">
          {/* Search Input */}
          <div className="relative">
            <input
              type="text"
              placeholder="Search symbols..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500 w-48"
            />
            {searchQuery !== debouncedSearchQuery && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <div className="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
            )}
          </div>
          {/* Legend */}
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 border-l-4 border-green-500 bg-green-500/10"></div>
              <span className="text-slate-400">Best Performer</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 border-l-4 border-red-500 bg-red-500/10"></div>
              <span className="text-slate-400">Worst Performer</span>
            </div>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center h-64">
          <p className="text-slate-400">Loading symbol performance...</p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="flex items-center justify-center h-64">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Table */}
      {!loading && !error && sortedData.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-800">
                <th
                  className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-200 transition-colors"
                  onClick={() => handleSort('symbol')}
                >
                  <div className="flex items-center gap-2">
                    Symbol
                    {getSortIcon('symbol')}
                  </div>
                </th>
                <th
                  className="text-right py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-200 transition-colors"
                  onClick={() => handleSort('winRate')}
                >
                  <div className="flex items-center justify-end gap-2">
                    Win Rate
                    {getSortIcon('winRate')}
                  </div>
                </th>
                <th
                  className="text-right py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-200 transition-colors"
                  onClick={() => handleSort('profitFactor')}
                >
                  <div className="flex items-center justify-end gap-2">
                    Profit Factor
                    {getSortIcon('profitFactor')}
                  </div>
                </th>
                <th
                  className="text-right py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-200 transition-colors"
                  onClick={() => handleSort('avgPnL')}
                >
                  <div className="flex items-center justify-end gap-2">
                    Avg PnL
                    {getSortIcon('avgPnL')}
                  </div>
                </th>
                <th
                  className="text-right py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-200 transition-colors"
                  onClick={() => handleSort('totalPnL')}
                >
                  <div className="flex items-center justify-end gap-2">
                    Total PnL
                    {getSortIcon('totalPnL')}
                  </div>
                </th>
                <th
                  className="text-right py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-200 transition-colors"
                  onClick={() => handleSort('totalTrades')}
                >
                  <div className="flex items-center justify-end gap-2">
                    Trades
                    {getSortIcon('totalTrades')}
                  </div>
                </th>
                <th
                  className="text-right py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-200 transition-colors"
                  onClick={() => handleSort('avgHoldTime')}
                >
                  <div className="flex items-center justify-end gap-2">
                    Avg Hold
                    {getSortIcon('avgHoldTime')}
                  </div>
                </th>
                <th
                  className="text-right py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-200 transition-colors"
                  onClick={() => handleSort('bestTrade')}
                >
                  <div className="flex items-center justify-end gap-2">
                    Best Trade
                    {getSortIcon('bestTrade')}
                  </div>
                </th>
                <th
                  className="text-right py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-200 transition-colors"
                  onClick={() => handleSort('worstTrade')}
                >
                  <div className="flex items-center justify-end gap-2">
                    Worst Trade
                    {getSortIcon('worstTrade')}
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedData.map((symbol) => (
                <tr
                  key={symbol.symbol}
                  className={getRowClassName(symbol)}
                  onClick={() => handleRowClick(symbol.symbol)}
                >
                  <td className="py-3 px-4 text-sm font-medium text-slate-100">
                    {symbol.symbol}
                  </td>
                  <td className="py-3 px-4 text-sm text-right">
                    <span
                      className={
                        symbol.winRate >= 60
                          ? 'text-green-500'
                          : symbol.winRate >= 50
                          ? 'text-yellow-500'
                          : 'text-red-400'
                      }
                    >
                      {symbol.winRate.toFixed(1)}%
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm text-right">
                    <span
                      className={
                        symbol.profitFactor >= 1.5
                          ? 'text-green-500'
                          : symbol.profitFactor >= 1.0
                          ? 'text-yellow-500'
                          : 'text-red-400'
                      }
                    >
                      {symbol.profitFactor.toFixed(2)}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm text-right">
                    <span className={symbol.avgPnL >= 0 ? 'text-green-500' : 'text-red-400'}>
                      {symbol.avgPnL >= 0 ? '+' : ''}
                      {symbol.avgPnL.toFixed(2)}%
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm text-right font-medium">
                    <span className={symbol.totalPnL >= 0 ? 'text-green-500' : 'text-red-400'}>
                      {symbol.totalPnL >= 0 ? '+' : ''}
                      {symbol.totalPnL.toFixed(2)}%
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm text-right text-slate-300">
                    {symbol.totalTrades}
                  </td>
                  <td className="py-3 px-4 text-sm text-right text-slate-300">
                    {formatDuration(symbol.avgHoldTime)}
                  </td>
                  <td className="py-3 px-4 text-sm text-right">
                    <span className="text-green-500">
                      +{symbol.bestTrade.toFixed(2)}%
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm text-right">
                    <span className="text-red-400">
                      {symbol.worstTrade.toFixed(2)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && sortedData.length === 0 && (
        <div className="flex items-center justify-center h-64">
          <p className="text-slate-400">No symbol performance data available</p>
        </div>
      )}
    </div>
  );
};
