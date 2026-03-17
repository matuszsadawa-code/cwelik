"""
Unit tests for PnL Breakdown Service

Tests PnL aggregation by day/week/month, cumulative PnL calculation,
and best/worst period identification.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock
from api.services.pnl_breakdown_service import PnLBreakdownService


class TestPnLBreakdownService:
    """Test suite for PnLBreakdownService"""
    
    @pytest.fixture
    def mock_database(self):
        """Create mock database"""
        db = Mock()
        db._get_conn = Mock()
        return db
    
    @pytest.fixture
    def service(self, mock_database):
        """Create PnL breakdown service with mock database"""
        return PnLBreakdownService(mock_database)
    
    def test_initialization(self, service):
        """Test service initialization"""
        assert service is not None
        assert service.database is not None
    
    def test_get_pnl_breakdown_empty_data(self, service, mock_database):
        """Test PnL breakdown generation with no data"""
        # Mock empty database response
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_database._get_conn.return_value = mock_conn
        
        result = service.get_pnl_breakdown("all")
        
        assert result["daily"] == []
        assert result["weekly"] == []
        assert result["monthly"] == []
        assert result["bestDay"] is None
        assert result["worstDay"] is None
        assert result["bestWeek"] is None
        assert result["worstWeek"] is None
        assert result["bestMonth"] is None
        assert result["worstMonth"] is None
    
    def test_aggregate_by_day(self, service, mock_database):
        """Test daily PnL aggregation"""
        # Create sample trades
        now = datetime.now(timezone.utc)
        trades = [
            {
                "closed_at": (now - timedelta(days=2)).isoformat(),
                "pnl_pct": 2.5,
                "exit_price": 100
            },
            {
                "closed_at": (now - timedelta(days=2, hours=3)).isoformat(),
                "pnl_pct": 1.5,
                "exit_price": 101
            },
            {
                "closed_at": (now - timedelta(days=1)).isoformat(),
                "pnl_pct": -1.2,
                "exit_price": 99
            },
            {
                "closed_at": now.isoformat(),
                "pnl_pct": 3.8,
                "exit_price": 103
            }
        ]
        
        # Mock database response
        mock_conn = MagicMock()
        mock_rows = [MagicMock() for _ in trades]
        for row, trade in zip(mock_rows, trades):
            row.__getitem__ = lambda self, key, t=trade: t.get(key)
            row.keys = lambda t=trade: t.keys()
        
        mock_conn.execute.return_value.fetchall.return_value = mock_rows
        mock_database._get_conn.return_value = mock_conn
        
        result = service.get_pnl_breakdown("all")
        
        # Should have 3 days of data
        assert len(result["daily"]) == 3
        
        # First day should have combined PnL of 2.5 + 1.5 = 4.0
        assert result["daily"][0]["pnl"] == 4.0
        
        # Second day should have -1.2
        assert result["daily"][1]["pnl"] == -1.2
        
        # Third day should have 3.8
        assert result["daily"][2]["pnl"] == 3.8
    
    def test_aggregate_by_week(self, service, mock_database):
        """Test weekly PnL aggregation"""
        # Create trades spanning multiple weeks
        now = datetime.now(timezone.utc)
        trades = [
            {
                "closed_at": (now - timedelta(days=14)).isoformat(),
                "pnl_pct": 2.5,
                "exit_price": 100
            },
            {
                "closed_at": (now - timedelta(days=13)).isoformat(),
                "pnl_pct": 1.5,
                "exit_price": 101
            },
            {
                "closed_at": (now - timedelta(days=7)).isoformat(),
                "pnl_pct": 3.0,
                "exit_price": 103
            },
            {
                "closed_at": now.isoformat(),
                "pnl_pct": 2.0,
                "exit_price": 105
            }
        ]
        
        # Mock database response
        mock_conn = MagicMock()
        mock_rows = [MagicMock() for _ in trades]
        for row, trade in zip(mock_rows, trades):
            row.__getitem__ = lambda self, key, t=trade: t.get(key)
            row.keys = lambda t=trade: t.keys()
        
        mock_conn.execute.return_value.fetchall.return_value = mock_rows
        mock_database._get_conn.return_value = mock_conn
        
        result = service.get_pnl_breakdown("all")
        
        # Should have weekly data
        assert len(result["weekly"]) >= 2
        
        # Each week entry should have week and pnl keys
        for week_data in result["weekly"]:
            assert "week" in week_data
            assert "pnl" in week_data
            assert "cumulativePnL" in week_data
    
    def test_aggregate_by_month(self, service, mock_database):
        """Test monthly PnL aggregation"""
        # Create trades spanning multiple months
        trades = [
            {
                "closed_at": "2024-01-15T10:00:00+00:00",
                "pnl_pct": 5.0,
                "exit_price": 100
            },
            {
                "closed_at": "2024-01-20T10:00:00+00:00",
                "pnl_pct": 3.0,
                "exit_price": 103
            },
            {
                "closed_at": "2024-02-10T10:00:00+00:00",
                "pnl_pct": 2.5,
                "exit_price": 105
            },
            {
                "closed_at": "2024-03-05T10:00:00+00:00",
                "pnl_pct": -1.5,
                "exit_price": 103
            }
        ]
        
        # Mock database response
        mock_conn = MagicMock()
        mock_rows = [MagicMock() for _ in trades]
        for row, trade in zip(mock_rows, trades):
            row.__getitem__ = lambda self, key, t=trade: t.get(key)
            row.keys = lambda t=trade: t.keys()
        
        mock_conn.execute.return_value.fetchall.return_value = mock_rows
        mock_database._get_conn.return_value = mock_conn
        
        result = service.get_pnl_breakdown("all")
        
        # Should have 3 months of data
        assert len(result["monthly"]) == 3
        
        # January should have combined PnL of 5.0 + 3.0 = 8.0
        assert result["monthly"][0]["month"] == "2024-01"
        assert result["monthly"][0]["pnl"] == 8.0
        
        # February should have 2.5
        assert result["monthly"][1]["month"] == "2024-02"
        assert result["monthly"][1]["pnl"] == 2.5
        
        # March should have -1.5
        assert result["monthly"][2]["month"] == "2024-03"
        assert result["monthly"][2]["pnl"] == -1.5
    
    def test_cumulative_pnl_calculation(self, service, mock_database):
        """Test cumulative PnL calculation"""
        trades = [
            {
                "closed_at": "2024-01-01T10:00:00+00:00",
                "pnl_pct": 2.5,
                "exit_price": 100
            },
            {
                "closed_at": "2024-01-02T10:00:00+00:00",
                "pnl_pct": -1.2,
                "exit_price": 99
            },
            {
                "closed_at": "2024-01-03T10:00:00+00:00",
                "pnl_pct": 3.8,
                "exit_price": 103
            }
        ]
        
        # Mock database response
        mock_conn = MagicMock()
        mock_rows = [MagicMock() for _ in trades]
        for row, trade in zip(mock_rows, trades):
            row.__getitem__ = lambda self, key, t=trade: t.get(key)
            row.keys = lambda t=trade: t.keys()
        
        mock_conn.execute.return_value.fetchall.return_value = mock_rows
        mock_database._get_conn.return_value = mock_conn
        
        result = service.get_pnl_breakdown("all")
        
        # Check cumulative PnL progression
        assert result["daily"][0]["cumulativePnL"] == 2.5
        assert result["daily"][1]["cumulativePnL"] == pytest.approx(1.3, rel=0.01)
        assert result["daily"][2]["cumulativePnL"] == pytest.approx(5.1, rel=0.01)
    
    def test_best_worst_day_identification(self, service, mock_database):
        """Test identification of best and worst days"""
        trades = [
            {
                "closed_at": "2024-01-01T10:00:00+00:00",
                "pnl_pct": 2.5,
                "exit_price": 100
            },
            {
                "closed_at": "2024-01-02T10:00:00+00:00",
                "pnl_pct": -3.5,
                "exit_price": 96
            },
            {
                "closed_at": "2024-01-03T10:00:00+00:00",
                "pnl_pct": 5.2,
                "exit_price": 101
            },
            {
                "closed_at": "2024-01-04T10:00:00+00:00",
                "pnl_pct": 1.0,
                "exit_price": 102
            }
        ]
        
        # Mock database response
        mock_conn = MagicMock()
        mock_rows = [MagicMock() for _ in trades]
        for row, trade in zip(mock_rows, trades):
            row.__getitem__ = lambda self, key, t=trade: t.get(key)
            row.keys = lambda t=trade: t.keys()
        
        mock_conn.execute.return_value.fetchall.return_value = mock_rows
        mock_database._get_conn.return_value = mock_conn
        
        result = service.get_pnl_breakdown("all")
        
        # Best day should be 2024-01-03 with 5.2%
        assert result["bestDay"]["date"] == "2024-01-03"
        assert result["bestDay"]["pnl"] == 5.2
        
        # Worst day should be 2024-01-02 with -3.5%
        assert result["worstDay"]["date"] == "2024-01-02"
        assert result["worstDay"]["pnl"] == -3.5
    
    def test_best_worst_week_identification(self, service, mock_database):
        """Test identification of best and worst weeks"""
        trades = [
            {
                "closed_at": "2024-01-01T10:00:00+00:00",
                "pnl_pct": 5.0,
                "exit_price": 100
            },
            {
                "closed_at": "2024-01-08T10:00:00+00:00",
                "pnl_pct": -2.0,
                "exit_price": 98
            },
            {
                "closed_at": "2024-01-15T10:00:00+00:00",
                "pnl_pct": 3.0,
                "exit_price": 101
            }
        ]
        
        # Mock database response
        mock_conn = MagicMock()
        mock_rows = [MagicMock() for _ in trades]
        for row, trade in zip(mock_rows, trades):
            row.__getitem__ = lambda self, key, t=trade: t.get(key)
            row.keys = lambda t=trade: t.keys()
        
        mock_conn.execute.return_value.fetchall.return_value = mock_rows
        mock_database._get_conn.return_value = mock_conn
        
        result = service.get_pnl_breakdown("all")
        
        # Should have best and worst weeks
        assert result["bestWeek"] is not None
        assert result["worstWeek"] is not None
        assert "week" in result["bestWeek"]
        assert "pnl" in result["bestWeek"]
    
    def test_best_worst_month_identification(self, service, mock_database):
        """Test identification of best and worst months"""
        trades = [
            {
                "closed_at": "2024-01-15T10:00:00+00:00",
                "pnl_pct": 8.0,
                "exit_price": 100
            },
            {
                "closed_at": "2024-02-10T10:00:00+00:00",
                "pnl_pct": -3.0,
                "exit_price": 97
            },
            {
                "closed_at": "2024-03-05T10:00:00+00:00",
                "pnl_pct": 5.0,
                "exit_price": 102
            }
        ]
        
        # Mock database response
        mock_conn = MagicMock()
        mock_rows = [MagicMock() for _ in trades]
        for row, trade in zip(mock_rows, trades):
            row.__getitem__ = lambda self, key, t=trade: t.get(key)
            row.keys = lambda t=trade: t.keys()
        
        mock_conn.execute.return_value.fetchall.return_value = mock_rows
        mock_database._get_conn.return_value = mock_conn
        
        result = service.get_pnl_breakdown("all")
        
        # Best month should be January with 8.0%
        assert result["bestMonth"]["month"] == "2024-01"
        assert result["bestMonth"]["pnl"] == 8.0
        
        # Worst month should be February with -3.0%
        assert result["worstMonth"]["month"] == "2024-02"
        assert result["worstMonth"]["pnl"] == -3.0
    
    def test_time_range_filter_1d(self, service, mock_database):
        """Test PnL breakdown with 1 day time range filter"""
        # Mock database response
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_database._get_conn.return_value = mock_conn
        
        service.get_pnl_breakdown("1d")
        
        # Verify SQL query was called with time filter
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        assert "WHERE closed_at IS NOT NULL" in call_args[0][0]
        assert "AND closed_at >=" in call_args[0][0]
    
    def test_time_range_filter_all(self, service, mock_database):
        """Test PnL breakdown with 'all' time range (no filter)"""
        # Mock database response
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_database._get_conn.return_value = mock_conn
        
        service.get_pnl_breakdown("all")
        
        # Verify SQL query was called without time filter
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        assert "WHERE closed_at IS NOT NULL" in call_args[0][0]
        assert "AND closed_at >=" not in call_args[0][0]
    
    def test_handle_null_pnl_values(self, service, mock_database):
        """Test handling of null PnL values"""
        trades = [
            {
                "closed_at": "2024-01-01T10:00:00+00:00",
                "pnl_pct": 2.5,
                "exit_price": 100
            },
            {
                "closed_at": "2024-01-02T10:00:00+00:00",
                "pnl_pct": None,  # Null PnL
                "exit_price": 100
            },
            {
                "closed_at": "2024-01-03T10:00:00+00:00",
                "pnl_pct": 3.0,
                "exit_price": 103
            }
        ]
        
        # Mock database response
        mock_conn = MagicMock()
        mock_rows = [MagicMock() for _ in trades]
        for row, trade in zip(mock_rows, trades):
            row.__getitem__ = lambda self, key, t=trade: t.get(key)
            row.keys = lambda t=trade: t.keys()
        
        mock_conn.execute.return_value.fetchall.return_value = mock_rows
        mock_database._get_conn.return_value = mock_conn
        
        result = service.get_pnl_breakdown("all")
        
        # Should skip null PnL values
        assert len(result["daily"]) == 2
        # Only days with valid PnL should be included
        assert result["daily"][0]["pnl"] == 2.5
        assert result["daily"][1]["pnl"] == 3.0
    
    def test_handle_invalid_timestamps(self, service, mock_database):
        """Test handling of invalid timestamp formats"""
        trades = [
            {
                "closed_at": "2024-01-01T10:00:00+00:00",
                "pnl_pct": 2.5,
                "exit_price": 100
            },
            {
                "closed_at": "invalid-timestamp",
                "pnl_pct": 1.5,
                "exit_price": 101
            },
            {
                "closed_at": "2024-01-03T10:00:00+00:00",
                "pnl_pct": 3.0,
                "exit_price": 103
            }
        ]
        
        # Mock database response
        mock_conn = MagicMock()
        mock_rows = [MagicMock() for _ in trades]
        for row, trade in zip(mock_rows, trades):
            row.__getitem__ = lambda self, key, t=trade: t.get(key)
            row.keys = lambda t=trade: t.keys()
        
        mock_conn.execute.return_value.fetchall.return_value = mock_rows
        mock_database._get_conn.return_value = mock_conn
        
        result = service.get_pnl_breakdown("all")
        
        # Should skip invalid timestamps
        assert len(result["daily"]) == 2
    
    def test_get_service_status(self, service, mock_database):
        """Test service status retrieval"""
        # Mock database response
        mock_conn = MagicMock()
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: 50 if key == "count" else None
        mock_row.keys = lambda: ["count"]
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        mock_database._get_conn.return_value = mock_conn
        
        status = service.get_service_status()
        
        assert status["initialized"] is True
        assert status["trade_count"] == 50
        assert status["has_data"] is True
    
    def test_get_service_status_no_data(self, service, mock_database):
        """Test service status with no data"""
        # Mock database response
        mock_conn = MagicMock()
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: 0 if key == "count" else None
        mock_row.keys = lambda: ["count"]
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        mock_database._get_conn.return_value = mock_conn
        
        status = service.get_service_status()
        
        assert status["initialized"] is True
        assert status["trade_count"] == 0
        assert status["has_data"] is False
    
    def test_error_handling_in_get_pnl_breakdown(self, service, mock_database):
        """Test error handling when database query fails"""
        # Mock database to raise exception
        mock_database._get_conn.side_effect = Exception("Database error")
        
        result = service.get_pnl_breakdown("all")
        
        # Should return empty data structure instead of raising
        assert result["daily"] == []
        assert result["weekly"] == []
        assert result["monthly"] == []
        assert result["bestDay"] is None
        assert result["worstDay"] is None
    
    def test_multiple_trades_same_day(self, service, mock_database):
        """Test aggregation of multiple trades on the same day"""
        trades = [
            {
                "closed_at": "2024-01-01T09:00:00+00:00",
                "pnl_pct": 2.0,
                "exit_price": 100
            },
            {
                "closed_at": "2024-01-01T14:00:00+00:00",
                "pnl_pct": 1.5,
                "exit_price": 101
            },
            {
                "closed_at": "2024-01-01T18:00:00+00:00",
                "pnl_pct": -0.5,
                "exit_price": 100
            }
        ]
        
        # Mock database response
        mock_conn = MagicMock()
        mock_rows = [MagicMock() for _ in trades]
        for row, trade in zip(mock_rows, trades):
            row.__getitem__ = lambda self, key, t=trade: t.get(key)
            row.keys = lambda t=trade: t.keys()
        
        mock_conn.execute.return_value.fetchall.return_value = mock_rows
        mock_database._get_conn.return_value = mock_conn
        
        result = service.get_pnl_breakdown("all")
        
        # Should have 1 day with combined PnL
        assert len(result["daily"]) == 1
        assert result["daily"][0]["date"] == "2024-01-01"
        assert result["daily"][0]["pnl"] == 3.0  # 2.0 + 1.5 - 0.5
    
    def test_sorted_output(self, service, mock_database):
        """Test that output is sorted chronologically"""
        trades = [
            {
                "closed_at": "2024-01-03T10:00:00+00:00",
                "pnl_pct": 3.0,
                "exit_price": 103
            },
            {
                "closed_at": "2024-01-01T10:00:00+00:00",
                "pnl_pct": 1.0,
                "exit_price": 101
            },
            {
                "closed_at": "2024-01-02T10:00:00+00:00",
                "pnl_pct": 2.0,
                "exit_price": 102
            }
        ]
        
        # Mock database response (already sorted by database query)
        mock_conn = MagicMock()
        sorted_trades = sorted(trades, key=lambda x: x["closed_at"])
        mock_rows = [MagicMock() for _ in sorted_trades]
        for row, trade in zip(mock_rows, sorted_trades):
            row.__getitem__ = lambda self, key, t=trade: t.get(key)
            row.keys = lambda t=trade: t.keys()
        
        mock_conn.execute.return_value.fetchall.return_value = mock_rows
        mock_database._get_conn.return_value = mock_conn
        
        result = service.get_pnl_breakdown("all")
        
        # Should be sorted chronologically
        assert result["daily"][0]["date"] == "2024-01-01"
        assert result["daily"][1]["date"] == "2024-01-02"
        assert result["daily"][2]["date"] == "2024-01-03"
