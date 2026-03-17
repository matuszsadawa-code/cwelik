import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { LiquidityZonesChart } from './LiquidityZonesChart';
import type { LiquidityZone } from '../types/index';

// Mock TradingView Lightweight Charts
vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => ({
    addSeries: vi.fn(() => ({
      setData: vi.fn(),
      createPriceLine: vi.fn(),
    })),
    timeScale: vi.fn(() => ({
      fitContent: vi.fn(),
    })),
    applyOptions: vi.fn(),
    remove: vi.fn(),
  })),
}));

describe('LiquidityZonesChart', () => {
  const mockLiquidityZones: LiquidityZone[] = [
    {
      symbol: 'BTCUSDT',
      priceLevel: 51200,
      type: 'resistance',
      strength: 'high',
      liquidityAmount: 2500000,
      isNearPrice: false,
    },
    {
      symbol: 'BTCUSDT',
      priceLevel: 50500,
      type: 'support',
      strength: 'high',
      liquidityAmount: 3200000,
      isNearPrice: true,
    },
    {
      symbol: 'BTCUSDT',
      priceLevel: 49800,
      type: 'support',
      strength: 'medium',
      liquidityAmount: 1800000,
      isNearPrice: false,
    },
  ];

  it('renders component with symbol and current price', () => {
    render(
      <LiquidityZonesChart
        symbol="BTCUSDT"
        liquidityZones={mockLiquidityZones}
        currentPrice={50450}
      />
    );

    expect(screen.getByText('Liquidity Zones')).toBeInTheDocument();
    expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
    expect(screen.getByText('$50450.00')).toBeInTheDocument();
  });

  it('displays all liquidity zones in the list', () => {
    render(
      <LiquidityZonesChart
        symbol="BTCUSDT"
        liquidityZones={mockLiquidityZones}
        currentPrice={50450}
      />
    );

    expect(screen.getByText(/resistance.*Zone/i)).toBeInTheDocument();
    expect(screen.getAllByText(/support.*Zone/i)).toHaveLength(2);
  });

  it('highlights zones near current price', () => {
    render(
      <LiquidityZonesChart
        symbol="BTCUSDT"
        liquidityZones={mockLiquidityZones}
        currentPrice={50450}
      />
    );

    // Zone with isNearPrice: true should show indicator
    expect(screen.getByText('Price within 0.5%')).toBeInTheDocument();
  });

  it('displays liquidity amounts correctly', () => {
    render(
      <LiquidityZonesChart
        symbol="BTCUSDT"
        liquidityZones={mockLiquidityZones}
        currentPrice={50450}
      />
    );

    expect(screen.getByText(/2.500.000/)).toBeInTheDocument();
    expect(screen.getByText(/3.200.000/)).toBeInTheDocument();
    expect(screen.getByText(/1.800.000/)).toBeInTheDocument();
  });

  it('opens modal when zone is clicked', () => {
    render(
      <LiquidityZonesChart
        symbol="BTCUSDT"
        liquidityZones={mockLiquidityZones}
        currentPrice={50450}
      />
    );

    const resistanceZone = screen.getByText(/resistance.*Zone/i);
    fireEvent.click(resistanceZone);

    expect(screen.getByText('Liquidity Zone Analysis')).toBeInTheDocument();
  });

  it('closes modal when close button is clicked', () => {
    render(
      <LiquidityZonesChart
        symbol="BTCUSDT"
        liquidityZones={mockLiquidityZones}
        currentPrice={50450}
      />
    );

    // Open modal
    const resistanceZone = screen.getByText(/resistance.*Zone/i);
    fireEvent.click(resistanceZone);

    // Close modal
    const closeButton = screen.getByLabelText('Close modal');
    fireEvent.click(closeButton);

    expect(screen.queryByText('Liquidity Zone Analysis')).not.toBeInTheDocument();
  });

  it('displays empty state when no zones are provided', () => {
    render(
      <LiquidityZonesChart
        symbol="BTCUSDT"
        liquidityZones={[]}
        currentPrice={50450}
      />
    );

    expect(screen.getByText('No liquidity zones identified')).toBeInTheDocument();
  });

  it('displays legend with all strength levels', () => {
    render(
      <LiquidityZonesChart
        symbol="BTCUSDT"
        liquidityZones={mockLiquidityZones}
        currentPrice={50450}
      />
    );

    expect(screen.getByText('High Strength')).toBeInTheDocument();
    expect(screen.getByText('Medium Strength')).toBeInTheDocument();
    expect(screen.getByText('Low Strength')).toBeInTheDocument();
    expect(screen.getByText('Near Price (±0.5%)')).toBeInTheDocument();
  });
});
