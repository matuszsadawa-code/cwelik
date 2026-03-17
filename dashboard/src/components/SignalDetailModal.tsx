import { useEffect, useRef, useState } from 'react';
import { createChart, type IChartApi, type ISeriesApi, LineStyle } from 'lightweight-charts';
import type { Signal } from '../types/index';

interface SignalDetailModalProps {
  signal: Signal | null;
  isOpen: boolean;
  onClose: () => void;
}

/**
 * SignalDetailModal Component
 * 
 * Displays detailed analysis for a selected signal in a modal overlay.
 * 
 * Features:
 * - All signal metadata (symbol, direction, quality, confidence, etc.)
 * - Price chart with TradingView Lightweight Charts showing:
 *   - Entry price (blue line)
 *   - Current price (yellow line)
 *   - Stop loss (red line)
 *   - Take profit (green line)
 * - MFE/MAE visualization as horizontal bars
 * - Feature contributions as horizontal bar chart
 * - Quality grade breakdown
 * - Close button (X) and click-outside-to-close
 * - ESC key to close
 * - Responsive and accessible (WCAG 2.1 AA)
 * 
 * Requirements: 4.10
 */
export const SignalDetailModal: React.FC<SignalDetailModalProps> = ({ signal, isOpen, onClose }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const [isChartReady, setIsChartReady] = useState(false);

  // Handle ESC key to close
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }

    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  // Initialize chart
  useEffect(() => {
    if (!isOpen || !signal || !chartContainerRef.current) {
      return;
    }

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: '#0F172A' },
        textColor: '#94A3B8',
      },
      grid: {
        vertLines: { color: '#1E293B' },
        horzLines: { color: '#1E293B' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 400,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: '#334155',
      },
      crosshair: {
        mode: 1,
      },
    });

    chartRef.current = chart;

    // Create candlestick series (placeholder data)
    const candlestickSeries = chart.addSeries({
      type: 'Candlestick',
    }, {
      upColor: '#22C55E',
      downColor: '#EF4444',
      borderUpColor: '#22C55E',
      borderDownColor: '#EF4444',
      wickUpColor: '#22C55E',
      wickDownColor: '#EF4444',
    });

    seriesRef.current = candlestickSeries as any;

    // Generate mock price data around signal prices
    const now = Math.floor(Date.now() / 1000);
    const mockData = generateMockPriceData(signal, now);
    candlestickSeries.setData(mockData);

    // Add price lines
    // Entry price (blue)
    candlestickSeries.createPriceLine({
      price: signal.entryPrice,
      color: '#3B82F6',
      lineWidth: 2,
      lineStyle: LineStyle.Solid,
      axisLabelVisible: true,
      title: 'Entry',
    });

    // Current price (yellow)
    candlestickSeries.createPriceLine({
      price: signal.currentPrice,
      color: '#FBBF24',
      lineWidth: 2,
      lineStyle: LineStyle.Solid,
      axisLabelVisible: true,
      title: 'Current',
    });

    // Stop loss (red)
    candlestickSeries.createPriceLine({
      price: signal.stopLoss,
      color: '#EF4444',
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: 'Stop Loss',
    });

    // Take profit (green)
    candlestickSeries.createPriceLine({
      price: signal.takeProfit,
      color: '#22C55E',
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: 'Take Profit',
    });

    chart.timeScale().fitContent();
    setIsChartReady(true);

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
      chartRef.current = null;
      seriesRef.current = null;
      setIsChartReady(false);
    };
  }, [isOpen, signal]);

  // Generate mock price data for visualization
  const generateMockPriceData = (signal: Signal, endTime: number) => {
    const data = [];
    const timeElapsed = signal.timeElapsed;
    const startTime = endTime - timeElapsed;
    const intervals = Math.min(50, Math.max(10, Math.floor(timeElapsed / 60))); // 1 candle per minute, max 50
    const timeStep = Math.floor(timeElapsed / intervals);

    let currentPrice = signal.entryPrice;
    const volatility = Math.abs(signal.entryPrice - signal.currentPrice) / intervals;

    for (let i = 0; i < intervals; i++) {
      const time = startTime + i * timeStep;
      const randomMove = (Math.random() - 0.5) * volatility * 2;
      
      // Trend towards current price
      const targetPrice = signal.entryPrice + (signal.currentPrice - signal.entryPrice) * (i / intervals);
      currentPrice = currentPrice * 0.7 + targetPrice * 0.3 + randomMove;

      const open = currentPrice;
      const close = currentPrice + (Math.random() - 0.5) * volatility;
      const high = Math.max(open, close) + Math.random() * volatility * 0.5;
      const low = Math.min(open, close) - Math.random() * volatility * 0.5;

      data.push({
        time: time as any,
        open,
        high,
        low,
        close,
      });

      currentPrice = close;
    }

    return data;
  };

  // Format helpers
  const formatPrice = (price: number): string => {
    return price.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 8,
    });
  };

  const formatPnL = (pnl: number): string => {
    return `${pnl > 0 ? '+' : ''}${pnl.toFixed(2)}%`;
  };

  const formatTimeElapsed = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  const getQualityColor = (quality: string): string => {
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
        return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const getQualityDescription = (quality: string): string => {
    switch (quality) {
      case 'A+':
        return 'Exceptional signal with strong confluence across all indicators';
      case 'A':
        return 'High-quality signal with good confluence and confirmation';
      case 'B':
        return 'Moderate signal with acceptable confluence';
      case 'C':
        return 'Lower confidence signal with limited confluence';
      default:
        return 'Unknown quality grade';
    }
  };

  if (!isOpen || !signal) {
    return null;
  }

  // Sort feature contributions by absolute value
  const sortedFeatures = Object.entries(signal.featureContributions)
    .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a));

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        className="relative bg-slate-900 border border-slate-700 rounded-lg shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-y-auto m-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 bg-slate-900 border-b border-slate-800 px-6 py-4 flex items-center justify-between">
          <h2 id="modal-title" className="text-2xl font-bold text-slate-100">
            {signal.symbol} {signal.direction} Signal Details
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-100 transition-colors p-2 rounded-lg hover:bg-slate-800"
            aria-label="Close modal"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Signal Metadata */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-800/50 rounded-lg p-4">
              <div className="text-xs text-slate-400 uppercase mb-1">Quality</div>
              <div className="flex items-center gap-2">
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold border ${getQualityColor(signal.quality)}`}>
                  {signal.quality}
                </span>
              </div>
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <div className="text-xs text-slate-400 uppercase mb-1">Confidence</div>
              <div className="text-2xl font-bold text-slate-100">
                {(signal.confidence * 100).toFixed(0)}%
              </div>
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <div className="text-xs text-slate-400 uppercase mb-1">Unrealized P&L</div>
              <div className={`text-2xl font-bold ${signal.unrealizedPnL > 0 ? 'text-green-500' : signal.unrealizedPnL < 0 ? 'text-red-500' : 'text-slate-400'}`}>
                {formatPnL(signal.unrealizedPnL)}
              </div>
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <div className="text-xs text-slate-400 uppercase mb-1">Time Elapsed</div>
              <div className="text-2xl font-bold text-slate-100">
                {formatTimeElapsed(signal.timeElapsed)}
              </div>
            </div>
          </div>

          {/* Price Information */}
          <div className="bg-slate-800/30 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-slate-100 mb-3">Price Levels</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <div className="text-xs text-slate-400 uppercase mb-1">Entry Price</div>
                <div className="text-lg font-mono text-blue-400">${formatPrice(signal.entryPrice)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400 uppercase mb-1">Current Price</div>
                <div className="text-lg font-mono text-yellow-400">${formatPrice(signal.currentPrice)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400 uppercase mb-1">Stop Loss</div>
                <div className="text-lg font-mono text-red-400">${formatPrice(signal.stopLoss)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400 uppercase mb-1">Take Profit</div>
                <div className="text-lg font-mono text-green-400">${formatPrice(signal.takeProfit)}</div>
              </div>
            </div>
          </div>

          {/* Price Chart */}
          <div className="bg-slate-800/30 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-slate-100 mb-3">Price Chart</h3>
            <div ref={chartContainerRef} className="w-full rounded-lg overflow-hidden" />
            {!isChartReady && (
              <div className="flex items-center justify-center h-[400px] text-slate-400">
                Loading chart...
              </div>
            )}
          </div>

          {/* MFE/MAE Visualization */}
          <div className="bg-slate-800/30 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-slate-100 mb-3">Maximum Excursion</h3>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-slate-300">MFE (Maximum Favorable Excursion)</span>
                  <span className="text-sm font-semibold text-green-400">{signal.mfe.toFixed(2)}%</span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-6 overflow-hidden">
                  <div
                    className="bg-green-500 h-full flex items-center justify-end pr-2 transition-all duration-300"
                    style={{ width: `${Math.min(Math.abs(signal.mfe) * 2, 100)}%` }}
                  >
                    <span className="text-xs font-semibold text-white">{signal.mfe.toFixed(2)}%</span>
                  </div>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-slate-300">MAE (Maximum Adverse Excursion)</span>
                  <span className="text-sm font-semibold text-red-400">{signal.mae.toFixed(2)}%</span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-6 overflow-hidden">
                  <div
                    className="bg-red-500 h-full flex items-center justify-end pr-2 transition-all duration-300"
                    style={{ width: `${Math.min(Math.abs(signal.mae) * 2, 100)}%` }}
                  >
                    <span className="text-xs font-semibold text-white">{signal.mae.toFixed(2)}%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Feature Contributions */}
          <div className="bg-slate-800/30 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-slate-100 mb-3">Feature Contributions</h3>
            <div className="space-y-2">
              {sortedFeatures.map(([feature, contribution]) => (
                <div key={feature}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-slate-300 capitalize">
                      {feature.replace(/_/g, ' ')}
                    </span>
                    <span className={`text-sm font-semibold ${contribution > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {contribution > 0 ? '+' : ''}{contribution.toFixed(2)}
                    </span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-4 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${contribution > 0 ? 'bg-green-500' : 'bg-red-500'}`}
                      style={{
                        width: `${Math.min(Math.abs(contribution) * 10, 100)}%`,
                        marginLeft: contribution < 0 ? 'auto' : '0',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quality Grade Breakdown */}
          <div className="bg-slate-800/30 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-slate-100 mb-3">Quality Grade Breakdown</h3>
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold border ${getQualityColor(signal.quality)}`}>
                  {signal.quality}
                </span>
                <p className="text-sm text-slate-300 flex-1">
                  {getQualityDescription(signal.quality)}
                </p>
              </div>
              <div className="text-xs text-slate-400 space-y-1">
                <p>• Quality grades are calculated based on confluence across multiple indicators</p>
                <p>• Higher grades (A+, A) indicate stronger signal confirmation</p>
                <p>• Confidence score represents the model's certainty in the signal direction</p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-slate-900 border-t border-slate-800 px-6 py-4 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-slate-100 rounded-lg transition-colors font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
