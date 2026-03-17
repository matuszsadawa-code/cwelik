# LiquidityZonesChart Component

## Overview

The `LiquidityZonesChart` component displays liquidity zones identified by the backend from order book imbalances and historical volume profiles. It overlays these zones on a price chart using TradingView Lightweight Charts, providing traders with visual insights into potential support and resistance levels with significant order concentration.

## Features

- **TradingView Lightweight Charts Integration**: High-performance candlestick chart
- **Liquidity Zone Overlays**: Visual rectangles/lines at identified price levels
- **Color-Coded Strength**: 
  - High strength: Green (#22C55E)
  - Medium strength: Yellow (#EAB308)
  - Low strength: Gray (#6B7280)
- **Proximity Highlighting**: Zones within 0.5% of current price are highlighted with thicker lines
- **Interactive Tooltips**: Hover to see estimated liquidity amount
- **Detailed Modal**: Click on a zone to view comprehensive analysis
- **Real-Time Updates**: Integrates with WebSocket for live data

## Requirements Validation

**Validates Requirements:**
- 3.4: Overlay Liquidity_Zone rectangles on price charts ✓
- 3.5: Color-code Liquidity_Zone by strength (high/medium/low) ✓
- 3.6: Highlight zone when price approaches within 0.5% ✓
- 3.7: Display estimated liquidity amount for each zone ✓
- 3.8: Display detailed zone analysis on click ✓

## Props

```typescript
interface LiquidityZonesChartProps {
  symbol: string;              // Trading pair (e.g., 'BTCUSDT')
  liquidityZones: LiquidityZone[]; // Array of liquidity zones
  currentPrice: number;        // Current market price for proximity detection
}
```

## Data Structure

```typescript
interface LiquidityZone {
  symbol: string;
  priceLevel: number;
  type: 'support' | 'resistance';
  strength: 'high' | 'medium' | 'low';
  liquidityAmount: number;
  isNearPrice: boolean;
}
```

## Backend Integration

The component expects liquidity zones to be fetched from:

```
GET /api/market/{symbol}/liquidity-zones
```

Response format:
```json
{
  "zones": [
    {
      "symbol": "BTCUSDT",
      "priceLevel": 50500,
      "type": "support",
      "strength": "high",
      "liquidityAmount": 3200000,
      "isNearPrice": true
    }
  ]
}
```

## Usage Example

```tsx
import { LiquidityZonesChart } from './components/LiquidityZonesChart';

function TradingDashboard() {
  const liquidityZones = [
    {
      symbol: 'BTCUSDT',
      priceLevel: 50500,
      type: 'support',
      strength: 'high',
      liquidityAmount: 3200000,
      isNearPrice: true,
    },
    // ... more zones
  ];

  return (
    <LiquidityZonesChart
      symbol="BTCUSDT"
      liquidityZones={liquidityZones}
      currentPrice={50450}
    />
  );
}
```

## Visual Design

### Color Scheme (Dark Mode OLED)
- Background: `#0F172A` (slate-950)
- Border: `#1E293B` (slate-800)
- Text: `#94A3B8` (slate-400)
- High Strength: `#22C55E` (green-500)
- Medium Strength: `#EAB308` (yellow-500)
- Low Strength: `#6B7280` (gray-500)

### Interaction States
- **Default**: Zone displayed with 40% opacity
- **Near Price**: Zone displayed with 80% opacity and thicker line (3px vs 2px)
- **Hover**: Tooltip appears with liquidity amount
- **Click**: Modal opens with detailed zone analysis

## Accessibility

- Keyboard navigation support for zone list
- ARIA labels for interactive elements
- Color is not the only indicator (text labels included)
- Focus states visible for all interactive elements

## Performance Considerations

- Chart rendering optimized with TradingView Lightweight Charts
- Memoized price data generation
- Efficient zone rendering with price lines
- Responsive resize handling with debouncing

## Future Enhancements

- Historical zone performance tracking
- Zone strength calculation transparency
- Multiple timeframe zone analysis
- Zone confluence detection
- Export zone data functionality
