import { useEffect, useRef, useState } from 'react';
import { createChart, type LineData, type Time } from 'lightweight-charts';
import type { IChartApi, ISeriesApi } from 'lightweight-charts';
import type { SymbolPnLData, SymbolTrade } from '../types/index';
import { fetchSymbolPnL, fetchMultiSymbolPnL } from '../services/api';

/**
 * PerSymbolPnLChart Component
 * 
 * Displays per-symbol PnL analysis with cumulative PnL chart and trade-by-trade scatter plot.
 * 
 * Features:
 * - Cumulative PnL line chart for selected symbol
 * - Trade-by-trade PnL scatter plot overlay
 * - Winning trades marked in green, losing trades in red
 * - Symbol-specific win rate and profit factor display
 * - Compare up to 4 symbols on same chart
 * - Trade details on hover
 * - Dark mode OLED optimized colors
 * - Responsive design
 * 
 * Requirements: 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9
 */

interface PerSymbolPnLChartProps {
  initialSymbol?: string;
  onSymbolChange?: (symbol: string) => void;
}

const CHART_COLORS = [
  '#22C55E', // green-500
  '#3B82F6', // blue-500
  '#F59E0B', // amber-500
  '#8B5CF6', // violet-500
];

export const PerSymbolPnLChart: React.FC<PerSymbolPnLChartProps> = ({
  initialSymbol = 'BTCUSDT',
  onSymbolChange,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const lineSeriesRefs = useRef<Map<string, ISeriesApi<'Line'>>>(new Map());
  
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([initialSymbol]);
  const [symbolData, setSymbolData] = useState<Map<string, SymbolPnLData>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [symbolInput, setSymbolInput] = useState('');
  const [hoveredTrade, setHoveredTrade] = useState<SymbolTrade & { symbol: string } | null>(null);

  // Fetch symbol PnL data
  useEffect(() => {
    const fetchData = async () => {
      if (selectedSymbols.length === 0) return;
      
      setLoading(true);
      setError(null);
      
      try {
        if (selectedSymbols.length === 1) {
          const data = await fetchSymbolPnL(selectedSymbols[0]);
          const newMap = new Map();
          newMap.set(selectedSymbols[0], data);
          setSymbolData(newMap);
        } else {
          const data = await fetchMultiSymbolPnL(selectedSymbols);
          const newMap = new Map();
          data.symbols.forEach(symbolData => {
            newMap.set(symbolData.symbol, symbolData);
          });
          setSymbolData(newMap);
        }
      } catch (err) {
        console.error('Error fetching symbol PnL:', err);
        setError(err instanceof Error ? err.message : 'Failed to load symbol PnL');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [selectedSymbols]);

  // Initialize and update chart
  useEffect(() => {
    if (!chartContainerRef.current || symbolData.size === 0) {
      return;
    }

    // Create chart if it doesn't exist
    if (!chartRef.current) {
      const chart = createChart(chartContainerRef.current, {
        layout: {
          background: { color: '#020617' }, // slate-950
          textColor: '#94A3B8', // slate-400
        },
        grid: {
          vertLines: { color: '#1E293B' }, // slate-800
          horzLines: { color: '#1E293B' },
        },
        crosshair: {
          mode: 1,
          vertLine: {
            color: '#475569',
            width: 1,
            style: 2,
          },
          horzLine: {
            color: '#475569',
            width: 1,
            style: 2,
          },
        },
        rightPriceScale: {
          borderColor: '#334155',
        },
        timeScale: {
          borderColor: '#334155',
          timeVisible: true,
          secondsVisible: false,
        },
        handleScroll: {
          mouseWheel: true,
          pressedMouseMove: true,
        },
        handleScale: {
          axisPressedMouseMove: true,
          mouseWheel: true,
          pinch: true,
        },
      });

      chartRef.current = chart;
    }

    // Clear existing series
    lineSeriesRefs.current.forEach(series => {
      if (chartRef.current) {
        chartRef.current.removeSeries(series);
      }
    });
    lineSeriesRefs.current.clear();

    // Add line series for each symbol
    selectedSymbols.forEach((symbol, index) => {
      const data = symbolData.get(symbol);
      if (!data || !chartRef.current) return;

      const color = CHART_COLORS[index % CHART_COLORS.length];
      
      // Create cumulative PnL line series
      const lineSeries = chartRef.current.addLineSeries({
        color: color,
        lineWidth: 2,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
        title: symbol,
        priceFormat: {
          type: 'custom',
          formatter: (price: number) => `${price.toFixed(2)}%`,
        },
      });

      lineSeriesRefs.current.set(symbol, lineSeries);

      // Convert trades to cumulative PnL line data
      const lineData: LineData[] = data.trades.map(trade => ({
        time: (trade.timestamp / 1000) as Time,
        value: trade.cumulativePnL,
      }));

      lineSeries.setData(lineData);

      // Add markers for individual trades (scatter plot effect)
      const markers = data.trades.map(trade => ({
        time: (trade.timestamp / 1000) as Time,
        position: trade.outcome === 'WIN' ? 'belowBar' as const : 'aboveBar' as const,
        color: trade.outcome === 'WIN' ? '#22C55E' : '#EF4444',
        shape: 'circle' as const,
        text: `${trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}%`,
      }));

      lineSeries.setMarkers(markers);
    });

    // Fit content
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }

    // Handle resize
    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [symbolData, selectedSymbols]);

  // Cleanup chart on unmount
  useEffect(() => {
    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
        lineSeriesRefs.current.clear();
      }
    };
  }, []);

  const handleAddSymbol = () => {
    const symbol = symbolInput.trim().toUpperCase();
    
    if (!symbol) return;
    
    if (selectedSymbols.includes(symbol)) {
      setError(`${symbol} is already selected`);
      return;
    }
    
    if (selectedSymbols.length >= 4) {
      setError('Maximum 4 symbols allowed for comparison');
      return;
    }
    
    setSelectedSymbols([...selectedSymbols, symbol]);
    setSymbolInput('');
    setError(null);
  };


  const handleRemoveSymbol = (symbol: string) => {
    if (selectedSymbols.length === 1) {
      setError('At least one symbol must be selected');
      return;
    }
    
    setSelectedSymbols(selectedSymbols.filter(s => s !== symbol));
    setError(null);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleAddSymbol();
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-slate-100">Per-Symbol PnL Analysis</h3>
      </div>

      {/* Symbol Selection */}
      <div className="mb-6">
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={symbolInput}
            onChange={(e) => setSymbolInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Enter symbol (e.g., BTCUSDT)"
            className="flex-1 px-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:border-green-500 transition-colors"
            disabled={selectedSymbols.length >= 4}
          />
          <button
            onClick={handleAddSymbol}
            disabled={selectedSymbols.length >= 4 || !symbolInput.trim()}
            className="px-6 py-2 bg-green-500 text-white rounded-lg font-medium hover:bg-green-600 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed transition-colors"
          >
            Add
          </button>
        </div>

        {/* Selected Symbols */}
        <div className="flex flex-wrap gap-2">
          {selectedSymbols.map((symbol, index) => {
            const data = symbolData.get(symbol);
            const color = CHART_COLORS[index % CHART_COLORS.length];
            
            return (
              <div
                key={symbol}
                className="flex items-center gap-3 px-4 py-2 bg-slate-950 border border-slate-700 rounded-lg"
                style={{ borderLeftWidth: '4px', borderLeftColor: color }}
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-100">{symbol}</span>
                    {data && (
                      <span className={`text-sm ${data.totalPnL >= 0 ? 'text-green-500' : 'text-red-400'}`}>
                        {data.totalPnL >= 0 ? '+' : ''}{data.totalPnL.toFixed(2)}%
                      </span>
                    )}
                  </div>
                  {data && (
                    <div className="flex items-center gap-4 text-xs text-slate-400 mt-1">
                      <span>Win Rate: {data.winRate.toFixed(1)}%</span>
                      <span>PF: {data.profitFactor.toFixed(2)}</span>
                      <span>Trades: {data.totalTrades}</span>
                    </div>
                  )}
                </div>
                <button
                  onClick={() => handleRemoveSymbol(symbol)}
                  className="text-slate-500 hover:text-red-400 transition-colors"
                  aria-label={`Remove ${symbol}`}
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            );
          })}
        </div>

        {selectedSymbols.length >= 4 && (
          <p className="text-xs text-amber-500 mt-2">
            Maximum 4 symbols reached. Remove a symbol to add another.
          </p>
        )}
      </div>

      {/* Error State */}
      {error && !loading && (
        <div className="mb-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center h-96">
          <p className="text-slate-400">Loading symbol PnL data...</p>
        </div>
      )}

      {/* Chart */}
      {!loading && !error && symbolData.size > 0 && (
        <>
          <div
            ref={chartContainerRef}
            className="w-full h-96 bg-slate-950 rounded-lg mb-4"
            style={{ minHeight: '384px' }}
          />

          {/* Legend */}
          <div className="flex items-center justify-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-green-500 rounded-full"></div>
              <span className="text-slate-400">Winning Trades</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-red-500 rounded-full"></div>
              <span className="text-slate-400">Losing Trades</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-0.5 bg-green-500"></div>
              <span className="text-slate-400">Cumulative PnL</span>
            </div>
          </div>


          {/* Summary Statistics */}
          {selectedSymbols.length === 1 && symbolData.get(selectedSymbols[0]) && (
            <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
              {(() => {
                const data = symbolData.get(selectedSymbols[0])!;
                return (
                  <>
                    <div className="bg-slate-950 rounded-lg p-4">
                      <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
                        Win Rate
                      </p>
                      <p className={`text-xl font-bold ${
                        data.winRate >= 60 ? 'text-green-500' :
                        data.winRate >= 50 ? 'text-yellow-500' :
                        'text-red-400'
                      }`}>
                        {data.winRate.toFixed(1)}%
                      </p>
                    </div>

                    <div className="bg-slate-950 rounded-lg p-4">
                      <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
                        Profit Factor
                      </p>
                      <p className={`text-xl font-bold ${
                        data.profitFactor >= 1.5 ? 'text-green-500' :
                        data.profitFactor >= 1.0 ? 'text-yellow-500' :
                        'text-red-400'
                      }`}>
                        {data.profitFactor.toFixed(2)}
                      </p>
                    </div>

                    <div className="bg-slate-950 rounded-lg p-4">
                      <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
                        Total Trades
                      </p>
                      <p className="text-xl font-bold text-slate-100">
                        {data.totalTrades}
                      </p>
                    </div>

                    <div className="bg-slate-950 rounded-lg p-4">
                      <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
                        Total PnL
                      </p>
                      <p className={`text-xl font-bold ${
                        data.totalPnL >= 0 ? 'text-green-500' : 'text-red-400'
                      }`}>
                        {data.totalPnL >= 0 ? '+' : ''}{data.totalPnL.toFixed(2)}%
                      </p>
                    </div>
                  </>
                );
              })()}
            </div>
          )}
        </>
      )}

      {/* Empty State */}
      {!loading && !error && symbolData.size === 0 && (
        <div className="flex items-center justify-center h-96">
          <p className="text-slate-400">No symbol data available</p>
        </div>
      )}
    </div>
  );
};
