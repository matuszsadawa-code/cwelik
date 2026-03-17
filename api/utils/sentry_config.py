"""
Sentry Error Tracking Configuration

Configures Sentry SDK for error tracking and performance monitoring in production.
"""

import os
import logging
from typing import Optional
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """
    Initialize Sentry error tracking
    
    Configures Sentry SDK with FastAPI, SQLAlchemy, and logging integrations.
    Only initializes if SENTRY_DSN is provided in environment variables.
    
    Environment Variables:
        SENTRY_DSN: Sentry Data Source Name (required)
        SENTRY_ENVIRONMENT: Environment name (default: development)
        SENTRY_TRACES_SAMPLE_RATE: Performance monitoring sample rate (default: 0.1)
        SENTRY_PROFILES_SAMPLE_RATE: Profiling sample rate (default: 0.1)
        ENVIRONMENT: Application environment (fallback for SENTRY_ENVIRONMENT)
    """
    sentry_dsn = os.getenv("SENTRY_DSN", "").strip()
    
    # Skip initialization if DSN is not provided
    if not sentry_dsn:
        logger.info("Sentry DSN not configured - error tracking disabled")
        return
    
    # Get configuration from environment
    environment = os.getenv("SENTRY_ENVIRONMENT") or os.getenv("ENVIRONMENT", "development")
    traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    profiles_sample_rate = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))
    
    # Configure logging integration
    # Capture ERROR and CRITICAL logs automatically
    logging_integration = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors and above as events
    )
    
    # Initialize Sentry SDK
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            logging_integration,
        ],
        # Send default PII (Personally Identifiable Information)
        send_default_pii=False,
        # Attach stack traces to messages
        attach_stacktrace=True,
        # Enable performance monitoring
        enable_tracing=True,
        # Filter out health check endpoints from performance monitoring
        before_send_transaction=filter_transactions,
        # Add custom error filtering
        before_send=filter_errors,
    )
    
    logger.info(f"Sentry initialized - Environment: {environment}, Traces: {traces_sample_rate}, Profiles: {profiles_sample_rate}")


def filter_transactions(event: dict, hint: dict) -> Optional[dict]:
    """
    Filter transactions before sending to Sentry
    
    Excludes health check and monitoring endpoints from performance tracking
    to reduce noise and quota usage.
    
    Args:
        event: Sentry event dictionary
        hint: Additional context about the event
        
    Returns:
        Event dictionary if should be sent, None to drop
    """
    # Get transaction name
    transaction = event.get("transaction", "")
    
    # Filter out health check and monitoring endpoints
    excluded_endpoints = [
        "/",
        "/api/health",
        "/health",
        "/metrics",
        "/ping",
    ]
    
    if transaction in excluded_endpoints:
        return None
    
    return event


def filter_errors(event: dict, hint: dict) -> Optional[dict]:
    """
    Filter errors before sending to Sentry
    
    Excludes known non-critical errors and adds custom context.
    
    Args:
        event: Sentry event dictionary
        hint: Additional context including exception info
        
    Returns:
        Event dictionary if should be sent, None to drop
    """
    # Get exception info if available
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]
        
        # Filter out WebSocket disconnect errors (expected behavior)
        if exc_type.__name__ == "WebSocketDisconnect":
            return None
        
        # Filter out client disconnect errors
        if "client disconnected" in str(exc_value).lower():
            return None
        
        # Filter out rate limit errors (handled by middleware)
        if "rate limit" in str(exc_value).lower():
            return None
    
    # Add custom tags for better error grouping
    event.setdefault("tags", {})
    event["tags"]["component"] = "backend"
    event["tags"]["service"] = "openclaw-dashboard"
    
    return event


def capture_exception(error: Exception, context: Optional[dict] = None) -> None:
    """
    Manually capture an exception with optional context
    
    Args:
        error: Exception to capture
        context: Additional context dictionary (tags, extra data)
    """
    with sentry_sdk.push_scope() as scope:
        if context:
            # Add tags
            if "tags" in context:
                for key, value in context["tags"].items():
                    scope.set_tag(key, value)
            
            # Add extra data
            if "extra" in context:
                for key, value in context["extra"].items():
                    scope.set_extra(key, value)
            
            # Set user context
            if "user" in context:
                scope.set_user(context["user"])
        
        sentry_sdk.capture_exception(error)


def capture_message(message: str, level: str = "info", context: Optional[dict] = None) -> None:
    """
    Manually capture a message with optional context
    
    Args:
        message: Message to capture
        level: Severity level (debug, info, warning, error, fatal)
        context: Additional context dictionary (tags, extra data)
    """
    with sentry_sdk.push_scope() as scope:
        if context:
            # Add tags
            if "tags" in context:
                for key, value in context["tags"].items():
                    scope.set_tag(key, value)
            
            # Add extra data
            if "extra" in context:
                for key, value in context["extra"].items():
                    scope.set_extra(key, value)
        
        sentry_sdk.capture_message(message, level=level)


def set_user_context(user_id: str, email: Optional[str] = None, username: Optional[str] = None) -> None:
    """
    Set user context for error tracking
    
    Args:
        user_id: User identifier
        email: User email (optional)
        username: Username (optional)
    """
    sentry_sdk.set_user({
        "id": user_id,
        "email": email,
        "username": username,
    })


def add_breadcrumb(message: str, category: str = "default", level: str = "info", data: Optional[dict] = None) -> None:
    """
    Add a breadcrumb for debugging context
    
    Breadcrumbs are logged events that help understand the sequence of events
    leading up to an error.
    
    Args:
        message: Breadcrumb message
        category: Category (e.g., "auth", "query", "http")
        level: Severity level (debug, info, warning, error)
        data: Additional data dictionary
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {}
    )
