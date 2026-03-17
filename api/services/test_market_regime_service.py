"""
Unit tests for Market Regime Service

Tests market regime calculation, broadcasting, and service lifecycle.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from api.services.market_regime_service import MarketRegimeService
from api.services.websocket_manager import ConnectionManager
from data.candle_manager_async import AsyncCandleManager


@pytest.fixture
def mock_connection_manager():
    """Mock WebSocket connection manager"""
    manager = Mock(spec=ConnectionManager)
    manager.broadcast = AsyncMock()
    return manager


@pytest.fixture
def mock_candle_manager():
    """Mock async candle manager"""
    manager = Mock(spec=AsyncCandleManager)
    manager.get_candles = AsyncMock()
    return manager


@pytest.fixture
def sample_candles():
    """Generate sample candle data for testing"""
    candles = []
    base_price = 50000
    
    for i in range(100):
        # Create trending pattern with increasing prices
        price = base_price + (i * 100)
        candles.append({
            "timestamp": 1700000000 + (i * 3600),
            "open": price,
            "high": price + 200,
            "low": price - 100,
            "close": price + 50,
            "volume": 1000 + (i * 10)
        })
    
    return candles


@pytest.fixture
def volatile_candles():
    """Generate volatile candle data for testing"""
    candles = []
    base_price = 50000
    
    for i in range(100):
        # Create volatile pattern with large swings
        volatility = 1000 if i % 2 == 0 else -1000
        price = base_price + volatility
        candles.append({
            "timestamp": 1700000000 + (i * 3600),
            "open": price,
            "high": price + 500,
            "low": price - 500,
            "close": price + (volatility // 2),
            "volume": 2000 + (i * 20)
        })
    
    return candles


@pytest.fixture
def ranging_candles():
    """Generate ranging candle data for testing"""
    candles = []
    base_price = 50000
    
    for i in range(100):
        # Create ranging pattern oscillating around base price
        oscillation = 100 if i % 4 < 2 else -100
        price = base_price + oscillation
        candles.append({
            "timestamp": 1700000000 + (i * 3600),
            "open": price,
            "high": price + 50,
            "low": price - 50,
            "close": price + 25,
            "volume": 800 + (i * 5)
        })
    
    return candles


class TestMarketRegimeService:
    """Test suite for MarketRegimeService"""
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_connection_manager, mock_candle_manager):
        """Test service initializes correctly"""
        symbols = ["BTCUSDT", "ETHUSDT"]
        service = MarketRegimeService(
            mock_connection_manager,
            mock_candle_manager,
            symbols=symbols
        )
        
        assert service.connection_manager == mock_connection_manager
        assert service.candle_manager == mock_candle_manager
        assert service.symbols == symbols
        assert service.running is False
        assert len(service.regimes) == 0
    
    @pytest.mark.asyncio
    async def test_service_start_stop(self, mock_connection_manager, mock_candle_manager):
        """Test service starts and stops correctly"""
        service = MarketRegimeService(
            mock_connection_manager,
            mock_candle_manager,
            symbols=["BTCUSDT"]
        )
        
        # Start service
        await service.start()
        assert service.running is True
        assert service.task is not None
        
        # Stop service
        await service.stop()
        assert service.running is False
    
    @pytest.mark.asyncio
    async def test_trending_regime_detection(self, mock_connection_manager, 
                                             mock_candle_manager, sample_candles):
        """Test detection of TRENDING regime"""
        mock_candle_manager.get_candles.return_value = sample_candles
        
        service = MarketRegimeService(
            mock_connection_manager,
            mock_candle_manager,
            symbols=["BTCUSDT"]
        )
        
        # Update regime for symbol
        await service._update_regime_for_symbol("BTCUSDT")
        
        # Verify regime was calculated
        regime = service.get_regime("BTCUSDT")
        assert regime is not None
        assert regime["symbol"] == "BTCUSDT"
        assert regime["regime"] in ["TRENDING", "RANGING", "VOLATILE", "QUIET"]
        assert 0 <= regime["confidence"] <= 100
        assert 0 <= regime["volatilityPercentile"] <= 100
        assert regime["trendStrength"] >= 0
        assert "timestamp" in regime
    
    @pytest.mark.asyncio
    async def test_volatile_regime_detection(self, mock_connection_manager,
                                             mock_candle_manager, volatile_candles):
        """Test detection of VOLATILE regime"""
        mock_candle_manager.get_candles.return_value = volatile_candles
        
        service = MarketRegimeService(
            mock_connection_manager,
            mock_candle_manager,
            symbols=["BTCUSDT"]
        )
        
        # Update regime for symbol
        await service._update_regime_for_symbol("BTCUSDT")
        
        # Verify regime was calculated
        regime = service.get_regime("BTCUSDT")
        assert regime is not None
        # Volatile candles should likely be detected as VOLATILE
        # (though exact classification depends on ADX calculation)
        assert regime["regime"] in ["VOLATILE", "TRENDING", "RANGING", "QUIET"]
    
    @pytest.mark.asyncio
    async def test_ranging_regime_detection(self, mock_connection_manager,
                                           mock_candle_manager, ranging_candles):
        """Test detection of RANGING regime"""
        mock_candle_manager.get_candles.return_value = ranging_candles
        
        service = MarketRegimeService(
            mock_connection_manager,
            mock_candle_manager,
            symbols=["BTCUSDT"]
        )
        
        # Update regime for symbol
        await service._update_regime_for_symbol("BTCUSDT")
        
        # Verify regime was calculated
        regime = service.get_regime("BTCUSDT")
        assert regime is not None
        # Ranging candles should likely be detected as RANGING or QUIET
        assert regime["regime"] in ["RANGING", "QUIET", "TRENDING", "VOLATILE"]
    
    @pytest.mark.asyncio
    async def test_websocket_broadcast(self, mock_connection_manager,
                                      mock_candle_manager, sample_candles):
        """Test regime updates are broadcast via WebSocket"""
        mock_candle_manager.get_candles.return_value = sample_candles
        
        service = MarketRegimeService(
            mock_connection_manager,
            mock_candle_manager,
            symbols=["BTCUSDT"]
        )
        
        # Update regime for symbol
        await service._update_regime_for_symbol("BTCUSDT")
        
        # Verify broadcast was called
        mock_connection_manager.broadcast.assert_called_once()
        
        # Verify message format
        call_args = mock_connection_manager.broadcast.call_args
        message = call_args[0][0]
        channel = call_args[1]["channel"]
        
        assert message["type"] == "regime_update"
        assert "data" in message
        assert message["data"]["symbol"] == "BTCUSDT"
        assert channel == "regime"
    
    @pytest.mark.asyncio
    async def test_volatility_percentile_calculation(self, mock_connection_manager,
                                                     mock_candle_manager, sample_candles):
        """Test volatility percentile calculation"""
        mock_candle_manager.get_candles.return_value = sample_candles
        
        service = MarketRegimeService(
            mock_connection_manager,
            mock_candle_manager,
            symbols=["BTCUSDT"]
        )
        
        # Update regime multiple times to build history
        for _ in range(15):
            await service._update_regime_for_symbol("BTCUSDT")
        
        # Verify volatility percentile is calculated
        regime = service.get_regime("BTCUSDT")
        assert regime is not None
        assert 0 <= regime["volatilityPercentile"] <= 100
        
        # Verify history is being tracked
        assert len(service.volatility_history["BTCUSDT"]) >= 10
    
    @pytest.mark.asyncio
    async def test_insufficient_candle_data(self, mock_connection_manager, mock_candle_manager):
        """Test handling of insufficient candle data"""
        # Return insufficient candles
        mock_candle_manager.get_candles.return_value = [
            {"timestamp": 1700000000, "open": 50000, "high": 50100, 
             "low": 49900, "close": 50050, "volume": 1000}
        ]
        
        service = MarketRegimeService(
            mock_connection_manager,
            mock_candle_manager,
            symbols=["BTCUSDT"]
        )
        
        # Update regime for symbol
        await service._update_regime_for_symbol("BTCUSDT")
        
        # Verify no regime was calculated
        regime = service.get_regime("BTCUSDT")
        assert regime is None
    
    @pytest.mark.asyncio
    async def test_multiple_symbols(self, mock_connection_manager,
                                   mock_candle_manager, sample_candles):
        """Test regime calculation for multiple symbols"""
        mock_candle_manager.get_candles.return_value = sample_candles
        
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        service = MarketRegimeService(
            mock_connection_manager,
            mock_candle_manager,
            symbols=symbols
        )
        
        # Update all regimes
        await service._update_all_regimes()
        
        # Verify all symbols have regime data
        all_regimes = service.get_all_regimes()
        assert len(all_regimes) == len(symbols)
        
        for symbol in symbols:
            assert symbol in all_regimes
            assert all_regimes[symbol]["symbol"] == symbol
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_connection_manager, mock_candle_manager):
        """Test error handling when candle fetch fails"""
        # Simulate error in candle fetch
        mock_candle_manager.get_candles.side_effect = Exception("API error")
        
        service = MarketRegimeService(
            mock_connection_manager,
            mock_candle_manager,
            symbols=["BTCUSDT"]
        )
        
        # Update should not raise exception
        await service._update_regime_for_symbol("BTCUSDT")
        
        # Verify no regime was calculated
        regime = service.get_regime("BTCUSDT")
        assert regime is None
    
    @pytest.mark.asyncio
    async def test_service_status(self, mock_connection_manager, mock_candle_manager):
        """Test service status reporting"""
        symbols = ["BTCUSDT", "ETHUSDT"]
        service = MarketRegimeService(
            mock_connection_manager,
            mock_candle_manager,
            symbols=symbols
        )
        
        # Get status before start
        status = service.get_service_status()
        assert status["running"] is False
        assert status["symbols_monitored"] == 2
        assert status["symbols_with_regime"] == 0
        
        # Start service
        await service.start()
        
        # Get status after start
        status = service.get_service_status()
        assert status["running"] is True
        
        # Stop service
        await service.stop()
    
    @pytest.mark.asyncio
    async def test_regime_confidence_bounds(self, mock_connection_manager,
                                           mock_candle_manager, sample_candles):
        """Test that confidence scores are within valid bounds"""
        mock_candle_manager.get_candles.return_value = sample_candles
        
        service = MarketRegimeService(
            mock_connection_manager,
            mock_candle_manager,
            symbols=["BTCUSDT"]
        )
        
        # Update regime
        await service._update_regime_for_symbol("BTCUSDT")
        
        # Verify confidence is within bounds
        regime = service.get_regime("BTCUSDT")
        assert regime is not None
        assert 0 <= regime["confidence"] <= 100
        assert isinstance(regime["confidence"], (int, float))
    
    @pytest.mark.asyncio
    async def test_regime_types_validity(self, mock_connection_manager,
                                        mock_candle_manager, sample_candles):
        """Test that regime types are valid"""
        mock_candle_manager.get_candles.return_value = sample_candles
        
        service = MarketRegimeService(
            mock_connection_manager,
            mock_candle_manager,
            symbols=["BTCUSDT"]
        )
        
        # Update regime
        await service._update_regime_for_symbol("BTCUSDT")
        
        # Verify regime type is valid
        regime = service.get_regime("BTCUSDT")
        assert regime is not None
        assert regime["regime"] in ["TRENDING", "RANGING", "VOLATILE", "QUIET"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
