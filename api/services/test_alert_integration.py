"""
Integration Tests for Alert Service

Tests alert detection, broadcasting, and storage in realistic scenarios.
"""

import pytest
from api.services.alert_service import AlertService
from storage.database import Database


@pytest.fixture
def db():
    """Create test database"""
    return Database()


@pytest.fixture
def alert_service(db):
    """Create alert service with real database"""
    return AlertService(db=db)


def test_signal_alert_creation(alert_service):
    """Test creating alert for new signal generation"""
    signal = {
        "signal_id": "test-signal-123",
        "symbol": "BTCUSDT",
        "signal_type": "LONG",
        "quality": "A+",
        "confidence": 0.85
    }
    
    alert_service.check_signal_generated(signal)
    
    # Verify alert was stored
    alerts = alert_service.get_alert_history(limit=1, category="signal")
    assert len(alerts) > 0
    assert alerts[0]["category"] == "signal"
    assert "BTCUSDT" in alerts[0]["message"]


def test_position_tp_alert(alert_service):
    """Test creating alert for TP hit"""
    position = {
        "execution_id": "test-pos-123",
        "symbol": "ETHUSDT",
        "realised_pnl": 2.5
    }
    
    alert_service.check_position_tp_sl(position, "TP")
    
    # Verify alert was stored
    alerts = alert_service.get_alert_history(limit=1, category="position")
    assert len(alerts) > 0
    assert alerts[0]["severity"] == "info"
    assert "TP hit" in alerts[0]["message"]


def test_position_sl_alert(alert_service):
    """Test creating alert for SL hit"""
    position = {
        "execution_id": "test-pos-456",
        "symbol": "ETHUSDT",
        "realised_pnl": -1.2
    }
    
    alert_service.check_position_tp_sl(position, "SL")
    
    # Verify alert was stored
    alerts = alert_service.get_alert_history(limit=1, category="position")
    assert len(alerts) > 0
    assert alerts[0]["severity"] == "warning"
    assert "SL hit" in alerts[0]["message"]


def test_drawdown_alert(alert_service):
    """Test creating alert for drawdown threshold exceeded"""
    # Default threshold is 15%
    alert_service.check_drawdown_exceeded(20.0)
    
    # Verify alert was stored
    alerts = alert_service.get_alert_history(limit=1, category="risk")
    assert len(alerts) > 0
    assert alerts[0]["severity"] == "error"
    assert "Drawdown exceeded" in alerts[0]["message"]


def test_daily_loss_alert(alert_service):
    """Test creating alert for daily loss threshold exceeded"""
    # Default threshold is 5%
    alert_service.check_daily_loss_exceeded(7.0)
    
    # Verify alert was stored
    alerts = alert_service.get_alert_history(limit=1, category="risk")
    assert len(alerts) > 0
    assert alerts[0]["severity"] == "error"
    assert "Daily loss exceeded" in alerts[0]["message"]


def test_health_degradation_api_success_rate(alert_service):
    """Test creating alert for low API success rate"""
    health_metrics = {
        "api_success_rate": {
            "binance": 90.0,  # Below 95% threshold
            "bybit": 98.0
        },
        "api_response_time": {
            "binance": 500,
            "bybit": 600
        }
    }
    
    alert_service.check_health_degradation(health_metrics)
    
    # Verify alert was stored
    alerts = alert_service.get_alert_history(limit=1, category="health")
    assert len(alerts) > 0
    assert alerts[0]["severity"] == "warning"
    assert "success rate below threshold" in alerts[0]["message"]


def test_health_degradation_api_response_time(alert_service):
    """Test creating alert for high API response time"""
    health_metrics = {
        "api_success_rate": {
            "binance": 99.0,
            "bybit": 98.0
        },
        "api_response_time": {
            "binance": 1500,  # Above 1000ms threshold
            "bybit": 600
        }
    }
    
    alert_service.check_health_degradation(health_metrics)
    
    # Verify alert was stored
    alerts = alert_service.get_alert_history(limit=1, category="health")
    assert len(alerts) > 0
    assert alerts[0]["severity"] == "warning"
    assert "response time exceeded" in alerts[0]["message"]


