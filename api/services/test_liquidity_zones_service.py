"""
Unit tests for Liquidity Zones Service

Tests liquidity zone identification from order book and volume profile data.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from api.services.liquidity_zones_service import LiquidityZonesService


@pytest.fixture
def mock_candle_manager():
    """Mock candle manager for testing"""
    manager = Mock()
    manager.get_candles = AsyncMock()
    return manager


@pytest.fixture
def liquidity_zones_service(mock_candle_manager):
    """Create liquidity zones service instance for testing"""
    service = LiquidityZonesService(
        candle_manager=mock_candle_manager,
        symbols=["BTCUSDT", "ETHUSDT"]
    )
    return service


@pytest.fixture
def sample_orderbook():
    """Sample order book data"""
    return {
        "bids": [
            {"price": 50000, "size": 5.0},
            {"price": 49950, "size": 3.0},
            {"price": 49900, "size": 50.0},  # Large order (wall) - 10x average
            {"price": 49850, "size": 2.0},
            {"price": 49800, "size": 4.0},
        ],
        "asks": [
            {"price": 50050, "size": 4.0},
            {"price": 50100, "size": 60.0},  # Large order (wall) - 12x average
            {"price": 50150, "size": 3.0},
            {"price": 50200, "size": 2.5},
            {"price": 50250, "size": 3.5},
        ],
        "best_bid": 50000,
        "best_ask": 50050,
    }


@pytest.fixture
def sample_candles():
    """Sample candle data for volume profile"""
    candles = []
    base_price = 49500
    for i in range(25):  # Generate 25 candles
        price = base_price + (i * 20)
        # Create volume distribution with POC at 50000
        if abs(price - 50000) < 50:
            volume = 800  # POC (highest volume)
        elif abs(price - 50100) < 50:
            volume = 600  # High volume level
        elif abs(price - 49900) < 50:
            volume = 500  # High volume level
        else:
            volume = 100 + (i * 10)  # Varying volume
        
        candles.append({"close": price, "volume": volume})
    
    return candles


class TestLiquidityZonesService:
    """Test suite for LiquidityZonesService"""
    
    def test_initialization(self, liquidity_zones_service):
        """Test service initialization"""
        assert liquidity_zones_service is not None
        assert len(liquidity_zones_service.symbols) == 2
        assert "BTCUSDT" in liquidity_zones_service.symbols
        assert liquidity_zones_service.running is False
    
    def test_merge_orderbooks(self, liquidity_zones_service):
        """Test order book merging from multiple exchanges"""
        bybit_ob = {
            "bids": [{"price": 50000, "size": 5.0}],
            "asks": [{"price": 50100, "size": 3.0}],
        }
        binance_ob = {
            "bids": [{"price": 50000, "size": 3.0}],
            "asks": [{"price": 50100, "size": 2.0}],
        }
        
        merged = liquidity_zones_service._merge_orderbooks(bybit_ob, binance_ob)
        
        assert merged["bids"][0]["price"] == 50000
        assert merged["bids"][0]["size"] == 8.0  # 5.0 + 3.0
        assert merged["asks"][0]["price"] == 50100
        assert merged["asks"][0]["size"] == 5.0  # 3.0 + 2.0
    
    def test_identify_orderbook_zones(self, liquidity_zones_service, sample_orderbook):
        """Test liquidity zone identification from order book"""
        current_price = 50025
        
        zones = liquidity_zones_service._identify_orderbook_zones(
            symbol="BTCUSDT",
            orderbook=sample_orderbook,
            current_price=current_price
        )
        
        # Should identify at least 2 zones (large bid and ask orders)
        assert len(zones) >= 2
        
        # Check for support zone (large bid at 49900)
        support_zones = [z for z in zones if z["type"] == "support"]
        assert len(support_zones) > 0
        assert any(abs(z["priceLevel"] - 49900) < 1 for z in support_zones)
        
        # Check for resistance zone (large ask at 50100)
        resistance_zones = [z for z in zones if z["type"] == "resistance"]
        assert len(resistance_zones) > 0
        assert any(abs(z["priceLevel"] - 50100) < 1 for z in resistance_zones)
        
        # Verify zone structure
        for zone in zones:
            assert "symbol" in zone
            assert "priceLevel" in zone
            assert "type" in zone
            assert zone["type"] in ["support", "resistance"]
            assert "strength" in zone
            assert zone["strength"] in ["high", "medium", "low"]
            assert "liquidityAmount" in zone
            assert "source" in zone
            assert zone["source"] == "orderbook"
    
    def test_identify_volume_profile_zones(self, liquidity_zones_service, sample_candles):
        """Test liquidity zone identification from volume profile"""
        current_price = 50025
        
        zones = liquidity_zones_service._identify_volume_profile_zones(
            symbol="BTCUSDT",
            candles=sample_candles,
            current_price=current_price
        )
        
        # Should identify POC, VAH, VAL at minimum
        assert len(zones) >= 3
        
        # Check for POC (highest volume)
        poc_zones = [z for z in zones if z.get("label") == "POC"]
        assert len(poc_zones) == 1
        # POC should be near 50000 (within 100)
        assert abs(poc_zones[0]["priceLevel"] - 50000) < 100
        assert poc_zones[0]["strength"] == "high"
        
        # Check for VAH and VAL
        vah_zones = [z for z in zones if z.get("label") == "VAH"]
        val_zones = [z for z in zones if z.get("label") == "VAL"]
        assert len(vah_zones) == 1
        assert len(val_zones) == 1
        
        # Verify zone structure
        for zone in zones:
            assert "symbol" in zone
            assert "priceLevel" in zone
            assert "type" in zone
            assert zone["type"] in ["support", "resistance"]
            assert "strength" in zone
            assert "liquidityAmount" in zone
            assert "source" in zone
            assert zone["source"] == "volume_profile"
    
    def test_calculate_strength(self, liquidity_zones_service):
        """Test strength calculation from order size"""
        avg_size = 10.0
        
        # High strength (5x average)
        assert liquidity_zones_service._calculate_strength(50.0, avg_size) == "high"
        
        # Medium strength (3x average)
        assert liquidity_zones_service._calculate_strength(30.0, avg_size) == "medium"
        
        # Low strength (2x average)
        assert liquidity_zones_service._calculate_strength(20.0, avg_size) == "low"
    
    def test_calculate_strength_from_volume(self, liquidity_zones_service):
        """Test strength calculation from volume"""
        avg_volume = 100.0
        max_volume = 1000.0
        
        # High strength (70% of max)
        assert liquidity_zones_service._calculate_strength_from_volume(
            700.0, avg_volume, max_volume
        ) == "high"
        
        # Medium strength (40% of max)
        assert liquidity_zones_service._calculate_strength_from_volume(
            400.0, avg_volume, max_volume
        ) == "medium"
        
        # Low strength (20% of max)
        assert liquidity_zones_service._calculate_strength_from_volume(
            200.0, avg_volume, max_volume
        ) == "low"
    
    def test_merge_zones(self, liquidity_zones_service):
        """Test zone merging and deduplication"""
        current_price = 50000
        
        ob_zones = [
            {
                "symbol": "BTCUSDT",
                "priceLevel": 49900,
                "priceRangeLow": 49890,
                "priceRangeHigh": 49910,
                "type": "support",
                "strength": "medium",
                "liquidityAmount": 100,
                "source": "orderbook",
                "isNearPrice": False,
            }
        ]
        
        vp_zones = [
            {
                "symbol": "BTCUSDT",
                "priceLevel": 49920,  # Within 0.5% of 49900
                "priceRangeLow": 49910,
                "priceRangeHigh": 49930,
                "type": "support",
                "strength": "high",
                "liquidityAmount": 200,
                "source": "volume_profile",
                "isNearPrice": False,
            },
            {
                "symbol": "BTCUSDT",
                "priceLevel": 50100,
                "priceRangeLow": 50090,
                "priceRangeHigh": 50110,
                "type": "resistance",
                "strength": "medium",
                "liquidityAmount": 150,
                "source": "volume_profile",
                "isNearPrice": False,
            }
        ]
        
        merged = liquidity_zones_service._merge_zones(ob_zones, vp_zones, current_price)
        
        # Should merge nearby zones (49900 and 49920) and keep resistance zone
        # After merging, we should have 2 zones total
        assert len(merged) >= 1  # At least the merged support zone
        
        # Check that zones were combined
        combined_zones = [z for z in merged if z["source"] == "combined"]
        assert len(combined_zones) >= 1  # At least one combined zone
    
    def test_zone_classification(self, liquidity_zones_service, sample_orderbook):
        """Test that zones are correctly classified as support or resistance"""
        current_price = 50025
        
        zones = liquidity_zones_service._identify_orderbook_zones(
            symbol="BTCUSDT",
            orderbook=sample_orderbook,
            current_price=current_price
        )
        
        for zone in zones:
            if zone["priceLevel"] < current_price:
                assert zone["type"] == "support"
            else:
                assert zone["type"] == "resistance"
    
    def test_near_price_detection(self, liquidity_zones_service, sample_orderbook):
        """Test detection of zones near current price (within 0.5%)"""
        current_price = 50000
        
        zones = liquidity_zones_service._identify_orderbook_zones(
            symbol="BTCUSDT",
            orderbook=sample_orderbook,
            current_price=current_price
        )
        
        # Zone at 50000 should be marked as near price
        near_zones = [z for z in zones if z["isNearPrice"]]
        assert len(near_zones) > 0
        
        # Verify near price calculation (within 0.5%)
        for zone in near_zones:
            price_diff_pct = abs(zone["priceLevel"] - current_price) / current_price
            assert price_diff_pct <= 0.005
    
    @pytest.mark.asyncio
    async def test_get_liquidity_zones_cached(self, liquidity_zones_service):
        """Test getting cached liquidity zones"""
        # Pre-populate cache
        liquidity_zones_service.zones_cache["BTCUSDT"] = [
            {
                "symbol": "BTCUSDT",
                "priceLevel": 50000,
                "type": "support",
                "strength": "high",
                "liquidityAmount": 100,
                "source": "orderbook",
                "isNearPrice": False,
                "timestamp": 1234567890,
            }
        ]
        
        zones = await liquidity_zones_service.get_liquidity_zones("BTCUSDT")
        
        assert len(zones) == 1
        assert zones[0]["priceLevel"] == 50000
    
    def test_service_status(self, liquidity_zones_service):
        """Test service status reporting"""
        # Add some cached zones
        liquidity_zones_service.zones_cache["BTCUSDT"] = [{"test": "zone1"}]
        liquidity_zones_service.zones_cache["ETHUSDT"] = [{"test": "zone2"}, {"test": "zone3"}]
        
        status = liquidity_zones_service.get_service_status()
        
        assert status["running"] is False
        assert status["symbols_monitored"] == 2
        assert status["symbols_with_zones"] == 2
        assert status["total_zones"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
