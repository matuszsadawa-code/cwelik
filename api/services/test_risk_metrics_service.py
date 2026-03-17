"""
Unit tests for RiskMetricsService

Tests risk-adjusted return calculations including Sharpe ratio, Sortino ratio,
Calmar ratio, drawdown metrics, rolling Sharpe ratio, and drawdown histogram.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
import math

from api.services.risk_metrics_service import RiskMetricsService


class TestRiskMetricsService:
    """Test suite for RiskMetricsService"""
    
    @pytest.fixture
    def mock_database(self):
        """Create mock database"""
        db = Mock()
        db._get_conn = Mock()
        return db
    
    @pytest.fixture
    def service(self, mock_database):
        """Create service instance with mock database"""
        return RiskMetricsService(mock_database)
    
    def test_initialization(self, service):
        """Test service initializes correctly"""
        assert service is not None
        assert service.database is not None
    
    def test_get_risk_metrics_empty_data(self, service, mock_database):
        """Test risk metrics with no data returns empty metrics"""
        # Mock empty returns
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_database._get_conn.return_value = mock_conn
        
        result = service.get_risk_metrics()
        
        assert result["sharpeRatio"] == 0.0
        assert result["sortinoRatio"] == 0.0
        assert result["calmarRatio"] == 0.0
        assert result["maxDrawdown"] == 0.0
        assert result["avgDrawdownDuration"] == 0.0
        assert result["rollingSharpe"] == []
        assert result["drawdownHistogram"]["buckets"] == []
        assert result["drawdownHistogram"]["counts"] == []
    
    def test_calculate_sharpe_ratio_basic(self, service):
        """Test Sharpe ratio calculation with basic returns"""
        # Create returns with mean 2% and some variance
        base_time = datetime(2024, 1, 1)
        returns = [
            (base_time + timedelta(days=i), 2.0 + (i % 3 - 1) * 0.5)
            for i in range(10)
        ]
        
        sharpe = service._calculate_sharpe_ratio(returns)
        
        # Sharpe should be positive for positive returns
        assert sharpe > 0
        # Should be annualized (multiplied by sqrt(252))
        assert sharpe > 2.0  # Should be significantly higher than mean return
    
    def test_calculate_sharpe_ratio_zero_volatility(self, service):
        """Test Sharpe ratio with zero volatility returns zero"""
        base_time = datetime(2024, 1, 1)
        returns = [(base_time + timedelta(days=i), 2.0) for i in range(10)]
        
        sharpe = service._calculate_sharpe_ratio(returns)
        
        assert sharpe == 0.0
    
    def test_calculate_sharpe_ratio_single_return(self, service):
        """Test Sharpe ratio with single return returns zero"""
        returns = [(datetime(2024, 1, 1), 2.0)]
        
        sharpe = service._calculate_sharpe_ratio(returns)
        
        assert sharpe == 0.0
    
    def test_calculate_sharpe_ratio_empty(self, service):
        """Test Sharpe ratio with empty returns returns zero"""
        sharpe = service._calculate_sharpe_ratio([])
        
        assert sharpe == 0.0
    
    def test_calculate_sortino_ratio_basic(self, service):
        """Test Sortino ratio calculation with mixed returns"""
        base_time = datetime(2024, 1, 1)
        returns = [
            (base_time + timedelta(days=0), 3.0),
            (base_time + timedelta(days=1), -1.0),
            (base_time + timedelta(days=2), 2.0),
            (base_time + timedelta(days=3), -0.5),
            (base_time + timedelta(days=4), 4.0),
        ]
        
        sortino = service._calculate_sortino_ratio(returns)
        
        # Sortino should be positive for positive mean returns
        assert sortino > 0
    
    def test_calculate_sortino_ratio_no_downside(self, service):
        """Test Sortino ratio with no negative returns returns high value"""
        base_time = datetime(2024, 1, 1)
        returns = [(base_time + timedelta(days=i), 2.0 + i * 0.5) for i in range(5)]
        
        sortino = service._calculate_sortino_ratio(returns)
        
        # Should return very high value when no downside
        assert sortino == 999.99
    
    def test_calculate_sortino_ratio_empty(self, service):
        """Test Sortino ratio with empty returns returns zero"""
        sortino = service._calculate_sortino_ratio([])
        
        assert sortino == 0.0
    
    def test_calculate_drawdown_metrics_no_drawdown(self, service, mock_database):
        """Test drawdown metrics with no drawdown (always increasing equity)"""
        mock_conn = MagicMock()
        
        # Mock equity snapshots - always increasing
        equity_rows = [
            {"timestamp": (datetime(2024, 1, 1) + timedelta(days=i)).isoformat(), 
             "equity": 10000 + i * 100}
            for i in range(10)
        ]
        mock_conn.execute.return_value.fetchall.return_value = equity_rows
        mock_database._get_conn.return_value = mock_conn
        
        max_dd, avg_duration, periods = service._calculate_drawdown_metrics()
        
        assert max_dd == 0.0
        assert avg_duration == 0.0
        assert len(periods) == 0
    
    def test_calculate_drawdown_metrics_with_drawdown(self, service, mock_database):
        """Test drawdown metrics with actual drawdown"""
        mock_conn = MagicMock()
        
        # Mock equity snapshots with drawdown
        equity_rows = [
            {"timestamp": datetime(2024, 1, 1).isoformat(), "equity": 10000},
            {"timestamp": datetime(2024, 1, 2).isoformat(), "equity": 10500},  # Peak
            {"timestamp": datetime(2024, 1, 3).isoformat(), "equity": 10000},  # -4.76% DD
            {"timestamp": datetime(2024, 1, 4).isoformat(), "equity": 9500},   # -9.52% DD
            {"timestamp": datetime(2024, 1, 5).isoformat(), "equity": 10600},  # New peak
        ]
        mock_conn.execute.return_value.fetchall.return_value = equity_rows
        mock_database._get_conn.return_value = mock_conn
        
        max_dd, avg_duration, periods = service._calculate_drawdown_metrics()
        
        # Should detect drawdown from 10500 to 9500
        assert max_dd > 9.0  # Should be around 9.52%
        assert max_dd < 10.0
        assert len(periods) == 1
        assert periods[0]["depth"] > 9.0
    
    def test_calculate_drawdown_metrics_empty_data(self, service, mock_database):
        """Test drawdown metrics with no equity data"""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_database._get_conn.return_value = mock_conn
        
        max_dd, avg_duration, periods = service._calculate_drawdown_metrics()
        
        assert max_dd == 0.0
        assert avg_duration == 0.0
        assert len(periods) == 0
    
    def test_calculate_calmar_ratio_basic(self, service):
        """Test Calmar ratio calculation"""
        total_return = 50.0
        max_drawdown = 10.0
        
        calmar = service._calculate_calmar_ratio(total_return, max_drawdown)
        
        assert calmar == 5.0
    
    def test_calculate_calmar_ratio_zero_drawdown(self, service):
        """Test Calmar ratio with zero drawdown returns high value"""
        total_return = 50.0
        max_drawdown = 0.0
        
        calmar = service._calculate_calmar_ratio(total_return, max_drawdown)
        
        assert calmar == 999.99
    
    def test_calculate_calmar_ratio_negative_return_zero_drawdown(self, service):
        """Test Calmar ratio with negative return and zero drawdown"""
        total_return = -10.0
        max_drawdown = 0.0
        
        calmar = service._calculate_calmar_ratio(total_return, max_drawdown)
        
        assert calmar == 0.0
    
    def test_calculate_rolling_sharpe_basic(self, service):
        """Test rolling Sharpe ratio calculation"""
        base_time = datetime(2024, 1, 1)
        returns = [
            (base_time + timedelta(days=i), 2.0 + (i % 3 - 1) * 0.5)
            for i in range(60)  # 60 days of data
        ]
        
        rolling = service._calculate_rolling_sharpe(returns, window_days=30)
        
        # Should have data points for each day after first window
        assert len(rolling) > 0
        assert all("timestamp" in point for point in rolling)
        assert all("sharpe" in point for point in rolling)
    
    def test_calculate_rolling_sharpe_insufficient_data(self, service):
        """Test rolling Sharpe with insufficient data returns empty"""
        returns = [(datetime(2024, 1, 1), 2.0)]
        
        rolling = service._calculate_rolling_sharpe(returns, window_days=30)
        
        assert rolling == []
    
    def test_generate_drawdown_histogram_basic(self, service):
        """Test drawdown histogram generation"""
        drawdown_periods = [
            {"duration": 30},    # <1h
            {"duration": 120},   # 1-4h
            {"duration": 180},   # 1-4h
            {"duration": 600},   # 4-24h
            {"duration": 2000},  # 1-7d
            {"duration": 15000}, # >7d
        ]
        
        histogram = service._generate_drawdown_histogram(drawdown_periods)
        
        assert histogram["buckets"] == ["<1h", "1-4h", "4-24h", "1-7d", ">7d"]
        assert histogram["counts"] == [1, 2, 1, 1, 1]
    
    def test_generate_drawdown_histogram_empty(self, service):
        """Test drawdown histogram with no drawdowns"""
        histogram = service._generate_drawdown_histogram([])
        
        assert histogram["buckets"] == []
        assert histogram["counts"] == []
    
    def test_get_service_status_with_data(self, service, mock_database):
        """Test service status with available data"""
        mock_conn = MagicMock()
        
        # Mock returns count
        returns_row = {"count": 50}
        equity_row = {"count": 100}
        
        mock_conn.execute.return_value.fetchone.side_effect = [returns_row, equity_row]
        mock_database._get_conn.return_value = mock_conn
        
        status = service.get_service_status()
        
        assert status["initialized"] is True
        assert status["returns_count"] == 50
        assert status["equity_snapshots_count"] == 100
        assert status["has_data"] is True
    
    def test_get_service_status_no_data(self, service, mock_database):
        """Test service status with no data"""
        mock_conn = MagicMock()
        
        # Mock empty counts
        returns_row = {"count": 0}
        equity_row = {"count": 0}
        
        mock_conn.execute.return_value.fetchone.side_effect = [returns_row, equity_row]
        mock_database._get_conn.return_value = mock_conn
        
        status = service.get_service_status()
        
        assert status["initialized"] is True
        assert status["returns_count"] == 0
        assert status["equity_snapshots_count"] == 0
        assert status["has_data"] is False
    
    def test_get_risk_metrics_integration(self, service, mock_database):
        """Test full risk metrics calculation with mock data"""
        mock_conn = MagicMock()
        
        # Mock returns data
        base_time = datetime(2024, 1, 1)
        returns_rows = [
            {"closed_at": (base_time + timedelta(days=i)).isoformat(), 
             "pnl_pct": 2.0 + (i % 3 - 1) * 0.5}
            for i in range(30)
        ]
        
        # Mock equity data with drawdown
        equity_rows = [
            {"timestamp": (base_time + timedelta(days=i)).isoformat(), 
             "equity": 10000 + i * 100 - (50 if 10 <= i <= 15 else 0)}
            for i in range(30)
        ]
        
        # Set up mock to return different data for different queries
        def mock_execute(query):
            mock_result = MagicMock()
            if "signal_outcomes" in query:
                mock_result.fetchall.return_value = returns_rows
            elif "equity_snapshots" in query:
                mock_result.fetchall.return_value = equity_rows
            return mock_result
        
        mock_conn.execute.side_effect = mock_execute
        mock_database._get_conn.return_value = mock_conn
        
        result = service.get_risk_metrics()
        
        # Verify all metrics are present
        assert "sharpeRatio" in result
        assert "sortinoRatio" in result
        assert "calmarRatio" in result
        assert "maxDrawdown" in result
        assert "avgDrawdownDuration" in result
        assert "rollingSharpe" in result
        assert "drawdownHistogram" in result
        
        # Verify metrics are reasonable
        assert result["sharpeRatio"] != 0.0
        assert result["sortinoRatio"] != 0.0
        assert result["maxDrawdown"] >= 0.0
        assert isinstance(result["rollingSharpe"], list)
        assert isinstance(result["drawdownHistogram"], dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
