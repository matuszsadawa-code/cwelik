/**
 * DebouncingExample Component
 * 
 * Demonstrates the debouncing implementation with visual feedback.
 * This is an educational component showing how debouncing works.
 */

import { useState } from 'react';
import { useDebounce, useDebouncedCallback } from '../hooks';

export const DebouncingExample: React.FC = () => {
  const [searchValue, setSearchValue] = useState('');
  const [callbackValue, setCallbackValue] = useState('');
  const [apiCallCount, setApiCallCount] = useState(0);
  const [debouncedCallCount, setDebouncedCallCount] = useState(0);

  // useDebounce example
  const debouncedSearchValue = useDebounce(searchValue, 300);

  // useDebouncedCallback example
  const handleDebouncedChange = useDebouncedCallback((value: string) => {
    setCallbackValue(value);
    setDebouncedCallCount(prev => prev + 1);
  }, 300);

  const handleSearchChange = (value: string) => {
    setSearchValue(value);
    setApiCallCount(prev => prev + 1);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-slate-100 mb-6">Debouncing Examples</h2>

      <div className="space-y-8">
        {/* useDebounce Example */}
        <div className="bg-slate-950 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">
            1. useDebounce Hook
          </h3>
          <p className="text-sm text-slate-400 mb-4">
            Type in the input below. The debounced value updates 300ms after you stop typing.
          </p>

          <div className="space-y-4">
            <div className="relative">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Search Input
              </label>
              <input
                type="text"
                value={searchValue}
                onChange={(e) => handleSearchChange(e.target.value)}
                placeholder="Type something..."
                className="w-full bg-slate-800 border border-slate-700 rounded px-4 py-2 text-slate-100 focus:outline-none focus:border-blue-500"
              />
              {searchValue !== debouncedSearchValue && (
                <div className="absolute right-3 top-10">
                  <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-900 rounded p-4">
                <div className="text-xs text-slate-400 mb-1">Immediate Value</div>
                <div className="text-lg font-mono text-slate-100">
                  {searchValue || '(empty)'}
                </div>
                <div className="text-xs text-slate-500 mt-2">
                  Updates: {apiCallCount}
                </div>
              </div>

              <div className="bg-slate-900 rounded p-4">
                <div className="text-xs text-slate-400 mb-1">Debounced Value (300ms)</div>
                <div className="text-lg font-mono text-green-400">
                  {debouncedSearchValue || '(empty)'}
                </div>
                <div className="text-xs text-slate-500 mt-2">
                  API Calls: {debouncedSearchValue ? 1 : 0}
                </div>
              </div>
            </div>

            <div className="bg-blue-500/10 border border-blue-500/30 rounded p-3">
              <div className="text-sm text-blue-300">
                <strong>Savings:</strong> Without debouncing, you would make{' '}
                <span className="font-bold">{apiCallCount}</span> API calls. With debouncing,
                you only make <span className="font-bold">1</span> call.
                {apiCallCount > 1 && (
                  <span className="text-green-400 font-semibold">
                    {' '}That's {Math.round((1 - 1/apiCallCount) * 100)}% fewer calls!
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* useDebouncedCallback Example */}
        <div className="bg-slate-950 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">
            2. useDebouncedCallback Hook
          </h3>
          <p className="text-sm text-slate-400 mb-4">
            Type in the input below. The callback fires 300ms after you stop typing.
          </p>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Callback Input
              </label>
              <input
                type="text"
                onChange={(e) => handleDebouncedChange(e.target.value)}
                placeholder="Type something..."
                className="w-full bg-slate-800 border border-slate-700 rounded px-4 py-2 text-slate-100 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div className="bg-slate-900 rounded p-4">
              <div className="text-xs text-slate-400 mb-1">Callback Result</div>
              <div className="text-lg font-mono text-green-400">
                {callbackValue || '(waiting for input)'}
              </div>
              <div className="text-xs text-slate-500 mt-2">
                Callback executions: {debouncedCallCount}
              </div>
            </div>
          </div>
        </div>

        {/* Real-World Use Cases */}
        <div className="bg-slate-950 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">
            Real-World Use Cases
          </h3>
          
          <div className="space-y-3 text-sm">
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 bg-green-500 rounded-full mt-1.5"></div>
              <div>
                <div className="text-slate-200 font-medium">Search Inputs</div>
                <div className="text-slate-400">
                  TradeTable, SymbolPerformanceTable - Reduces API calls by ~90%
                </div>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-2 h-2 bg-green-500 rounded-full mt-1.5"></div>
              <div>
                <div className="text-slate-200 font-medium">Filter Controls</div>
                <div className="text-slate-400">
                  ActiveSignalsPanel - Smooth filtering without performance impact
                </div>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-2 h-2 bg-green-500 rounded-full mt-1.5"></div>
              <div>
                <div className="text-slate-200 font-medium">Configuration Parameters</div>
                <div className="text-slate-400">
                  StrategyParametersPanel - Batches slider changes, reduces API calls by ~95%
                </div>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-2 h-2 bg-green-500 rounded-full mt-1.5"></div>
              <div>
                <div className="text-slate-200 font-medium">Form Validation</div>
                <div className="text-slate-400">
                  Delays expensive validation until user stops typing
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Performance Tips */}
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-300 mb-4">
            Performance Tips
          </h3>
          
          <ul className="space-y-2 text-sm text-blue-200">
            <li className="flex items-start gap-2">
              <span className="text-blue-400">•</span>
              <span>Use 300ms delay for most inputs (balances responsiveness and efficiency)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-400">•</span>
              <span>Always provide visual feedback (spinners, "Saving..." indicators)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-400">•</span>
              <span>Update UI immediately, debounce only API calls and expensive operations</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-400">•</span>
              <span>Combine with useMemo for filtered/sorted data to prevent unnecessary recalculations</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};
