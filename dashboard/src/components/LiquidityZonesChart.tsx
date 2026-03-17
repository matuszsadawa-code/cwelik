import { useEffect, useRef, useState, useMemo } from 'react';
import { createChart, type IChartApi, type ISeriesApi, type CandlestickData } from 'lightweight-charts';
import type { LiquidityZone } from '../types/index';

interface LiquidityZonesChartProps {
  symbol: string;
  liquidityZones: LiquidityZone[];
  currentPrice: number;
}

interface ZoneDetailModalProps {
  zone: LiquidityZone | null;
  onClose: () => void;
}

/**
 * ZoneDetailModal Component
 * 
 * Displays detailed analysis for a selected liquidity zone
 */
const ZoneDetailModal: React.FC<ZoneDetailModalProps> = ({ zone, onClose }) => {
  if (!zone) return null;

  const getStrengthColor = (strength: string) => {
    switch (strength) {
      case 'high': return 'text-green-400';
      case 'medium': return 'text-yellow-400';
      case 'low': return 'text-gray-400';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-100">Liquidity Zone Analysis</h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-100 transition-colors"
            aria-label="Close modal"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          {/* Zone Type */}
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Type</p>
            <p className="text-lg font-semibold text-slate-100 capitalize">{zone.type}</p>
          </div>

          {/* Price Level */}
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Price Level</p>
            <p className="text-lg font-semibold text-slate-100">${zone.priceLevel.toFixed(2)}</p>
          </div>

          {/* Strength */}
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Strength</p>
            <p className={`text-lg font-semibold capitalize ${getStrengthColor(zone.strength)}`}>
              {zone.strength}
            </p>
          </div>

          {/* Liquidity Amount */}
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Estimated Liquidity</p>
            <p className="text-lg font-semibold text-slate-100">
              ${zone.liquidityAmount.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </p>
          </div>

          {/* Near Price Indicator */}
          {zone.isNearPrice && (
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3">
              <p className="text-sm text-yellow-400 flex items-center">
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                Price is within 0.5% of this zone
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * LiquidityZonesChart Component
 * 
 * Displays liquidity zones identified by the backend from order book imbalances
 * and historical volume profiles overlaid on a price chart.
 * 
 * Features:
 * - TradingView Lightweight Charts for price display
 * - Overlay liquidity zone rectangles at appropriate price levels
 * - Color-code zones by strength (high: green, medium: yellow, low: gray)
 * - Highlight zones when current price is within 0.5% of the zone
 * - Show tooltip on hover with liquidity amount
 * - Open detailed modal on click showing zone analysis
 * 
 * @param symbol - Trading pair symbol (e.g., 'BTCUSDT')
 * @param liquidityZones - Array of liquidity zones to display
 * @param currentPrice - Current market price for proximity detection
 * 
 * Requirements: 3.4, 3.5, 3.6, 3.7, 3.8
 */
export const LiquidityZonesChart: React.FC<LiquidityZonesChartProps> = ({
  symbol,
  liquidityZones,
  currentPrice,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const [selectedZone, setSelectedZone] = useState<LiquidityZone | null>(null);
  const [hoveredZone, setHoveredZone] = useState<LiquidityZone | null>(null);

  // Generate mock price data (in production, this would come from API)
  const priceData = useMemo<CandlestickData[]>(() => {
    const data: CandlestickData[] = [];
    const now = Date.now();
    let price = currentPrice || 50000;

    // Generate 100 candles
    for (let i = 100; i >= 0; i--) {
      const timestamp = Math.floor((now - i * 60 * 1000) / 1000);
      const change = (Math.random() - 0.5) * price * 0.02;
      const open = price;
      const close = price + change;
      const high = Math.max(open, close) + Math.random() * price * 0.01;
      const low = Math.min(open, close) - Math.random() * price * 0.01;

      data.push({
        time: timestamp as any,
        open,
        high,
        low,
        close,
      });

      price = close;
    }

    return data;
  }, [currentPrice]);

  // Get zone color based on strength
  const getZoneColor = (strength: string, isNear: boolean): string => {
    const alpha = isNear ? '80' : '40';
    switch (strength) {
      case 'high': return `#22C55E${alpha}`;
      case 'medium': return `#EAB308${alpha}`;
      case 'low': return `#6B7280${alpha}`;
      default: return `#6B7280${alpha}`;
    }
  };

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 500,
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
      crosshair: {
        mode: 1,
      },
    });

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

    candlestickSeries.setData(priceData);
    chart.timeScale().fitContent();

    chartRef.current = chart;
    candlestickSeriesRef.current = candlestickSeries as any;

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
  }, [priceData]);

  // Draw liquidity zones as price lines with markers
  useEffect(() => {
    if (!chartRef.current || !candlestickSeriesRef.current) return;

    // Add price lines for each liquidity zone
    liquidityZones.forEach((zone) => {
      const color = getZoneColor(zone.strength, zone.isNearPrice);
      
      candlestickSeriesRef.current?.createPriceLine({
        price: zone.priceLevel,
        color: color,
        lineWidth: zone.isNearPrice ? 3 : 2,
        lineStyle: 2, // Dashed
        axisLabelVisible: true,
        title: `${zone.type.toUpperCase()} - ${zone.strength.toUpperCase()}`,
      });
    });
  }, [liquidityZones]);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-950 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-100">Liquidity Zones</h3>
            <p className="text-sm text-slate-400 mt-1">{symbol}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-slate-400 uppercase tracking-wider">Current Price</p>
            <p className="text-xl font-bold text-slate-100 mt-1">
              ${currentPrice.toFixed(2)}
            </p>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="p-6">
        <div ref={chartContainerRef} className="w-full" />

        {/* Legend */}
        <div className="mt-6 flex flex-wrap gap-4 text-xs">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-0.5 bg-green-500" />
            <span className="text-slate-400">High Strength</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-0.5 bg-yellow-500" />
            <span className="text-slate-400">Medium Strength</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-0.5 bg-gray-500" />
            <span className="text-slate-400">Low Strength</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-1 bg-yellow-500" />
            <span className="text-slate-400">Near Price (±0.5%)</span>
          </div>
        </div>

        {/* Liquidity Zones List */}
        <div className="mt-6 space-y-2">
          <h4 className="text-sm font-semibold text-slate-300 mb-3">Active Zones</h4>
          {liquidityZones.length === 0 ? (
            <p className="text-sm text-slate-500 italic">No liquidity zones identified</p>
          ) : (
            liquidityZones.map((zone, index) => (
              <div
                key={index}
                className={`bg-slate-800/50 rounded-lg p-4 cursor-pointer transition-all duration-200 hover:bg-slate-800 ${
                  zone.isNearPrice ? 'ring-2 ring-yellow-500/50' : ''
                }`}
                onClick={() => setSelectedZone(zone)}
                onMouseEnter={() => setHoveredZone(zone)}
                onMouseLeave={() => setHoveredZone(null)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div
                      className={`w-3 h-3 rounded-full ${
                        zone.strength === 'high'
                          ? 'bg-green-500'
                          : zone.strength === 'medium'
                          ? 'bg-yellow-500'
                          : 'bg-gray-500'
                      }`}
                    />
                    <div>
                      <p className="text-sm font-medium text-slate-100 capitalize">
                        {zone.type} Zone
                      </p>
                      <p className="text-xs text-slate-400 mt-0.5">
                        ${zone.priceLevel.toFixed(2)}
                      </p>
                    </div>
                  </div>

                  <div className="text-right">
                    <p className="text-xs text-slate-400 uppercase tracking-wider">Liquidity</p>
                    <p className="text-sm font-semibold text-slate-100 mt-0.5">
                      ${zone.liquidityAmount.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </p>
                  </div>
                </div>

                {zone.isNearPrice && (
                  <div className="mt-2 flex items-center text-xs text-yellow-400">
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Price within 0.5%
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Hover Tooltip */}
        {hoveredZone && (
          <div className="fixed pointer-events-none z-40 bg-slate-800 border border-slate-700 rounded-lg p-3 shadow-xl">
            <p className="text-xs text-slate-400 mb-1">Estimated Liquidity</p>
            <p className="text-lg font-bold text-slate-100">
              ${hoveredZone.liquidityAmount.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </p>
          </div>
        )}
      </div>

      {/* Zone Detail Modal */}
      <ZoneDetailModal zone={selectedZone} onClose={() => setSelectedZone(null)} />
    </div>
  );
};
