/**
 * ActiveSignalsPanel Component (Optimized)
 * 
 * Displays all active trading signals with real-time updates.
 * 
 * Performance Optimizations:
 * - React.memo to prevent unnecessary re-renders
 * - Selective Zustand subscription (activeSignals only)
 * - useMemo for filtered signals
 * - useCallback for event handlers
 * - Debounced filter controls (300ms)
 * 
 * Features:
 * - Real-time P&L updates via WebSocket
 * - Quality grade badges (A+, A, B, C)
 * - MFE/MAE tracking
 * - Debounced filter controls (300ms)
 * - Time elapsed indicators
 * - Click to view detailed signal analysis
 * 
 * Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.9, 29.5, Task 6.10
 */

import { useState, useMemo, useCallback, memo } from 'react';
import { useDashboardStore } from '../stores/dashboardStore';
import { useDebounce } from '../hooks';
import { shallowEqual } from '../utils/performanceOptimization';
import type { Signal } from '../types/index';

interface ActiveSignalsPanelProps {
  onSignalClick?: (signalId: string) => void;
}

// Memoized signal card component
interface SignalCardProps {
  signal: Signal;
  onSignalClick: (signalId: string) => void;
}

const SignalCard = memo<SignalCardProps>(({ signal, onSignalClick }) => {
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
  
  const formatTimeElapsed = useCallback((minutes: number): string => {
    if (minutes < 60) {
      return `${minutes}m`;
    } else if (minutes < 1440) {
      const hours = Math.floor(minutes / 60);
      const mins = minutes % 60;
      return `${hours}h ${mins}m`;
    } else {
      const days = Math.floor(minutes / 1440);
      const hours = Math.floor((minutes % 1440) / 60);
      return `${days}d ${hours}h`;
    }
  }, []);
  
  const getQualityColor = useCallback((quality: string) => {
    switch (quality) {
      case 'A+':
        return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'A':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'B':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'C':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  }, []);

  const handleClick = useCallback(() => {
    onSignalClick(signal.signalId);
  }, [signal.signalId, onSignalClick]);

  return (
    <article
      onClick={handleClick}
      className="bg-slate-950 border border-slate-800 rounded-lg p-4 hover:border-slate-700 cursor-pointer transition-colors"
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
      aria-label={`Signal for ${signal.symbol} ${signal.direction}, P&L ${signal.unrealizedPnL > 0 ? 'up' : 'down'} ${Math.abs(signal.unrealizedPnL).toFixed(2)} percent`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold text-slate-100">{signal.symbol}</span>
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              signal.direction === 'LONG'
                ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                : 'bg-red-500/20 text-red-400 border border-red-500/30'
            }`}
            aria-label={`Direction: ${signal.direction}`}
          >
            {signal.direction}
          </span>
          <span 
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getQualityColor(signal.quality)}`}
            aria-label={`Quality grade: ${signal.quality}`}
          >
            {signal.quality}
          </span>
        </div>
        <div className="text-right">
          <div
            className={`text-lg font-bold ${
              signal.unrealizedPnL > 0
                ? 'text-green-500'
                : signal.unrealizedPnL < 0
                ? 'text-red-500'
                : 'text-slate-400'
            }`}
            aria-label={`Unrealized P&L: ${signal.unrealizedPnL > 0 ? 'positive' : 'negative'} ${Math.abs(signal.unrealizedPnL).toFixed(2)} percent`}
          >
            {signal.unrealizedPnL > 0 ? '+' : ''}
            {formatPnL(signal.unrealizedPnL)}%
          </div>
          <div className="text-xs text-slate-400">{formatTimeElapsed(signal.timeElapsed)}</div>
        </div>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div>
          <div className="text-xs text-slate-400 mb-1">Entry Price</div>
          <div className="font-mono text-slate-200">${formatPrice(signal.entryPrice)}</div>
        </div>
        <div>
          <div className="text-xs text-slate-400 mb-1">Current Price</div>
          <div className="font-mono text-slate-100 font-semibold">${formatPrice(signal.currentPrice)}</div>
        </div>
        <div>
          <div className="text-xs text-slate-400 mb-1">MFE</div>
          <div className="font-mono text-green-500">+{formatPnL(signal.mfe)}%</div>
        </div>
        <div>
          <div className="text-xs text-slate-400 mb-1">MAE</div>
          <div className="font-mono text-red-500">{formatPnL(signal.mae)}%</div>
        </div>
      </div>
      
      <div className="mt-3 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
        <div className="text-slate-400">
          Confidence: <span className="text-slate-300 font-medium">{(signal.confidence * 100).toFixed(1)}%</span>
        </div>
        <div className="text-slate-400">
          TP: <span className="text-green-400 font-mono">${formatPrice(signal.takeProfit)}</span>
          {' | '}
          SL: <span className="text-red-400 font-mono">${formatPrice(signal.stopLoss)}</span>
        </div>
      </div>
    </article>
  );
});

