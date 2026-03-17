import { useEffect, useState, useMemo } from 'react';
import type { OrderBook } from '../types/index';

interface OrderBookVisualizationProps {
  symbol: string;
  onClose?: () => void;
}

interface OrderBookLevel {
  price: number;
  size: number;
  total: number;
  percentage: number;
}

/**
 * OrderBookVisualization Component
 * 
 * Displays detailed order book data with depth visualization for a selected symbol.
 * 
 * Features:
 * - Displays at least 20 price levels for bids and asks
 * - Visualizes order book depth with horizontal bars
 * - Animates changes to highlight significant shifts
 * - Calculates and displays bid-ask spread
 * - Shows order book imbalances
 * - Real-time updates via WebSocket
 * 
 * @param symbol - Trading pair symbol (e.g., 'BTCUSDT')
 * @param onClose - Callback when close button is clicked
 * 
 * Requirements: 1.6, 1.7
 */
export const OrderBookVisualization: React.FC<OrderBookVisualizationProps> = ({
  symbol,
  onClose,
}) => {
  const [orderBook, setOrderBook] = useState<OrderBook | null>(null);
  const [animatingLevels, setAnimatingLevels] = useState<Set<number>>(new Set());

  // Fetch order book data (in real implementation, this would come from WebSocket)
  useEffect(() => {
    // TODO: Subscribe to order book updates via WebSocket
    // For now, we'll simulate with mock data
    const mockOrderBook: OrderBook = {
      symbol,
      bids: Array.from({ length: 25 }, (_, i) => [
        50000 - i * 10,
        Math.random() * 5 + 0.1,
      ] as [number, number]),
      asks: Array.from({ length: 25 }, (_, i) => [
        50010 + i * 10,
        Math.random() * 5 + 0.1,
      ] as [number, number]),
      timestamp: Date.now(),
    };

    setOrderBook(mockOrderBook);

    // Simulate real-time updates
    const interval = setInterval(() => {
      const updatedOrderBook: OrderBook = {
        symbol,
        bids: Array.from({ length: 25 }, (_, i) => [
          50000 - i * 10,
          Math.random() * 5 + 0.1,
        ] as [number, number]),
        asks: Array.from({ length: 25 }, (_, i) => [
          50010 + i * 10,
          Math.random() * 5 + 0.1,
        ] as [number, number]),
        timestamp: Date.now(),
      };
      setOrderBook(updatedOrderBook);

      // Detect significant changes (>20% size change)
      const changedLevels = new Set<number>();
      updatedOrderBook.bids.forEach(([price, size], idx) => {
        const prevSize = mockOrderBook.bids[idx]?.[1] || 0;
        if (Math.abs(size - prevSize) / prevSize > 0.2) {
          changedLevels.add(price);
        }
      });
      updatedOrderBook.asks.forEach(([price, size], idx) => {
        const prevSize = mockOrderBook.asks[idx]?.[1] || 0;
        if (Math.abs(size - prevSize) / prevSize > 0.2) {
          changedLevels.add(price);
        }
      });

      setAnimatingLevels(changedLevels);
      setTimeout(() => setAnimatingLevels(new Set()), 500);
    }, 2000);

    return () => clearInterval(interval);
  }, [symbol]);

  // Process order book levels
  const { bidsData, asksData } = useMemo(() => {
    if (!orderBook) {
      return { bidsData: [], asksData: [] };
    }

    // Calculate cumulative totals for bids
    let bidTotal = 0;
    const bids: OrderBookLevel[] = orderBook.bids.slice(0, 20).map(([price, size]) => {
      bidTotal += size;
      return {
        price,
        size,
        total: bidTotal,
        percentage: 0, // Will be calculated after we know maxTotal
      };
    });

    // Calculate cumulative totals for asks
    let askTotal = 0;
    const asks: OrderBookLevel[] = orderBook.asks.slice(0, 20).map(([price, size]) => {
      askTotal += size;
      return {
        price,
        size,
        total: askTotal,
        percentage: 0, // Will be calculated after we know maxTotal
      };
    });

    const max = Math.max(bidTotal, askTotal);

    // Calculate percentages
    bids.forEach((level) => {
      level.percentage = (level.total / max) * 100;
    });
    asks.forEach((level) => {
      level.percentage = (level.total / max) * 100;
    });

    return { bidsData: bids, asksData: asks };
  }, [orderBook]);

  // Calculate bid-ask spread
  const spread = useMemo(() => {
    if (!orderBook || orderBook.asks.length === 0 || orderBook.bids.length === 0) {
      return { absolute: 0, percentage: 0 };
    }

    const bestAsk = orderBook.asks[0][0];
    const bestBid = orderBook.bids[0][0];
    const absolute = bestAsk - bestBid;
    const percentage = (absolute / bestBid) * 100;

    return { absolute, percentage };
  }, [orderBook]);

  // Calculate order book imbalance
  const imbalance = useMemo(() => {
    if (!orderBook) return { ratio: 0, side: 'neutral' as const };

    const totalBidSize = orderBook.bids.slice(0, 20).reduce((sum, [, size]) => sum + size, 0);
    const totalAskSize = orderBook.asks.slice(0, 20).reduce((sum, [, size]) => sum + size, 0);
    const total = totalBidSize + totalAskSize;

    if (total === 0) return { ratio: 0, side: 'neutral' as const };

    const bidPercentage = (totalBidSize / total) * 100;
    const askPercentage = (totalAskSize / total) * 100;

    let side: 'bid' | 'ask' | 'neutral' = 'neutral';
    if (bidPercentage > 55) side = 'bid';
    else if (askPercentage > 55) side = 'ask';

    return {
      ratio: Math.abs(bidPercentage - askPercentage),
      side,
      bidPercentage,
      askPercentage,
    };
  }, [orderBook]);

  const formatPrice = (price: number): string => {
    return price.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  const formatSize = (size: number): string => {
    return size.toFixed(4);
  };

  if (!orderBook) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-8">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500"></div>
          <span className="ml-3 text-slate-400">Loading order book...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-950 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-100">Order Book</h3>
            <p className="text-sm text-slate-400 mt-1">{symbol}</p>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-200 transition-colors"
              aria-label="Close order book"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          )}
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-2 gap-4 mt-4">
          {/* Bid-Ask Spread */}
          <div className="bg-slate-800/50 rounded-lg p-3">
            <p className="text-xs text-slate-400 uppercase tracking-wider">Spread</p>
            <p className="text-lg font-semibold text-slate-100 mt-1">
              ${spread.absolute.toFixed(2)}
            </p>
            <p className="text-xs text-slate-400 mt-0.5">
              {spread.percentage.toFixed(4)}%
            </p>
          </div>

          {/* Order Book Imbalance */}
          <div className="bg-slate-800/50 rounded-lg p-3">
            <p className="text-xs text-slate-400 uppercase tracking-wider">Imbalance</p>
            <p
              className={`text-lg font-semibold mt-1 ${
                imbalance.side === 'bid'
                  ? 'text-green-500'
                  : imbalance.side === 'ask'
                  ? 'text-red-500'
                  : 'text-slate-400'
              }`}
            >
              {imbalance.ratio.toFixed(1)}%
            </p>
            <p className="text-xs text-slate-400 mt-0.5">
              {imbalance.side === 'bid'
                ? 'Bid Heavy'
                : imbalance.side === 'ask'
                ? 'Ask Heavy'
                : 'Balanced'}
            </p>
          </div>
        </div>
      </div>

      {/* Order Book Levels */}
      <div className="grid grid-cols-2 divide-x divide-slate-800">
        {/* Bids (Left Side) */}
        <div className="p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-green-400 uppercase tracking-wider">
              Bids
            </h4>
            <span className="text-xs text-slate-400">
              {imbalance.bidPercentage?.toFixed(1)}%
            </span>
          </div>

          {/* Column Headers */}
          <div className="grid grid-cols-3 gap-2 text-xs text-slate-400 uppercase tracking-wider mb-2 px-2">
            <div className="text-left">Price</div>
            <div className="text-right">Size</div>
            <div className="text-right">Total</div>
          </div>

          {/* Bid Levels */}
          <div className="space-y-1">
            {bidsData.map((level) => (
              <div
                key={level.price}
                className={`relative rounded transition-all duration-300 ${
                  animatingLevels.has(level.price)
                    ? 'bg-green-500/20 scale-105'
                    : 'hover:bg-slate-800/50'
                }`}
              >
                {/* Depth Bar */}
                <div
                  className="absolute inset-0 bg-green-500/10 rounded transition-all duration-300"
                  style={{ width: `${level.percentage}%` }}
                />

                {/* Level Data */}
                <div className="relative grid grid-cols-3 gap-2 text-sm px-2 py-1.5">
                  <div className="text-left text-green-400 font-mono">
                    {formatPrice(level.price)}
                  </div>
                  <div className="text-right text-slate-300 font-mono">
                    {formatSize(level.size)}
                  </div>
                  <div className="text-right text-slate-400 font-mono text-xs">
                    {formatSize(level.total)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Asks (Right Side) */}
        <div className="p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-red-400 uppercase tracking-wider">
              Asks
            </h4>
            <span className="text-xs text-slate-400">
              {imbalance.askPercentage?.toFixed(1)}%
            </span>
          </div>

          {/* Column Headers */}
          <div className="grid grid-cols-3 gap-2 text-xs text-slate-400 uppercase tracking-wider mb-2 px-2">
            <div className="text-left">Price</div>
            <div className="text-right">Size</div>
            <div className="text-right">Total</div>
          </div>

          {/* Ask Levels */}
          <div className="space-y-1">
            {asksData.map((level) => (
              <div
                key={level.price}
                className={`relative rounded transition-all duration-300 ${
                  animatingLevels.has(level.price)
                    ? 'bg-red-500/20 scale-105'
                    : 'hover:bg-slate-800/50'
                }`}
              >
                {/* Depth Bar */}
                <div
                  className="absolute inset-0 bg-red-500/10 rounded transition-all duration-300"
                  style={{ width: `${level.percentage}%` }}
                />

                {/* Level Data */}
                <div className="relative grid grid-cols-3 gap-2 text-sm px-2 py-1.5">
                  <div className="text-left text-red-400 font-mono">
                    {formatPrice(level.price)}
                  </div>
                  <div className="text-right text-slate-300 font-mono">
                    {formatSize(level.size)}
                  </div>
                  <div className="text-right text-slate-400 font-mono text-xs">
                    {formatSize(level.total)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
