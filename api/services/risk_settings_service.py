"""
Risk Management Settings Service for OpenClaw Trading Dashboard

Manages risk management settings with validation and position checks.

Features:
- Retrieve current risk settings from config.py
- Update risk settings with validation
- Check if current positions violate new settings
- Persist settings changes to configuration file
- Return risk utilization metrics
"""

import logging
import os
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class RiskSettingsService:
    """
    Service for managing risk management settings.
    
    Responsibilities:
    - Load risk settings from config.py
    - Validate risk setting values
    - Check position violations against new settings
    - Update risk settings
    - Persist changes to configuration file
    - Calculate risk utilization metrics
    """
    
    # Risk setting definitions with valid ranges
    RISK_DEFINITIONS = {
        "max_position_size": {
            "min": 0.01,
            "max": 100.0,
            "default": 10.0,
            "description": "Maximum position size per trade (% of portfolio)",
            "unit": "%"
        },
        "max_portfolio_exposure": {
            "min": 10.0,
            "max": 200.0,
            "default": 100.0,
            "description": "Maximum total portfolio exposure (%)",
            "unit": "%"
        },
        "max_drawdown_limit": {
            "min": 5.0,
            "max": 50.0,
            "default": 20.0,
            "description": "Maximum drawdown limit before stopping (%)",
            "unit": "%"
        },
        "max_daily_loss_limit": {
            "min": 1.0,
            "max": 20.0,
            "default": 5.0,
            "description": "Maximum daily loss limit (%)",
            "unit": "%"
        },
        "correlation_threshold": {
            "min": 0.3,
            "max": 0.95,
            "default": 0.7,
            "description": "Maximum correlation between positions",
            "unit": ""
        }
    }
    
    def __init__(self, db=None):
        """
        Initialize risk settings service.
        
        Args:
            db: Database instance for checking positions (optional)
        """
        self.config_path = "config.py"
        self.db = db
        logger.info("RiskSettingsService initialized")
    
    def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all risk settings with current values and metadata.
        
        Returns:
            dict: Risk settings with metadata
            {
                "settings": [
                    {
                        "name": "max_position_size",
                        "value": 10.0,
                        "default": 10.0,
                        "min": 0.01,
                        "max": 100.0,
                        "description": "Maximum position size...",
                        "unit": "%"
                    },
                    ...
                ],
                "current_utilization": {
                    "portfolio_exposure": 45.0,
                    "current_drawdown": 2.5,
                    "daily_loss": 1.2,
                    "open_positions": 3
                }
            }
        """
        try:
            # Import config dynamically
            import config
            
            # Build settings list
            settings = []
            for setting_name, definition in self.RISK_DEFINITIONS.items():
                # Try to get from config, fallback to default
                current_value = getattr(config, setting_name.upper(), definition["default"])
                
                settings.append({
                    "name": setting_name,
                    "value": current_value,
                    "default": definition["default"],
                    "min": definition["min"],
                    "max": definition["max"],
                    "description": definition["description"],
                    "unit": definition["unit"]
                })
            
            # Get current utilization
            utilization = self._get_current_utilization()
            
            logger.debug(f"Retrieved {len(settings)} risk settings")
            return {
                "settings": settings,
                "current_utilization": utilization
            }
            
        except Exception as e:
            logger.error(f"Error loading risk settings: {e}", exc_info=True)
            raise
    
    def get_setting(self, setting_name: str) -> Optional[Dict]:
        """
        Get a specific risk setting with metadata.
        
        Args:
            setting_name: Name of the setting
            
        Returns:
            dict: Setting value and metadata, or None if not found
        """
        try:
            if setting_name not in self.RISK_DEFINITIONS:
                return None
            
            import config
            definition = self.RISK_DEFINITIONS[setting_name]
            current_value = getattr(config, setting_name.upper(), definition["default"])
            
            return {
                "name": setting_name,
                "value": current_value,
                "default": definition["default"],
                "min": definition["min"],
                "max": definition["max"],
                "description": definition["description"],
                "unit": definition["unit"]
            }
            
        except Exception as e:
            logger.error(f"Error getting setting {setting_name}: {e}")
            return None
    
    def update_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update risk settings and persist to configuration file.
        
        Args:
            settings: Dictionary of setting names and new values
            
        Returns:
            dict: Result with success status, updated settings, and warnings
            {
                "success": True,
                "updated": {...},
                "warnings": [...],  # Position violations if any
                "message": "Settings updated successfully"
            }
            
        Raises:
            ValueError: If setting validation fails
            IOError: If unable to persist changes
        """
        try:
            # Validate all settings first
            validation_errors = []
            for setting_name, value in settings.items():
                error = self._validate_setting(setting_name, value)
                if error:
                    validation_errors.append(error)
            
            if validation_errors:
                raise ValueError("; ".join(validation_errors))
            
            # Check for position violations
            warnings = self._check_position_violations(settings)
            
            # Update in-memory configuration
            for setting_name, value in settings.items():
                self._update_in_memory(setting_name, value)
            
            # Persist to file
            for setting_name, value in settings.items():
                self._persist_to_file(setting_name, value)
            
            # Get updated settings
            updated_settings = {name: self.get_setting(name) for name in settings.keys()}
            
            logger.info(f"Updated {len(settings)} risk settings")
            
            return {
                "success": True,
                "updated": updated_settings,
                "warnings": warnings,
                "message": f"Updated {len(settings)} setting(s) successfully",
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
            }
            
        except ValueError as e:
            logger.warning(f"Validation error updating settings: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
            }
        except Exception as e:
            logger.error(f"Error updating risk settings: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to update settings: {str(e)}",
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
            }
    
    def _validate_setting(self, setting_name: str, value: Any) -> Optional[str]:
        """
        Validate setting value against valid range.
        
        Args:
            setting_name: Name of the setting
            value: New value to validate
            
        Returns:
            str: Error message if invalid, None if valid
        """
        if setting_name not in self.RISK_DEFINITIONS:
            return f"Unknown risk setting: {setting_name}"
        
        definition = self.RISK_DEFINITIONS[setting_name]
        min_val = definition["min"]
        max_val = definition["max"]
        
        try:
            value = float(value)
            
            if value < min_val or value > max_val:
                return f"{setting_name} must be between {min_val} and {max_val}, got {value}"
            
            return None
            
        except (ValueError, TypeError):
            return f"Invalid value for {setting_name}: {value}"
    
    def _check_position_violations(self, new_settings: Dict[str, Any]) -> List[str]:
        """
        Check if current positions violate new risk settings.
        
        Args:
            new_settings: Dictionary of new setting values
            
        Returns:
            list: List of warning messages for violations
        """
        warnings = []
        
        if not self.db:
            return warnings
        
        try:
            # Get open positions
            open_positions = self.db.get_executions(status="OPEN")
            
            if not open_positions:
                return warnings
            
            # Check max_position_size violations
            if "max_position_size" in new_settings:
                max_size = new_settings["max_position_size"]
                for pos in open_positions:
                    # Calculate position size as % (simplified)
                    pos_size = pos.get("qty", 0) * pos.get("entry_price", 0) / 10000  # Assuming 10k portfolio
                    if pos_size > max_size:
                        warnings.append(
                            f"Position {pos['symbol']} ({pos_size:.2f}%) exceeds new max position size ({max_size}%)"
                        )
            
            # Check max_portfolio_exposure violations
            if "max_portfolio_exposure" in new_settings:
                max_exposure = new_settings["max_portfolio_exposure"]
                total_exposure = sum(
                    pos.get("qty", 0) * pos.get("entry_price", 0) / 10000
                    for pos in open_positions
                )
                if total_exposure > max_exposure:
                    warnings.append(
                        f"Current portfolio exposure ({total_exposure:.2f}%) exceeds new limit ({max_exposure}%)"
                    )
            
        except Exception as e:
            logger.error(f"Error checking position violations: {e}")
        
        return warnings
    
    def _get_current_utilization(self) -> Dict[str, Any]:
        """
        Calculate current risk utilization metrics.
        
        Returns:
            dict: Current utilization metrics
        """
        utilization = {
            "portfolio_exposure": 0.0,
            "current_drawdown": 0.0,
            "daily_loss": 0.0,
            "open_positions": 0
        }
        
        if not self.db:
            return utilization
        
        try:
            # Get open positions
            open_positions = self.db.get_executions(status="OPEN")
            utilization["open_positions"] = len(open_positions)
            
            # Calculate portfolio exposure (simplified)
            total_exposure = sum(
                pos.get("qty", 0) * pos.get("entry_price", 0) / 10000
                for pos in open_positions
            )
            utilization["portfolio_exposure"] = round(total_exposure, 2)
            
            # Get equity history for drawdown calculation
            equity_history = self.db.get_equity_history(limit=100)
            if equity_history:
                peak_equity = max(e["equity"] for e in equity_history)
                current_equity = equity_history[-1]["equity"]
                drawdown = ((peak_equity - current_equity) / peak_equity) * 100
                utilization["current_drawdown"] = round(drawdown, 2)
                
                # Calculate daily loss (last 24 hours)
                if len(equity_history) > 1:
                    start_equity = equity_history[0]["equity"]
                    daily_loss = ((start_equity - current_equity) / start_equity) * 100
                    utilization["daily_loss"] = round(daily_loss, 2)
            
        except Exception as e:
            logger.error(f"Error calculating utilization: {e}")
        
        return utilization
    
    def _update_in_memory(self, setting_name: str, value: Any):
        """
        Update setting in the in-memory configuration.
        
        Args:
            setting_name: Name of the setting
            value: New value
        """
        import config
        value = float(value)
        setattr(config, setting_name.upper(), value)
    
    def _persist_to_file(self, setting_name: str, value: Any):
        """
        Persist setting change to configuration file.
        
        Updates the config.py file by modifying the setting value.
        
        Args:
            setting_name: Name of the setting
            value: New value
            
        Raises:
            IOError: If unable to read or write configuration file
        """
        try:
            # Read current file content
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find the setting and update value
            # Pattern: SETTING_NAME = value
            pattern = rf'({setting_name.upper()}\s*=\s*)([^\n]+)'
            
            # Check if pattern exists
            if not re.search(pattern, content):
                # Setting might not exist in config.py, skip persistence
                logger.warning(f"Setting '{setting_name}' not found in config.py, skipping persistence")
                return
            
            # Format new value
            new_value_str = str(float(value))
            
            # Replace value
            updated_content = re.sub(pattern, rf'\g<1>{new_value_str}', content)
            
            # Write back to file
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            logger.debug(f"Persisted setting '{setting_name}' to {self.config_path}")
            
        except FileNotFoundError:
            raise IOError(f"Configuration file not found: {self.config_path}")
        except Exception as e:
            raise IOError(f"Failed to persist configuration: {str(e)}")
