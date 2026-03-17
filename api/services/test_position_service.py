"""
Unit tests for Position Service

Tests position tracking, P&L calculations, and WebSocket broadcasting.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from api.services.position_service import PositionService
from api.services.websocket_manager import ConnectionManager
from api.services.market_data_service import MarketDataService


@pytest.fixture
def mock_connection_manager():
    """Mock WebSocket connection manager"""
    manager = MagicMock(spec=ConnectionManager)
    manager.broadcast = AsyncMock()
    return manager


@pytest.fixture
def mock_market_data_service():
    """Mock market data service"""
    service = MagicMock(spec=MarketDataService)
    service.get_market_data = MagicMock(return_value={
        "symbol": "BTCUSDT",
        "price": 50000.0,
        "volume24h": 1000000,
        "change24h": 2.5,
    })
    return service


@pytest.fixture
def mock_database():
    """Mock database"""
    db = MagicMock()
    db.get_executions = MagicMock(return_value=[])
    db.save_execution = MagicMock()
    return db


@pytest.fixture
def position_service(mock_connection_manager, mock_market_data_service, mock_database):
    """Create position service instance"""
    return PositionService(
        connection_manager=mock_connection_manager,
        market_data_service=mock_market_data_service,
        database=mock_database
    )


class TestPositionServiceInitialization:
    """Test position service initialization"""
    
    def test_initialization(self, position_service):
        """Test service initializes correctly"""
        assert position_service is not None
        assert not position_service.running
        assert position_service.task is None


class TestPositionPnLCalculations:
    """Test P&L calculation logic"""
    
    def test_calculate_unrealized_pnl_long_profit(self, position_service):
        """Test unrealized PnL calculation for LONG position in profit"""
        # LONG: Entry 50000, Current 51000, Leverage 10x
        # PnL = (51000 - 50000) / 50000 * 10 * 100 = 20%
        pnl = position_service._calculate_unrealized_pnl(
            direction="LONG",
            entry_price=50000.0,
            current_price=51000.0,
            leverage=10
        )
        assert pnl == pytest.approx(20.0, rel=0.01)
    
    def test_calculate_unrealized_pnl_long_loss(self, position_service):
        """Test unrealized PnL calculation for LONG position in loss"""
        # LONG: Entry 50000, Current 49000, Leverage 10x
        # PnL = (49000 - 50000) / 50000 * 10 * 100 = -20%
        pnl = position_service._calculate_unrealized_pnl(
            direction="LONG",
            entry_price=50000.0,
            current_price=49000.0,
            leverage=10
        )
        assert pnl == pytest.approx(-20.0, rel=0.01)
    
    def test_calculate_unrealized_pnl_short_profit(self, position_service):
        """Test unrealized PnL calculation for SHORT position in profit"""
        # SHORT: Entry 50000, Current 49000, Leverage 10x
        # PnL = (50000 - 49000) / 50000 * 10 * 100 = 20%
        pnl = position_service._calculate_unrealized_pnl(
            direction="SHORT",
            entry_price=50000.0,
            current_price=49000.0,
            leverage=10
        )
        assert pnl == pytest.approx(20.0, rel=0.01)
    
    def test_calculate_unrealized_pnl_short_loss(self, position_service):
        """Test unrealized PnL calculation for SHORT position in loss"""
        # SHORT: Entry 50000, Current 51000, Leverage 10x
        # PnL = (50000 - 51000) / 50000 * 10 * 100 = -20%
        pnl = position_service._calculate_unrealized_pnl(
            direction="SHORT",
            entry_price=50000.0,
            current_price=51000.0,
            leverage=10
        )
        assert pnl == pytest.approx(-20.0, rel=0.01)
    
    def test_calculate_unrealized_pnl_no_leverage(self, position_service):
        """Test unrealized PnL calculation with no leverage"""
        # LONG: Entry 50000, Current 51000, Leverage 1x
        # PnL = (51000 - 50000) / 50000 * 1 * 100 = 2%
        pnl = position_service._calculate_unrealized_pnl(
            direction="LONG",
            entry_price=50000.0,
            current_price=51000.0,
            leverage=1
        )
        assert pnl == pytest.approx(2.0, rel=0.01)


class TestRiskRewardCalculation:
    """Test risk-reward ratio calculation"""
    
    def test_calculate_rr_ratio_long(self, position_service):
        """Test R:R calculation for LONG position"""
        # LONG: Entry 50000, SL 49000, TP 52000
        # Risk = 50000 - 49000 = 1000
        # Reward = 52000 - 50000 = 2000
        # R:R = 2000 / 1000 = 2.0
        rr = position_service._calculate_rr_ratio(
            direction="LONG",
            entry_price=50000.0,
            sl_price=49000.0,
            tp_price=52000.0
        )
        assert rr == pytest.approx(2.0, rel=0.01)
    
    def test_calculate_rr_ratio_short(self, position_service):
        """Test R:R calculation for SHORT position"""
        # SHORT: Entry 50000, SL 51000, TP 48000
        # Risk = 51000 - 50000 = 1000
        # Reward = 50000 - 48000 = 2000
        # R:R = 2000 / 1000 = 2.0
        rr = position_service._calculate_rr_ratio(
            direction="SHORT",
            entry_price=50000.0,
            sl_price=51000.0,
            tp_price=48000.0
        )
        assert rr == pytest.approx(2.0, rel=0.01)
    
    def test_calculate_rr_ratio_missing_sl(self, position_service):
        """Test R:R calculation with missing SL"""
        rr = position_service._calculate_rr_ratio(
            direction="LONG",
            entry_price=50000.0,
            sl_price=None,
            tp_price=52000.0
        )
        assert rr is None
    
    def test_calculate_rr_ratio_missing_tp(self, position_service):
        """Test R:R calculation with missing TP"""
        rr = position_service._calculate_rr_ratio(
            direction="LONG",
            entry_price=50000.0,
            sl_price=49000.0,
            tp_price=None
        )
        assert rr is None


class TestDurationCalculation:
    """Test position duration calculation"""
    
    def test_calculate_duration(self, position_service):
        """Test duration calculation"""
        # Create timestamp 60 seconds ago
        past_time = datetime.now(timezone.utc)
        past_time = past_time.replace(second=past_time.second - 60)
        created_at = past_time.isoformat()
        
        duration = position_service._calculate_duration(created_at)
        
        # Should be approximately 60 seconds (allow 2 second tolerance)
        assert 58 <= duration <= 62


@pytest.mark.asyncio
class TestPositionTracking:
    """Test position tracking loop"""
    
    async def test_update_all_positions_empty(self, position_service, mock_connection_manager):
        """Test update with no open positions"""
        await position_service._update_all_positions()
        
        # Should broadcast empty portfolio update
        assert mock_connection_manager.broadcast.called
        call_args = mock_connection_manager.broadcast.call_args
        message = call_args[0][0]
        
        assert message["type"] == "portfolio_update"
        assert message["data"]["totalPositions"] == 0
        assert message["data"]["totalExposure"] == 0.0
        assert message["data"]["totalUnrealizedPnL"] == 0.0
    
    async def test_update_all_positions_with_data(self, position_service, mock_database, mock_connection_manager):
        """Test update with open positions"""
        # Mock open position
        mock_database.get_executions.return_value = [{
            "execution_id": "exec_001",
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "entry_price": 50000.0,
            "qty": 1.0,
            "leverage": 10,
            "sl_price": 49000.0,
            "tp_price": 52000.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }]
        
        await position_service._update_all_positions()
        
        # Should broadcast position and portfolio updates
        assert mock_connection_manager.broadcast.call_count >= 2


@pytest.mark.asyncio
class TestPositionClosure:
    """Test manual position closure"""
    
    async def test_close_position_success(self, position_service, mock_database, mock_market_data_service):
        """Test successful position closure"""
        # Mock open position
        mock_database.get_executions.return_value = [{
            "execution_id": "exec_001",
            "signal_id": "sig_001",
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "entry_price": 50000.0,
            "qty": 1.0,
            "leverage": 10,
            "sl_price": 49000.0,
            "tp_price": 52000.0,
            "mode": "paper",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }]
        
        result = await position_service.close_position("exec_001", "MANUAL_CLOSE")
        
        assert result["success"] is True
        assert "exec_001" in result["message"]
        assert result["data"]["symbol"] == "BTCUSDT"
        assert mock_database.save_execution.called
    
    async def test_close_position_not_found(self, position_service, mock_database):
        """Test closing non-existent position"""
        mock_database.get_executions.return_value = []
        
        result = await position_service.close_position("exec_999", "MANUAL_CLOSE")
        
        assert result["success"] is False
        assert "not found" in result["message"].lower()


class TestServiceStatus:
    """Test service status reporting"""
    
    def test_get_service_status(self, position_service):
        """Test service status retrieval"""
        status = position_service.get_service_status()
        
        assert "running" in status
        assert status["running"] is False  # Not started yet


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
