/**
 * Custom Hook for Performance Metrics with React Query Caching
 */

import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '../services/api';
import type { PerformanceMetrics } from '../types/index';

/**
 * Fetch real-time performance metrics.
 */
export function usePerformanceMetrics() {
  return useQuery({
    queryKey: ['performance', 'metrics'],
    queryFn: () => apiRequest<PerformanceMetrics>('/api/analytics/metrics'),
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes cache
    refetchInterval: 30 * 1000, // Refetch every 30 seconds
  });
}
