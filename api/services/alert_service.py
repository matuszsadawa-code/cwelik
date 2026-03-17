"""
Alert System Service for OpenClaw Trading Dashboard

Manages alert detection, broadcasting, and history storage.

Features:
- Detect alert conditions (signal generation, TP/SL hits, drawdown, health degradation, API failures)
- Broadcast alerts via WebSocket with severity levels
- Store alert history in database
- Retrieve alert history
- Configure alert thresholds
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


class AlertService:
    """
    Service for managing system alerts and notifications.
    
    Responsibilities:
    - Detect alert conditions
    - Broadcast alerts via WebSocket
    - Store alert history in database
    - Retrieve alert history
    - Manage alert configuration
    """
    
    # Alert categories
    CATEGORIES = ["signal", "position", "system", "risk", "health"]
    
    # Severity levels
    SEVERITIES = ["info", "warning", "error"]
    
    # Default alert thresholds
    DEFAULT_THRESHOLDS = {
        "drawdown_threshold": 15.0,  # %
        "daily_loss_threshold": 5.0,  # %
        "api_success_rate_threshold": 95.0,  # %
        "api_response_time_threshold": 1000,  # ms
        "health_score_threshold": 70.0  # %
    }
    
    def __init__(self, db=None, websocket_manager=None):
        """
        Initialize alert service.
        
        Args:
            db: Database instance for storing alert history
            websocket_manager: WebSocket manager for broadcasting alerts
        """
        self.db = db
        self.websocket_manager = websocket_manager
        self.thresholds = self.DEFAULT_THRESHOLDS.copy()
        self._ensure_alert_table()
        logger.info("AlertService initialized")
    
    def _ensure_alert_table(self):
        """Ensure alert_history table exists in database."""
        if not self.db:
            return
        
        try:
            conn = self.db._get_conn()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE NOT NULL,
                    severity TEXT NOT NULL,
                    category TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT,
                    dismissed INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_created ON alert_history(created_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alert_history(severity)
            """)
            conn.commit()
            logger.debug("Alert history table ensured")
        except Exception as e:
            logger.error(f"Error creating alert table: {e}")
    
    def create_alert(
        self,
        severity: str,
        category: str,
        message: str,
        details: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create and broadcast an alert.
        
        Args:
            severity: Alert severity (info, warning, error)
            category: Alert category (signal, position, system, risk, health)
            message: Alert message
            details: Optional additional details
            
        Returns:
            dict: Created alert
        """
        try:
            # Validate inputs
            if severity not in self.SEVERITIES:
                raise ValueError(f"Invalid severity: {severity}")
            if category not in self.CATEGORIES:
                raise ValueError(f"Invalid category: {category}")
            
            # Create alert
            alert = {
                "alert_id": str(uuid.uuid4()),
                "severity": severity,
                "category": category,
                "message": message,
                "details": details or {},
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                "dismissed": False
            }
            
            # Store in database
            if self.db:
                self._store_alert(alert)
            
            # Broadcast via WebSocket
            if self.websocket_manager:
                self._broadcast_alert(alert)
            
            logger.info(f"Alert created: [{severity}] {category} - {message}")
            return alert
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}", exc_info=True)
            raise
    
    def _store_alert(self, alert: Dict[str, Any]):
        """Store alert in database."""
        try:
            import json
            conn = self.db._get_conn()
            conn.execute("""
                INSERT INTO alert_history
                (alert_id, severity, category, message, details, dismissed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                alert["alert_id"],
                alert["severity"],
                alert["category"],
                alert["message"],
                json.dumps(alert["details"]),
                0,
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Error storing alert: {e}")
    
    def _broadcast_alert(self, alert: Dict[str, Any]):
        """Broadcast alert via WebSocket."""
        try:
            message = {
                "type": "alert",
                "data": alert
            }
            # WebSocket broadcast would happen here
            # self.websocket_manager.broadcast(message)
            logger.debug(f"Alert broadcast: {alert['alert_id']}")
        except Exception as e:
            logger.error(f"Error broadcasting alert: {e}")
    
    def get_alert_history(
        self,
        limit: int = 100,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        dismissed: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Get alert history with optional filters.
        
        Args:
            limit: Maximum number of alerts to return
            severity: Filter by severity (optional)
            category: Filter by category (optional)
            dismissed: Filter by dismissed status (optional)
            
        Returns:
            list: List of alerts
        """
        try:
            if not self.db:
                return []
            
            import json
            conn = self.db._get_conn()
            
            # Build query
            query = "SELECT * FROM alert_history WHERE 1=1"
            params = []
            
            if severity:
                query += " AND severity = ?"
                params.append(severity)
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            if dismissed is not None:
                query += " AND dismissed = ?"
                params.append(1 if dismissed else 0)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            
            alerts = []
            for row in rows:
                alert = dict(row)
                # Parse details JSON
                if alert.get("details"):
                    try:
                        alert["details"] = json.loads(alert["details"])
                    except:
                        alert["details"] = {}
                alert["dismissed"] = bool(alert.get("dismissed", 0))
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error fetching alert history: {e}", exc_info=True)
            return []
    
    def dismiss_alert(self, alert_id: str) -> bool:
        """
        Dismiss an alert.
        
        Args:
            alert_id: Alert ID to dismiss
            
        Returns:
            bool: True if successful
        """
        try:
            if not self.db:
                return False
            
            conn = self.db._get_conn()
            conn.execute("""
                UPDATE alert_history
                SET dismissed = 1
                WHERE alert_id = ?
            """, (alert_id,))
            conn.commit()
            
            logger.debug(f"Alert dismissed: {alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error dismissing alert: {e}")
            return False
    
    def update_thresholds(self, thresholds: Dict[str, float]) -> Dict[str, Any]:
        """
        Update alert thresholds.
        
        Args:
            thresholds: Dictionary of threshold values
            
        Returns:
            dict: Result with success status
        """
        try:
            # Validate thresholds
            for key, value in thresholds.items():
                if key not in self.DEFAULT_THRESHOLDS:
                    raise ValueError(f"Unknown threshold: {key}")
                if not isinstance(value, (int, float)) or value < 0:
                    raise ValueError(f"Invalid threshold value for {key}: {value}")
            
            # Update thresholds
            self.thresholds.update(thresholds)
            
            logger.info(f"Updated {len(thresholds)} alert thresholds")
            return {
                "success": True,
                "thresholds": self.thresholds,
                "message": "Alert thresholds updated successfully"
            }
            
        except ValueError as e:
            logger.warning(f"Validation error updating thresholds: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error updating thresholds: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to update thresholds: {str(e)}"
            }
    
    def get_thresholds(self) -> Dict[str, float]:
        """Get current alert thresholds."""
        return self.thresholds.copy()
    
    # Alert detection methods
    
    def check_signal_generated(self, signal: Dict[str, Any]):
        """Check and create alert for new signal generation."""
        try:
            quality = signal.get("quality", "")
            if quality in ["A+", "A"]:
                self.create_alert(
                    severity="info",
                    category="signal",
                    message=f"New {quality} signal generated for {signal.get('symbol')}",
                    details={
                        "signal_id": signal.get("signal_id"),
                        "symbol": signal.get("symbol"),
                        "direction": signal.get("signal_type"),
                        "quality": quality,
                        "confidence": signal.get("confidence")
                    }
                )
        except Exception as e:
            logger.error(f"Error checking signal alert: {e}")
    
    def check_position_tp_sl(self, position: Dict[str, Any], hit_type: str):
        """Check and create alert for TP/SL hits."""
        try:
            severity = "info" if hit_type == "TP" else "warning"
            self.create_alert(
                severity=severity,
                category="position",
                message=f"{hit_type} hit for {position.get('symbol')}",
                details={
                    "position_id": position.get("execution_id"),
                    "symbol": position.get("symbol"),
                    "hit_type": hit_type,
                    "pnl": position.get("realised_pnl")
                }
            )
        except Exception as e:
            logger.error(f"Error checking position alert: {e}")
    
    def check_drawdown_exceeded(self, current_drawdown: float):
        """Check and create alert for drawdown threshold exceeded."""
        try:
            threshold = self.thresholds["drawdown_threshold"]
            if current_drawdown > threshold:
                self.create_alert(
                    severity="error",
                    category="risk",
                    message=f"Drawdown exceeded threshold: {current_drawdown:.2f}% > {threshold}%",
                    details={
                        "current_drawdown": current_drawdown,
                        "threshold": threshold
                    }
                )
        except Exception as e:
            logger.error(f"Error checking drawdown alert: {e}")
    
    def check_daily_loss_exceeded(self, daily_loss: float):
        """Check and create alert for daily loss threshold exceeded."""
        try:
            threshold = self.thresholds["daily_loss_threshold"]
            if daily_loss > threshold:
                self.create_alert(
                    severity="error",
                    category="risk",
                    message=f"Daily loss exceeded threshold: {daily_loss:.2f}% > {threshold}%",
                    details={
                        "daily_loss": daily_loss,
                        "threshold": threshold
                    }
                )
        except Exception as e:
            logger.error(f"Error checking daily loss alert: {e}")
    
    def check_health_degradation(self, health_metrics: Dict[str, Any]):
        """Check and create alert for system health degradation."""
        try:
            # Check API success rate
            for exchange, success_rate in health_metrics.get("api_success_rate", {}).items():
                threshold = self.thresholds["api_success_rate_threshold"]
                if success_rate < threshold:
                    self.create_alert(
                        severity="warning",
                        category="health",
                        message=f"{exchange} API success rate below threshold: {success_rate:.1f}% < {threshold}%",
                        details={
                            "exchange": exchange,
                            "success_rate": success_rate,
                            "threshold": threshold
                        }
                    )
            
            # Check API response time
            for exchange, response_time in health_metrics.get("api_response_time", {}).items():
                threshold = self.thresholds["api_response_time_threshold"]
                if response_time > threshold:
                    self.create_alert(
                        severity="warning",
                        category="health",
                        message=f"{exchange} API response time exceeded: {response_time}ms > {threshold}ms",
                        details={
                            "exchange": exchange,
                            "response_time": response_time,
                            "threshold": threshold
                        }
                    )
        except Exception as e:
            logger.error(f"Error checking health alert: {e}")
    
    def check_api_failure(self, exchange: str, error: str):
        """Check and create alert for API connection failure."""
        try:
            self.create_alert(
                severity="error",
                category="system",
                message=f"{exchange} API connection failed",
                details={
                    "exchange": exchange,
                    "error": error
                }
            )
        except Exception as e:
            logger.error(f"Error checking API failure alert: {e}")
