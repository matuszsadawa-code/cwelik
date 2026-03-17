/**
 * TradeTable Component
 * 
 * Displays trade history with virtual scrolling, filtering, sorting, and pagination.
 * Requirements: 21.3, 21.4, 21.6, 21.7, 21.8, 29.3
 */

import { useState, useEffect, useMemo } from 'react';
import { FixedSizeList } from 'react-window';
import type { Trade, TradeFilters } from '../types';
import { fetchTradeHistory } from '../services/api';
import { useDebounce } from '../hooks';

interface TradeTableProps {
  onTradeClick?: (trade: Trade) => void;
}

export default function TradeTable({ onTradeClick }: TradeTableProps) {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [total, setTotal] = useState(0);
  const [sortBy, setSortBy] = useState<string>('entryTime');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [filters, setFilters] = useState<TradeFilters>({});
  const [isDebouncing, setIsDebouncing] = useState(false);

  // Debounce filters to reduce API calls (300ms delay)
  const debouncedFilters = useDebounce(filters, 300);

  // Fetch trades
  useEffect(() => {
    const loadTrades = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetchTradeHistory(page, pageSize, debouncedFilters, sortBy, sortOrder);
        setTrades(response.trades);
        setTotal(response.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load trades');
      } finally {
        setLoading(false);
        setIsDebouncing(false);
      }
    };

    loadTrades();
  }, [page, pageSize, debouncedFilters, sortBy, sortOrder]);

  // Track when debouncing is active
  useEffect(() => {
    if (JSON.stringify(filters) !== JSON.stringify(debouncedFilters)) {
      setIsDebouncing(true);
    }
  }, [filters, debouncedFilters]);

  // Handle sort
  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  // Handle filter change
  const handleFilterChange = (key: keyof TradeFilters, value: string) => {
    setFilters(prev => ({
      ...prev,
      [key]: value || undefined,
    }));
    setPage(1); // Reset to first page
  };

  // Format date
  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Format duration
  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  // Row renderer for virtual scrolling
  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const trade = trades[index];
    if (!trade) return null;

    return (
      <div
        style={style}
        className="flex items-center border-b border-gray-800 hover:bg-gray-800/50 cursor-pointer transition-colors"
        onClick={() => onTradeClick?.(trade)}
      >
        <div className="w-24 px-4 py-3 text-sm font-medium">{trade.symbol}</div>
        <div className="w-32 px-4 py-3 text-sm text-gray-400">{formatDate(trade.entryTime)}</div>
        <div className="w-32 px-4 py-3 text-sm text-gray-400">{formatDate(trade.exitTime)}</div>
        <div className="w-20 px-4 py-3">
          <span className={`text-xs font-semibold px-2 py-1 rounded ${
            trade.direction === 'LONG' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
          }`}>
            {trade.direction}
          </span>
        </div>
        <div className="w-28 px-4 py-3 text-sm text-gray-300">${trade.entryPrice.toFixed(2)}</div>
        <div className="w-28 px-4 py-3 text-sm text-gray-300">${trade.exitPrice.toFixed(2)}</div>
        <div className={`w-24 px-4 py-3 text-sm font-semibold ${
          trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'
        }`}>
          {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toFixed(2)}%
        </div>
        <div className={`w-24 px-4 py-3 text-sm font-semibold ${
          trade.pnlPercent >= 0 ? 'text-green-400' : 'text-red-400'
        }`}>
          {trade.pnlPercent >= 0 ? '+' : ''}{trade.pnlPercent.toFixed(2)}%
        </div>
        <div className="w-20 px-4 py-3">
          <span className={`text-xs font-semibold px-2 py-1 rounded ${
            trade.outcome === 'WIN' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
          }`}>
            {trade.outcome}
          </span>
        </div>
        <div className="w-16 px-4 py-3">
          <span className="text-xs font-semibold px-2 py-1 rounded bg-blue-500/20 text-blue-400">
            {trade.quality}
          </span>
        </div>
        <div className="w-24 px-4 py-3 text-sm text-gray-400">{formatDuration(trade.duration)}</div>
      </div>
    );
  };

  const totalPages = Math.ceil(total / pageSize);

  if (error) {
    return (
      <div className="bg-gray-900 rounded-lg p-6">
        <div className="text-red-400">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4">Trade Journal</h2>

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-4">
        <div className="relative">
          <input
            type="text"
            placeholder="Symbol"
            value={filters.symbol || ''}
            onChange={(e) => handleFilterChange('symbol', e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          />
          {isDebouncing && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          )}
        </div>
        <input
          type="date"
          placeholder="Start Date"
          value={filters.startDate || ''}
          onChange={(e) => handleFilterChange('startDate', e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
        />
        <input
          type="date"
          placeholder="End Date"
          value={filters.endDate || ''}
          onChange={(e) => handleFilterChange('endDate', e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
        />
        <select
          value={filters.outcome || ''}
          onChange={(e) => handleFilterChange('outcome', e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">All Outcomes</option>
          <option value="WIN">Win</option>
          <option value="LOSS">Loss</option>
        </select>
        <select
          value={filters.quality || ''}
          onChange={(e) => handleFilterChange('quality', e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">All Qualities</option>
          <option value="A+">A+</option>
          <option value="A">A</option>
          <option value="B">B</option>
          <option value="C">C</option>
        </select>
      </div>

      {/* Table Header */}
      <div className="flex items-center bg-gray-800 border-b-2 border-gray-700 font-semibold text-sm">
        <div className="w-24 px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleSort('symbol')}>
          Symbol {sortBy === 'symbol' && (sortOrder === 'asc' ? '↑' : '↓')}
        </div>
        <div className="w-32 px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleSort('entryTime')}>
          Entry Time {sortBy === 'entryTime' && (sortOrder === 'asc' ? '↑' : '↓')}
        </div>
        <div className="w-32 px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleSort('exitTime')}>
          Exit Time {sortBy === 'exitTime' && (sortOrder === 'asc' ? '↑' : '↓')}
        </div>
        <div className="w-20 px-4 py-3">Direction</div>
        <div className="w-28 px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleSort('entryPrice')}>
          Entry Price {sortBy === 'entryPrice' && (sortOrder === 'asc' ? '↑' : '↓')}
        </div>
        <div className="w-28 px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleSort('exitPrice')}>
          Exit Price {sortBy === 'exitPrice' && (sortOrder === 'asc' ? '↑' : '↓')}
        </div>
        <div className="w-24 px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleSort('pnl')}>
          PnL {sortBy === 'pnl' && (sortOrder === 'asc' ? '↑' : '↓')}
        </div>
        <div className="w-24 px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleSort('pnlPercent')}>
          PnL % {sortBy === 'pnlPercent' && (sortOrder === 'asc' ? '↑' : '↓')}
        </div>
        <div className="w-20 px-4 py-3">Outcome</div>
        <div className="w-16 px-4 py-3">Quality</div>
        <div className="w-24 px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleSort('duration')}>
          Duration {sortBy === 'duration' && (sortOrder === 'asc' ? '↑' : '↓')}
        </div>
      </div>

      {/* Virtual Scrolling List */}
      {loading ? (
        <div className="flex items-center justify-center h-96">
          <div className="text-gray-400">Loading trades...</div>
        </div>
      ) : trades.length === 0 ? (
        <div className="flex items-center justify-center h-96">
          <div className="text-gray-400">No trades found</div>
        </div>
      ) : (
        <FixedSizeList
          height={600}
          itemCount={trades.length}
          itemSize={56}
          width="100%"
          className="scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-900"
        >
          {Row}
        </FixedSizeList>
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between mt-4 text-sm">
        <div className="text-gray-400">
          Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} trades
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 bg-gray-800 rounded hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="text-gray-400">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 bg-gray-800 rounded hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
