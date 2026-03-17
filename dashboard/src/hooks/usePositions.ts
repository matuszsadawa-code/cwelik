/**
 * Custom Hook for Open Positions with React Query Caching
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '../services/api';
import type { Position } from '../types/index';

/**
 * Fetch all open positions.
 */
export function useOpenPositions() {
  return useQuery({
    queryKey: ['positions', 'open'],
    queryFn: () => apiRequest<Position[]>('/api/positions/open'),
    staleTime: 15 * 1000, // 15 seconds
    gcTime: 3 * 60 * 1000, // 3 minutes cache
    refetchInterval: 30 * 1000, // Refetch every 30 seconds
  });
}

/**
 * Close a position manually.
 */
export function useClosePosition() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (positionId: string) =>
      apiRequest(`/api/positions/${positionId}/close`, { method: 'POST' }),
    onSuccess: () => {
      // Invalidate positions query to refetch
      queryClient.invalidateQueries({ queryKey: ['positions', 'open'] });
    },
  });
}
