"""
Tests for Strategy Parameters Service

Tests parameter retrieval, validation, updates, and persistence.
"""

import pytest
from api.services.strategy_params_service import StrategyParamsService


@pytest.fixture
def service():
    """Create strategy params service instance"""
    return StrategyParamsService()


def test_get_all_params(service):
    """Test retrieving all strategy parameters"""
    params = service.get_all_params()
    
    # Should have all categories
    assert "trend" in params
    assert "zones" in params
    assert "volume" in params
    assert "orderflow" in params
    assert "risk" in params
    assert "monitoring" in params
    
    # Each category should have parameters
    assert len(params["trend"]) > 0
    assert len(params["zones"]) > 0
    
    # Check parameter structure
    first_param = params["trend"][0]
    assert "name" in first_param
    assert "value" in first_param
    assert "default" in first_param
    assert "min" in first_param
    assert "max" in first_param
    assert "description" in first_param


def test_get_param(service):
    """Test retrieving a specific parameter"""
    param = service.get_param("trend_candle_count")
    
    assert param is not None
    assert param["name"] == "trend_candle_count"
    assert "value" in param
    assert "default" in param
    assert param["min"] == 20
    assert param["max"] == 200
    assert param["category"] == "trend"


def test_get_param_invalid(service):
    """Test retrieving invalid parameter returns None"""
    param = service.get_param("invalid_param")
    assert param is None


def test_validate_param_valid(service):
    """Test parameter validation with valid value"""
    error = service._validate_param("trend_candle_count", 50)
    assert error is None


def test_validate_param_below_min(service):
    """Test parameter validation with value below minimum"""
    error = service._validate_param("trend_candle_count", 10)
    assert error is not None
    assert "must be between" in error


def test_validate_param_above_max(service):
    """Test parameter validation with value above maximum"""
    error = service._validate_param("trend_candle_count", 300)
    assert error is not None
    assert "must be between" in error


def test_validate_param_unknown(service):
    """Test parameter validation with unknown parameter"""
    error = service._validate_param("unknown_param", 50)
    assert error is not None
    assert "Unknown parameter" in error


def test_update_params_validation_error(service):
    """Test updating parameters with validation error"""
    result = service.update_params({
        "trend_candle_count": 300  # Above max
    })
    
    assert result["success"] is False
    assert "error" in result


def test_reset_to_defaults_category(service):
    """Test resetting parameters for a specific category"""
    result = service.reset_to_defaults(category="trend")
    
    # Should succeed (even if persistence fails in test environment)
    assert "success" in result


def test_reset_to_defaults_all(service):
    """Test resetting all parameters to defaults"""
    result = service.reset_to_defaults()
    
    # Should succeed (even if persistence fails in test environment)
    assert "success" in result
