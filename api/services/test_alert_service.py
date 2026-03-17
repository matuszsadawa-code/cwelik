"""
Tests for Alert Service

Tests alert creation, storage, retrieval, and threshold management.
"""

import pytest
from api.services.alert_service import AlertService


@pytest.fixture
def mock_db():
    """Create mock database"""
    class MockDB:
        def __init__(self):
            self.alerts = []
            self.conn_called = False
        
        def _get_conn(self):
            self.conn_called = True
            return MockConnection(self.alerts)
    
    class MockConnection:
        def __init__(self, alerts):
            self.alerts = alerts
        
        def execute(self, query, params=None):
            if "CREATE TABLE" in query or "CREATE INDEX" in query:
                return MockCursor()
            if "INSERT INTO" in query:
                # Store alert
                self.alerts.append(params)
                return MockCursor()
            if "SELECT" in query:
                # Return alerts
                return MockCursor(self.alerts)
            if "UPDATE" in query:
                return MockCursor()
            return MockCursor()
        
        def commit(self):
            pass
    
    class MockCursor:
        def __init__(self, data=None):
            self.data = data or []
            self.rowcount = 1
        
        def fetchall(self):
            return [{"alert_id": "test-123", "severity": "info", "category": "signal",
                    "message": "Test alert", "details": "{}", "dismissed": 0,
                    "created_at": "2024-01-01T00:00:00"}]
    
    return MockDB()


@pytest.fixture
def service(mock_db):
    """Create alert service instance"""
    return AlertService(db=mock_db)


def test_create_alert(service):
    """Test creating an alert"""
    alert = service.create_alert(
        severity="info",
        category="signal",
        message="Test alert",
        details={"symbol": "BTCUSDT"}
    )
    
    assert alert["severity"] == "info"
    assert alert["category"] == "signal"
    assert alert["message"] == "Test alert"
    assert alert["details"]["symbol"] == "BTCUSDT"
    assert "alert_id" in alert
    assert "timestamp" in alert


def test_create_alert_invalid_severity(service):
    """Test creating alert with invalid severity"""
    with pytest.raises(ValueError):
        service.create_alert(
            severity="invalid",
            category="signal",
            message="Test"
        )


def test_create_alert_invalid_category(service):
    """Test creating alert with invalid category"""
    with pytest.raises(ValueError):
        service.create_alert(
            severity="info",
            category="invalid",
            message="Test"
        )


def test_get_alert_history(service):
    """Test retrieving alert history"""
    alerts = service.get_alert_history(limit=10)
    
    assert isinstance(alerts, list)


def test_get_alert_history_with_filters(service):
    """Test retrieving alert history with filters"""
    alerts = service.get_alert_history(
        limit=10,
        severity="warning",
        category="risk"
    )
    
    assert isinstance(alerts, list)


def test_get_thresholds(service):
    """Test getting alert thresholds"""
    thresholds = service.get_thresholds()
    
    assert "drawdown_threshold" in thresholds
    assert "daily_loss_threshold" in thresholds
    assert "api_success_rate_threshold" in thresholds
    assert "api_response_time_threshold" in thresholds
    assert "health_score_threshold" in thresholds


def test_update_thresholds_valid(service):
    """Test updating thresholds with valid values"""
    result = service.update_thresholds({
        "drawdown_threshold": 25.0,
        "daily_loss_threshold": 7.0
    })
    
    assert result["success"] is True
    assert result["thresholds"]["drawdown_threshold"] == 25.0
    assert result["thresholds"]["daily_loss_threshold"] == 7.0


def test_update_thresholds_invalid_key(service):
    """Test updating thresholds with invalid key"""
    result = service.update_thresholds({
        "invalid_threshold": 10.0
    })
    
    assert result["success"] is False
    assert "error" in result


def test_update_thresholds_invalid_value(service):
    """Test updating thresholds with invalid value"""
    result = service.update_thresholds({
        "drawdown_threshold": -5.0  # Negative value
    })
    
    assert result["success"] is False
    assert "error" in result


def test_check_drawdown_exceeded(service):
    """Test checking drawdown threshold"""
    # Should create alert when threshold exceeded
    service.check_drawdown_exceeded(25.0)  # Above default 15%
    
    # No exception should be raised


def test_check_daily_loss_exceeded(service):
    """Test checking daily loss threshold"""
    # Should create alert when threshold exceeded
    service.check_daily_loss_exceeded(7.0)  # Above default 5%
    
    # No exception should be raised


def test_check_health_degradation(service):
    """Test checking health degradation"""
    health_metrics = {
        "api_success_rate": {
            "binance": 90.0,  # Below 95% threshold
            "bybit": 98.0
        },
        "api_response_time": {
            "binance": 1500,  # Above 1000ms threshold
            "bybit": 500
        }
    }
    
    service.check_health_degradation(health_metrics)
    
    # No exception should be raised


def test_check_api_failure(service):
    """Test checking API failure"""
    service.check_api_failure("binance", "Connection timeout")
    
    # No exception should be raised
