# ActiveSignalsPanel Component

## Overview

The `ActiveSignalsPanel` component displays all active trading signals with real-time updates in a virtualized list for optimal performance with 100+ signals.

## Features

- **Virtualized List**: Uses `react-window` for efficient rendering of large signal lists
- **Real-time Updates**: Subscribes to `signal_update` WebSocket messages for live P&L updates
- **Color-coded P&L**: Green for positive, red for negative unrealized P&L
- **Advanced Filtering**: Filter by Symbol, Direction, and Quality Grade
- **Sortable Columns**: Click any column header to sort ascending/descending
- **TP/SL Notifications**: Browser notifications when signals reach Take Profit or Stop Loss
- **Interactive Rows**: Click any row to open detailed signal modal

## Props

```typescript
interface ActiveSignalsPanelProps {
  onSignalClick?: (signalId: string) => void;
}
```

- `onSignalClick`: Optional callback when a signal row is clicked, receives the signal ID

## Usage

```tsx
import { ActiveSignalsPanel } from './components/ActiveSignalsPanel';

function Dashboard() {
  const handleSignalClick = (signalId: string) => {
    // Open signal detail modal
    console.log('Signal clicked:', signalId);
  };

  return (
    <div>
      <h2>Active Signals</h2>
      <ActiveSignalsPanel onSignalClick={handleSignalClick} />
    </div>
  );
}
```

## Data Structure

The component expects signals from the Zustand store with the following structure:

```typescript
interface Signal {
  signalId: string;
  symbol: string;
  direction: 'LONG' | 'SHORT';
  entryPrice: number;
  currentPrice: number;
  stopLoss: number;
  takeProfit: number;
  unrealizedPnL: number;
  mfe: number;  // Maximum Favorable Excursion (>= 0)
  mae: number;  // Maximum Adverse Excursion (<= 0)
  quality: 'A+' | 'A' | 'B' | 'C';
  confidence: number;
  status: 'ACTIVE' | 'CLOSED';
  createdAt: Date;
  timeElapsed: number;
  featureContributions: Record<string, number>;
}
```

## Columns

1. **Symbol**: Trading pair (e.g., BTCUSDT)
2. **Direction**: LONG or SHORT with color badge
3. **Entry Price**: Price at signal entry
4. **Current Price**: Real-time current price
5. **Unrealized P&L**: Current profit/loss percentage (color-coded)
6. **MFE**: Maximum Favorable Excursion (best unrealized profit)
7. **MAE**: Maximum Adverse Excursion (worst unrealized loss)
8. **Quality**: Signal quality grade (A+, A, B, C)
9. **Confidence**: ML confidence score (0-100%)
10. **Time**: Time elapsed since signal creation

## Filtering

The component provides three filter dropdowns:

- **Symbol**: Filter by specific trading pair or "All"
- **Direction**: Filter by LONG, SHORT, or "All"
- **Quality**: Filter by quality grade (A+, A, B, C) or "All"

Filters are applied in real-time and the count of filtered signals is displayed.

## Sorting

Click any column header to sort by that column. Click again to reverse the sort direction. The sort icon (↕ ↑ ↓) indicates the current sort state.

## Notifications

The component monitors signals for TP/SL hits and shows browser notifications:

- **Take Profit**: Green notification when signal reaches target
- **Stop Loss**: Red notification when signal hits stop loss

Notifications require browser permission (requested on component mount).

## Performance

- **Virtualization**: Only renders visible rows (56px height each)
- **Memoization**: Filters and sorts are memoized to prevent unnecessary recalculations
- **Efficient Updates**: WebSocket updates merge with existing signals rather than replacing the entire list

## Styling

The component follows the Dark Mode OLED design system:

- Background: `bg-slate-900`
- Borders: `border-slate-800`
- Text: `text-slate-100` (primary), `text-slate-300` (secondary)
- Positive values: `text-green-500`
- Negative values: `text-red-500`
- Hover states: `hover:bg-slate-800/50`

## Requirements Validated

- **4.4**: Display active signals with all required columns
- **4.5**: Real-time unrealized P&L updates
- **4.6**: MFE and MAE display
- **4.7**: Quality grade and confidence display
- **4.8**: TP/SL notifications
- **4.9**: Filter by Symbol, Direction, Quality
- **4.10**: Detailed signal modal on row click

## WebSocket Integration

The component automatically receives updates via the `signal_update` WebSocket message type. The WebSocket service handles:

- Connection management with exponential backoff
- Heartbeat ping/pong
- Message buffering during disconnection
- Signal merging and updates

## Browser Compatibility

- Modern browsers with WebSocket support
- Notification API support (optional, gracefully degrades)
- CSS Grid and Flexbox support
