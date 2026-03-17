/**
 * Custom Hooks for Backtesting with React Query Caching
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchBacktestRuns, fetchBacktestResults, fetchBacktestComparison } from '../services/api';
import type { BacktestRun, BacktestResults, BacktestComparison } from '../types/index';

/**
 * Fetch list of backtest runs.
 */
export function useBacktestRuns() {
  return useQuery({
    queryKey: ['backtest', 'runs'],
    queryFn: fetchBacktestRuns,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes cache
  });
}

/**
 * Fetch backtest results by run ID.
 */
export function useBacktestResults(runId: string | null) {
  return useQuery({
    queryKey: ['backtest', 'results', runId],
    queryFn: () => {
      if (!runId) throw new Error('Run ID is required');
      return fetchBacktestResults(runId);
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 60 * 60 * 1000, // 1 hour cache
    enabled: !!runId,
  });
}

/**
 * Fetch backtest comparison.
 */
export function useBacktestComparison(runIds: string[]) {
  return useQuery({
    queryKey: ['backtest', 'comparison', runIds.sort().join(',')],
    queryFn: () => fetchBacktestComparison(runIds),
    staleTime: 10 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    enabled: runIds.length > 0,
  });
}
