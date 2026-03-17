"""
Unit tests for PerformanceMetricsService

Tests performance metrics calculations including win rate, profit factor,
Sharpe ratio, drawdown calculations, and P&L aggregations.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch
from api.services.performance_metrics_service import PerformanceMetricsService


@pytest.fixture
def mock_connection_manager():
    """Mock WebSocket connection manager."""
    manager = Mock()
    
    async def mock_broadcast(msg, channel=None):
        pass
    
    manager.broadcast = mock_broadcast
    return manager


@pytest.fixture
def mock_database():
    """Mock database with test data."""
    db = Mock()
    
    # Mock get_conn to return a mock connection
    mock_conn = Mock()
    db._get_conn = Mock(return_value=mock_conn)
    
    # Mock equity history
    db.get_equity_history = Mock(return_value=[
        {"equity": 10000, "timestamp": "2024-01-01T00:00:00Z"},
        {"equity": 10500, "timestamp": "2024-01-02T00:00:00Z"},
        {"equity": 10200, "timestamp": "2024-01-03T00:00:00Z"},
        {"equity": 11000, "timestamp": "2024-01-04T00:00:00Z"},
    ])
    
    return db


@pytest.fixture
def service(mock_connection_manager, mock_database):
    """Create PerformanceMetricsService instance."""
    return PerformanceMetricsService(mock_connection_manager, mock_database)


class TestPerformanceMetricsService:
    """Test suite for PerformanceMetricsService."""
    
    def test_initialization(self, service):
        """Test service initialization."""
        assert service.running is False
        assert service.task is None
        assert service.cached_metrics is None

    
    def test_calculate_win_rate(self, service):
        """Test win rate calculation."""
        # Test with wins and losses
        outcomes = [
            {"outcome": "WIN", "pnl_pct": 5.0},
            {"outcome": "WIN", "pnl_pct": 3.0},
            {"outcome": "LOSS", "pnl_pct": -2.0},
            {"outcome": "WIN", "pnl_pct": 4.0},
            {"outcome": "LOSS", "pnl_pct": -1.5},
        ]
        win_rate = service._calculate_win_rate(outcomes)
        assert win_rate == 60.0  # 3 wins out of 5 trades
        
        # Test with empty outcomes
        assert service._calculate_win_rate([]) == 0.0
        
        # Test with all wins
        all_wins = [{"outcome": "WIN", "pnl_pct": 5.0}] * 5
        assert service._calculate_win_rate(all_wins) == 100.0
    
    def test_calculate_profit_factor(self, service):
        """Test profit factor calculation."""
        # Test with wins and losses
        outcomes = [
            {"pnl_pct": 10.0},
            {"pnl_pct": 5.0},
            {"pnl_pct": -3.0},
            {"pnl_pct": -2.0},
        ]
        profit_factor = service._calculate_profit_factor(outcomes)
        assert profit_factor == 3.0  # (10 + 5) / (3 + 2) = 15 / 5 = 3.0
        
        # Test with empty outcomes
        assert service._calculate_profit_factor([]) == 0.0
        
        # Test with only wins (no losses)
        only_wins = [{"pnl_pct": 5.0}, {"pnl_pct": 3.0}]
        assert service._calculate_profit_factor(only_wins) == 8.0
    
    def test_calculate_sharpe_ratio(self, service):
        """Test Sharpe ratio calculation."""
        # Test with returns
        outcomes = [
            {"pnl_pct": 5.0},
            {"pnl_pct": -2.0},
            {"pnl_pct": 3.0},
            {"pnl_pct": 1.0},
            {"pnl_pct": -1.0},
        ]
        sharpe = service._calculate_sharpe_ratio(outcomes)
        assert isinstance(sharpe, float)
        
        # Test with empty outcomes
        assert service._calculate_sharpe_ratio([]) == 0.0
        
        # Test with single outcome
        assert service._calculate_sharpe_ratio([{"pnl_pct": 5.0}]) == 0.0

    
    def test_calculate_max_drawdown(self, service):
        """Test maximum drawdown calculation."""
        # Test with drawdown
        equity_data = [
            {"equity": 10000},
            {"equity": 10500},  # Peak
            {"equity": 9500},   # Trough (-9.52% from peak)
            {"equity": 10200},
        ]
        max_dd = service._calculate_max_drawdown(equity_data)
        assert max_dd < 0  # Should be negative
        assert abs(max_dd - (-9.52)) < 0.1  # Approximately -9.52%
        
        # Test with no drawdown (always increasing)
        no_dd = [{"equity": 10000}, {"equity": 11000}, {"equity": 12000}]
        assert service._calculate_max_drawdown(no_dd) == 0.0
        
        # Test with empty data
        assert service._calculate_max_drawdown([]) == 0.0
    
    def test_calculate_current_drawdown(self, service):
        """Test current drawdown calculation."""
        # Test at peak (no drawdown)
        at_peak = [
            {"equity": 10000},
            {"equity": 10500},
            {"equity": 11000},  # Current = Peak
        ]
        assert service._calculate_current_drawdown(at_peak) == 0.0
        
        # Test in drawdown
        in_drawdown = [
            {"equity": 10000},
            {"equity": 11000},  # Peak
            {"equity": 10500},  # Current (4.55% below peak)
        ]
        current_dd = service._calculate_current_drawdown(in_drawdown)
        assert current_dd < 0
        assert abs(current_dd - (-4.55)) < 0.1
        
        # Test with empty data
        assert service._calculate_current_drawdown([]) == 0.0
    
    def test_calculate_daily_pnl(self, service):
        """Test daily P&L calculation."""
        today = datetime.now(timezone.utc).isoformat()
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        
        outcomes = [
            {"pnl_pct": 5.0, "closed_at": today},
            {"pnl_pct": 3.0, "closed_at": today},
            {"pnl_pct": -2.0, "closed_at": yesterday},
        ]
        daily_pnl = service._calculate_daily_pnl(outcomes)
        assert daily_pnl == 8.0  # Only today's trades
        
        # Test with empty outcomes
        assert service._calculate_daily_pnl([]) == 0.0

    
    def test_calculate_weekly_pnl(self, service):
        """Test weekly P&L calculation."""
        now = datetime.now(timezone.utc)
        within_week = (now - timedelta(days=3)).isoformat()
        outside_week = (now - timedelta(days=10)).isoformat()
        
        outcomes = [
            {"pnl_pct": 5.0, "closed_at": within_week},
            {"pnl_pct": 3.0, "closed_at": within_week},
            {"pnl_pct": -2.0, "closed_at": outside_week},
        ]
        weekly_pnl = service._calculate_weekly_pnl(outcomes)
        assert weekly_pnl == 8.0  # Only last 7 days
        
        # Test with empty outcomes
        assert service._calculate_weekly_pnl([]) == 0.0
    
    def test_calculate_monthly_pnl(self, service):
        """Test monthly P&L calculation."""
        now = datetime.now(timezone.utc)
        within_month = (now - timedelta(days=15)).isoformat()
        outside_month = (now - timedelta(days=35)).isoformat()
        
        outcomes = [
            {"pnl_pct": 5.0, "closed_at": within_month},
            {"pnl_pct": 3.0, "closed_at": within_month},
            {"pnl_pct": -2.0, "closed_at": outside_month},
        ]
        monthly_pnl = service._calculate_monthly_pnl(outcomes)
        assert monthly_pnl == 8.0  # Only last 30 days
        
        # Test with empty outcomes
        assert service._calculate_monthly_pnl([]) == 0.0
    
    @pytest.mark.asyncio
    async def test_start_stop(self, service):
        """Test service start and stop."""
        # Start service
        await service.start()
        assert service.running is True
        assert service.task is not None
        
        # Stop service
        await service.stop()
        assert service.running is False
    
    def test_get_service_status(self, service):
        """Test service status retrieval."""
        status = service.get_service_status()
        assert "running" in status
        assert "has_cached_metrics" in status
        assert status["running"] is False
        assert status["has_cached_metrics"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
