# OrderBookVisualization Component

## Overview

The `OrderBookVisualization` component displays detailed order book data with depth visualization for a selected trading symbol. It provides real-time updates of bid and ask levels, calculates spread and imbalance metrics, and uses visual depth bars to represent liquidity at each price level.

## Features

- **20+ Price Levels**: Displays at least 20 price levels for both bids and asks
- **Depth Visualization**: Horizontal bars show cumulative order book depth
- **Real-time Updates**: Animates significant changes (>20% size change) to highlight shifts
- **Bid-Ask Spread**: Calculates and displays both absolute and percentage spread
- **Order Book Imbalance**: Shows bid/ask distribution and identifies market bias
- **Color Coding**: Green for bids, red for asks, following institutional trading conventions
- **Responsive Design**: Adapts to different screen sizes with Dark Mode OLED theme

## Props

```typescript
interface OrderBookVisualizationProps {
  symbol: string;        // Trading pair symbol (e.g., 'BTCUSDT')
  onClose?: () => void;  // Optional callback when close button is clicked
}
```

## Usage

```tsx
import { OrderBookVisualization } from '@components/OrderBookVisualization';

// Basic usage
<OrderBookVisualization symbol="BTCUSDT" />

// With close handler
<OrderBookVisualization 
  symbol="ETHUSDT" 
  onClose={() => console.log('Closed')} 
/>
```

## Integration with MarketDataGrid

The component is designed to be displayed when a user clicks on a symbol in the `MarketDataGrid`:

```tsx
const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);

<MarketDataGrid 
  symbols={['BTCUSDT', 'ETHUSDT']} 
  onSymbolSelect={setSelectedSymbol}
/>

{selectedSymbol && (
  <OrderBookVisualization 
    symbol={selectedSymbol}
    onClose={() => setSelectedSymbol(null)}
  />
)}
```

## Data Structure

The component expects order book data in the following format:

```typescript
interface OrderBook {
  symbol: string;
  bids: [price: number, size: number][];  // Sorted descending by price
  asks: [price: number, size: number][];  // Sorted ascending by price
  timestamp: number;
}
```

## Metrics Calculated

### Bid-Ask Spread

- **Absolute Spread**: `bestAsk - bestBid` (in dollars)
- **Percentage Spread**: `(absolute / bestBid) * 100` (in %)

### Order Book Imbalance

- **Bid Percentage**: `(totalBidSize / (totalBidSize + totalAskSize)) * 100`
- **Ask Percentage**: `(totalAskSize / (totalBidSize + totalAskSize)) * 100`
- **Imbalance Ratio**: `|bidPercentage - askPercentage|`
- **Side Classification**:
  - `bid` if bidPercentage > 55%
  - `ask` if askPercentage > 55%
  - `neutral` otherwise

### Depth Visualization

Each price level displays:
- **Price**: Formatted with 2 decimal places
- **Size**: Order size at that price level (4 decimal places)
- **Total**: Cumulative size from best price to current level (4 decimal places)
- **Depth Bar**: Visual representation scaled to maximum cumulative total

## Animation

The component animates price levels that experience significant changes (>20% size change):
- Highlights the level with a colored background (green for bids, red for asks)
- Applies a subtle scale transform
- Animation duration: 500ms

## WebSocket Integration

In production, the component should subscribe to order book updates via WebSocket:

```typescript
useEffect(() => {
  const ws = getWebSocketManager();
  
  ws.subscribe('orderbook_update', (data) => {
    if (data.symbol === symbol) {
      setOrderBook(data);
    }
  });
  
  return () => {
    ws.unsubscribe('orderbook_update');
  };
}, [symbol]);
```

## Styling

The component uses Tailwind CSS with the Dark Mode OLED design system:

- **Background**: `bg-slate-900` (main), `bg-slate-950` (header)
- **Borders**: `border-slate-800`
- **Text**: `text-slate-100` (primary), `text-slate-400` (secondary)
- **Bids**: `text-green-400` (prices), `bg-green-500/10` (depth bars)
- **Asks**: `text-red-400` (prices), `bg-red-500/10` (depth bars)
- **Hover**: `hover:bg-slate-800/50` (rows)

## Accessibility

- Semantic HTML structure with proper heading hierarchy
- ARIA labels for interactive elements (close button)
- Keyboard navigation support
- High contrast colors meeting WCAG 2.1 AA standards
- Screen reader friendly with descriptive text

## Performance Considerations

- **Memoization**: Uses `useMemo` for expensive calculations (sorting, cumulative totals)
- **Efficient Updates**: Only re-renders when order book data changes
- **Animation Throttling**: Limits animation triggers to significant changes only
- **Virtual Scrolling**: Not needed for 20 levels, but can be added for larger datasets

## Requirements Satisfied

- **Requirement 1.6**: Display at least 20 price levels for bids and asks ✓
- **Requirement 1.6**: Visualize order book depth with horizontal bars ✓
- **Requirement 1.7**: Animate changes to highlight significant shifts ✓
- **Requirement 1.7**: Calculate and display bid-ask spread ✓
- **Requirement 1.7**: Show order book imbalances ✓

## Testing

The component includes comprehensive unit tests covering:
- Rendering and display of all UI elements
- Spread calculations (absolute and percentage)
- Imbalance calculations and side classification
- Color coding for bids and asks
- Animation triggers for significant changes
- Close button functionality
- Requirements validation

Run tests with:
```bash
npm test OrderBookVisualization.test.tsx
```

## Future Enhancements

- **Historical Depth**: Show depth changes over time
- **Liquidity Zones**: Highlight significant support/resistance levels
- **Order Flow**: Integrate with trade flow data
- **Heatmap**: Color-code levels by liquidity concentration
- **Alerts**: Notify on significant imbalance changes
- **Export**: Allow exporting order book snapshot as CSV/JSON
