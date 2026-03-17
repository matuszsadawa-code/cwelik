"""
Security Event Logger for OpenClaw Trading Dashboard

Logs security-related events including:
- Authentication failures
- Rate limit exceeded
- Suspicious actions
- Unauthorized access attempts
- Configuration changes
- Anomaly detection

Requirements: Security - Logging and Monitoring
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from enum import Enum
import json

logger = logging.getLogger(__name__)


class SecurityEventType(Enum):
    """Security event types"""
    AUTH_FAILURE = "auth_failure"
    AUTH_SUCCESS = "auth_success"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    CONFIG_CHANGE = "config_change"
    ANOMALY_DETECTED = "anomaly_detected"
    TOKEN_EXPIRED = "token_expired"
    INVALID_TOKEN = "invalid_token"
    PERMISSION_DENIED = "permission_denied"


class SecurityEventSeverity(Enum):
    """Security event severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SecurityLogger:
    """
    Security event logger with anomaly detection.
    
    Features:
    - Log security events with user context
    - Track authentication failures per user/IP
    - Detect unusual activity patterns
    - Alert on critical security events
    """
    
    def __init__(self):
        """Initialize security logger"""
        self.auth_failures = {}  # Track failures per user/IP
        self.suspicious_ips = set()  # IPs with suspicious activity
        self.config_changes = []  # Recent config changes
        
        # Thresholds for anomaly detection
        self.max_auth_failures = 5  # Max failures before flagging
        self.max_rate_limit_hits = 10  # Max rate limit hits before flagging
        self.suspicious_threshold = 3  # Suspicious actions before flagging IP
        
        logger.info("SecurityLogger initialized")
    
    def log_event(
        self,
        event_type: SecurityEventType,
        severity: SecurityEventSeverity,
        message: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log a security event.
        
        Args:
            event_type: Type of security event
            severity: Severity level
            message: Human-readable message
            user_id: User ID if applicable
            username: Username if applicable
            ip_address: IP address if applicable
            user_agent: User agent string if applicable
            details: Additional event details
        """
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type.value,
            "severity": severity.value,
            "message": message,
            "user_id": user_id,
            "username": username,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details or {}
        }
        
        # Log to appropriate level based on severity
        log_message = f"SECURITY EVENT: {event_type.value} - {message}"
        if severity == SecurityEventSeverity.CRITICAL:
            logger.critical(log_message, extra=event)
        elif severity == SecurityEventSeverity.ERROR:
            logger.error(log_message, extra=event)
        elif severity == SecurityEventSeverity.WARNING:
            logger.warning(log_message, extra=event)
        else:
            logger.info(log_message, extra=event)
        
        # Update tracking for anomaly detection
        self._update_tracking(event_type, user_id, username, ip_address)
        
        # Check for anomalies
        self._check_anomalies(event_type, user_id, username, ip_address)
    
    def log_auth_failure(
        self,
        username: str,
        ip_address: str,
        reason: str,
        user_agent: Optional[str] = None
    ):
        """
        Log authentication failure.
        
        Args:
            username: Username that failed authentication
            ip_address: IP address of the request
            reason: Reason for failure
            user_agent: User agent string
        """
        self.log_event(
            event_type=SecurityEventType.AUTH_FAILURE,
            severity=SecurityEventSeverity.WARNING,
            message=f"Authentication failed for user '{username}': {reason}",
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"reason": reason}
        )
    
    def log_auth_success(
        self,
        user_id: str,
        username: str,
        ip_address: str,
        user_agent: Optional[str] = None
    ):
        """
        Log successful authentication.
        
        Args:
            user_id: User ID
            username: Username
            ip_address: IP address of the request
            user_agent: User agent string
        """
        self.log_event(
            event_type=SecurityEventType.AUTH_SUCCESS,
            severity=SecurityEventSeverity.INFO,
            message=f"User '{username}' authenticated successfully",
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Reset failure count on successful auth
        key = f"{username}:{ip_address}"
        if key in self.auth_failures:
            del self.auth_failures[key]
    
    def log_rate_limit_exceeded(
        self,
        user_id: Optional[str],
        username: Optional[str],
        ip_address: str,
        endpoint: str,
        user_agent: Optional[str] = None
    ):
        """
        Log rate limit exceeded event.
        
        Args:
            user_id: User ID if authenticated
            username: Username if authenticated
            ip_address: IP address of the request
            endpoint: API endpoint that was rate limited
            user_agent: User agent string
        """
        self.log_event(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            severity=SecurityEventSeverity.WARNING,
            message=f"Rate limit exceeded for {username or 'anonymous'} on {endpoint}",
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"endpoint": endpoint}
        )
    
    def log_unauthorized_access(
        self,
        user_id: str,
        username: str,
        ip_address: str,
        resource: str,
        required_role: str,
        user_role: str,
        user_agent: Optional[str] = None
    ):
        """
        Log unauthorized access attempt.
        
        Args:
            user_id: User ID
            username: Username
            ip_address: IP address of the request
            resource: Resource that was accessed
            required_role: Role required for access
            user_role: User's actual role
            user_agent: User agent string
        """
        self.log_event(
            event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
            severity=SecurityEventSeverity.ERROR,
            message=f"User '{username}' (role: {user_role}) attempted to access '{resource}' (requires: {required_role})",
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "resource": resource,
                "required_role": required_role,
                "user_role": user_role
            }
        )
    
    def log_config_change(
        self,
        user_id: str,
        username: str,
        ip_address: str,
        config_type: str,
        changes: Dict[str, Any],
        user_agent: Optional[str] = None
    ):
        """
        Log configuration change.
        
        Args:
            user_id: User ID
            username: Username
            ip_address: IP address of the request
            config_type: Type of configuration changed
            changes: Dictionary of changes made
            user_agent: User agent string
        """
        self.log_event(
            event_type=SecurityEventType.CONFIG_CHANGE,
            severity=SecurityEventSeverity.INFO,
            message=f"User '{username}' changed {config_type} configuration",
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "config_type": config_type,
                "changes": changes
            }
        )
        
        # Track config changes
        self.config_changes.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "username": username,
            "config_type": config_type,
            "changes": changes
        })
        
        # Keep only last 100 changes
        if len(self.config_changes) > 100:
            self.config_changes = self.config_changes[-100:]
    
    def log_anomaly(
        self,
        anomaly_type: str,
        description: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log detected anomaly.
        
        Args:
            anomaly_type: Type of anomaly detected
            description: Description of the anomaly
            user_id: User ID if applicable
            username: Username if applicable
            ip_address: IP address if applicable
            details: Additional details
        """
        self.log_event(
            event_type=SecurityEventType.ANOMALY_DETECTED,
            severity=SecurityEventSeverity.CRITICAL,
            message=f"Anomaly detected: {anomaly_type} - {description}",
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            details={
                "anomaly_type": anomaly_type,
                **( details or {})
            }
        )
    
    def _update_tracking(
        self,
        event_type: SecurityEventType,
        user_id: Optional[str],
        username: Optional[str],
        ip_address: Optional[str]
    ):
        """
        Update tracking data for anomaly detection.
        
        Args:
            event_type: Type of security event
            user_id: User ID if applicable
            username: Username if applicable
            ip_address: IP address if applicable
        """
        if event_type == SecurityEventType.AUTH_FAILURE and username and ip_address:
            key = f"{username}:{ip_address}"
            self.auth_failures[key] = self.auth_failures.get(key, 0) + 1
    
    def _check_anomalies(
        self,
        event_type: SecurityEventType,
        user_id: Optional[str],
        username: Optional[str],
        ip_address: Optional[str]
    ):
        """
        Check for anomalies based on tracked data.
        
        Args:
            event_type: Type of security event
            user_id: User ID if applicable
            username: Username if applicable
            ip_address: IP address if applicable
        """
        # Check for excessive authentication failures
        if event_type == SecurityEventType.AUTH_FAILURE and username and ip_address:
            key = f"{username}:{ip_address}"
            failure_count = self.auth_failures.get(key, 0)
            
            if failure_count >= self.max_auth_failures:
                self.log_anomaly(
                    anomaly_type="excessive_auth_failures",
                    description=f"User '{username}' from IP {ip_address} has {failure_count} failed authentication attempts",
                    username=username,
                    ip_address=ip_address,
                    details={"failure_count": failure_count}
                )
                
                # Add IP to suspicious list
                if ip_address:
                    self.suspicious_ips.add(ip_address)
        
        # Check for suspicious IP
        if ip_address and ip_address in self.suspicious_ips:
            if event_type in [SecurityEventType.UNAUTHORIZED_ACCESS, SecurityEventType.RATE_LIMIT_EXCEEDED]:
                self.log_anomaly(
                    anomaly_type="suspicious_ip_activity",
                    description=f"Suspicious IP {ip_address} performing {event_type.value}",
                    user_id=user_id,
                    username=username,
                    ip_address=ip_address
                )
    
    def get_recent_events(self, limit: int = 100) -> list:
        """
        Get recent security events.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            list: Recent security events
        """
        # This would typically query a database or log file
        # For now, return empty list as events are logged to file
        return []
    
    def get_suspicious_ips(self) -> set:
        """
        Get list of suspicious IP addresses.
        
        Returns:
            set: Set of suspicious IP addresses
        """
        return self.suspicious_ips.copy()
    
    def get_auth_failure_stats(self) -> Dict[str, int]:
        """
        Get authentication failure statistics.
        
        Returns:
            dict: Authentication failure counts by user:ip
        """
        return self.auth_failures.copy()
    
    def reset_tracking(self, username: Optional[str] = None, ip_address: Optional[str] = None):
        """
        Reset tracking data.
        
        Args:
            username: Username to reset (None = reset all)
            ip_address: IP address to reset (None = reset all)
        """
        if username and ip_address:
            key = f"{username}:{ip_address}"
            if key in self.auth_failures:
                del self.auth_failures[key]
            if ip_address in self.suspicious_ips:
                self.suspicious_ips.remove(ip_address)
        elif username:
            # Reset all entries for username
            keys_to_delete = [k for k in self.auth_failures.keys() if k.startswith(f"{username}:")]
            for key in keys_to_delete:
                del self.auth_failures[key]
        elif ip_address:
            # Reset all entries for IP
            keys_to_delete = [k for k in self.auth_failures.keys() if k.endswith(f":{ip_address}")]
            for key in keys_to_delete:
                del self.auth_failures[key]
            if ip_address in self.suspicious_ips:
                self.suspicious_ips.remove(ip_address)
        else:
            # Reset all
            self.auth_failures.clear()
            self.suspicious_ips.clear()


# Global security logger instance
_security_logger = None


def get_security_logger() -> SecurityLogger:
    """
    Get the global security logger instance.
    
    Returns:
        SecurityLogger: The security logger instance
    """
    global _security_logger
    if _security_logger is None:
        _security_logger = SecurityLogger()
    return _security_logger
