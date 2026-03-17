/**
 * EquityCurveChart Component Usage Examples
 * 
 * This file demonstrates various ways to use the EquityCurveChart component
 * in the OpenClaw Trading Dashboard.
 */

import { useState } from 'react';
import { EquityCurveChart } from './EquityCurveChart';
import type { TimeRange } from '../types/index';

/**
 * Example 1: Basic Usage
 * 
 * Simplest implementation with default time range (7d)
 */
export function BasicEquityCurveExample() {
  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold text-slate-100 mb-4">Basic Equity Curve</h2>
      <EquityCurveChart />
    </div>
  );
}

/**
 * Example 2: Controlled Time Range
 * 
 * Parent component controls the time range state
 */
export function ControlledEquityCurveExample() {
  const [timeRange, setTimeRange] = useState<TimeRange>('30d');

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold text-slate-100 mb-4">
        Controlled Equity Curve
      </h2>
      <p className="text-slate-400 mb-4">
        Current time range: <span className="font-semibold text-green-500">{timeRange}</span>
      </p>
      <EquityCurveChart
        timeRange={timeRange}
        onTimeRangeChange={setTimeRange}
      />
    </div>
  );
}

/**
 * Example 3: Analytics Dashboard Integration
 * 
 * Shows how to integrate with other analytics components
 */
export function AnalyticsDashboardExample() {
  const [equityTimeRange, setEquityTimeRange] = useState<TimeRange>('7d');

  return (
    <div className="space-y-6 p-6">
      <div>
        <h2 className="text-3xl font-bold text-slate-100 mb-2">Performance Analytics</h2>
        <p className="text-slate-400">
          Comprehensive trading performance visualization
        </p>
      </div>

      {/* Performance Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            Total Return
          </p>
          <p className="text-2xl font-bold text-green-500">+24.5%</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            Win Rate
          </p>
          <p className="text-2xl font-bold text-slate-100">58.3%</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            Sharpe Ratio
          </p>
          <p className="text-2xl font-bold text-slate-100">1.85</p>
        </div>
      </div>

      {/* Equity Curve */}
      <EquityCurveChart
        timeRange={equityTimeRange}
        onTimeRangeChange={setEquityTimeRange}
      />

      {/* Additional Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">
            PnL Breakdown
          </h3>
          <p className="text-slate-400 text-sm">Daily/Weekly/Monthly PnL charts</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">
            Risk Metrics
          </h3>
          <p className="text-slate-400 text-sm">Drawdown analysis and risk ratios</p>
        </div>
      </div>
    </div>
  );
}

/**
 * Example 4: Multiple Time Range Views
 * 
 * Display multiple equity curves with different time ranges side by side
 */
export function MultipleTimeRangeExample() {
  return (
    <div className="space-y-6 p-6">
      <h2 className="text-2xl font-bold text-slate-100 mb-4">
        Multi-Timeframe Analysis
      </h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h3 className="text-lg font-semibold text-slate-100 mb-3">Short Term (7 Days)</h3>
          <EquityCurveChart timeRange="7d" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-slate-100 mb-3">Long Term (1 Year)</h3>
          <EquityCurveChart timeRange="1y" />
        </div>
      </div>
    </div>
  );
}

/**
 * Example 5: With Custom Actions
 * 
 * Add custom actions based on time range changes
 */
export function CustomActionsExample() {
  const [timeRange, setTimeRange] = useState<TimeRange>('7d');
  const [lastChanged, setLastChanged] = useState<Date | null>(null);

  const handleTimeRangeChange = (newRange: TimeRange) => {
    setTimeRange(newRange);
    setLastChanged(new Date());
    
    // Custom actions
    console.log(`Time range changed to: ${newRange}`);
    
    // Could trigger additional data fetches, analytics, etc.
    // Example: fetchAdditionalMetrics(newRange);
  };

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold text-slate-100 mb-4">
        Equity Curve with Custom Actions
      </h2>
      
      {lastChanged && (
        <div className="mb-4 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
          <p className="text-sm text-green-400">
            Time range updated to <span className="font-semibold">{timeRange}</span> at{' '}
            {lastChanged.toLocaleTimeString()}
          </p>
        </div>
      )}

      <EquityCurveChart
        timeRange={timeRange}
        onTimeRangeChange={handleTimeRangeChange}
      />
    </div>
  );
}

/**
 * Example 6: Responsive Layout
 * 
 * Shows how the component adapts to different container sizes
 */
export function ResponsiveLayoutExample() {
  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold text-slate-100 mb-4">
        Responsive Equity Curve
      </h2>

      {/* Full Width */}
      <div className="mb-8">
        <h3 className="text-lg font-semibold text-slate-100 mb-3">Full Width</h3>
        <EquityCurveChart timeRange="30d" />
      </div>

      {/* Half Width Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div>
          <h3 className="text-lg font-semibold text-slate-100 mb-3">Half Width</h3>
          <EquityCurveChart timeRange="7d" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-slate-100 mb-3">Half Width</h3>
          <EquityCurveChart timeRange="30d" />
        </div>
      </div>

      {/* Mobile View Simulation */}
      <div className="max-w-md">
        <h3 className="text-lg font-semibold text-slate-100 mb-3">Mobile View (max-w-md)</h3>
        <EquityCurveChart timeRange="7d" />
      </div>
    </div>
  );
}

/**
 * Example 7: Error Handling Demo
 * 
 * Shows how the component handles various error states
 * (This would require mocking the API to return errors)
 */
export function ErrorHandlingExample() {
  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold text-slate-100 mb-4">
        Error Handling
      </h2>
      <p className="text-slate-400 mb-4">
        The component gracefully handles API errors, network issues, and empty data states.
      </p>
      
      {/* In a real scenario, you would mock the API to return errors */}
      <EquityCurveChart timeRange="all" />
      
      <div className="mt-4 p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
        <h4 className="text-sm font-semibold text-slate-100 mb-2">Error States Handled:</h4>
        <ul className="text-sm text-slate-400 space-y-1">
          <li>• Network connection failures</li>
          <li>• API endpoint errors (404, 500, etc.)</li>
          <li>• Empty data sets</li>
          <li>• Invalid time ranges</li>
          <li>• Malformed response data</li>
        </ul>
      </div>
    </div>
  );
}

/**
 * Default Export: All Examples
 */
export default function EquityCurveExamples() {
  const [activeExample, setActiveExample] = useState<number>(1);

  const examples = [
    { id: 1, name: 'Basic Usage', component: <BasicEquityCurveExample /> },
    { id: 2, name: 'Controlled', component: <ControlledEquityCurveExample /> },
    { id: 3, name: 'Dashboard', component: <AnalyticsDashboardExample /> },
    { id: 4, name: 'Multi-Timeframe', component: <MultipleTimeRangeExample /> },
    { id: 5, name: 'Custom Actions', component: <CustomActionsExample /> },
    { id: 6, name: 'Responsive', component: <ResponsiveLayoutExample /> },
    { id: 7, name: 'Error Handling', component: <ErrorHandlingExample /> },
  ];

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="border-b border-slate-800 bg-slate-900">
        <div className="container mx-auto px-6 py-4">
          <h1 className="text-3xl font-bold text-slate-100 mb-4">
            EquityCurveChart Examples
          </h1>
          <div className="flex flex-wrap gap-2">
            {examples.map((example) => (
              <button
                key={example.id}
                onClick={() => setActiveExample(example.id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeExample === example.id
                    ? 'bg-green-500 text-white'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                {example.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="container mx-auto">
        {examples.find((ex) => ex.id === activeExample)?.component}
      </div>
    </div>
  );
}
