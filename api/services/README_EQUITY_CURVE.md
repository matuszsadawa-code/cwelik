# Equity Curve Service

## Overview

The `EquityCurveService` generates equity curves from historical equity snapshots, identifies significant drawdown periods, and provides data formatted for TradingView Lightweight Charts visualization.

## Features

- Query equity snapshots from `equity_snapshots` table
- Calculate peak and current equity values
- Identify drawdown periods exceeding 5% threshold
- Support time range filtering (1d, 7d, 30d, 90d, 1y, all)
- Calculate maximum drawdown depth and duration
- Format timestamps for TradingView Lightweight Charts (Unix ms)

## Installation

```python
from api.services.equity_curve_service import EquityCurveService
from storage.database import Database

# Initialize with existing database
db = Database()
service = EquityCurveService(database=db)

# Or let service create its own database instance
service = EquityCurveService()
```

## API Reference

### `get_equity_curve(time_range: str = "all") -> Dict`

Generate equity curve data with drawdown analysis.

**Parameters:**
- `time_range` (str): Time range filter
  - `"1d"` - Last 24 hours
  - `"7d"` - Last 7 days
  - `"30d"` - Last 30 days
  - `"90d"` - Last 90 days
  - `"1y"` - Last 365 days
  - `"all"` - All available data (default)

**Returns:**
```python
{
    "timestamps": [1704067200000, ...],  # Unix timestamps in milliseconds
    "equityValues": [10000.0, 10250.5, ...],  # Equity values
    "drawdownPeriods": [
        {
            "startDate": 1704067200000,  # Drawdown start (Unix ms)
            "endDate": 1704153600000,      # Drawdown end (Unix ms)
            "depth": -8.5,                 # Drawdown depth (%)
            "duration": 1440,              # Duration in minutes
            "peakEquity": 10500.0,         # Peak before drawdown
            "troughEquity": 9607.5         # Lowest point
        }
    ],
    "peakEquity": 10500.0,           # All-time peak
    "currentEquity": 10250.5,        # Current equity
    "maxDrawdown": -8.5,             # Maximum drawdown (%)
    "maxDrawdownDuration": 1440      # Longest drawdown (minutes)
}
```

### `get_service_status() -> Dict`

Get service health status for monitoring.

**Returns:**
```python
{
    "initialized": True,
    "snapshot_count": 1523,
    "has_data": True
}
```

## Usage Examples

### Basic Usage

```python
from api.services.equity_curve_service import EquityCurveService

service = EquityCurveService()

# Get all-time equity curve
data = service.get_equity_curve()

print(f"Peak Equity: ${data['peakEquity']:,.2f}")
print(f"Current Equity: ${data['currentEquity']:,.2f}")
print(f"Max Drawdown: {data['maxDrawdown']:.2f}%")
print(f"Drawdown Periods: {len(data['drawdownPeriods'])}")
```

### Time Range Filtering

```python
# Last 30 days
monthly_data = service.get_equity_curve(time_range="30d")

# Last 7 days
weekly_data = service.get_equity_curve(time_range="7d")
```

### Drawdown Analysis

```python
data = service.get_equity_curve()

for period in data['drawdownPeriods']:
    print(f"Drawdown: {period['depth']:.2f}%")
    print(f"Duration: {period['duration']} minutes")
    print(f"Peak: ${period['peakEquity']:,.2f}")
    print(f"Trough: ${period['troughEquity']:,.2f}")
    print("---")
```

### Integration with FastAPI

```python
from fastapi import APIRouter
from api.services.equity_curve_service import EquityCurveService

router = APIRouter()
service = EquityCurveService()

@router.get("/api/analytics/equity-curve")
async def get_equity_curve(time_range: str = "all"):
    """Get equity curve with drawdown analysis"""
    return service.get_equity_curve(time_range)
```

## Drawdown Detection Algorithm

The service identifies drawdown periods using a peak-tracking algorithm:

1. **Track Running Peak**: Maintain the highest equity value seen so far
2. **Calculate Drawdown**: For each point, calculate percentage drop from peak
3. **Threshold Check**: If drawdown exceeds 5%, mark as drawdown period
4. **Track Trough**: Record the lowest point during the drawdown
5. **End Detection**: Drawdown ends when equity reaches a new peak
6. **Ongoing Drawdowns**: If still in drawdown at data end, record as ongoing

**Key Properties:**
- Drawdown depth is always negative (e.g., -8.5%)
- Duration is in minutes for precision
- Multiple drawdown periods can exist
- Drawdowns < 5% are not recorded

## Database Schema

The service queries the `equity_snapshots` table:

```sql
CREATE TABLE equity_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    equity REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_equity_snapshots_timestamp 
ON equity_snapshots(timestamp DESC);
```

## Performance Characteristics

- **Query Time**: <10ms for typical datasets (1000-10000 snapshots)
- **Memory Usage**: O(n) where n = number of snapshots
- **Drawdown Detection**: O(n) single-pass algorithm
- **Time Range Filtering**: Indexed query on timestamp column

## Error Handling

The service handles errors gracefully:

- **No Data**: Returns empty arrays and zero values
- **Invalid Timestamps**: Skips malformed timestamps, logs debug message
- **Database Errors**: Logs error, returns empty result structure
- **Division by Zero**: Protected in drawdown calculations

## Testing

```python
# Run unit tests
pytest api/services/test_equity_curve_service.py -v

# Test with sample data
from api.services.equity_curve_service import EquityCurveService
from storage.database import Database

db = Database()
service = EquityCurveService(database=db)

# Check service status
status = service.get_service_status()
assert status['initialized'] == True
```

## Requirements Validated

- ✅ **8.1**: Generate equity curve from equity_snapshots table
- ✅ **8.2**: Identify drawdown periods exceeding 5%
- ✅ **8.3**: Calculate peak equity and current equity
- ✅ **8.10**: Support time range filtering

## Integration Points

### Frontend (EquityCurveChart Component)
```typescript
// Fetch equity curve data
const response = await fetch('/api/analytics/equity-curve?time_range=30d');
const data = await response.json();

// Use with TradingView Lightweight Charts
chart.setData(data.timestamps.map((t, i) => ({
  time: t / 1000,  // Convert ms to seconds
  value: data.equityValues[i]
})));
```

### WebSocket Broadcasting
```python
# Broadcast equity updates
async def broadcast_equity_update():
    data = service.get_equity_curve(time_range="1d")
    await connection_manager.broadcast({
        "type": "equity_update",
        "data": data
    }, channel="performance")
```

## Troubleshooting

**No data returned:**
- Check if `equity_snapshots` table has data
- Verify timestamp format is ISO 8601
- Check time range parameter is valid

**Incorrect drawdowns:**
- Verify equity values are cumulative (not daily P&L)
- Check for data gaps that might affect peak tracking
- Ensure timestamps are in chronological order

**Performance issues:**
- Add index on timestamp column if missing
- Limit time range for large datasets
- Consider caching results for frequently accessed ranges

## Future Enhancements

- Configurable drawdown threshold (currently fixed at 5%)
- Underwater equity curve (distance from peak over time)
- Recovery time analysis (time to recover from drawdowns)
- Drawdown severity classification (mild/moderate/severe)
- Comparison with benchmark equity curves
