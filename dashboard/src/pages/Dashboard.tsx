import { useState } from 'react';
import { useDashboardStore } from '@stores/dashboardStore';
import { MarketDataGrid } from '../components/MarketDataGrid';
import SectionErrorBoundary from '../components/SectionErrorBoundary';

export default function Dashboard() {
  const { activeSignals, openPositions, performanceMetrics } = useDashboardStore();
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);

  // Default symbols to monitor - this should come from configuration
  const monitoredSymbols = [
    'BTCUSDT',
    'ETHUSDT',
    'BNBUSDT',
    'SOLUSDT',
    'XRPUSDT',
    'ADAUSDT',
    'DOGEUSDT',
    'AVAXUSDT',
    'DOTUSDT',
    'MATICUSDT',
  ];

  const handleSymbolSelect = (symbol: string) => {
    setSelectedSymbol(symbol);
    // TODO: Open detailed order book modal/view
    console.log('Selected symbol:', symbol);
  };

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-3xl font-bold mb-2">Dashboard</h2>
        <p className="text-text-secondary">
          Real-time market monitoring and trading overview
        </p>
      </header>

      {/* Quick Stats - Tablet: 2 columns, Desktop: 4 columns */}
      <section aria-labelledby="quick-stats-heading">
        <h3 id="quick-stats-heading" className="sr-only">Quick Statistics</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <article className="bg-glass border-glass rounded-lg p-6">
            <div className="text-text-muted text-sm mb-1">Active Signals</div>
            <div className="text-3xl font-bold" aria-label={`${activeSignals.length} active signals`}>
              {activeSignals.length}
            </div>
          </article>

          <article className="bg-glass border-glass rounded-lg p-6">
            <div className="text-text-muted text-sm mb-1">Open Positions</div>
            <div className="text-3xl font-bold" aria-label={`${openPositions.length} open positions`}>
              {openPositions.length}
            </div>
          </article>

          <article className="bg-glass border-glass rounded-lg p-6">
            <div className="text-text-muted text-sm mb-1">Win Rate</div>
            <div className="text-3xl font-bold" aria-label={`Win rate: ${performanceMetrics?.winRate.toFixed(1) ?? 'not available'} percent`}>
              {performanceMetrics?.winRate.toFixed(1) ?? '--'}%
            </div>
          </article>

          <article className="bg-glass border-glass rounded-lg p-6">
            <div className="text-text-muted text-sm mb-1">Profit Factor</div>
            <div className="text-3xl font-bold" aria-label={`Profit factor: ${performanceMetrics?.profitFactor.toFixed(2) ?? 'not available'}`}>
              {performanceMetrics?.profitFactor.toFixed(2) ?? '--'}
            </div>
          </article>
        </div>
      </section>

      {/* Market Data Section */}
      <section aria-labelledby="market-data-heading">
        <h3 id="market-data-heading" className="text-xl font-semibold mb-4">Market Data</h3>
        <SectionErrorBoundary section="Market Data Grid">
          <MarketDataGrid symbols={monitoredSymbols} onSymbolSelect={handleSymbolSelect} />
        </SectionErrorBoundary>
        {selectedSymbol && (
          <div 
            className="mt-4 p-4 bg-slate-800/50 border border-slate-700 rounded-lg"
            role="status"
            aria-live="polite"
          >
            <p className="text-sm text-slate-300">
              Selected: <span className="font-semibold text-green-400">{selectedSymbol}</span>
              <span className="ml-2 text-slate-500">(Detailed order book view coming soon)</span>
            </p>
          </div>
        )}
      </section>

      {/* Active Signals Section */}
      <section 
        className="bg-glass border-glass rounded-lg p-6"
        aria-labelledby="active-signals-section-heading"
      >
        <h3 id="active-signals-section-heading" className="text-xl font-semibold mb-4">Active Signals</h3>
        <SectionErrorBoundary section="Active Signals Panel">
          {activeSignals.length === 0 ? (
            <p className="text-text-muted">No active signals</p>
          ) : (
            <p className="text-text-muted">Active signals list will be displayed here</p>
          )}
        </SectionErrorBoundary>
      </section>

      {/* Open Positions Section */}
      <section 
        className="bg-glass border-glass rounded-lg p-6"
        aria-labelledby="open-positions-section-heading"
      >
        <h3 id="open-positions-section-heading" className="text-xl font-semibold mb-4">Open Positions</h3>
        <SectionErrorBoundary section="Positions Panel">
          {openPositions.length === 0 ? (
            <p className="text-text-muted">No open positions</p>
          ) : (
            <p className="text-text-muted">Open positions list will be displayed here</p>
          )}
        </SectionErrorBoundary>
      </section>
    </div>
  );
}
