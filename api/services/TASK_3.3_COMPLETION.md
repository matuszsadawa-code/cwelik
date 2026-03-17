# Task 3.3 Completion: Backend PnL Breakdown Aggregation

## Summary

Successfully implemented the PnL breakdown aggregation service for the OpenClaw Trading Dashboard. The service aggregates profit/loss data by day, week, and month from the signal_outcomes table, calculates cumulative PnL, and identifies best/worst performing periods.

## Implementation Details

### Files Created

1. **api/services/pnl_breakdown_service.py** (370 lines)
   - `PnLBreakdownService` class with database dependency injection
   - Aggregates PnL by day, week, and month
   - Calculates cumulative PnL for each time period
   - Identifies best and worst performing periods
   - Supports time range filtering (1d, 7d, 30d, 90d, 1y, all)
   - Comprehensive error handling and logging

2. **api/services/test_pnl_breakdown_service.py** (650+ lines)
   - 18 comprehensive unit tests
   - Tests for daily, weekly, and monthly aggregation
   - Tests for cumulative PnL calculation
   - Tests for best/worst period identification
   - Tests for time range filtering
   - Tests for edge cases (null values, invalid timestamps, multiple trades same day)
   - Tests for error handling
   - All tests passing ✓

3. **api/test_pnl_breakdown_endpoint.py** (160 lines)
   - Integration tests for API endpoints
   - Tests for successful retrieval
   - Tests for time range parameters
   - Tests for validation
   - Tests for service status endpoint

### Files Modified

1. **api/routes/analytics.py**
   - Added `pnl_breakdown_service` global variable
   - Updated `init_analytics_services()` to initialize PnL breakdown service
   - Added `GET /api/analytics/pnl-breakdown` endpoint with comprehensive documentation
   - Added `GET /api/analytics/pnl-breakdown/status` endpoint for health monitoring

## API Endpoints

### GET /api/analytics/pnl-breakdown

Aggregates PnL by day, week, and month with cumulative calculations.

**Query Parameters:**
- `time_range` (optional): Time range filter - `1d`, `7d`, `30d`, `90d`, `1y`, `all` (default: `all`)

**Response:**
```json
{
  "daily": [
    {"date": "2024-01-01", "pnl": 2.5, "cumulativePnL": 2.5},
    {"date": "2024-01-02", "pnl": -1.2, "cumulativePnL": 1.3},
    {"date": "2024-01-03", "pnl": 3.8, "cumulativePnL": 5.1}
  ],
  "weekly": [
    {"week": "2024-W01", "pnl": 5.1, "cumulativePnL": 5.1}
  ],
  "monthly": [
    {"month": "2024-01", "pnl": 5.1, "cumulativePnL": 5.1}
  ],
  "bestDay": {"date": "2024-01-03", "pnl": 3.8},
  "worstDay": {"date": "2024-01-02", "pnl": -1.2},
  "bestWeek": {"week": "2024-W01", "pnl": 5.1},
  "worstWeek": {"week": "2024-W01", "pnl": 5.1},
  "bestMonth": {"month": "2024-01", "pnl": 5.1},
  "worstMonth": {"month": "2024-01", "pnl": 5.1}
}
```

### GET /api/analytics/pnl-breakdown/status

Returns service health status.

**Response:**
```json
{
  "initialized": true,
  "trade_count": 50,
  "has_data": true
}
```

## Key Features

### 1. Time Period Aggregation

- **Daily Aggregation**: Groups trades by calendar date
- **Weekly Aggregation**: Groups trades by ISO week (YYYY-Www format)
- **Monthly Aggregation**: Groups trades by year-month (YYYY-MM format)
- Handles multiple trades on the same day/week/month correctly

### 2. Cumulative PnL Calculation

- Calculates running cumulative PnL for each time period
- Enables visualization of equity curve progression
- Useful for identifying performance trends over time

### 3. Best/Worst Period Identification

- Identifies best performing day, week, and month
- Identifies worst performing day, week, and month
- Helps traders understand peak performance and drawdown periods

### 4. Time Range Filtering

Supports filtering by:
- `1d`: Last 24 hours
- `7d`: Last 7 days
- `30d`: Last 30 days
- `90d`: Last 90 days
- `1y`: Last 365 days
- `all`: All historical data

### 5. Robust Error Handling

- Gracefully handles null PnL values (skips them)
- Handles invalid timestamp formats (skips them)
- Returns empty structure on database errors
- Comprehensive logging for debugging

## Database Schema

The service queries the `signal_outcomes` table:

```sql
SELECT closed_at, pnl_pct, exit_price
FROM signal_outcomes
WHERE closed_at IS NOT NULL
  AND closed_at >= ? -- Optional time range filter
ORDER BY closed_at ASC
```

**Required columns:**
- `closed_at`: Timestamp when trade closed (ISO format)
- `pnl_pct`: Profit/loss percentage for the trade
- `exit_price`: Exit price (for reference)

## Test Coverage

### Unit Tests (18 tests, all passing)

