import { useState, lazy, Suspense } from 'react';
import LoadingFallback from '../components/LoadingFallback';
import TradeDetailModal from '../components/TradeDetailModal';
import TradeExport from '../components/TradeExport';
import type { Trade } from '../types/index';

// Lazy load heavy TradeTable component with virtual scrolling
const TradeTable = lazy(() => import('../components/TradeTable'));

/**
 * Trade Journal Page
 * 
 * Displays detailed trade history with:
 * - Paginated trade table
 * - Filtering by symbol, date range, outcome, quality grade
 * - Sortable columns
 * - Trade detail modal
 * - Export functionality
 */
export default function TradeJournal() {
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

  const handleTradeClick = (trade: Trade) => {
    setSelectedTrade(trade);
    setShowDetailModal(true);
  };

  const handleCloseModal = () => {
    setShowDetailModal(false);
    setSelectedTrade(null);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold mb-2">Trade Journal</h2>
        <p className="text-text-secondary">
          Detailed history of all trades with analysis
        </p>
      </div>

      {/* Filters */}
      <div className="bg-glass border-glass rounded-lg p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Symbol
            </label>
            <select className="w-full bg-background-secondary border border-slate-700 rounded-lg px-3 py-2 text-text-primary">
              <option value="">All Symbols</option>
              <option value="BTCUSDT">BTCUSDT</option>
              <option value="ETHUSDT">ETHUSDT</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Outcome
            </label>
            <select className="w-full bg-background-secondary border border-slate-700 rounded-lg px-3 py-2 text-text-primary">
              <option value="">All</option>
              <option value="WIN">Win</option>
              <option value="LOSS">Loss</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Quality Grade
            </label>
            <select className="w-full bg-background-secondary border border-slate-700 rounded-lg px-3 py-2 text-text-primary">
              <option value="">All</option>
              <option value="A+">A+</option>
              <option value="A">A</option>
              <option value="B">B</option>
              <option value="C">C</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Date Range
            </label>
            <select className="w-full bg-background-secondary border border-slate-700 rounded-lg px-3 py-2 text-text-primary">
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
              <option value="all">All time</option>
            </select>
          </div>
        </div>
      </div>

      {/* Trade Table */}
      <Suspense fallback={<LoadingFallback />}>
        <div className="bg-glass border-glass rounded-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-xl font-semibold">Trade History</h3>
            <TradeExport />
          </div>
          <TradeTable onTradeClick={handleTradeClick} />
        </div>
      </Suspense>

      {/* Trade Detail Modal */}
      {showDetailModal && selectedTrade && (
        <TradeDetailModal
          trade={selectedTrade}
          onClose={handleCloseModal}
        />
      )}
    </div>
  );
}
