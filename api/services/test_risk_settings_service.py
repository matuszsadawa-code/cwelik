"""
Unit tests for Risk Settings Service

Tests risk management settings retrieval, validation, and updates.
"""

import pytest
import sys
from unittest.mock import Mock, patch, mock_open, MagicMock
from api.services.risk_settings_service import RiskSettingsService


class TestRiskSettingsService:
    """Test suite for RiskSettingsService"""
    
    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        return RiskSettingsService(db=None)
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database"""
        db = Mock()
        db.get_executions.return_value = []
        db.get_equity_history.return_value = []
        return db
    
    def test_service_initialization(self, service):
        """Test service initializes correctly"""
        assert service is not None
        assert service.config_path == "config.py"
        assert service.db is None
    
    def test_get_all_settings_structure(self, service):
        """Test get_all_settings returns correct structure"""
        # Create a mock config module
        mock_config = MagicMock()
        mock_config.MAX_POSITION_SIZE = 10.0
        mock_config.MAX_PORTFOLIO_EXPOSURE = 100.0
        mock_config.MAX_DRAWDOWN_LIMIT = 20.0
        mock_config.MAX_DAILY_LOSS_LIMIT = 5.0
        mock_config.CORRELATION_THRESHOLD = 0.7
        
        with patch.dict('sys.modules', {'config': mock_config}):
            result = service.get_all_settings()
            
            # Check structure
            assert "settings" in result
            assert "current_utilization" in result
            assert isinstance(result["settings"], list)
            assert len(result["settings"]) == 5
            
            # Check each setting has required fields
            for setting in result["settings"]:
                assert "name" in setting
                assert "value" in setting
                assert "default" in setting
                assert "min" in setting
                assert "max" in setting
                assert "description" in setting
                assert "unit" in setting
    
    def test_get_setting_valid(self, service):
        """Test getting a valid setting"""
        mock_config = MagicMock()
        mock_config.MAX_POSITION_SIZE = 10.0
        
        with patch.dict('sys.modules', {'config': mock_config}):
            result = service.get_setting("max_position_size")
            
            assert result is not None
            assert result["name"] == "max_position_size"
            assert result["value"] == 10.0
            assert result["min"] == 0.01
            assert result["max"] == 100.0
    
    def test_get_setting_invalid(self, service):
        """Test getting an invalid setting returns None"""
        result = service.get_setting("invalid_setting")
        assert result is None
    
    def test_validate_setting_valid(self, service):
        """Test validation passes for valid values"""
        error = service._validate_setting("max_position_size", 10.0)
        assert error is None
        
        error = service._validate_setting("correlation_threshold", 0.5)
        assert error is None
    
    def test_validate_setting_out_of_range(self, service):
        """Test validation fails for out-of-range values"""
        # Too low
        error = service._validate_setting("max_position_size", 0.001)
        assert error is not None
        assert "must be between" in error
        
        # Too high
        error = service._validate_setting("max_position_size", 150.0)
        assert error is not None
        assert "must be between" in error
    
    def test_validate_setting_invalid_type(self, service):
        """Test validation fails for invalid types"""
        error = service._validate_setting("max_position_size", "invalid")
        assert error is not None
        assert "Invalid value" in error
    
    def test_validate_setting_unknown(self, service):
        """Test validation fails for unknown settings"""
        error = service._validate_setting("unknown_setting", 10.0)
        assert error is not None
        assert "Unknown risk setting" in error
    
    def test_update_settings_success(self, service):
        """Test successful settings update"""
        mock_config = MagicMock()
        mock_config.MAX_POSITION_SIZE = 10.0
        
        with patch.dict('sys.modules', {'config': mock_config}):
            with patch.object(service, '_persist_to_file'):
                result = service.update_settings({
                    "max_position_size": 15.0
                })
                
                assert result["success"] is True
                assert "updated" in result
                assert "message" in result
                assert "timestamp" in result
    
    def test_update_settings_validation_error(self, service):
        """Test update fails with validation error"""
        result = service.update_settings({
            "max_position_size": 200.0  # Out of range
        })
        
        assert result["success"] is False
        assert "error" in result
        assert "must be between" in result["error"]
    
    def test_update_settings_multiple(self, service):
        """Test updating multiple settings"""
        mock_config = MagicMock()
        mock_config.MAX_POSITION_SIZE = 10.0
        mock_config.MAX_PORTFOLIO_EXPOSURE = 100.0
        
        with patch.dict('sys.modules', {'config': mock_config}):
            with patch.object(service, '_persist_to_file'):
                result = service.update_settings({
                    "max_position_size": 12.0,
                    "max_portfolio_exposure": 120.0
                })
                
                assert result["success"] is True
                assert len(result["updated"]) == 2
    
    def test_check_position_violations_no_db(self, service):
        """Test position violation check with no database"""
        warnings = service._check_position_violations({
            "max_position_size": 5.0
        })
        
        assert warnings == []
    
    def test_check_position_violations_no_positions(self):
        """Test position violation check with no open positions"""
        mock_db = Mock()
        mock_db.get_executions.return_value = []
        
        service = RiskSettingsService(db=mock_db)
        warnings = service._check_position_violations({
            "max_position_size": 5.0
        })
        
        assert warnings == []
    
    def test_check_position_violations_with_violations(self):
        """Test position violation detection"""
        mock_db = Mock()
        mock_db.get_executions.return_value = [
            {"symbol": "BTCUSDT", "qty": 1.0, "entry_price": 50000}
        ]
        
        service = RiskSettingsService(db=mock_db)
        warnings = service._check_position_violations({
            "max_position_size": 3.0  # Position is 5% (50000/10000)
        })
        
        assert len(warnings) > 0
        assert "BTCUSDT" in warnings[0]
    
    def test_get_current_utilization_no_db(self, service):
        """Test utilization calculation with no database"""
        utilization = service._get_current_utilization()
        
        assert utilization["portfolio_exposure"] == 0.0
        assert utilization["current_drawdown"] == 0.0
        assert utilization["daily_loss"] == 0.0
        assert utilization["open_positions"] == 0
    
    def test_get_current_utilization_with_positions(self):
        """Test utilization calculation with open positions"""
        mock_db = Mock()
        mock_db.get_executions.return_value = [
            {"symbol": "BTCUSDT", "qty": 0.1, "entry_price": 50000},
            {"symbol": "ETHUSDT", "qty": 1.0, "entry_price": 3000}
        ]
        mock_db.get_equity_history.return_value = [
            {"equity": 10000},
            {"equity": 9500}
        ]
        
        service = RiskSettingsService(db=mock_db)
        utilization = service._get_current_utilization()
        
        assert utilization["open_positions"] == 2
        assert utilization["portfolio_exposure"] > 0
        assert utilization["current_drawdown"] >= 0
    
    def test_persist_to_file_success(self, service):
        """Test successful file persistence"""
        mock_content = "MAX_POSITION_SIZE = 10.0\n"
        
        with patch("builtins.open", mock_open(read_data=mock_content)) as mock_file:
            service._persist_to_file("max_position_size", 15.0)
            
            # Verify file was opened for reading and writing
            assert mock_file.call_count == 2
    
    def test_persist_to_file_setting_not_found(self, service):
        """Test persistence when setting not in config file"""
        mock_content = "# Config file without the setting\n"
        
        with patch("builtins.open", mock_open(read_data=mock_content)):
            # Should not raise exception, just log warning
            service._persist_to_file("max_position_size", 15.0)
    
    def test_persist_to_file_io_error(self, service):
        """Test persistence handles IO errors"""
        with patch("builtins.open", side_effect=IOError("File error")):
            with pytest.raises(IOError):
                service._persist_to_file("max_position_size", 15.0)
    
    def test_update_in_memory(self, service):
        """Test in-memory config update"""
        mock_config = MagicMock()
        
        with patch.dict('sys.modules', {'config': mock_config}):
            service._update_in_memory("max_position_size", 15.0)
            
            # Verify setattr was called on the mock config
            # The actual value should be set as MAX_POSITION_SIZE
            assert mock_config.MAX_POSITION_SIZE == 15.0


class TestRiskSettingsDefinitions:
    """Test risk settings definitions"""
    
    def test_all_settings_have_required_fields(self):
        """Test all risk settings have required metadata"""
        service = RiskSettingsService()
        
        for setting_name, definition in service.RISK_DEFINITIONS.items():
            assert "min" in definition
            assert "max" in definition
            assert "default" in definition
            assert "description" in definition
            assert "unit" in definition
            
            # Validate ranges
            assert definition["min"] < definition["max"]
            assert definition["min"] <= definition["default"] <= definition["max"]
    
    def test_setting_names(self):
        """Test expected risk settings are defined"""
        service = RiskSettingsService()
        
        expected_settings = [
            "max_position_size",
            "max_portfolio_exposure",
            "max_drawdown_limit",
            "max_daily_loss_limit",
            "correlation_threshold"
        ]
        
        for setting in expected_settings:
            assert setting in service.RISK_DEFINITIONS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
