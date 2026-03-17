"""
Unit tests for Equity Curve Service

Tests equity curve generation, drawdown identification, and time range filtering.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock
from api.services.equity_curve_service import EquityCurveService


class TestEquityCurveService:
    """Test suite for EquityCurveService"""
    
    @pytest.fixture
    def mock_database(self):
        """Create mock database"""
        db = Mock()
        db._get_conn = Mock()
        return db
    
    @pytest.fixture
    def service(self, mock_database):
        """Create equity curve service with mock database"""
        return EquityCurveService(mock_database)
    
    def test_initialization(self, service):
        """Test service initialization"""
        assert service is not None
        assert service.database is not None
    
    def test_get_equity_curve_empty_data(self, service, mock_database):
        """Test equity curve generation with no data"""
        # Mock empty database response
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_database._get_conn.return_value = mock_conn
        
        result = service.get_equity_curve("all")
        
        assert result["timestamps"] == []
        assert result["equityValues"] == []
        assert result["drawdownPeriods"] == []
        assert result["peakEquity"] == 0
        assert result["currentEquity"] == 0
        assert result["maxDrawdown"] == 0
        assert result["maxDrawdownDuration"] == 0
    
    def test_get_equity_curve_with_data(self, service, mock_database):
        """Test equity curve generation with sample data"""
        # Create sample equity snapshots
        now = datetime.now(timezone.utc)
        snapshots = [
            {
                "timestamp": (now - timedelta(hours=3)).isoformat(),
                "equity": 10000
            },
            {
                "timestamp": (now - timedelta(hours=2)).isoformat(),
                "equity": 10500
            },
            {
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "equity": 10200
            },
            {
                "timestamp": now.isoformat(),
                "equity": 10300
            }
        ]
        
        # Mock database response
        mock_conn = MagicMock()
        mock_rows = [MagicMock() for _ in snapshots]
        for row, snapshot in zip(mock_rows, snapshots):
            row.__getitem__ = lambda self, key, s=snapshot: s.get(key)
            row.keys = lambda s=snapshot: s.keys()
        
        mock_conn.execute.return_value.fetchall.return_value = mock_rows
        mock_database._get_conn.return_value = mock_conn
        
        result = service.get_equity_curve("all")
        
        assert len(result["timestamps"]) == 4
        assert len(result["equityValues"]) == 4
        assert result["peakEquity"] == 10500
        assert result["currentEquity"] == 10300
        assert result["equityValues"] == [10000, 10500, 10200, 10300]
    
    def test_identify_drawdown_periods_no_drawdown(self, service):
        """Test drawdown identification with no significant drawdown"""
        timestamps = [1000, 2000, 3000, 4000]
        equity_values = [10000, 10100, 10200, 10300]
        
        drawdowns = service._identify_drawdown_periods(timestamps, equity_values)
        
        assert drawdowns == []
    
    def test_identify_drawdown_periods_with_drawdown(self, service):
        """Test drawdown identification with >5% drawdown"""
        timestamps = [1000, 2000, 3000, 4000, 5000]
        equity_values = [10000, 10500, 9900, 9500, 10600]  # -9.5% drawdown from 10500
        
        drawdowns = service._identify_drawdown_periods(timestamps, equity_values)
        
        assert len(drawdowns) == 1
        assert drawdowns[0]["startDate"] == 2000  # Peak at index 1
        assert drawdowns[0]["endDate"] == 5000   # Recovery at index 4
        assert drawdowns[0]["depth"] < -5        # More than 5% drawdown
        assert drawdowns[0]["peakEquity"] == 10500
        assert drawdowns[0]["troughEquity"] == 9500
    
    def test_identify_drawdown_periods_multiple_drawdowns(self, service):
        """Test identification of multiple drawdown periods"""
        timestamps = [1000, 2000, 3000, 4000, 5000, 6000, 7000]
        equity_values = [10000, 10500, 9900, 11000, 10300, 10200, 11500]
        # First drawdown: 10500 -> 9900 (-5.7%)
        # Second drawdown: 11000 -> 10200 (-7.3%)
        
        drawdowns = service._identify_drawdown_periods(timestamps, equity_values)
        
        assert len(drawdowns) == 2
        # First drawdown
        assert drawdowns[0]["peakEquity"] == 10500
        assert drawdowns[0]["troughEquity"] == 9900
        # Second drawdown
        assert drawdowns[1]["peakEquity"] == 11000
        assert drawdowns[1]["troughEquity"] == 10200
    
    def test_identify_drawdown_periods_ongoing_drawdown(self, service):
        """Test identification when still in drawdown at end"""
        timestamps = [1000, 2000, 3000, 4000]
        equity_values = [10000, 10500, 9900, 9500]  # Still in drawdown
        
        drawdowns = service._identify_drawdown_periods(timestamps, equity_values)
        
        assert len(drawdowns) == 1
        assert drawdowns[0]["startDate"] == 2000
        assert drawdowns[0]["endDate"] == 4000  # End at last timestamp
        assert drawdowns[0]["peakEquity"] == 10500
        assert drawdowns[0]["troughEquity"] == 9500
    
    def test_identify_drawdown_periods_edge_case_exactly_5_percent(self, service):
        """Test drawdown exactly at 5% threshold"""
        timestamps = [1000, 2000, 3000]
        equity_values = [10000, 10000, 9500]  # Exactly -5%
        
        drawdowns = service._identify_drawdown_periods(timestamps, equity_values)
        
        # Should NOT trigger (needs to exceed 5%, not equal)
        assert len(drawdowns) == 0
    
    def test_identify_drawdown_periods_just_over_5_percent(self, service):
        """Test drawdown just over 5% threshold"""
        timestamps = [1000, 2000, 3000, 4000]
        equity_values = [10000, 10000, 9490, 10100]  # -5.1%
        
        drawdowns = service._identify_drawdown_periods(timestamps, equity_values)
        
        # Should trigger (exceeds 5%)
        assert len(drawdowns) == 1
        assert drawdowns[0]["depth"] < -5
    
    def test_get_equity_curve_time_range_1d(self, service, mock_database):
        """Test equity curve with 1 day time range filter"""
        # Mock database response
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_database._get_conn.return_value = mock_conn
        
        service.get_equity_curve("1d")
        
        # Verify SQL query was called with time filter
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        assert "WHERE timestamp >=" in call_args[0][0]
    
    def test_get_equity_curve_time_range_all(self, service, mock_database):
        """Test equity curve with 'all' time range (no filter)"""
        # Mock database response
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_database._get_conn.return_value = mock_conn
        
        service.get_equity_curve("all")
        
        # Verify SQL query was called without time filter
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        assert "WHERE timestamp >=" not in call_args[0][0]
    
    def test_max_drawdown_calculation(self, service, mock_database):
        """Test max drawdown calculation from multiple drawdowns"""
        now = datetime.now(timezone.utc)
        snapshots = [
            {"timestamp": (now - timedelta(hours=5)).isoformat(), "equity": 10000},
            {"timestamp": (now - timedelta(hours=4)).isoformat(), "equity": 10500},
            {"timestamp": (now - timedelta(hours=3)).isoformat(), "equity": 9900},  # -5.7%
            {"timestamp": (now - timedelta(hours=2)).isoformat(), "equity": 11000},
            {"timestamp": (now - timedelta(hours=1)).isoformat(), "equity": 10100},  # -8.2%
            {"timestamp": now.isoformat(), "equity": 11500}
        ]
        
        # Mock database response
        mock_conn = MagicMock()
        mock_rows = [MagicMock() for _ in snapshots]
        for row, snapshot in zip(mock_rows, snapshots):
            row.__getitem__ = lambda self, key, s=snapshot: s.get(key)
            row.keys = lambda s=snapshot: s.keys()
        
        mock_conn.execute.return_value.fetchall.return_value = mock_rows
        mock_database._get_conn.return_value = mock_conn
        
        result = service.get_equity_curve("all")
        
        # Max drawdown should be the deepest one (-8.2%)
        assert result["maxDrawdown"] < -8
        assert result["maxDrawdown"] > -9
    
    def test_max_drawdown_duration_calculation(self, service, mock_database):
        """Test max drawdown duration calculation"""
        now = datetime.now(timezone.utc)
        snapshots = [
            {"timestamp": (now - timedelta(hours=10)).isoformat(), "equity": 10000},
            {"timestamp": (now - timedelta(hours=9)).isoformat(), "equity": 10500},
            {"timestamp": (now - timedelta(hours=8)).isoformat(), "equity": 9900},
            {"timestamp": (now - timedelta(hours=7)).isoformat(), "equity": 9800},
            {"timestamp": (now - timedelta(hours=6)).isoformat(), "equity": 9700},
            {"timestamp": (now - timedelta(hours=5)).isoformat(), "equity": 10600},  # 4 hour drawdown
        ]
        
        # Mock database response
        mock_conn = MagicMock()
        mock_rows = [MagicMock() for _ in snapshots]
        for row, snapshot in zip(mock_rows, snapshots):
            row.__getitem__ = lambda self, key, s=snapshot: s.get(key)
            row.keys = lambda s=snapshot: s.keys()
        
        mock_conn.execute.return_value.fetchall.return_value = mock_rows
        mock_database._get_conn.return_value = mock_conn
        
        result = service.get_equity_curve("all")
        
        # Duration should be approximately 4 hours = 240 minutes
        assert result["maxDrawdownDuration"] >= 230
        assert result["maxDrawdownDuration"] <= 250
    
    def test_get_service_status(self, service, mock_database):
        """Test service status retrieval"""
        # Mock database response
        mock_conn = MagicMock()
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: 100 if key == "count" else None
        mock_row.keys = lambda: ["count"]
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        mock_database._get_conn.return_value = mock_conn
        
        status = service.get_service_status()
        
        assert status["initialized"] is True
        assert status["snapshot_count"] == 100
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
        assert status["snapshot_count"] == 0
        assert status["has_data"] is False
    
    def test_error_handling_in_get_equity_curve(self, service, mock_database):
        """Test error handling when database query fails"""
        # Mock database to raise exception
        mock_database._get_conn.side_effect = Exception("Database error")
        
        result = service.get_equity_curve("all")
        
        # Should return empty data structure instead of raising
        assert result["timestamps"] == []
        assert result["equityValues"] == []
        assert result["peakEquity"] == 0
        assert result["currentEquity"] == 0
