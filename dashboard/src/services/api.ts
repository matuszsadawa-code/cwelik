/**
 * API Service for OpenClaw Trading Dashboard
 * 
 * Provides helper functions for making API requests to the backend.
 */

import type { EquityCurveData, PnLBreakdownData, TimeRange, SymbolMetrics } from '../types/index';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Fetch equity curve data from the backend API.
 * 
 * @param timeRange - Time range filter (1d, 7d, 30d, 90d, 1y, all)
 * @returns Promise resolving to equity curve data
 */
export async function fetchEquityCurve(timeRange: TimeRange = '7d'): Promise<EquityCurveData> {
  const response = await fetch(`${API_BASE_URL}/api/analytics/equity-curve?time_range=${timeRange}`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch equity curve: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Fetch PnL breakdown data from the backend API.
 * 
 * @param timeRange - Time range filter (1d, 7d, 30d, 90d, 1y, all)
 * @returns Promise resolving to PnL breakdown data
 */
export async function fetchPnLBreakdown(timeRange: TimeRange = 'all'): Promise<PnLBreakdownData> {
  const response = await fetch(`${API_BASE_URL}/api/analytics/pnl-breakdown?time_range=${timeRange}`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch PnL breakdown: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Fetch symbol performance statistics from the backend API.
 * 
 * @returns Promise resolving to array of symbol metrics
 */
export async function fetchSymbolPerformance(): Promise<SymbolMetrics[]> {
  const response = await fetch(`${API_BASE_URL}/api/analytics/symbol-performance`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch symbol performance: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.symbols || [];
}

/**
 * Generic API request helper with error handling.
 * 
 * @param endpoint - API endpoint path
 * @param options - Fetch options
 * @returns Promise resolving to response data
 */
export async function apiRequest<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API request failed: ${response.status} ${response.statusText} - ${errorText}`);
  }
  
  return response.json();
}


/**
 * Fetch per-symbol PnL data from the backend API.
 * 
 * @param symbol - Symbol name (e.g., "BTCUSDT")
 * @returns Promise resolving to symbol PnL data
 */
export async function fetchSymbolPnL(symbol: string): Promise<import('../types/index').SymbolPnLData> {
  const response = await fetch(`${API_BASE_URL}/api/analytics/symbol-pnl/${symbol}`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch symbol PnL: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Fetch PnL data for multiple symbols for comparison.
 * 
 * @param symbols - Array of symbol names (max 4)
 * @returns Promise resolving to multi-symbol PnL data
 */
export async function fetchMultiSymbolPnL(symbols: string[]): Promise<import('../types/index').MultiSymbolPnLData> {
  if (symbols.length > 4) {
    throw new Error('Maximum 4 symbols allowed for comparison');
  }
  
  const symbolsParam = symbols.join(',');
  const response = await fetch(`${API_BASE_URL}/api/analytics/symbol-pnl-multi?symbols=${symbolsParam}`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch multi-symbol PnL: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Fetch risk-adjusted return metrics from the backend API.
 * 
 * @returns Promise resolving to risk metrics data
 */
export async function fetchRiskMetrics(): Promise<import('../types/index').RiskMetrics> {
  const response = await fetch(`${API_BASE_URL}/api/analytics/risk-metrics`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch risk metrics: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Fetch quality grade analysis from the backend API.
 * 
 * @returns Promise resolving to quality analysis data
 */
export async function fetchQualityAnalysis(): Promise<import('../types/index').QualityAnalysisData> {
  const response = await fetch(`${API_BASE_URL}/api/analytics/quality-analysis`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch quality analysis: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Fetch R:R distribution from the backend API.
 * 
 * @returns Promise resolving to R:R distribution data
 */
export async function fetchRRDistribution(): Promise<import('../types/index').RRDistributionData> {
  const response = await fetch(`${API_BASE_URL}/api/analytics/rr-distribution`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch R:R distribution: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Fetch system health metrics from the backend API.
 * 
 * @returns Promise resolving to system health data
 */
export async function fetchSystemHealth(): Promise<import('../types/index').SystemHealthData> {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch system health: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Fetch trade history with pagination and filters.
 * 
 * @param page - Page number (1-indexed)
 * @param pageSize - Number of trades per page
 * @param filters - Optional filters (symbol, date range, outcome, quality)
 * @param sortBy - Column to sort by
 * @param sortOrder - Sort order (asc or desc)
 * @returns Promise resolving to trade history response
 */
export async function fetchTradeHistory(
  page: number = 1,
  pageSize: number = 50,
  filters?: import('../types/index').TradeFilters,
  sortBy?: string,
  sortOrder: 'asc' | 'desc' = 'desc'
): Promise<import('../types/index').TradeHistoryResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  });
  
  if (filters?.symbol) params.append('symbol', filters.symbol);
  if (filters?.startDate) params.append('start_date', filters.startDate);
  if (filters?.endDate) params.append('end_date', filters.endDate);
  if (filters?.outcome) params.append('outcome', filters.outcome);
  if (filters?.quality) params.append('quality', filters.quality);
  if (sortBy) params.append('sort_by', sortBy);
  if (sortOrder) params.append('sort_order', sortOrder);
  
  const response = await fetch(`${API_BASE_URL}/api/trades/history?${params}`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch trade history: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Fetch detailed information for a specific trade.
 * 
 * @param tradeId - Trade ID
 * @returns Promise resolving to trade details
 */
export async function fetchTradeDetail(tradeId: string): Promise<import('../types/index').Trade> {
  const response = await fetch(`${API_BASE_URL}/api/trades/${tradeId}`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch trade detail: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Export trades to CSV or JSON format.
 * 
 * @param format - Export format (csv or json)
 * @param startDate - Start date (YYYY-MM-DD)
 * @param endDate - End date (YYYY-MM-DD)
 * @returns Promise resolving to blob for download
 */
export async function exportTrades(
  format: 'csv' | 'json',
  startDate?: string,
  endDate?: string
): Promise<Blob> {
  const params = new URLSearchParams({ format });
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  
  const response = await fetch(`${API_BASE_URL}/api/trades/export?${params}`);
  
  if (!response.ok) {
    throw new Error(`Failed to export trades: ${response.statusText}`);
  }
  
  return response.blob();
}

/**
 * Fetch list of backtest runs.
 * 
 * @returns Promise resolving to array of backtest runs
 */
export async function fetchBacktestRuns(): Promise<import('../types/index').BacktestRun[]> {
  const response = await fetch(`${API_BASE_URL}/api/backtest/runs`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch backtest runs: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Fetch detailed results for a specific backtest run.
 * 
 * @param runId - Backtest run ID
 * @returns Promise resolving to backtest results
 */
export async function fetchBacktestResults(runId: string): Promise<import('../types/index').BacktestResults> {
  const response = await fetch(`${API_BASE_URL}/api/backtest/runs/${runId}`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch backtest results: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Fetch comparison of multiple backtest runs with live performance.
 * 
 * @param runIds - Array of backtest run IDs to compare
 * @returns Promise resolving to backtest comparison data
 */
export async function fetchBacktestComparison(runIds: string[]): Promise<import('../types/index').BacktestComparison> {
  const params = new URLSearchParams({ run_ids: runIds.join(',') });
  const response = await fetch(`${API_BASE_URL}/api/backtest/compare?${params}`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch backtest comparison: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Fetch list of A/B testing experiments.
 * 
 * @returns Promise resolving to array of experiments
 */
export async function fetchExperiments(): Promise<import('../types/index').Experiment[]> {
  const response = await fetch(`${API_BASE_URL}/api/experiments`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch experiments: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Fetch detailed results for a specific experiment.
 * 
 * @param experimentId - Experiment ID
 * @returns Promise resolving to experiment details
 */
export async function fetchExperimentDetail(experimentId: string): Promise<import('../types/index').Experiment> {
  const response = await fetch(`${API_BASE_URL}/api/experiments/${experimentId}`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch experiment detail: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Stop an A/B testing experiment early.
 * 
 * @param experimentId - Experiment ID
 * @returns Promise resolving when experiment is stopped
 */
export async function stopExperiment(experimentId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/experiments/${experimentId}/stop`, {
    method: 'POST',
  });
  
  if (!response.ok) {
    throw new Error(`Failed to stop experiment: ${response.statusText}`);
  }
}

/**
 * Export performance report in specified format.
 * 
 * @param request - Report export request with format, date range, and sections
 * @returns Promise resolving to blob for download
 */
export async function exportReport(request: import('../types/index').ReportExportRequest): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/export/report`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Failed to export report: ${response.statusText}`);
  }
  
  return response.blob();
}
