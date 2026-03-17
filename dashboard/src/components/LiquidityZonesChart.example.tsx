import { LiquidityZonesChart } from './LiquidityZonesChart';
import type { LiquidityZone } from '../types/index';

/**
 * Example usage of LiquidityZonesChart component
 * 
 * This demonstrates how to use the component with mock data.
 * In production, liquidity zones would be fetched from the backend API:
 * GET /api/market/{symbol}/liquidity-zones
 */
export const LiquidityZonesChartExample = () => {
  // Mock liquidity zones data
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
      isNearPrice: true, // Price is within 0.5%
    },
    {
      symbol: 'BTCUSDT',
      priceLevel: 49800,
      type: 'support',
      strength: 'medium',
      liquidityAmount: 1800000,
      isNearPrice: false,
    },
    {
      symbol: 'BTCUSDT',
      priceLevel: 52000,
      type: 'resistance',
      strength: 'medium',
      liquidityAmount: 1500000,
      isNearPrice: false,
    },
    {
      symbol: 'BTCUSDT',
      priceLevel: 48500,
      type: 'support',
      strength: 'low',
      liquidityAmount: 800000,
      isNearPrice: false,
    },
  ];

  const currentPrice = 50450; // Current market price

  return (
    <div className="p-8 bg-slate-950 min-h-screen">
      <LiquidityZonesChart
        symbol="BTCUSDT"
        liquidityZones={mockLiquidityZones}
        currentPrice={currentPrice}
      />
    </div>
  );
};
