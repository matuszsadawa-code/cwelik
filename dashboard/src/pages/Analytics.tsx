import { useState, lazy, Suspense } from 'react';
import LoadingFallback from '../components/LoadingFallback';
import type { TimeRange } from '../types/index';

// Lazy load heavy chart components
const EquityCurveChart = lazy(() => import('../components/EquityCurveChart').then(m => ({ default: m.EquityCurveChart })));
const PerformanceMetricsPanel = lazy(() => import('../components/PerformanceMetricsPanel').then(m => ({ default: m.PerformanceMetricsPanel })));
const PnLBreakdownCharts = lazy(() => import('../components/PnLBreakdownCharts').then(m => ({ default: m.PnLBreakdownCharts })));
const SymbolPerformanceTable = lazy(() => import('../components/SymbolPerformanceTable').then(m => ({ default: m.SymbolPerformanceTable })));
const RiskMetricsPanel = lazy(() => import('../components/RiskMetricsPanel').then(m => ({ default: m.RiskMetricsPanel })));
const QualityGradeAnalysis = lazy(() => import('../components/QualityGradeAnalysis').then(m => ({ default: m.QualityGradeAnalysis })));
const RRDistributionChart = lazy(() => import('../components/RRDistributionChart').then(m => ({ default: m.RRDistributionChart })));
const BacktestViewer = lazy(() => import('../components/BacktestViewer').then(m => ({ default: m.BacktestViewer })));
const ABTestingDashboard = lazy(() => import('../components/ABTestingDashboard').then(m => ({ default: m.ABTestingDashboard })));

/**
 * Analytics Page
 * 
 * Displays comprehensive performance analytics including:
 * - Performance metrics panel
 * - Equity curve visualization
 * - PnL breakdown charts
 * - Symbol performance statistics
 * - Risk metrics
 * - Quality grade analysis
 * - R:R distribution
 * - Backtesting results
 * - A/B testing experiments
 */
export default function Analytics() {
  const [equityTimeRange, setEquityTimeRange] = useState<TimeRange>('7d');
  const [pnlTimeRange, setPnlTimeRange] = useState<TimeRange>('all');
  const [activeTab, setActiveTab] = useState<'performance' | 'backtest' | 'experiments'>('performance');

  const handleSymbolClick = (symbol: string) => {
    // TODO: Open detailed symbol analysis chart/modal
    console.log('Selected symbol:', symbol);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold mb-2 text-slate-100">Analytics</h2>
        <p className="text-slate-400">
          Comprehensive performance analytics and trading insights
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-slate-800">
        <button
          onClick={() => setActiveTab('performance')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'performance'
              ? 'text-cta border-b-2 border-cta'
              : 'text-slate-400 hover:text-slate-300'
          }`}
        >
          Performance
        </button>
        <button
          onClick={() => setActiveTab('backtest')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'backtest'
              ? 'text-cta border-b-2 border-cta'
              : 'text-slate-400 hover:text-slate-300'
          }`}
        >
          Backtesting
        </button>
        <button
          onClick={() => setActiveTab('experiments')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'experiments'
              ? 'text-cta border-b-2 border-cta'
              : 'text-slate-400 hover:text-slate-300'
          }`}
        >
          A/B Testing
        </button>
      </div>

      {/* Performance Tab */}
      {activeTab === 'performance' && (
        <>
          {/* Performance Metrics */}
          <Suspense fallback={<LoadingFallback />}>
            <PerformanceMetricsPanel />
          </Suspense>

          {/* Equity Curve */}
          <Suspense fallback={<LoadingFallback />}>
            <EquityCurveChart
              timeRange={equityTimeRange}
              onTimeRangeChange={setEquityTimeRange}
            />
          </Suspense>

          {/* PnL Breakdown Charts */}
          <Suspense fallback={<LoadingFallback />}>
            <PnLBreakdownCharts
              timeRange={pnlTimeRange}
              onTimeRangeChange={setPnlTimeRange}
            />
          </Suspense>

          {/* Symbol Performance Table */}
          <Suspense fallback={<LoadingFallback />}>
            <SymbolPerformanceTable onSymbolClick={handleSymbolClick} />
          </Suspense>

          {/* Risk Metrics, Quality Grade Analysis, R:R Distribution */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Suspense fallback={<LoadingFallback />}>
              <RiskMetricsPanel />
            </Suspense>

            <Suspense fallback={<LoadingFallback />}>
              <QualityGradeAnalysis />
            </Suspense>
          </div>

          <Suspense fallback={<LoadingFallback />}>
            <RRDistributionChart />
          </Suspense>
        </>
      )}

      {/* Backtesting Tab */}
      {activeTab === 'backtest' && (
        <Suspense fallback={<LoadingFallback />}>
          <BacktestViewer />
        </Suspense>
      )}

      {/* A/B Testing Tab */}
      {activeTab === 'experiments' && (
        <Suspense fallback={<LoadingFallback />}>
          <ABTestingDashboard />
        </Suspense>
      )}
    </div>
  );
}
