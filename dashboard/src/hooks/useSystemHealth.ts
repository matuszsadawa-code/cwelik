/**
 * Custom Hook for System Health with React Query Caching
 */

import { useQuery } from '@tanstack/react-query';
import { fetchSystemHealth } from '../services/api';
import type { SystemHealthData } from '../types/index';

/**
 * Fetch system health metrics.
 */
export function useSystemHealth() {
  return useQuery({
    queryKey: ['system', 'health'],
    queryFn: fetchSystemHealth,
    staleTime: 15 * 1000, // 15 seconds
    gcTime: 2 * 60 * 1000, // 2 minutes cache
    refetchInterval: 30 * 1000, // Refetch every 30 seconds
  });
}