SignalCard.displayName = 'SignalCard';

const ActiveSignalsPanelComponent: React.FC<ActiveSignalsPanelProps> = ({ onSignalClick }) => {
  // Selective Zustand subscription - only subscribe to activeSignals
  const activeSignals = useDashboardStore((state) => state.activeSignals, shallowEqual);
  
  // Filter state
  const [symbolFilter, setSymbolFilter] = useState('');
  const [directionFilter, setDirectionFilter] = useState<'ALL' | 'LONG' | 'SHORT'>('ALL');
  const [qualityFilter, setQualityFilter] = useState<'ALL' | 'A+' | 'A' | 'B' | 'C'>('ALL');
  
  // Debounce symbol filter (300ms delay)
  const debouncedSymbolFilter = useDebounce(symbolFilter, 300);
  
  // Memoize filter handlers
  const handleSymbolFilterChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSymbolFilter(e.target.value);
  }, []);

  const handleDirectionFilterChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setDirectionFilter(e.target.value as 'ALL' | 'LONG' | 'SHORT');
  }, []);

  const handleQualityFilterChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setQualityFilter(e.target.value as 'ALL' | 'A+' | 'A' | 'B' | 'C');
  }, []);

  // Memoize signal click handler
  const handleSignalClick = useCallback((signalId: string) => {
    if (onSignalClick) {
      onSignalClick(signalId);
    }
  }, [onSignalClick]);
  
  // Memoize filtered signals
  const filteredSignals = useMemo(() => {
    return activeSignals.filter(signal => {
      // Symbol filter
      if (debouncedSymbolFilter && !signal.symbol.toLowerCase().includes(debouncedSymbolFilter.toLowerCase())) {
        return false;
      }
      
      // Direction filter
      if (directionFilter !== 'ALL' && signal.direction !== directionFilter) {
        return false;
      }
      
      // Quality filter
      if (qualityFilter !== 'ALL' && signal.quality !== qualityFilter) {
        return false;
      }
      
      return true;
    });
  }, [activeSignals, debouncedSymbolFilter, directionFilter, qualityFilter]);
  
  return (
    <section 
      className="bg-slate-900 border border-slate-800 rounded-lg p-6"
      aria-labelledby="active-signals-heading"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 id="active-signals-heading" className="text-lg font-semibold text-slate-100">
          Active Signals ({filteredSignals.length})
        </h3>
      </div>
      
      {/* Filters */}
      <div 
        className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4"
        role="search"
        aria-label="Filter active signals"
      >
        <div className="relative">
          <label htmlFor="symbol-filter" className="sr-only">
            Search by symbol
          </label>
          <input
            id="symbol-filter"
            type="text"
            placeholder="Search symbol..."
            value={symbolFilter}
            onChange={handleSymbolFilterChange}
            className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            aria-describedby={symbolFilter !== debouncedSymbolFilter ? 'symbol-filter-loading' : undefined}
          />
          {symbolFilter !== debouncedSymbolFilter && (
            <div 
              className="absolute right-3 top-1/2 -translate-y-1/2"
              id="symbol-filter-loading"
              role="status"
              aria-label="Loading search results"
            >
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          )}
        </div>
        
        <div>
          <label htmlFor="direction-filter" className="sr-only">
            Filter by direction
          </label>
          <select
            id="direction-filter"
            value={directionFilter}
            onChange={handleDirectionFilterChange}
            className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          >
            <option value="ALL">All Directions</option>
            <option value="LONG">Long</option>
            <option value="SHORT">Short</option>
          </select>
        </div>
        
        <div>
          <label htmlFor="quality-filter" className="sr-only">
            Filter by quality grade
          </label>
          <select
            id="quality-filter"
            value={qualityFilter}
            onChange={handleQualityFilterChange}
            className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          >
            <option value="ALL">All Qualities</option>
            <option value="A+">A+</option>
            <option value="A">A</option>
            <option value="B">B</option>
            <option value="C">C</option>
          </select>
        </div>
      </div>
      
      {/* Signals List */}
      <div 
        role="region"
        aria-live="polite"
        aria-atomic="false"
        aria-label="Active signals list"
      >
        {filteredSignals.length === 0 ? (
          <div className="text-center py-12 text-slate-400">
            {activeSignals.length === 0 ? 'No active signals' : 'No signals match filters'}
          </div>
        ) : (
          <div className="space-y-3 max-h-[600px] overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-slate-900">
            {filteredSignals.map((signal) => (
              <SignalCard
                key={signal.signalId}
                signal={signal}
                onSignalClick={handleSignalClick}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  );
};

// Export memoized component
export const ActiveSignalsPanel = memo(ActiveSignalsPanelComponent);
