/**
 * Tests for Market Data Hooks with Caching
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMarketData, useSymbolMarketData } from '../useMarketData';
import * as api from '../../services/api';

// Mock API
vi.mock('../../services/api');

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: Infinity,
      },
    },
  });

  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
  
  return Wrapper;
};

describe('useMarketData', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch and cache market data', async () => {
    const mockData = [
      {
        symbol: 'BTCUSDT',
        price: 50000,
        volume24h: 1000000,
        change24h: 2.5,
        bidAskSpread: 0.01,
        cvd: 500,
        timestamp: new Date(),
      },
    ];

    vi.mocked(api.apiRequest).mockResolvedValue(mockData);

    const { result } = renderHook(() => useMarketData(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockData);
    expect(api.apiRequest).toHaveBeenCalledTimes(1);
  });

  it('should use cached data on subsequent renders', async () => {
    const mockData = [
      {
        symbol: 'BTCUSDT',
        price: 50000,
        volume24h: 1000000,
        change24h: 2.5,
        bidAskSpread: 0.01,
        cvd: 500,
        timestamp: new Date(),
      },
    ];

    vi.mocked(api.apiRequest).mockResolvedValue(mockData);

    const wrapper = createWrapper();

    // First render
    const { result: result1 } = renderHook(() => useMarketData(), { wrapper });
    await waitFor(() => expect(result1.current.isSuccess).toBe(true));

    // Second render - should use cache
    const { result: result2 } = renderHook(() => useMarketData(), { wrapper });
    
    // Data should be immediately available from cache
    expect(result2.current.data).toEqual(mockData);
    
    // API should only be called once
    expect(api.apiRequest).toHaveBeenCalledTimes(1);
  });
});

describe('useSymbolMarketData', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch symbol-specific data', async () => {
    const mockData = {
      symbol: 'BTCUSDT',
      price: 50000,
      volume24h: 1000000,
      change24h: 2.5,
      bidAskSpread: 0.01,
      cvd: 500,
      timestamp: new Date(),
    };

    vi.mocked(api.apiRequest).mockResolvedValue(mockData);

    const { result } = renderHook(() => useSymbolMarketData('BTCUSDT'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockData);
    expect(api.apiRequest).toHaveBeenCalledWith('/api/market/BTCUSDT');
  });

  it('should not fetch when symbol is empty', () => {
    const { result } = renderHook(() => useSymbolMarketData(''), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.fetchStatus).toBe('idle');
  });
});