1. ✓ Service initialization
2. ✓ Empty data handling
3. ✓ Daily aggregation
4. ✓ Weekly aggregation
5. ✓ Monthly aggregation
6. ✓ Cumulative PnL calculation
7. ✓ Best/worst day identification
8. ✓ Best/worst week identification
9. ✓ Best/worst month identification
10. ✓ Time range filter (1d)
11. ✓ Time range filter (all)
12. ✓ Null PnL value handling
13. ✓ Invalid timestamp handling
14. ✓ Service status retrieval
15. ✓ Service status with no data
16. ✓ Error handling in get_pnl_breakdown
17. ✓ Multiple trades same day
18. ✓ Sorted output verification

### Test Results

```
===================================== 18 passed in 1.08s ======================================
```

## Requirements Validation

This implementation satisfies the following requirements from the spec:

### Requirement 9.1: Aggregate PnL by day ✓
- Implemented in `_aggregate_by_day()` method
- Groups trades by calendar date
- Sums PnL for all trades on the same day

### Requirement 9.2: Aggregate PnL by week ✓
- Implemented in `_aggregate_by_week()` method
- Groups trades by ISO week (YYYY-Www)
- Sums PnL for all trades in the same week

### Requirement 9.3: Aggregate PnL by month ✓
- Implemented in `_aggregate_by_month()` method
- Groups trades by year-month (YYYY-MM)
- Sums PnL for all trades in the same month

### Requirement 9.8: Calculate best day, week, month ✓
- Implemented in `_find_best_worst()` method
- Identifies period with highest PnL
- Returns best day, week, and month

### Requirement 9.9: Calculate worst day, week, month ✓
- Implemented in `_find_best_worst()` method
- Identifies period with lowest PnL
- Returns worst day, week, and month

## Design Pattern

The implementation follows the same pattern as `equity_curve_service.py`:

1. **Service Class**: `PnLBreakdownService` with database dependency injection
2. **Time Range Filtering**: Consistent time range support (1d, 7d, 30d, 90d, 1y, all)
3. **Error Handling**: Comprehensive try-catch blocks with logging
4. **Empty Response**: Returns structured empty response on errors
5. **Service Status**: Health monitoring endpoint
6. **Unit Tests**: Mock database with comprehensive test coverage

## Integration

The service is fully integrated into the analytics API:

1. **Router Registration**: Already included in `api/main.py` via `analytics_router`
2. **Lazy Initialization**: Services initialized on first API call
3. **Database Connection**: Uses existing `Database` class with connection pooling
4. **WebSocket Ready**: Can be extended to broadcast PnL updates in real-time

## Usage Example

```python
from api.services.pnl_breakdown_service import PnLBreakdownService
from storage.database import Database

# Initialize service
db = Database()
service = PnLBreakdownService(db)

# Get PnL breakdown for last 30 days
breakdown = service.get_pnl_breakdown("30d")

# Access daily data
for day in breakdown["daily"]:
    print(f"{day['date']}: {day['pnl']}% (cumulative: {day['cumulativePnL']}%)")

# Access best/worst periods
print(f"Best day: {breakdown['bestDay']['date']} with {breakdown['bestDay']['pnl']}%")
print(f"Worst day: {breakdown['worstDay']['date']} with {breakdown['worstDay']['pnl']}%")
```

## Performance Considerations

1. **Database Query**: Single query fetches all trades, sorted by closed_at
2. **In-Memory Aggregation**: Uses `defaultdict` for efficient grouping
3. **Time Complexity**: O(n) where n is number of trades
4. **Space Complexity**: O(d + w + m) where d=days, w=weeks, m=months
5. **Connection Pooling**: Leverages thread-local database connections

## Future Enhancements (Other Tasks)

- [ ] Task 3.14: Frontend PnLBreakdownCharts component
- [ ] Task 3.4: Per-symbol performance statistics
- [ ] Task 3.5: Risk-adjusted returns calculation
- [ ] WebSocket broadcasting of PnL updates
- [ ] Caching for frequently accessed time ranges
- [ ] Support for custom date ranges

## Verification Steps

To verify the implementation:

1. **Run Unit Tests**:
   ```bash
   python -m pytest api/services/test_pnl_breakdown_service.py -v
   ```
   Expected: 18 passed

2. **Start API Server**:
   ```bash
   cd api
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Test Endpoint**:
   ```bash
   curl http://localhost:8000/api/analytics/pnl-breakdown?time_range=30d
   ```

4. **Check Service Status**:
   ```bash
   curl http://localhost:8000/api/analytics/pnl-breakdown/status
   ```

5. **View API Documentation**:
   Open http://localhost:8000/docs in browser

## Conclusion

Task 3.3 is complete with:
- ✓ Service implementation (370 lines)
- ✓ API endpoints with comprehensive documentation
- ✓ 18 unit tests (all passing)
- ✓ Integration tests
- ✓ Error handling and logging
- ✓ Time range filtering
- ✓ Service health monitoring
- ✓ Requirements 9.1, 9.2, 9.3, 9.8, 9.9 satisfied

The PnL breakdown service is production-ready and follows the established patterns in the codebase.