def test_api_failure_alert(alert_service):
    """Test creating alert for API connection failure"""
    alert_service.check_api_failure("binance", "Connection timeout after 30s")
    
    # Verify alert was stored
    alerts = alert_service.get_alert_history(limit=1, category="system")
    assert len(alerts) > 0
    assert alerts[0]["severity"] == "error"
    assert "API connection failed" in alerts[0]["message"]


def test_alert_filtering_by_severity(alert_service):
    """Test filtering alerts by severity"""
    # Create alerts with different severities
    alert_service.create_alert("info", "signal", "Info alert")
    alert_service.create_alert("warning", "health", "Warning alert")
    alert_service.create_alert("error", "system", "Error alert")
    
    # Get only error alerts
    error_alerts = alert_service.get_alert_history(severity="error")
    assert all(a["severity"] == "error" for a in error_alerts)
    
    # Get only warning alerts
    warning_alerts = alert_service.get_alert_history(severity="warning")
    assert all(a["severity"] == "warning" for a in warning_alerts)


def test_alert_filtering_by_category(alert_service):
    """Test filtering alerts by category"""
    # Create alerts with different categories
    alert_service.create_alert("info", "signal", "Signal alert")
    alert_service.create_alert("warning", "position", "Position alert")
    alert_service.create_alert("error", "risk", "Risk alert")
    
    # Get only signal alerts
    signal_alerts = alert_service.get_alert_history(category="signal")
    assert all(a["category"] == "signal" for a in signal_alerts)
    
    # Get only risk alerts
    risk_alerts = alert_service.get_alert_history(category="risk")
    assert all(a["category"] == "risk" for a in risk_alerts)


def test_alert_dismiss(alert_service):
    """Test dismissing an alert"""
    # Create an alert
    alert = alert_service.create_alert("info", "signal", "Test alert")
    alert_id = alert["alert_id"]
    
    # Dismiss the alert
    success = alert_service.dismiss_alert(alert_id)
    assert success is True
    
    # Verify alert is dismissed
    dismissed_alerts = alert_service.get_alert_history(dismissed=True)
    assert any(a["alert_id"] == alert_id for a in dismissed_alerts)


def test_threshold_update(alert_service):
    """Test updating alert thresholds"""
    # Update thresholds
    result = alert_service.update_thresholds({
        "drawdown_threshold": 20.0,
        "daily_loss_threshold": 8.0
    })
    
    assert result["success"] is True
    assert result["thresholds"]["drawdown_threshold"] == 20.0
    assert result["thresholds"]["daily_loss_threshold"] == 8.0
    
    # Verify thresholds are applied
    thresholds = alert_service.get_thresholds()
    assert thresholds["drawdown_threshold"] == 20.0
    assert thresholds["daily_loss_threshold"] == 8.0


def test_multiple_alerts_same_category(alert_service):
    """Test creating multiple alerts in same category"""
    # Create multiple signal alerts
    for i in range(5):
        signal = {
            "signal_id": f"signal-{i}",
            "symbol": f"SYMBOL{i}",
            "signal_type": "LONG",
            "quality": "A",
            "confidence": 0.75
        }
        alert_service.check_signal_generated(signal)
    
    # Verify all alerts were stored
    alerts = alert_service.get_alert_history(category="signal", limit=10)
    assert len(alerts) >= 5


def test_alert_history_limit(alert_service):
    """Test alert history respects limit parameter"""
    # Create multiple alerts
    for i in range(20):
        alert_service.create_alert("info", "signal", f"Alert {i}")
    
    # Get limited results
    alerts = alert_service.get_alert_history(limit=5)
    assert len(alerts) <= 5


def test_alert_details_preserved(alert_service):
    """Test that alert details are preserved correctly"""
    details = {
        "symbol": "BTCUSDT",
        "price": 50000.0,
        "volume": 1000.0,
        "nested": {
            "key": "value"
        }
    }
    
    alert = alert_service.create_alert(
        "info",
        "signal",
        "Test with details",
        details=details
    )
    
    # Retrieve and verify details
    alerts = alert_service.get_alert_history(limit=1)
    assert len(alerts) > 0
    retrieved_alert = alerts[0]
    assert retrieved_alert["details"]["symbol"] == "BTCUSDT"
    assert retrieved_alert["details"]["price"] == 50000.0
    assert retrieved_alert["details"]["nested"]["key"] == "value"
