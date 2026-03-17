import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MarketRegimeIndicator } from './MarketRegimeIndicator';
import { useDashboardStore } from '../stores/dashboardStore';
import type { MarketRegime } from '../types/index';

// Mock the store
vi.mock('../stores/dashboardStore', () => ({
  useDashboardStore: vi.fn(),
}));

// Mock lightweight-charts
vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => ({
    addLineSeries: vi.fn(() => ({
      setData: vi.fn(),
    })),
    timeScale: vi.fn(() => ({
      fitContent: vi.fn(),
    })),
    applyOptions: vi.fn(),
    remove: vi.fn(),
  })),
}));

describe('MarketRegimeIndicator', () => {
  const mockRegime: MarketRegime = {
    symbol: 'BTCUSDT',
    regime: 'TRENDING',
    confidence: 85.5,
    volatilityPercentile: 65.2,
    trendStrength: 72.8,
    timestamp: Date.now(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state when no regime data is available', () => {
    (useDashboardStore as any).mockReturnValue(new Map());

    render(<MarketRegimeIndicator symbol="BTCUSDT" />);

    expect(screen.getByText('Loading market regime...')).toBeInTheDocument();
  });

  it('renders regime badge with correct color for TRENDING', () => {
    const regimeMap = new Map<string, MarketRegime>();
    regimeMap.set('BTCUSDT', mockRegime);
    (useDashboardStore as any).mockReturnValue(regimeMap);

    render(<MarketRegimeIndicator symbol="BTCUSDT" />);

    expect(screen.getByText('TRENDING')).toBeInTheDocument();
    expect(screen.getByText('TRENDING')).toHaveClass('text-blue-400');
  });

  it('renders regime badge with correct color for RANGING', () => {
    const rangingRegime: MarketRegime = {
      ...mockRegime,
      regime: 'RANGING',
    };
    const regimeMap = new Map<string, MarketRegime>();
    regimeMap.set('BTCUSDT', rangingRegime);
    (useDashboardStore as any).mockReturnValue(regimeMap);

    render(<MarketRegimeIndicator symbol="BTCUSDT" />);

    expect(screen.getByText('RANGING')).toBeInTheDocument();
    expect(screen.getByText('RANGING')).toHaveClass('text-yellow-400');
  });

  it('renders regime badge with correct color for VOLATILE', () => {
    const volatileRegime: MarketRegime = {
      ...mockRegime,
      regime: 'VOLATILE',
    };
    const regimeMap = new Map<string, MarketRegime>();
    regimeMap.set('BTCUSDT', volatileRegime);
    (useDashboardStore as any).mockReturnValue(regimeMap);

    render(<MarketRegimeIndicator symbol="BTCUSDT" />);

    expect(screen.getByText('VOLATILE')).toBeInTheDocument();
    expect(screen.getByText('VOLATILE')).toHaveClass('text-red-400');
  });

  it('renders regime badge with correct color for QUIET', () => {
    const quietRegime: MarketRegime = {
      ...mockRegime,
      regime: 'QUIET',
    };
    const regimeMap = new Map<string, MarketRegime>();
    regimeMap.set('BTCUSDT', quietRegime);
    (useDashboardStore as any).mockReturnValue(regimeMap);

    render(<MarketRegimeIndicator symbol="BTCUSDT" />);

    expect(screen.getByText('QUIET')).toBeInTheDocument();
    expect(screen.getByText('QUIET')).toHaveClass('text-gray-400');
  });

  it('displays confidence score as percentage', () => {
    const regimeMap = new Map<string, MarketRegime>();
    regimeMap.set('BTCUSDT', mockRegime);
    (useDashboardStore as any).mockReturnValue(regimeMap);

    render(<MarketRegimeIndicator symbol="BTCUSDT" />);

    expect(screen.getByText('85.5%')).toBeInTheDocument();
    expect(screen.getByText('Confidence')).toBeInTheDocument();
  });

  it('displays volatility percentile', () => {
    const regimeMap = new Map<string, MarketRegime>();
    regimeMap.set('BTCUSDT', mockRegime);
    (useDashboardStore as any).mockReturnValue(regimeMap);

    render(<MarketRegimeIndicator symbol="BTCUSDT" />);

    expect(screen.getByText('65.2%')).toBeInTheDocument();
    expect(screen.getByText('Volatility Percentile')).toBeInTheDocument();
  });

  it('displays trend strength', () => {
    const regimeMap = new Map<string, MarketRegime>();
    regimeMap.set('BTCUSDT', mockRegime);
    (useDashboardStore as any).mockReturnValue(regimeMap);

    render(<MarketRegimeIndicator symbol="BTCUSDT" />);

    expect(screen.getByText('72.8%')).toBeInTheDocument();
    expect(screen.getByText('Trend Strength')).toBeInTheDocument();
  });

  it('displays symbol name', () => {
    const regimeMap = new Map<string, MarketRegime>();
    regimeMap.set('BTCUSDT', mockRegime);
    (useDashboardStore as any).mockReturnValue(regimeMap);

    render(<MarketRegimeIndicator symbol="BTCUSDT" />);

    expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
  });

  it('displays regime history chart title', () => {
    const regimeMap = new Map<string, MarketRegime>();
    regimeMap.set('BTCUSDT', mockRegime);
    (useDashboardStore as any).mockReturnValue(regimeMap);

    render(<MarketRegimeIndicator symbol="BTCUSDT" />);

    expect(screen.getByText('Regime History (24 Hours)')).toBeInTheDocument();
  });

  it('displays legend with all regime types', () => {
    const regimeMap = new Map<string, MarketRegime>();
    regimeMap.set('BTCUSDT', mockRegime);
    (useDashboardStore as any).mockReturnValue(regimeMap);

    render(<MarketRegimeIndicator symbol="BTCUSDT" />);

    expect(screen.getByText('Trending')).toBeInTheDocument();
    expect(screen.getByText('Ranging')).toBeInTheDocument();
    expect(screen.getByText('Volatile')).toBeInTheDocument();
    expect(screen.getByText('Quiet')).toBeInTheDocument();
  });

  it('applies correct volatility bar color for high volatility', () => {
    const highVolRegime: MarketRegime = {
      ...mockRegime,
      volatilityPercentile: 85,
    };
    const regimeMap = new Map<string, MarketRegime>();
    regimeMap.set('BTCUSDT', highVolRegime);
    (useDashboardStore as any).mockReturnValue(regimeMap);

    const { container } = render(<MarketRegimeIndicator symbol="BTCUSDT" />);

    const volatilityBars = container.querySelectorAll('.bg-red-500');
    expect(volatilityBars.length).toBeGreaterThan(0);
  });

  it('applies correct volatility bar color for low volatility', () => {
    const lowVolRegime: MarketRegime = {
      ...mockRegime,
      volatilityPercentile: 20,
    };
    const regimeMap = new Map<string, MarketRegime>();
    regimeMap.set('BTCUSDT', lowVolRegime);
    (useDashboardStore as any).mockReturnValue(regimeMap);

    const { container } = render(<MarketRegimeIndicator symbol="BTCUSDT" />);

    const volatilityBars = container.querySelectorAll('.bg-green-500');
    expect(volatilityBars.length).toBeGreaterThan(0);
  });

  it('applies correct trend strength bar color for strong trend', () => {
    const strongTrendRegime: MarketRegime = {
      ...mockRegime,
      trendStrength: 75,
    };
    const regimeMap = new Map<string, MarketRegime>();
    regimeMap.set('BTCUSDT', strongTrendRegime);
    (useDashboardStore as any).mockReturnValue(regimeMap);

    const { container } = render(<MarketRegimeIndicator symbol="BTCUSDT" />);

    const trendBars = container.querySelectorAll('.bg-blue-500');
    expect(trendBars.length).toBeGreaterThan(0);
  });

  it('applies correct trend strength bar color for weak trend', () => {
    const weakTrendRegime: MarketRegime = {
      ...mockRegime,
      trendStrength: 20,
    };
    const regimeMap = new Map<string, MarketRegime>();
    regimeMap.set('BTCUSDT', weakTrendRegime);
    (useDashboardStore as any).mockReturnValue(regimeMap);

    const { container } = render(<MarketRegimeIndicator symbol="BTCUSDT" />);

    const trendBars = container.querySelectorAll('.bg-gray-500');
    expect(trendBars.length).toBeGreaterThan(0);
  });
});
