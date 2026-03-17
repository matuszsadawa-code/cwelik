/**
 * Custom Hooks for Trade History with React Query Caching
 */

import { useQuery } from '@tanstack/react-query';
import { fetchTradeHistory, fetchTradeDetail } from '../services/api';
import type { TradeHistoryResponse, Trade, TradeFilters } from '../types/index';

/**
 * Fetch trade history with pagination and filters.
 */
export function useTradeHistory(
  page: number = 1,
  pageSize: number = 50,
  filters?: TradeFilters,
  sortBy?: string,
  sortOrder: 'asc' | 'desc' = 'desc'
) {
  return useQuery<TradeHistoryResponse, Error>({
    queryKey: ['trades', 'history', page, pageSize, filters, sortBy, sortOrder],
    queryFn: () => fetchTradeHistory(page, pageSize, filters, sortBy, sortOrder),
    staleTime: 60 * 1000, // 1 minute
    gcTime: 10 * 60 * 1000, // 10 minutes cache
    placeholderData: (previousData) => previousData, // Keep previous page data while fetching new page
  });
}

/**
 * Fetch trade detail by ID.
 */
export function useTradeDetail(tradeId: string | null) {
  return useQuery({
    queryKey: ['trades', tradeId],
    queryFn: () => {
      if (!tradeId) throw new Error('Trade ID is required');
      return fetchTradeDetail(tradeId);
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes cache
    enabled: !!tradeId,
  });
}
