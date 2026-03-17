"""
Tests for Symbol Configuration Service

Tests symbol selection configuration including:
- Retrieving available symbols from exchanges
- Getting currently monitored symbols
- Updating monitored symbols list
- Fetching performance metrics per symbol
- Persisting symbol configuration changes
"""

import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
from api.services.symbol_config_service import SymbolConfigService


class TestSymbolConfigService:
    """Test suite for SymbolConfigService"""
    
    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        return SymbolConfigService(db=None)
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database"""
        db = Mock()
        
        # Mock connection
        mock_conn = Mock()
        db._get_conn.return_value = mock_conn
        
        # Mock execute for metrics query
        mock_result = Mock()
        mock_result.fetchone.return_value = {
            "total_trades": 100,
            "wins": 60,
            "total_pnl": 15.5,
            "avg_pnl": 0.155
        }
        mock_conn.execute.return_value = mock_result
        
        return db
    
    def test_service_initialization(self, service):
        """Test service initializes correctly"""
        assert service is not None
        assert service.config_path == "config.py"
        assert service.db is None
    
    def test_get_available_symbols_structure(self, service):
        """Test get_available_symbols returns correct structure"""
        result = service.get_available_symbols()
        
        # Check structure
        assert "symbols" in result
        assert "count" in result
        assert isinstance(result["symbols"], list)
        assert result["count"] > 0
        
        # Check each symbol has required fields
        for symbol in result["symbols"]:
            assert "symbol" in symbol
            assert "exchange" in symbol
            assert "volume24h" in symbol
            assert "price" in symbol
            assert "change24h" in symbol
            assert "win_rate" in symbol
            assert "total_trades" in symbol
            assert "total_pnl" in symbol
    
    def test_get_available_symbols_sorted(self, service):
        """Test available symbols are sorted alphabetically"""
        result = service.get_available_symbols()
        symbols = [s["symbol"] for s in result["symbols"]]
        
        assert symbols == sorted(symbols)
    
    def test_get_monitored_symbols_structure(self, service):
        """Test get_monitored_symbols returns correct structure"""
        mock_config = MagicMock()
        mock_config.FIXED_SYMBOLS = ["BTCUSDT", "ETHUSDT"]
        mock_config.DYNAMIC_SYMBOLS_CONFIG = {
            "top_gainers": 10,
            "top_losers": 10,
            "update_interval_minutes": 60
        }
        mock_config.SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        
        with patch.dict('sys.modules', {'config': mock_config}):
            result = service.get_monitored_symbols()
            
            # Check structure
            assert "fixed_symbols" in result
            assert "dynamic_config" in result
            assert "all_symbols" in result
            assert "count" in result
            
            assert result["fixed_symbols"] == ["BTCUSDT", "ETHUSDT"]
            assert result["count"] == 3
    
    def test_update_monitored_symbols_success(self, service):
        """Test successful symbols update"""
        mock_config = MagicMock()
        
        with patch.dict('sys.modules', {'config': mock_config}):
            with patch.object(service, '_persist_to_file'):
                result = service.update_monitored_symbols(["BTCUSDT", "ETHUSDT"])
                
                assert result["success"] is True
                assert "symbols" in result
                assert "count" in result
                assert "message" in result
                assert "timestamp" in result
                assert result["count"] == 2
    
    def test_update_monitored_symbols_empty_list(self, service):
        """Test update fails with empty list"""
        result = service.update_monitored_symbols([])
        
        assert result["success"] is False
        assert "error" in result
        assert "non-empty list" in result["error"].lower()
    
    def test_update_monitored_symbols_not_list(self, service):
        """Test update fails with non-list input"""
        result = service.update_monitored_symbols("BTCUSDT")
        
        assert result["success"] is False
        assert "error" in result
    
    def test_update_monitored_symbols_too_many(self, service):
        """Test update fails with too many symbols"""
        symbols = [f"SYM{i}USDT" for i in range(101)]
        result = service.update_monitored_symbols(symbols)
        
        assert result["success"] is False
        assert "error" in result
        assert "maximum 100" in result["error"].lower()
    
    def test_update_monitored_symbols_invalid_format(self, service):
        """Test update fails with invalid symbol format"""
        result = service.update_monitored_symbols(["BTCUSD", "ETHUSDT"])
        
        assert result["success"] is False
        assert "error" in result
        assert "invalid symbol format" in result["error"].lower()
    
    def test_get_symbol_metrics_no_db(self, service):
        """Test metrics return zeros without database"""
        metrics = service._get_symbol_metrics("BTCUSDT")
        
        assert metrics["volume24h"] == 0
        assert metrics["price"] == 0
        assert metrics["change24h"] == 0
        assert metrics["win_rate"] == 0
        assert metrics["total_trades"] == 0
        assert metrics["total_pnl"] == 0
    
    def test_get_symbol_metrics_with_db(self, mock_db):
        """Test metrics calculation with database"""
        service = SymbolConfigService(db=mock_db)
        metrics = service._get_symbol_metrics("BTCUSDT")
        
        assert metrics["total_trades"] == 100
        assert metrics["win_rate"] == 60.0
        assert metrics["total_pnl"] == 15.5
    
    def test_update_in_memory(self, service):
        """Test in-memory config update"""
        mock_config = MagicMock()
        
        with patch.dict('sys.modules', {'config': mock_config}):
            service._update_in_memory(["BTCUSDT", "ETHUSDT"])
            
            assert mock_config.FIXED_SYMBOLS == ["BTCUSDT", "ETHUSDT"]
            assert mock_config.SYMBOLS == ["BTCUSDT", "ETHUSDT"]
    
    def test_persist_to_file_success(self, service):
        """Test successful file persistence"""
        mock_content = 'FIXED_SYMBOLS = [\n    "BTCUSDT",\n    "ETHUSDT",\n]\n'
        
        with patch("builtins.open", mock_open(read_data=mock_content)) as mock_file:
            service._persist_to_file(["SOLUSDT", "BNBUSDT"])
            
            # Verify file was opened for reading and writing
            assert mock_file.call_count == 2
    
    def test_persist_to_file_not_found(self, service):
        """Test persistence handles missing FIXED_SYMBOLS"""
        mock_content = "# Config file without FIXED_SYMBOLS\n"
        
        with patch("builtins.open", mock_open(read_data=mock_content)):
            with pytest.raises(IOError, match="Failed to persist configuration"):
                service._persist_to_file(["BTCUSDT"])
    
    def test_persist_to_file_io_error(self, service):
        """Test persistence handles IO errors"""
        with patch("builtins.open", side_effect=FileNotFoundError()):
            with pytest.raises(IOError, match="Configuration file not found"):
                service._persist_to_file(["BTCUSDT"])
    
    def test_get_symbol_performance_no_db(self, service):
        """Test performance query without database"""
        result = service.get_symbol_performance("BTCUSDT")
        
        assert result["symbol"] == "BTCUSDT"
        assert "error" in result
        assert "Database not available" in result["error"]
    
    def test_get_symbol_performance_no_trades(self):
        """Test performance query with no trading history"""
        mock_db = Mock()
        mock_conn = Mock()
        mock_db._get_conn.return_value = mock_conn
        
        # Mock no trades
        mock_result = Mock()
        mock_result.fetchone.return_value = {"total_trades": 0}
        mock_conn.execute.return_value = mock_result
        
        service = SymbolConfigService(db=mock_db)
        result = service.get_symbol_performance("BTCUSDT")
        
        assert result["symbol"] == "BTCUSDT"
        assert result["total_trades"] == 0
        assert "message" in result
    
    def test_get_symbol_performance_with_trades(self):
        """Test performance query with trading history"""
        mock_db = Mock()
        mock_conn = Mock()
        mock_db._get_conn.return_value = mock_conn
        
        # Mock comprehensive stats
        mock_result1 = Mock()
        mock_result1.fetchone.return_value = {
            "total_trades": 100,
            "wins": 60,
            "losses": 40,
            "total_pnl": 15.5,
            "avg_pnl": 0.155,
            "best_trade": 5.2,
            "worst_trade": -3.1,
            "avg_duration": 120.5,
            "avg_rr": 1.8
        }
        
        # Mock winning PnL
        mock_result2 = Mock()
        mock_result2.fetchone.return_value = {"sum_wins": 25.0}
        
        # Mock losing PnL
        mock_result3 = Mock()
        mock_result3.fetchone.return_value = {"sum_losses": -9.5}
        
        mock_conn.execute.side_effect = [mock_result1, mock_result2, mock_result3]
        
        service = SymbolConfigService(db=mock_db)
        result = service.get_symbol_performance("BTCUSDT")
        
        assert result["symbol"] == "BTCUSDT"
        assert result["total_trades"] == 100
        assert result["wins"] == 60
        assert result["losses"] == 40
        assert result["win_rate"] == 60.0
        assert result["total_pnl"] == 15.5
        assert result["profit_factor"] > 0


class TestSymbolValidation:
    """Test symbol validation logic"""
    
    def test_valid_symbols(self):
        """Test validation passes for valid symbols"""
        service = SymbolConfigService()
        
        valid_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        
        with patch.object(service, '_persist_to_file'):
            with patch.object(service, '_update_in_memory'):
                result = service.update_monitored_symbols(valid_symbols)
                assert result["success"] is True
    
    def test_invalid_symbol_format(self):
        """Test validation fails for invalid formats"""
        service = SymbolConfigService()
        
        # Test symbols that don't end with USDT
        invalid_symbols = ["BTCUSD", "ETHBTC", "SOL", "BTC-USD", ""]
        
        # Mock the file operations to prevent actual file writes
        with patch.object(service, '_persist_to_file'):
            with patch.object(service, '_update_in_memory'):
                for symbol in invalid_symbols:
                    result = service.update_monitored_symbols([symbol])
                    assert result["success"] is False, f"Expected failure for '{symbol}', got: {result}"
                    assert "error" in result
                    # Check for either "invalid symbol format" or "non-empty list" error for empty string
                    assert ("invalid symbol format" in result["error"].lower() or 
                            "non-empty list" in result["error"].lower())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])