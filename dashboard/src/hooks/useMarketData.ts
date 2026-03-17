/**
 * Custom Hook for Market Data with React Query Caching
 */

import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '../services/api';
import type { MarketDataSnapshot } from '../types/index';

/**
 * Fetch market data for all monitored symbols.
 */
export function useMarketData() {
  return useQuery({
    queryKey: ['marketData'],
    queryFn: () => apiRequest<MarketDataSnapshot[]>('/api/market/data'),
    staleTime: 10 * 1000, // 10 seconds for real-time data
    gcTime: 2 * 60 * 1000, // 2 minutes cache
    refetchInterval: 30 * 1000, // Refetch every 30 seconds
  });
}

/**
 * Fetch market data for a specific symbol.
 */
export function useSymbolMarketData(symbol: string) {
  return useQuery({
    queryKey: ['marketData', symbol],
    queryFn: () => apiRequest<MarketDataSnapshot>(`/api/market/${symbol}`),
    staleTime: 10 * 1000,
    gcTime: 2 * 60 * 1000,
    refetchInterval: 30 * 1000,
    enabled: !!symbol,
  });
}

/**
 * Fetch orderbook for a specific symbol.
 */
export function useOrderBook(symbol: string | null) {
  return useQuery({
    queryKey: ['orderbook', symbol],
    queryFn: () => apiRequest(`/api/market/${symbol}/orderbook`),
    staleTime: 5 * 1000, // 5 seconds for orderbook
    gcTime: 1 * 60 * 1000, // 1 minute cache
    refetchInterval: 10 * 1000, // Refetch every 10 seconds
    enabled: !!symbol,
  });
}
