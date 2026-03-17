# MarketDataGrid Component

## Overview

The `MarketDataGrid` component displays real-time market data for monitored cryptocurrency symbols in a sortable table format. It integrates with the Zustand store and WebSocket service to provide sub-100ms update latency.

## Features

- **Real-time Updates**: Displays market data with <100ms latency via WebSocket
- **Color Coding**: Green for positive changes, red for negative changes
- **Sortable Columns**: Click any column header to sort ascending/descending
- **Market Regime Indicators**: Shows current regime (TRENDING/RANGING/VOLATILE/QUIET) with confidence scores
- **Interactive Rows**: Click any row to view detailed order book (triggers callback)
- **Responsive Design**: Horizontal scroll on smaller screens

## Usage

```tsx
import { MarketDataGrid } from '../components/MarketDataGrid';

function Dashboard() {
  const symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'];
  
  const handleSymbolSelect = (symbol: string) => {
    console.log('Selected:', symbol);
    // Open order book modal/view
  };

  return (
    <MarketDataGrid 
      symbols={symbols} 
      onSymbolSelect={handleSymbolSelect} 
    />
  );
}
```

## Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `symbols` | `string[]` | Yes | Array of symbol names to display (e.g., `['BTCUSDT', 'ETHUSDT']`) |
| `onSymbolSelect` | `(symbol: string) => void` | No | Callback function when a row is clicked |

## Data Sources

The component subscribes to the following Zustand store slices:

- `marketData`: Map of symbol → MarketDataSnapshot
- `marketRegimes`: Map of symbol → MarketRegime

Data is updated via WebSocket messages:
- `market_data_update`: Updates price, volume, CVD, etc.
- `regime_update`: Updates market regime classification

## Columns

| Column | Description | Sortable | Format |
|--------|-------------|----------|--------|
| Symbol | Trading pair name | Yes | Text |
| Price | Current price | Yes | Currency with 2-8 decimals |
| 24h Change | 24-hour price change | Yes | Percentage (color-coded) |
| Volume | 24-hour trading volume | Yes | Abbreviated (K/M/B) |
| Bid-Ask Spread | Current spread | Yes | Percentage (4 decimals) |
| CVD | Cumulative Volume Delta | Yes | Abbreviated (K/M) |
| Regime | Market regime with confidence | No | Badge with color |

## Color Coding

### Price Changes
- **Green** (#22C55E): Positive change (> 0%)
- **Red** (#EF4444): Negative change (< 0%)
- **Gray** (#94A3B8): No change (0%)

### Market Regimes
- **Blue**: TRENDING (directional movement)
- **Yellow**: RANGING (sideways movement)
- **Red**: VOLATILE (high volatility)
- **Gray**: QUIET (low volatility)

## Performance

- **Virtual Scrolling**: Not yet implemented (planned for >100 symbols)
- **Memoization**: Uses `useMemo` for sorted data to prevent unnecessary re-renders
- **Update Latency**: <100ms from WebSocket message to display update

## Requirements Validation

This component validates the following requirements:

- **1.2**: Display current price within 100ms of WebSocket update
- **1.3**: Color-coded 24h price change (green/red)
- **1.4**: Display bid-ask spread
- **1.5**: Display 24h volume
- **1.9**: Display CVD (Cumulative Volume Delta)
- **1.10**: Update display without full page refresh

## Future Enhancements

- [ ] Virtual scrolling for 100+ symbols
- [ ] Detailed order book modal on row click
- [ ] Sparkline charts in each row
- [ ] Filter/search functionality
- [ ] Export to CSV
- [ ] Customizable column visibility
- [ ] Persistent sort preferences

## Testing

To test the component:

1. Ensure WebSocket connection is established
2. Subscribe to `market_data` and `regime_update` channels
3. Verify data updates appear within 100ms
4. Test sorting by clicking column headers
5. Test row click callback

## Dependencies

- React 19+
- Zustand (state management)
- Tailwind CSS (styling)
- TypeScript (type safety)
