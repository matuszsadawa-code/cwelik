/**
 * Custom Hook for Active Signals with React Query Caching
 */

import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '../services/api';
import type { Signal } from '../types/index';

/**
 * Fetch all active signals.
 */
export function useActiveSignals() {
  return useQuery({
    queryKey: ['signals', 'active'],
    queryFn: () => apiRequest<Signal[]>('/api/signals/active'),
    staleTime: 15 * 1000, // 15 seconds
    gcTime: 3 * 60 * 1000, // 3 minutes cache
    refetchInterval: 30 * 1000, // Refetch every 30 seconds
  });
}

/**
 * Fetch signal details by ID.
 */
export function useSignalDetail(signalId: string | null) {
  return useQuery({
    queryKey: ['signals', signalId],
    queryFn: () => apiRequest<Signal>(`/api/signals/${signalId}`),
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
    enabled: !!signalId,
  });
}
