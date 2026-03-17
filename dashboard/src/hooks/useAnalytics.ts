/**
 * Custom Hooks for Analytics Data with React Query Caching
 */

import { useQuery } from '@tanstack/react-query';
import {
  fetchEquityCurve,
  fetchPnLBreakdown,
  fetchSymbolPerformance,
  fetchSymbolPnL,
  fetchMultiSymbolPnL,
  fetchRiskMetrics,
  fetchQualityAnalysis,
  fetchRRDistribution,
} from '../services/api';
import type {
  EquityCurveData,
  PnLBreakdownData,
  SymbolMetrics,
  SymbolPnLData,
  MultiSymbolPnLData,
  RiskMetrics,
  QualityAnalysisData,
  RRDistributionData,
  TimeRange,
} from '../types/index';
import { chartCache, generateChartCacheKey } from '../lib/chartCache';

/**
 * Fetch equity curve data with chart caching.
 */
export function useEquityCurve(timeRange: TimeRange = '7d') {
  return useQuery({
    queryKey: ['analytics', 'equityCurve', timeRange],
    queryFn: async () => {
      const cacheKey = generateChartCacheKey('equityCurve', undefined, timeRange);
      
      // Check chart cache first
      const cached = chartCache.get<EquityCurveData>(cacheKey);
      if (cached) return cached;
      
      // Fetch from API
      const data = await fetchEquityCurve(timeRange);
      
      // Store in chart cache
      chartCache.set(cacheKey, data);
      
      return data;
    },
    staleTime: 60 * 1000, // 1 minute
    gcTime: 10 * 60 * 1000, // 10 minutes cache
  });
}

/**
 * Fetch PnL breakdown data with chart caching.
 */
export function usePnLBreakdown(timeRange: TimeRange = 'all') {
  return useQuery({
    queryKey: ['analytics', 'pnlBreakdown', timeRange],
    queryFn: async () => {
      const cacheKey = generateChartCacheKey('pnlBreakdown', undefined, timeRange);
      
      const cached = chartCache.get<PnLBreakdownData>(cacheKey);
      if (cached) return cached;
      
      const data = await fetchPnLBreakdown(timeRange);
      chartCache.set(cacheKey, data);
      
      return data;
    },
    staleTime: 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}

/**
 * Fetch symbol performance statistics.
 */
export function useSymbolPerformance() {
  return useQuery({
    queryKey: ['analytics', 'symbolPerformance'],
    queryFn: fetchSymbolPerformance,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000,
  });
}

/**
 * Fetch per-symbol PnL data with chart caching.
 */
export function useSymbolPnL(symbol: string | null) {
  return useQuery({
    queryKey: ['analytics', 'symbolPnL', symbol],
    queryFn: async () => {
      if (!symbol) throw new Error('Symbol is required');
      
      const cacheKey = generateChartCacheKey('symbolPnL', symbol);
      
      const cached = chartCache.get<SymbolPnLData>(cacheKey);
      if (cached) return cached;
      
      const data = await fetchSymbolPnL(symbol);
      chartCache.set(cacheKey, data);
      
      return data;
    },
    staleTime: 60 * 1000,
    gcTime: 10 * 60 * 1000,
    enabled: !!symbol,
  });
}

/**
 * Fetch multi-symbol PnL comparison with chart caching.
 */
export function useMultiSymbolPnL(symbols: string[]) {
  return useQuery({
    queryKey: ['analytics', 'multiSymbolPnL', symbols.sort().join(',')],
    queryFn: async () => {
      const cacheKey = generateChartCacheKey('multiSymbolPnL', symbols.sort().join(','));
      
      const cached = chartCache.get<MultiSymbolPnLData>(cacheKey);
      if (cached) return cached;
      
      const data = await fetchMultiSymbolPnL(symbols);
      chartCache.set(cacheKey, data);
      
      return data;
    },
    staleTime: 60 * 1000,
    gcTime: 10 * 60 * 1000,
    enabled: symbols.length > 0 && symbols.length <= 4,
  });
}

/**
 * Fetch risk-adjusted return metrics.
 */
export function useRiskMetrics() {
  return useQuery({
    queryKey: ['analytics', 'riskMetrics'],
    queryFn: fetchRiskMetrics,
    staleTime: 2 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}

/**
 * Fetch quality grade analysis with chart caching.
 */
export function useQualityAnalysis() {
  return useQuery({
    queryKey: ['analytics', 'qualityAnalysis'],
    queryFn: async () => {
      const cacheKey = generateChartCacheKey('qualityAnalysis');
      
      const cached = chartCache.get<QualityAnalysisData>(cacheKey);
      if (cached) return cached;
      
      const data = await fetchQualityAnalysis();
      chartCache.set(cacheKey, data);
      
      return data;
    },
    staleTime: 2 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}

/**
 * Fetch R:R distribution with chart caching.
 */
export function useRRDistribution() {
  return useQuery({
    queryKey: ['analytics', 'rrDistribution'],
    queryFn: async () => {
      const cacheKey = generateChartCacheKey('rrDistribution');
      
      const cached = chartCache.get<RRDistributionData>(cacheKey);
      if (cached) return cached;
      
      const data = await fetchRRDistribution();
      chartCache.set(cacheKey, data);
      
      return data;
    },
    staleTime: 2 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}
