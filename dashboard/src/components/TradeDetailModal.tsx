/**
 * TradeDetailModal Component
 * 
 * Displays complete trade details with price chart, feature contributions, and MFE/MAE visualization.
 * Requirements: 21.8, 21.9, 21.10
 */

import { useEffect, useRef, useState } from 'react';
import { createChart, LineStyle } from 'lightweight-charts';
import type { IChartApi, ISeriesApi } from 'lightweight-charts';
import type { Trade } from '../types';

interface TradeDetailModalProps {
  trade: Trade | null;
  onClose: () => void;
}

export default function TradeDetailModal({ trade, onClose }: TradeDetailModalProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [activeTab, setActiveTab] = useState<'chart' | 'features' | 'analysis'>('chart');

  useEffect(() => {
    if (!trade || !chartContainerRef.current || activeTab !== 'chart') return;

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { color: '#111827' },
        textColor: '#9CA3AF',
      },
      grid: {
        vertLines: { color: '#1F2937' },
        horzLines: { color: '#1F2937' },
      },
      timeScale: {
        borderColor: '#374151',
      },
      rightPriceScale: {
        borderColor: '#374151',
      },
    });

    chartRef.current = chart;

    // Generate sample price data (in production, fetch from backend)
    const generatePriceData = () => {
      const data = [];
      const startTime = trade.entryTime / 1000; // Convert to seconds
      const endTime = trade.exitTime / 1000;
      const duration = endTime - startTime;
      const points = Math.min(100, Math.max(20, Math.floor(duration / 60))); // 1 point per minute
      
      for (let i = 0; i <= points; i++) {
        const time = startTime + (duration * i / points);
        const progress = i / points;
        
        // Simulate price movement from entry to exit
        const priceRange = trade.exitPrice - trade.entryPrice;
        const noise = (Math.random() - 0.5) * Math.abs(priceRange) * 0.1;
        const price = trade.entryPrice + (priceRange * progress) + noise;
        
        data.push({ time: time as any, value: price });
      }
      
      return data;
    };

    const lineSeries = chart.addLineSeries({
      color: '#3B82F6',
      lineWidth: 2,
    });

    lineSeries.setData(generatePriceData());

    // Add entry price line
    lineSeries.createPriceLine({
      price: trade.entryPrice,
      color: '#22C55E',
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: 'Entry',
    });

    // Add exit price line
    lineSeries.createPriceLine({
      price: trade.exitPrice,
      color: trade.pnl >= 0 ? '#22C55E' : '#EF4444',
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: 'Exit',
    });

    // Add stop loss line (estimate based on direction)
    const stopLoss = trade.direction === 'LONG' 
      ? trade.entryPrice * 0.98 
      : trade.entryPrice * 1.02;
    lineSeries.createPriceLine({
      price: stopLoss,
      color: '#EF4444',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      axisLabelVisible: true,
      title: 'SL',
    });

    // Add take profit line (estimate based on direction)
    const takeProfit = trade.direction === 'LONG'
      ? trade.entryPrice * 1.03
      : trade.entryPrice * 0.97;
    lineSeries.createPriceLine({
      price: takeProfit,
      color: '#22C55E',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      axisLabelVisible: true,
      title: 'TP',
    });

    chart.timeScale().fitContent();

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
    };
  }, [trade, activeTab]);

  if (!trade) return null;

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes} minutes`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours < 24) return `${hours}h ${mins}m`;
    const days = Math.floor(hours / 24);
    const remainingHours = hours % 24;
    return `${days}d ${remainingHours}h`;
  };

  // Get quality grade color
  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'A+': return 'text-green-400 bg-green-500/20';
      case 'A': return 'text-blue-400 bg-blue-500/20';
      case 'B': return 'text-yellow-400 bg-yellow-500/20';
      case 'C': return 'text-orange-400 bg-orange-500/20';
      default: return 'text-gray-400 bg-gray-500/20';
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-lg max-w-6xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-800">
          <div>
            <h2 className="text-2xl font-bold">{trade.symbol} Trade Details</h2>
            <p className="text-sm text-gray-400 mt-1">
              {formatDate(trade.entryTime)} → {formatDate(trade.exitTime)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Trade Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-6 border-b border-gray-800">
          <div>
            <div className="text-sm text-gray-400">Direction</div>
            <div className={`text-lg font-semibold mt-1 ${
              trade.direction === 'LONG' ? 'text-green-400' : 'text-red-400'
            }`}>
              {trade.direction}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-400">PnL</div>
            <div className={`text-lg font-semibold mt-1 ${
              trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toFixed(2)}% ({trade.pnlPercent >= 0 ? '+' : ''}{trade.pnlPercent.toFixed(2)}%)
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-400">Quality Grade</div>
            <div className="mt-1">
              <span className={`text-sm font-semibold px-3 py-1 rounded ${getQualityColor(trade.quality)}`}>
                {trade.quality}
              </span>
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-400">Duration</div>
            <div className="text-lg font-semibold mt-1">{formatDuration(trade.duration)}</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-800">
          <button
            onClick={() => setActiveTab('chart')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'chart'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Price Chart
          </button>
          <button
            onClick={() => setActiveTab('features')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'features'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Feature Contributions
          </button>
          <button
            onClick={() => setActiveTab('analysis')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'analysis'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Analysis
          </button>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'chart' && (
            <div>
              <div ref={chartContainerRef} className="w-full h-[400px] bg-gray-800 rounded-lg" />
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                <div className="bg-gray-800 p-4 rounded-lg">
                  <div className="text-sm text-gray-400">Entry Price</div>
                  <div className="text-lg font-semibold mt-1">${trade.entryPrice.toFixed(2)}</div>
                </div>
                <div className="bg-gray-800 p-4 rounded-lg">
                  <div className="text-sm text-gray-400">Exit Price</div>
                  <div className="text-lg font-semibold mt-1">${trade.exitPrice.toFixed(2)}</div>
                </div>
                <div className="bg-gray-800 p-4 rounded-lg">
                  <div className="text-sm text-gray-400">Size</div>
                  <div className="text-lg font-semibold mt-1">{trade.size.toFixed(4)}</div>
                </div>
                <div className="bg-gray-800 p-4 rounded-lg">
                  <div className="text-sm text-gray-400">Outcome</div>
                  <div className={`text-lg font-semibold mt-1 ${
                    trade.outcome === 'WIN' ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {trade.outcome}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'features' && (
            <div>
              <h3 className="text-lg font-semibold mb-4">Feature Contributions</h3>
              <div className="space-y-2">
                {Object.entries(trade.featureContributions)
                  .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
                  .map(([feature, contribution]) => (
                    <div key={feature} className="flex items-center gap-4">
                      <div className="w-48 text-sm text-gray-400">{feature}</div>
                      <div className="flex-1 bg-gray-800 rounded-full h-6 relative overflow-hidden">
                        <div
                          className={`h-full ${contribution >= 0 ? 'bg-green-500' : 'bg-red-500'}`}
                          style={{
                            width: `${Math.abs(contribution) * 100}%`,
                            marginLeft: contribution < 0 ? `${100 - Math.abs(contribution) * 100}%` : '0',
                          }}
                        />
                        <div className="absolute inset-0 flex items-center justify-center text-xs font-semibold">
                          {(contribution * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {activeTab === 'analysis' && (
            <div className="space-y-6">
              {/* MFE/MAE Visualization */}
              <div>
                <h3 className="text-lg font-semibold mb-4">MFE/MAE Analysis</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-gray-800 p-4 rounded-lg">
                    <div className="text-sm text-gray-400">Maximum Favorable Excursion (MFE)</div>
                    <div className="text-2xl font-bold text-green-400 mt-2">
                      +{trade.mfe.toFixed(2)}%
                    </div>
                    <div className="text-xs text-gray-500 mt-1">Best unrealized profit during trade</div>
                  </div>
                  <div className="bg-gray-800 p-4 rounded-lg">
                    <div className="text-sm text-gray-400">Maximum Adverse Excursion (MAE)</div>
                    <div className="text-2xl font-bold text-red-400 mt-2">
                      {trade.mae.toFixed(2)}%
                    </div>
                    <div className="text-xs text-gray-500 mt-1">Worst unrealized loss during trade</div>
                  </div>
                </div>
              </div>

              {/* Quality Grade Breakdown */}
              <div>
                <h3 className="text-lg font-semibold mb-4">Quality Grade Breakdown</h3>
                <div className="bg-gray-800 p-4 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-400">Overall Quality</span>
                    <span className={`text-lg font-semibold px-3 py-1 rounded ${getQualityColor(trade.quality)}`}>
                      {trade.quality}
                    </span>
                  </div>
                  <div className="text-sm text-gray-400 mt-4">
                    This grade is calculated based on multiple factors including trend strength, 
                    volume confirmation, order flow validation, and feature contributions.
                  </div>
                </div>
              </div>

              {/* Entry/Exit Reasons */}
              <div>
                <h3 className="text-lg font-semibold mb-4">Trade Reasons</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-gray-800 p-4 rounded-lg">
                    <div className="text-sm text-gray-400 mb-2">Entry Reason</div>
                    <div className="text-sm">{trade.entryReason}</div>
                  </div>
                  <div className="bg-gray-800 p-4 rounded-lg">
                    <div className="text-sm text-gray-400 mb-2">Exit Reason</div>
                    <div className="text-sm">{trade.exitReason}</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
