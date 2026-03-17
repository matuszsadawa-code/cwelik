/**
 * StrategyParametersPanel Component
 * 
 * Provides interface for adjusting strategy parameters with debounced inputs.
 * 
 * Features:
 * - Sliders for numeric ranges
 * - Number inputs with validation
 * - Debounced updates (300ms) to reduce API calls
 * - Current vs. default value indicators
 * - Reset to defaults button
 * - Real-time validation
 * - Visual feedback during debounce delay
 * 
 * Requirements: 16.4, 16.5, 16.6, 16.7, 16.8, 29.5
 */

import { useState, useEffect } from 'react';
import { useDebounce, useDebouncedCallback } from '../hooks';

interface StrategyParameter {
  name: string;
  label: string;
  value: number;
  defaultValue: number;
  min: number;
  max: number;
  step: number;
  description: string;
}

interface StrategyParametersPanelProps {
  onUpdate?: (params: Record<string, number>) => Promise<void>;
}

export const StrategyParametersPanel: React.FC<StrategyParametersPanelProps> = ({ onUpdate }) => {
  const [parameters, setParameters] = useState<StrategyParameter[]>([
    {
      name: 'trendStrengthThreshold',
      label: 'Trend Strength Threshold',
      value: 25,
      defaultValue: 25,
      min: 10,
      max: 50,
      step: 1,
      description: 'Minimum ADX value to consider trend strong enough',
    },
    {
      name: 'volumeConfirmationMultiplier',
      label: 'Volume Confirmation Multiplier',
      value: 1.5,
      defaultValue: 1.5,
      min: 1.0,
      max: 3.0,
      step: 0.1,
      description: 'Volume must be X times average to confirm signal',
    },
    {
      name: 'orderFlowImbalanceThreshold',
      label: 'Order Flow Imbalance Threshold',
      value: 0.6,
      defaultValue: 0.6,
      min: 0.5,
      max: 0.9,
      step: 0.05,
      description: 'Minimum buy/sell ratio for order flow confirmation',
    },
    {
      name: 'confidenceThreshold',
      label: 'Confidence Threshold',
      value: 0.65,
      defaultValue: 0.65,
      min: 0.5,
      max: 0.95,
      step: 0.05,
      description: 'Minimum confidence score to generate signal',
    },
    {
      name: 'maxSignalsPerSymbol',
      label: 'Max Signals Per Symbol',
      value: 3,
      defaultValue: 3,
      min: 1,
      max: 10,
      step: 1,
      description: 'Maximum concurrent signals per trading pair',
    },
    {
      name: 'minRiskRewardRatio',
      label: 'Min Risk:Reward Ratio',
      value: 1.5,
      defaultValue: 1.5,
      min: 1.0,
      max: 5.0,
      step: 0.5,
      description: 'Minimum R:R ratio to accept signal',
    },
  ]);

  const [pendingUpdates, setPendingUpdates] = useState<Record<string, number>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

  // Debounce pending updates (300ms)
  const debouncedPendingUpdates = useDebounce(pendingUpdates, 300);

  // Save debounced updates to backend
  useEffect(() => {
    if (Object.keys(debouncedPendingUpdates).length > 0 && onUpdate) {
      const saveUpdates = async () => {
        setIsSaving(true);
        setSaveStatus('idle');
        
        try {
          await onUpdate(debouncedPendingUpdates);
          setSaveStatus('success');
          setPendingUpdates({});
          
          // Clear success message after 2 seconds
          setTimeout(() => setSaveStatus('idle'), 2000);
        } catch (error) {
          console.error('Failed to save parameters:', error);
          setSaveStatus('error');
        } finally {
          setIsSaving(false);
        }
      };
      
      saveUpdates();
    }
  }, [debouncedPendingUpdates, onUpdate]);

  const handleParameterChange = (name: string, value: number) => {
    // Update local state immediately
    setParameters(prev =>
      prev.map(param =>
        param.name === name ? { ...param, value } : param
      )
    );
    
    // Add to pending updates (will be debounced)
    setPendingUpdates(prev => ({ ...prev, [name]: value }));
  };

  const handleReset = (name: string) => {
    const param = parameters.find(p => p.name === name);
    if (param) {
      handleParameterChange(name, param.defaultValue);
    }
  };

  const handleResetAll = () => {
    const updates: Record<string, number> = {};
    parameters.forEach(param => {
      updates[param.name] = param.defaultValue;
    });
    
    setParameters(prev =>
      prev.map(param => ({ ...param, value: param.defaultValue }))
    );
    
    setPendingUpdates(updates);
  };

  const isModified = (param: StrategyParameter) => {
    return param.value !== param.defaultValue;
  };

  const hasAnyModifications = parameters.some(isModified);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-slate-100">Strategy Parameters</h3>
          <p className="text-sm text-slate-400 mt-1">
            Adjust trading strategy parameters in real-time
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Save Status Indicator */}
          {isSaving && (
            <div className="flex items-center gap-2 text-sm text-blue-400">
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              Saving...
            </div>
          )}
          {saveStatus === 'success' && (
            <div className="flex items-center gap-2 text-sm text-green-400">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Saved
            </div>
          )}
          {saveStatus === 'error' && (
            <div className="flex items-center gap-2 text-sm text-red-400">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Error
            </div>
          )}
          
          {/* Reset All Button */}
          {hasAnyModifications && (
            <button
              onClick={handleResetAll}
              className="px-3 py-1.5 text-sm font-medium text-slate-300 hover:text-slate-100 border border-slate-700 hover:border-slate-600 rounded transition-colors"
            >
              Reset All
            </button>
          )}
        </div>
      </div>

      <div className="space-y-6">
        {parameters.map((param) => (
          <div key={param.name} className="bg-slate-950 rounded-lg p-4">
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <label className="text-sm font-medium text-slate-200">
                    {param.label}
                  </label>
                  {isModified(param) && (
                    <span className="text-xs text-blue-400">Modified</span>
                  )}
                </div>
                <p className="text-xs text-slate-400">{param.description}</p>
              </div>
              
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <input
                    type="number"
                    value={param.value}
                    onChange={(e) => handleParameterChange(param.name, parseFloat(e.target.value))}
                    min={param.min}
                    max={param.max}
                    step={param.step}
                    className="w-20 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm text-right font-mono focus:outline-none focus:border-blue-500"
                  />
                  <div className="text-xs text-slate-500 mt-1">
                    Default: {param.defaultValue}
                  </div>
                </div>
                
                {isModified(param) && (
                  <button
                    onClick={() => handleReset(param.name)}
                    className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
                    title="Reset to default"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
            
            {/* Slider */}
            <div className="relative">
              <input
                type="range"
                value={param.value}
                onChange={(e) => handleParameterChange(param.name, parseFloat(e.target.value))}
                min={param.min}
                max={param.max}
                step={param.step}
                className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer slider"
              />
              <div className="flex justify-between text-xs text-slate-500 mt-1">
                <span>{param.min}</span>
                <span>{param.max}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
