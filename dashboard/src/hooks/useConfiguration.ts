/**
 * Custom Hooks for Configuration with React Query Caching and LocalStorage
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '../services/api';
import { setCache, getCache, CACHE_KEYS } from '../lib/localStorage';
import type { FeatureFlags } from '../types/index';

/**
 * Fetch feature flags with localStorage caching.
 */
export function useFeatureFlags() {
  return useQuery({
    queryKey: ['config', 'featureFlags'],
    queryFn: async () => {
      // Try localStorage first
      const cached = getCache<FeatureFlags>(CACHE_KEYS.FEATURE_FLAGS);
      if (cached) return cached;
      
      // Fetch from API
      const data = await apiRequest<FeatureFlags>('/api/config/feature-flags');
      
      // Cache in localStorage (24 hours)
      setCache(CACHE_KEYS.FEATURE_FLAGS, data, 24 * 60 * 60 * 1000);
      
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes cache
  });
}

/**
 * Update feature flags.
 */
export function useUpdateFeatureFlags() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (update: { flagName: string; enabled: boolean }) =>
      apiRequest('/api/config/feature-flags', {
        method: 'PUT',
        body: JSON.stringify(update),
      }),
    onSuccess: (data) => {
      // Update cache
      queryClient.setQueryData(['config', 'featureFlags'], data);
      setCache(CACHE_KEYS.FEATURE_FLAGS, data, 24 * 60 * 60 * 1000);
    },
  });
}

/**
 * Fetch strategy parameters with localStorage caching.
 */
export function useStrategyParameters() {
  return useQuery({
    queryKey: ['config', 'strategyParameters'],
    queryFn: async () => {
      const cached = getCache<Record<string, any>>(CACHE_KEYS.CONFIGURATION);
      if (cached) return cached;
      
      const data = await apiRequest<Record<string, any>>('/api/config/strategy-params');
      setCache(CACHE_KEYS.CONFIGURATION, data, 24 * 60 * 60 * 1000);
      
      return data;
    },
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });
}

/**
 * Update strategy parameters.
 */
export function useUpdateStrategyParameters() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (parameters: Record<string, any>) =>
      apiRequest('/api/config/strategy-params', {
        method: 'PUT',
        body: JSON.stringify({ parameters }),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(['config', 'strategyParameters'], data);
      setCache(CACHE_KEYS.CONFIGURATION, data, 24 * 60 * 60 * 1000);
    },
  });
}

/**
 * Fetch risk settings.
 */
export function useRiskSettings() {
  return useQuery({
    queryKey: ['config', 'riskSettings'],
    queryFn: () => apiRequest<Record<string, any>>('/api/config/risk-settings'),
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });
}

/**
 * Update risk settings.
 */
export function useUpdateRiskSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (settings: Record<string, any>) =>
      apiRequest('/api/config/risk-settings', {
        method: 'PUT',
        body: JSON.stringify(settings),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(['config', 'riskSettings'], data);
    },
  });
}

/**
 * Fetch monitored symbols with localStorage caching.
 */
export function useMonitoredSymbols() {
  return useQuery({
    queryKey: ['config', 'symbols'],
    queryFn: async () => {
      const cached = getCache<string[]>(CACHE_KEYS.SYMBOLS);
      if (cached) return cached;
      
      const data = await apiRequest<string[]>('/api/market/symbols');
      setCache(CACHE_KEYS.SYMBOLS, data, 24 * 60 * 60 * 1000);
      
      return data;
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 60 * 60 * 1000, // 1 hour cache
  });
}
