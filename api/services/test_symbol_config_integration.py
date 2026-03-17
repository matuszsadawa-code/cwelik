"""
Integration tests for Symbol Configuration API endpoints

Tests the full API flow including:
- GET /api/config/symbols/available
- GET /api/config/symbols/monitored
- PUT /api/config/symbols/monitored
- GET /api/config/symbols/{symbol}/performance
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def client():
    """Create test client"""
    # Import here to avoid circular imports
    from api.main import app
    return TestClient(app)


@pytest.fixture
def mock_symbol_service():
    """Create mock symbol config service"""
    service = Mock()
    
    # Mock get_available_symbols
    service.get_available_symbols.return_value = {
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "exchange": "cross",
                "volume24h": 1000000000,
                "price": 50000,
                "change24h": 2.5,
                "win_rate": 60.0,
                "total_trades": 100,
                "total_pnl": 15.5
            },
            {
                "symbol": "ETHUSDT",
                "exchange": "cross",
                "volume24h": 500000000,
                "price": 3000,
                "change24h": 1.8,
                "win_rate": 55.0,
                "total_trades": 80,
                "total_pnl": 12.3
            }
        ],
        "count": 2
    }
    
    # Mock get_monitored_symbols
    service.get_monitored_symbols.return_value = {
        "fixed_symbols": ["BTCUSDT", "ETHUSDT"],
        "dynamic_config": {
            "top_gainers": 10,
            "top_losers": 10,
            "update_interval_minutes": 60
        },
        "all_symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "count": 3
    }
    
    # Mock update_monitored_symbols
    service.update_monitored_symbols.return_value = {
        "success": True,
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "count": 2,
        "message": "Updated monitored symbols successfully (2 symbols)",
        "timestamp": 1234567890
    }
    
    # Mock get_symbol_performance
    service.get_symbol_performance.return_value = {
        "symbol": "BTCUSDT",
        "total_trades": 100,
        "wins": 60,
        "losses": 40,
        "win_rate": 60.0,
        "total_pnl": 15.5,
        "avg_pnl": 0.155,
        "best_trade": 5.2,
        "worst_trade": -3.1,
        "avg_duration_minutes": 120.5,
        "avg_rr": 1.8,
        "profit_factor": 2.63
    }
    
    return service


class TestSymbolConfigEndpoints:
    """Test symbol configuration API endpoints"""
    
    def test_get_available_symbols(self, client, mock_symbol_service):
        """Test GET /api/config/symbols/available endpoint"""
        with patch('api.routes.config.symbol_config_service', mock_symbol_service):
            response = client.get("/api/config/symbols/available")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "symbols" in data
            assert "count" in data
            assert data["count"] == 2
            assert len(data["symbols"]) == 2
            
            # Check first symbol structure
            symbol = data["symbols"][0]
            assert symbol["symbol"] == "BTCUSDT"
            assert symbol["exchange"] == "cross"
            assert "volume24h" in symbol
            assert "price" in symbol
            assert "change24h" in symbol
            assert "win_rate" in symbol
            assert "total_trades" in symbol
            assert "total_pnl" in symbol
    
    def test_get_monitored_symbols(self, client, mock_symbol_service):
        """Test GET /api/config/symbols/monitored endpoint"""
        with patch('api.routes.config.symbol_config_service', mock_symbol_service):
            response = client.get("/api/config/symbols/monitored")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "fixed_symbols" in data
            assert "dynamic_config" in data
            assert "all_symbols" in data
            assert "count" in data
            assert data["count"] == 3
            assert len(data["all_symbols"]) == 3
    
    def test_update_monitored_symbols_success(self, client, mock_symbol_service):
        """Test PUT /api/config/symbols/monitored endpoint with valid data"""
        with patch('api.routes.config.symbol_config_service', mock_symbol_service):
            response = client.put(
                "/api/config/symbols/monitored",
                json={"symbols": ["BTCUSDT", "ETHUSDT"]}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert "symbols" in data
            assert "count" in data
            assert "message" in data
            assert data["count"] == 2
    
    def test_update_monitored_symbols_validation_error(self, client, mock_symbol_service):
        """Test PUT /api/config/symbols/monitored with invalid data"""
        # Mock validation error
        mock_symbol_service.update_monitored_symbols.return_value = {
            "success": False,
            "error": "Invalid symbol format: BTCUSD",
            "timestamp": 1234567890
        }
        
        with patch('api.routes.config.symbol_config_service', mock_symbol_service):
            response = client.put(
                "/api/config/symbols/monitored",
                json={"symbols": ["BTCUSD"]}
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            assert "Invalid symbol format" in data["detail"]
    
    def test_get_symbol_performance(self, client, mock_symbol_service):
        """Test GET /api/config/symbols/{symbol}/performance endpoint"""
        with patch('api.routes.config.symbol_config_service', mock_symbol_service):
            response = client.get("/api/config/symbols/BTCUSDT/performance")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["symbol"] == "BTCUSDT"
            assert data["total_trades"] == 100
            assert data["win_rate"] == 60.0
            assert data["profit_factor"] == 2.63
            assert "avg_pnl" in data
            assert "best_trade" in data
            assert "worst_trade" in data


class TestSymbolConfigValidation:
    """Test validation in symbol configuration endpoints"""
    
    def test_update_empty_symbols_list(self, client, mock_symbol_service):
        """Test update fails with empty symbols list"""
        mock_symbol_service.update_monitored_symbols.return_value = {
            "success": False,
            "error": "Symbols must be a non-empty list",
            "timestamp": 1234567890
        }
        
        with patch('api.routes.config.symbol_config_service', mock_symbol_service):
            response = client.put(
                "/api/config/symbols/monitored",
                json={"symbols": []}
            )
            
            assert response.status_code == 400
    
    def test_update_too_many_symbols(self, client, mock_symbol_service):
        """Test update fails with too many symbols"""
        mock_symbol_service.update_monitored_symbols.return_value = {
            "success": False,
            "error": "Maximum 100 symbols can be monitored",
            "timestamp": 1234567890
        }
        
        symbols = [f"SYM{i}USDT" for i in range(101)]
        
        with patch('api.routes.config.symbol_config_service', mock_symbol_service):
            response = client.put(
                "/api/config/symbols/monitored",
                json={"symbols": symbols}
            )
            
            assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
