"""
Tests for Health Alerts Endpoint

Tests the GET /api/health/alerts endpoint for retrieving alert history.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app


client = TestClient(app)


def test_get_alerts_default():
    """Test getting alerts with default parameters"""
    response = client.get("/api/health/alerts")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "alerts" in data
    assert "count" in data
    assert "filters" in data
    assert isinstance(data["alerts"], list)
    assert data["filters"]["limit"] == 100
    assert data["filters"]["severity"] is None
    assert data["filters"]["category"] is None
    assert data["filters"]["dismissed"] is None


def test_get_alerts_with_limit():
    """Test getting alerts with custom limit"""
    response = client.get("/api/health/alerts?limit=50")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["filters"]["limit"] == 50
    assert len(data["alerts"]) <= 50


def test_get_alerts_with_severity_filter():
    """Test getting alerts filtered by severity"""
    response = client.get("/api/health/alerts?severity=error")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["filters"]["severity"] == "error"
    
    # All returned alerts should have error severity
    for alert in data["alerts"]:
        assert alert.get("severity") == "error"


def test_get_alerts_with_category_filter():
    """Test getting alerts filtered by category"""
    response = client.get("/api/health/alerts?category=signal")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["filters"]["category"] == "signal"
    
    # All returned alerts should have signal category
    for alert in data["alerts"]:
        assert alert.get("category") == "signal"


def test_get_alerts_with_dismissed_filter():
    """Test getting alerts filtered by dismissed status"""
    response = client.get("/api/health/alerts?dismissed=false")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["filters"]["dismissed"] is False
    
    # All returned alerts should not be dismissed
    for alert in data["alerts"]:
        assert alert.get("dismissed") is False


def test_get_alerts_with_multiple_filters():
    """Test getting alerts with multiple filters"""
    response = client.get("/api/health/alerts?severity=warning&category=health&limit=25")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["filters"]["severity"] == "warning"
    assert data["filters"]["category"] == "health"
    assert data["filters"]["limit"] == 25
    assert len(data["alerts"]) <= 25


def test_get_alerts_invalid_severity():
    """Test getting alerts with invalid severity"""
    response = client.get("/api/health/alerts?severity=invalid")
    
    assert response.status_code == 400
    assert "Invalid severity" in response.json()["detail"]


def test_get_alerts_invalid_category():
    """Test getting alerts with invalid category"""
    response = client.get("/api/health/alerts?category=invalid")
    
    assert response.status_code == 400
    assert "Invalid category" in response.json()["detail"]


def test_get_alerts_limit_too_low():
    """Test getting alerts with limit below minimum"""
    response = client.get("/api/health/alerts?limit=0")
    
    assert response.status_code == 422  # Validation error


def test_get_alerts_limit_too_high():
    """Test getting alerts with limit above maximum"""
    response = client.get("/api/health/alerts?limit=2000")
    
    assert response.status_code == 422  # Validation error


def test_get_alerts_response_structure():
    """Test that alert response has correct structure"""
    response = client.get("/api/health/alerts?limit=1")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check top-level structure
    assert "alerts" in data
    assert "count" in data
    assert "filters" in data
    
    # If there are alerts, check their structure
    if data["alerts"]:
        alert = data["alerts"][0]
        assert "alert_id" in alert
        assert "severity" in alert
        assert "category" in alert
        assert "message" in alert
        assert "details" in alert
        assert "dismissed" in alert
        assert "created_at" in alert
        
        # Check severity is valid
        assert alert["severity"] in ["info", "warning", "error"]
        
        # Check category is valid
        assert alert["category"] in ["signal", "position", "system", "risk", "health"]


def test_get_alerts_all_severities():
    """Test getting alerts for each severity level"""
    for severity in ["info", "warning", "error"]:
        response = client.get(f"/api/health/alerts?severity={severity}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["severity"] == severity


def test_get_alerts_all_categories():
    """Test getting alerts for each category"""
    for category in ["signal", "position", "system", "risk", "health"]:
        response = client.get(f"/api/health/alerts?category={category}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["category"] == category


def test_get_alerts_count_matches_length():
    """Test that count field matches actual number of alerts"""
    response = client.get("/api/health/alerts")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["count"] == len(data["alerts"])
