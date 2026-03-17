/**
 * ABTestingDashboard Component
 * 
 * Displays A/B testing experiments with control vs treatment comparison and statistical analysis.
 * Requirements: 23.4, 23.5, 23.6, 23.7, 23.8, 23.9, 23.10, 23.11
 */

import { useState, useEffect } from 'react';
import type { Experiment } from '../types';
import { fetchExperiments, fetchExperimentDetail, stopExperiment } from '../services/api';

export default function ABTestingDashboard() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedExperiment, setSelectedExperiment] = useState<Experiment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);

  // Fetch experiments
  useEffect(() => {
    const loadExperiments = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchExperiments();
        setExperiments(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load experiments');
      } finally {
        setLoading(false);
      }
    };

    loadExperiments();
  }, []);

  // Fetch selected experiment details
  const handleExperimentSelect = async (experimentId: string) => {
    try {
      const data = await fetchExperimentDetail(experimentId);
      setSelectedExperiment(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load experiment details');
    }
  };

  // Stop experiment
  const handleStopExperiment = async (experimentId: string) => {
    if (!confirm('Are you sure you want to stop this experiment?')) return;

    try {
      setStopping(true);
      await stopExperiment(experimentId);
      
      // Refresh experiments list
      const data = await fetchExperiments();
      setExperiments(data);
      
      // Update selected experiment if it was stopped
      if (selectedExperiment?.experimentId === experimentId) {
        const updated = await fetchExperimentDetail(experimentId);
        setSelectedExperiment(updated);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop experiment');
    } finally {
      setStopping(false);
    }
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'bg-green-500/20 text-green-400';
      case 'completed': return 'bg-blue-500/20 text-blue-400';
      case 'stopped': return 'bg-gray-500/20 text-gray-400';
      default: return 'bg-gray-500/20 text-gray-400';
    }
  };

  const getSignificanceColor = (isSignificant: boolean) => {
    return isSignificant ? 'text-green-400' : 'text-yellow-400';
  };

  if (loading) {
    return (
      <div className="bg-gray-900 rounded-lg p-6">
        <div className="flex items-center justify-center h-96">
          <div className="text-gray-400">Loading experiments...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-900 rounded-lg p-6">
        <div className="text-red-400">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Experiments List */}
      <div className="bg-gray-900 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">A/B Testing Experiments</h2>

        <div className="space-y-3">
          {experiments.map((experiment) => (
            <div
              key={experiment.experimentId}
              className={`bg-gray-800 p-4 rounded-lg cursor-pointer hover:bg-gray-700 transition-colors ${
                selectedExperiment?.experimentId === experiment.experimentId ? 'ring-2 ring-blue-500' : ''
              }`}
              onClick={() => handleExperimentSelect(experiment.experimentId)}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <h3 className="font-semibold">{experiment.name}</h3>
                  <span className={`text-xs font-semibold px-2 py-1 rounded ${getStatusColor(experiment.status)}`}>
                    {experiment.status.toUpperCase()}
                  </span>
                </div>
                {experiment.status === 'running' && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleStopExperiment(experiment.experimentId);
                    }}
                    disabled={stopping}
                    className="px-3 py-1 text-sm bg-red-600 hover:bg-red-700 rounded transition-colors disabled:opacity-50"
                  >
                    Stop
                  </button>
                )}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="text-gray-400">Start Date</div>
                  <div className="font-medium">{formatDate(experiment.startDate)}</div>
                </div>
                <div>
                  <div className="text-gray-400">Control Win Rate</div>
                  <div className="font-medium">{experiment.controlGroup.winRate.toFixed(1)}%</div>
                </div>
                <div>
                  <div className="text-gray-400">Treatment Win Rate</div>
                  <div className="font-medium">{experiment.treatmentGroup.winRate.toFixed(1)}%</div>
                </div>
                <div>
                  <div className="text-gray-400">Statistical Significance</div>
                  <div className={`font-medium ${getSignificanceColor(experiment.statisticalSignificance.isSignificant)}`}>
                    {experiment.statisticalSignificance.isSignificant ? 'Significant' : 'Not Significant'}
                  </div>
                </div>
              </div>
            </div>
          ))}

          {experiments.length === 0 && (
            <div className="text-center text-gray-400 py-8">
              No experiments found
            </div>
          )}
        </div>
      </div>

      {/* Selected Experiment Details */}
      {selectedExperiment && (
        <div className="bg-gray-900 rounded-lg p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold">{selectedExperiment.name}</h2>
            <span className={`text-sm font-semibold px-3 py-1 rounded ${getStatusColor(selectedExperiment.status)}`}>
              {selectedExperiment.status.toUpperCase()}
            </span>
          </div>

          {/* Statistical Significance */}
          <div className="bg-gray-800 p-4 rounded-lg mb-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Statistical Analysis</h3>
              <div className={`text-lg font-bold ${getSignificanceColor(selectedExperiment.statisticalSignificance.isSignificant)}`}>
                {selectedExperiment.statisticalSignificance.isSignificant ? '✓ Significant' : '⚠ Not Significant'}
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <div className="text-sm text-gray-400">P-Value</div>
                <div className="text-lg font-semibold mt-1">
                  {selectedExperiment.statisticalSignificance.pValue.toFixed(4)}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-400">Confidence Level</div>
                <div className="text-lg font-semibold mt-1">
                  {selectedExperiment.statisticalSignificance.confidenceLevel.toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-400">Confidence Interval</div>
                <div className="text-lg font-semibold mt-1">
                  [{selectedExperiment.metricDifferences.confidenceInterval.lower.toFixed(2)}, 
                   {selectedExperiment.metricDifferences.confidenceInterval.upper.toFixed(2)}]
                </div>
              </div>
            </div>
          </div>

          {/* Control vs Treatment Comparison */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* Control Group */}
            <div className="bg-gray-800 p-4 rounded-lg">
              <h3 className="text-lg font-semibold mb-4 text-blue-400">Control Group</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">Sample Size</span>
                  <span className="font-semibold">{selectedExperiment.controlGroup.sampleSize}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Win Rate</span>
                  <span className="font-semibold">{selectedExperiment.controlGroup.winRate.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Profit Factor</span>
                  <span className="font-semibold">{selectedExperiment.controlGroup.profitFactor.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Avg PnL</span>
                  <span className={`font-semibold ${
                    selectedExperiment.controlGroup.avgPnL >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {selectedExperiment.controlGroup.avgPnL >= 0 ? '+' : ''}{selectedExperiment.controlGroup.avgPnL.toFixed(2)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Total PnL</span>
                  <span className={`font-semibold ${
                    selectedExperiment.controlGroup.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {selectedExperiment.controlGroup.totalPnL >= 0 ? '+' : ''}{selectedExperiment.controlGroup.totalPnL.toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Treatment Group */}
            <div className="bg-gray-800 p-4 rounded-lg">
              <h3 className="text-lg font-semibold mb-4 text-green-400">Treatment Group</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">Sample Size</span>
                  <span className="font-semibold">{selectedExperiment.treatmentGroup.sampleSize}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Win Rate</span>
                  <span className="font-semibold">{selectedExperiment.treatmentGroup.winRate.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Profit Factor</span>
                  <span className="font-semibold">{selectedExperiment.treatmentGroup.profitFactor.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Avg PnL</span>
                  <span className={`font-semibold ${
                    selectedExperiment.treatmentGroup.avgPnL >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {selectedExperiment.treatmentGroup.avgPnL >= 0 ? '+' : ''}{selectedExperiment.treatmentGroup.avgPnL.toFixed(2)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Total PnL</span>
                  <span className={`font-semibold ${
                    selectedExperiment.treatmentGroup.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {selectedExperiment.treatmentGroup.totalPnL >= 0 ? '+' : ''}{selectedExperiment.treatmentGroup.totalPnL.toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Metric Differences */}
          <div className="bg-gray-800 p-4 rounded-lg">
            <h3 className="text-lg font-semibold mb-4">Performance Differences (Treatment - Control)</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <div className="text-sm text-gray-400">Win Rate Difference</div>
                <div className={`text-xl font-bold mt-1 ${
                  selectedExperiment.metricDifferences.winRateDiff >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {selectedExperiment.metricDifferences.winRateDiff >= 0 ? '+' : ''}
                  {selectedExperiment.metricDifferences.winRateDiff.toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-400">Profit Factor Difference</div>
                <div className={`text-xl font-bold mt-1 ${
                  selectedExperiment.metricDifferences.profitFactorDiff >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {selectedExperiment.metricDifferences.profitFactorDiff >= 0 ? '+' : ''}
                  {selectedExperiment.metricDifferences.profitFactorDiff.toFixed(2)}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-400">Avg PnL Difference</div>
                <div className={`text-xl font-bold mt-1 ${
                  selectedExperiment.metricDifferences.avgPnLDiff >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {selectedExperiment.metricDifferences.avgPnLDiff >= 0 ? '+' : ''}
                  {selectedExperiment.metricDifferences.avgPnLDiff.toFixed(2)}%
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
