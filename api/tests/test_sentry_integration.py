"""
Tests for Sentry Error Tracking Integration

Tests the Sentry configuration and error capture functionality.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from api.utils.sentry_config import (
    init_sentry,
    filter_transactions,
    filter_errors,
    capture_exception,
    capture_message,
    set_user_context,
    add_breadcrumb
)


class TestSentryInitialization:
    """Test Sentry initialization"""
    
    def test_init_sentry_without_dsn(self):
        """Test that Sentry is not initialized without DSN"""
        with patch.dict(os.environ, {"SENTRY_DSN": ""}, clear=True):
            with patch("api.utils.sentry_config.sentry_sdk.init") as mock_init:
                init_sentry()
                mock_init.assert_not_called()
    
    def test_init_sentry_with_dsn(self):
        """Test that Sentry is initialized with DSN"""
        test_dsn = "https://test@sentry.io/123"
        with patch.dict(os.environ, {
            "SENTRY_DSN": test_dsn,
            "SENTRY_ENVIRONMENT": "test",
            "SENTRY_TRACES_SAMPLE_RATE": "0.5",
            "SENTRY_PROFILES_SAMPLE_RATE": "0.3"
        }):
            with patch("api.utils.sentry_config.sentry_sdk.init") as mock_init:
                init_sentry()
                mock_init.assert_called_once()
                
                # Verify initialization parameters
                call_kwargs = mock_init.call_args[1]
                assert call_kwargs["dsn"] == test_dsn
                assert call_kwargs["environment"] == "test"
                assert call_kwargs["traces_sample_rate"] == 0.5
                assert call_kwargs["profiles_sample_rate"] == 0.3
                assert call_kwargs["send_default_pii"] is False
                assert call_kwargs["attach_stacktrace"] is True
                assert call_kwargs["enable_tracing"] is True
    
    def test_init_sentry_default_values(self):
        """Test Sentry initialization with default values"""
        test_dsn = "https://test@sentry.io/123"
        with patch.dict(os.environ, {"SENTRY_DSN": test_dsn}, clear=True):
            with patch("api.utils.sentry_config.sentry_sdk.init") as mock_init:
                init_sentry()
                
                call_kwargs = mock_init.call_args[1]
                assert call_kwargs["environment"] == "development"
                assert call_kwargs["traces_sample_rate"] == 0.1
                assert call_kwargs["profiles_sample_rate"] == 0.1


class TestTransactionFiltering:
    """Test transaction filtering"""
    
    def test_filter_health_check_endpoints(self):
        """Test that health check endpoints are filtered out"""
        health_endpoints = ["/", "/api/health", "/health", "/metrics", "/ping"]
        
        for endpoint in health_endpoints:
            event = {"transaction": endpoint}
            result = filter_transactions(event, {})
            assert result is None, f"Endpoint {endpoint} should be filtered"
    
    def test_allow_normal_endpoints(self):
        """Test that normal endpoints are not filtered"""
        normal_endpoints = [
            "/api/signals/active",
            "/api/positions/open",
            "/api/analytics/metrics",
            "/api/config/feature-flags"
        ]
        
        for endpoint in normal_endpoints:
            event = {"transaction": endpoint}
            result = filter_transactions(event, {})
            assert result is not None, f"Endpoint {endpoint} should not be filtered"
            assert result == event


class TestErrorFiltering:
    """Test error filtering"""
    
    def test_filter_websocket_disconnect(self):
        """Test that WebSocket disconnect errors are filtered"""
        class WebSocketDisconnect(Exception):
            pass
        
        exc = WebSocketDisconnect("Client disconnected")
        hint = {"exc_info": (WebSocketDisconnect, exc, None)}
        event = {}
        
        result = filter_errors(event, hint)
        assert result is None
    
    def test_filter_client_disconnect(self):
        """Test that client disconnect errors are filtered"""
        exc = Exception("Client disconnected unexpectedly")
        hint = {"exc_info": (Exception, exc, None)}
        event = {}
        
        result = filter_errors(event, hint)
        assert result is None
    
    def test_filter_rate_limit_errors(self):
        """Test that rate limit errors are filtered"""
        exc = Exception("Rate limit exceeded")
        hint = {"exc_info": (Exception, exc, None)}
        event = {}
        
        result = filter_errors(event, hint)
        assert result is None
    
    def test_allow_normal_errors(self):
        """Test that normal errors are not filtered"""
        exc = ValueError("Invalid input")
        hint = {"exc_info": (ValueError, exc, None)}
        event = {}
        
        result = filter_errors(event, hint)
        assert result is not None
        assert result["tags"]["component"] == "backend"
        assert result["tags"]["service"] == "openclaw-dashboard"
    
    def test_add_custom_tags(self):
        """Test that custom tags are added to errors"""
        hint = {}
        event = {}
        
        result = filter_errors(event, hint)
        assert "tags" in result
        assert result["tags"]["component"] == "backend"
        assert result["tags"]["service"] == "openclaw-dashboard"


class TestManualCapture:
    """Test manual error and message capture"""
    
    def test_capture_exception_basic(self):
        """Test basic exception capture"""
        with patch("api.utils.sentry_config.sentry_sdk.capture_exception") as mock_capture:
            error = ValueError("Test error")
            capture_exception(error)
            mock_capture.assert_called_once_with(error)
    
    def test_capture_exception_with_context(self):
        """Test exception capture with context"""
        with patch("api.utils.sentry_config.sentry_sdk.push_scope") as mock_scope:
            mock_scope_instance = MagicMock()
            mock_scope.return_value.__enter__.return_value = mock_scope_instance
            
            error = ValueError("Test error")
            context = {
                "tags": {"operation": "test", "symbol": "BTCUSDT"},
                "extra": {"user_id": "123", "retry_count": 3}
            }
            
            capture_exception(error, context)
            
            # Verify tags were set
            assert mock_scope_instance.set_tag.call_count == 2
            mock_scope_instance.set_tag.assert_any_call("operation", "test")
            mock_scope_instance.set_tag.assert_any_call("symbol", "BTCUSDT")
            
            # Verify extra data was set
            assert mock_scope_instance.set_extra.call_count == 2
            mock_scope_instance.set_extra.assert_any_call("user_id", "123")
            mock_scope_instance.set_extra.assert_any_call("retry_count", 3)
    
    def test_capture_message_basic(self):
        """Test basic message capture"""
        with patch("api.utils.sentry_config.sentry_sdk.capture_message") as mock_capture:
            capture_message("Test message")
            mock_capture.assert_called_once_with("Test message", level="info")
    
    def test_capture_message_with_level(self):
        """Test message capture with custom level"""
        with patch("api.utils.sentry_config.sentry_sdk.capture_message") as mock_capture:
            capture_message("Warning message", level="warning")
            mock_capture.assert_called_once_with("Warning message", level="warning")
    
    def test_capture_message_with_context(self):
        """Test message capture with context"""
        with patch("api.utils.sentry_config.sentry_sdk.push_scope") as mock_scope:
            mock_scope_instance = MagicMock()
            mock_scope.return_value.__enter__.return_value = mock_scope_instance
            
            context = {
                "tags": {"component": "trading"},
                "extra": {"volume": 1000000}
            }
            
            capture_message("High volume", level="warning", context=context)
            
            mock_scope_instance.set_tag.assert_called_once_with("component", "trading")
            mock_scope_instance.set_extra.assert_called_once_with("volume", 1000000)


class TestUserContext:
    """Test user context setting"""
    
    def test_set_user_context_full(self):
        """Test setting full user context"""
        with patch("api.utils.sentry_config.sentry_sdk.set_user") as mock_set_user:
            set_user_context(
                user_id="user_123",
                email="trader@example.com",
                username="trader1"
            )
            
            mock_set_user.assert_called_once_with({
                "id": "user_123",
                "email": "trader@example.com",
                "username": "trader1"
            })
    
    def test_set_user_context_minimal(self):
        """Test setting minimal user context"""
        with patch("api.utils.sentry_config.sentry_sdk.set_user") as mock_set_user:
            set_user_context(user_id="user_123")
            
            mock_set_user.assert_called_once_with({
                "id": "user_123",
                "email": None,
                "username": None
            })


class TestBreadcrumbs:
    """Test breadcrumb functionality"""
    
    def test_add_breadcrumb_basic(self):
        """Test adding basic breadcrumb"""
        with patch("api.utils.sentry_config.sentry_sdk.add_breadcrumb") as mock_add:
            add_breadcrumb("User action")
            
            mock_add.assert_called_once_with(
                message="User action",
                category="default",
                level="info",
                data={}
            )
    
    def test_add_breadcrumb_with_details(self):
        """Test adding breadcrumb with details"""
        with patch("api.utils.sentry_config.sentry_sdk.add_breadcrumb") as mock_add:
            add_breadcrumb(
                message="Order placed",
                category="trading",
                level="info",
                data={"symbol": "BTCUSDT", "side": "BUY"}
            )
            
            mock_add.assert_called_once_with(
                message="Order placed",
                category="trading",
                level="info",
                data={"symbol": "BTCUSDT", "side": "BUY"}
            )


class TestIntegrationScenarios:
    """Test real-world integration scenarios"""
    
    def test_trading_error_scenario(self):
        """Test error capture in trading scenario"""
        with patch("api.utils.sentry_config.sentry_sdk.push_scope") as mock_scope:
            mock_scope_instance = MagicMock()
            mock_scope.return_value.__enter__.return_value = mock_scope_instance
            
            # Simulate trading error
            error = Exception("Order execution failed")
            context = {
                "tags": {
                    "component": "execution",
                    "symbol": "BTCUSDT",
                    "side": "LONG"
                },
                "extra": {
                    "signal_id": "sig_123",
                    "entry_price": 50000.0,
                    "quantity": 0.1
                }
            }
            
            capture_exception(error, context)
            
            # Verify all context was set
            assert mock_scope_instance.set_tag.call_count == 3
            assert mock_scope_instance.set_extra.call_count == 3
    
    def test_performance_warning_scenario(self):
        """Test message capture for performance warning"""
        with patch("api.utils.sentry_config.sentry_sdk.push_scope") as mock_scope:
            mock_scope_instance = MagicMock()
            mock_scope.return_value.__enter__.return_value = mock_scope_instance
            
            # Simulate performance warning
            context = {
                "tags": {"component": "market_data"},
                "extra": {"latency_ms": 5000, "threshold_ms": 1000}
            }
            
            capture_message(
                "High latency detected",
                level="warning",
                context=context
            )
            
            mock_scope_instance.set_tag.assert_called_once()
            assert mock_scope_instance.set_extra.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
