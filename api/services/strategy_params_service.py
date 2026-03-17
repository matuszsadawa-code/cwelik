"""
Strategy Parameters Service for OpenClaw Trading Dashboard

Manages strategy parameters with validation and persistence.

Features:
- Retrieve current strategy parameters from config.py
- Update individual or multiple parameters
- Validate parameter values against valid ranges
- Persist parameter changes to configuration file
- Return parameter metadata (description, valid range, default value)
"""

import logging
import os
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class StrategyParamsService:
    """
    Service for managing strategy parameters configuration.
    
    Responsibilities:
    - Load strategy parameters from config.py
    - Validate parameter values against valid ranges
    - Update parameter values
    - Persist changes to configuration file
    - Return parameter metadata
    """
    
    # Parameter definitions with valid ranges and descriptions
    PARAM_DEFINITIONS = {
        # Step 1: Trend
        "trend_candle_count": {
            "min": 20,
            "max": 200,
            "default": 50,
            "description": "Number of 4H candles to analyze for trend",
            "category": "trend"
        },
        "min_hh_for_bullish": {
            "min": 1,
            "max": 10,
            "default": 3,
            "description": "Minimum Higher Highs for bullish trend",
            "category": "trend"
        },
        "min_hl_for_bullish": {
            "min": 1,
            "max": 10,
            "default": 2,
            "description": "Minimum Higher Lows for bullish trend",
            "category": "trend"
        },
        "min_ll_for_bearish": {
            "min": 1,
            "max": 10,
            "default": 3,
            "description": "Minimum Lower Lows for bearish trend",
            "category": "trend"
        },
        "min_lh_for_bearish": {
            "min": 1,
            "max": 10,
            "default": 2,
            "description": "Minimum Lower Highs for bearish trend",
            "category": "trend"
        },
        "range_tolerance_pct": {
            "min": 0.1,
            "max": 5.0,
            "default": 1.0,
            "description": "Range detection tolerance (%)",
            "category": "trend"
        },
        # Step 2: Zones
        "zone_candle_count": {
            "min": 50,
            "max": 500,
            "default": 100,
            "description": "Number of 30M candles for zone identification",
            "category": "zones"
        },
        "max_zone_distance_pct": {
            "min": 0.5,
            "max": 10.0,
            "default": 3.0,
            "description": "Max distance from current price to zone (%)",
            "category": "zones"
        },
        "base_max_range_pct": {
            "min": 0.5,
            "max": 5.0,
            "default": 2.0,
            "description": "Max range for base/consolidation (%)",
            "category": "zones"
        },
        "zone_min_strength": {
            "min": 30,
            "max": 100,
            "default": 60,
            "description": "Minimum zone strength to consider",
            "category": "zones"
        },
        # Step 3: Volume
        "volume_candle_count": {
            "min": 20,
            "max": 200,
            "default": 50,
            "description": "Number of 5M candles for volume analysis",
            "category": "volume"
        },
        "volume_shrink_threshold": {
            "min": 0.3,
            "max": 0.9,
            "default": 0.7,
            "description": "Volume shrink threshold (exhaustion)",
            "category": "volume"
        },
        "volume_window_recent": {
            "min": 5,
            "max": 50,
            "default": 10,
            "description": "Recent candles window for volume",
            "category": "volume"
        },
        "volume_window_earlier": {
            "min": 5,
            "max": 50,
            "default": 10,
            "description": "Earlier candles window for volume",
            "category": "volume"
        },
        # Step 4: Order Flow
        "orderflow_candle_count": {
            "min": 10,
            "max": 100,
            "default": 20,
            "description": "Number of 5M candles for order flow",
            "category": "orderflow"
        },
        "delta_flip_threshold": {
            "min": 0.1,
            "max": 0.9,
            "default": 0.3,
            "description": "Delta ratio flip threshold",
            "category": "orderflow"
        },
        "imbalance_threshold": {
            "min": 1.1,
            "max": 3.0,
            "default": 1.5,
            "description": "Bid/ask imbalance ratio for confirmation",
            "category": "orderflow"
        },
        "absorption_min_volume": {
            "min": 1.5,
            "max": 5.0,
            "default": 2.0,
            "description": "Min volume multiplier for absorption",
            "category": "orderflow"
        },
        "cluster_min_trades": {
            "min": 5,
            "max": 50,
            "default": 10,
            "description": "Min trades in cluster",
            "category": "orderflow"
        },
        "cluster_time_window_sec": {
            "min": 30,
            "max": 300,
            "default": 60,
            "description": "Cluster time window (seconds)",
            "category": "orderflow"
        },
        # Risk Management
        "sl_buffer_pct": {
            "min": 0.1,
            "max": 2.0,
            "default": 0.5,
            "description": "Buffer below/above zone for SL (%)",
            "category": "risk"
        },
        "tp_rr_ratio": {
            "min": 1.0,
            "max": 5.0,
            "default": 2.0,
            "description": "Primary TP at R:R ratio",
            "category": "risk"
        },
        "default_leverage": {
            "min": 1,
            "max": 50,
            "default": 25,
            "description": "Default leverage for position sizing",
            "category": "risk"
        },
        "order_expiration_minutes": {
            "min": 5,
            "max": 60,
            "default": 15,
            "description": "Order expiration time (minutes)",
            "category": "risk"
        },
        # Monitoring
        "scan_interval_seconds": {
            "min": 60,
            "max": 600,
            "default": 300,
            "description": "Full scan interval (seconds)",
            "category": "monitoring"
        },
        "ws_reconnect_delay_sec": {
            "min": 1,
            "max": 30,
            "default": 5,
            "description": "WebSocket reconnect delay (seconds)",
            "category": "monitoring"
        }
    }
    
    def __init__(self):
        """Initialize strategy parameters service."""
        self.config_path = "config.py"
        logger.info("StrategyParamsService initialized")
    
    def get_all_params(self) -> Dict[str, Any]:
        """
        Get all strategy parameters with current values and metadata.
        
        Returns:
            dict: Parameters grouped by category with metadata
            {
                "trend": [
                    {
                        "name": "trend_candle_count",
                        "value": 50,
                        "default": 50,
                        "min": 20,
                        "max": 200,
                        "description": "Number of 4H candles..."
                    },
                    ...
                ],
                "zones": [...],
                ...
            }
        """
        try:
            # Import config dynamically
            import config
            
            # Build response grouped by category
            result = {}
            for param_name, definition in self.PARAM_DEFINITIONS.items():
                category = definition["category"]
                if category not in result:
                    result[category] = []
                
                # Get current value from config.STRATEGY
                current_value = config.STRATEGY.get(param_name, definition["default"])
                
                result[category].append({
                    "name": param_name,
                    "value": current_value,
                    "default": definition["default"],
                    "min": definition["min"],
                    "max": definition["max"],
                    "description": definition["description"]
                })
            
            logger.debug(f"Retrieved {sum(len(v) for v in result.values())} strategy parameters")
            return result
            
        except Exception as e:
            logger.error(f"Error loading strategy parameters: {e}", exc_info=True)
            raise
    
    def get_param(self, param_name: str) -> Optional[Dict]:
        """
        Get a specific strategy parameter with metadata.
        
        Args:
            param_name: Name of the parameter
            
        Returns:
            dict: Parameter value and metadata, or None if not found
        """
        try:
            if param_name not in self.PARAM_DEFINITIONS:
                return None
            
            import config
            definition = self.PARAM_DEFINITIONS[param_name]
            current_value = config.STRATEGY.get(param_name, definition["default"])
            
            return {
                "name": param_name,
                "value": current_value,
                "default": definition["default"],
                "min": definition["min"],
                "max": definition["max"],
                "description": definition["description"],
                "category": definition["category"]
            }
            
        except Exception as e:
            logger.error(f"Error getting parameter {param_name}: {e}")
            return None
    
    def update_params(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update multiple strategy parameters and persist to configuration file.
        
        Args:
            parameters: Dictionary of parameter names and new values
            
        Returns:
            dict: Result with success status and updated parameters
            {
                "success": True,
                "updated": {...},
                "message": "Parameters updated successfully"
            }
            
        Raises:
            ValueError: If parameter validation fails
            IOError: If unable to persist changes
        """
        try:
            # Validate all parameters first
            validation_errors = []
            for param_name, value in parameters.items():
                error = self._validate_param(param_name, value)
                if error:
                    validation_errors.append(error)
            
            if validation_errors:
                raise ValueError("; ".join(validation_errors))
            
            # Update in-memory configuration
            for param_name, value in parameters.items():
                self._update_in_memory(param_name, value)
            
            # Persist to file
            for param_name, value in parameters.items():
                self._persist_to_file(param_name, value)
            
            # Get updated parameters
            updated_params = {name: self.get_param(name) for name in parameters.keys()}
            
            logger.info(f"Updated {len(parameters)} strategy parameters")
            
            return {
                "success": True,
                "updated": updated_params,
                "message": f"Updated {len(parameters)} parameter(s) successfully",
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
            }
            
        except ValueError as e:
            logger.warning(f"Validation error updating parameters: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
            }
        except Exception as e:
            logger.error(f"Error updating strategy parameters: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to update parameters: {str(e)}",
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
            }
    
    def _validate_param(self, param_name: str, value: Any) -> Optional[str]:
        """
        Validate parameter value against valid range.
        
        Args:
            param_name: Name of the parameter
            value: New value to validate
            
        Returns:
            str: Error message if invalid, None if valid
        """
        if param_name not in self.PARAM_DEFINITIONS:
            return f"Unknown parameter: {param_name}"
        
        definition = self.PARAM_DEFINITIONS[param_name]
        min_val = definition["min"]
        max_val = definition["max"]
        
        try:
            # Convert to appropriate type
            if isinstance(min_val, int):
                value = int(value)
            else:
                value = float(value)
            
            if value < min_val or value > max_val:
                return f"{param_name} must be between {min_val} and {max_val}, got {value}"
            
            return None
            
        except (ValueError, TypeError):
            return f"Invalid value for {param_name}: {value}"
    
    def _update_in_memory(self, param_name: str, value: Any):
        """
        Update parameter in the in-memory configuration.
        
        Args:
            param_name: Name of the parameter
            value: New value
        """
        import config
        
        # Convert to appropriate type
        definition = self.PARAM_DEFINITIONS[param_name]
        if isinstance(definition["min"], int):
            value = int(value)
        else:
            value = float(value)
        
        config.STRATEGY[param_name] = value
    
    def _persist_to_file(self, param_name: str, value: Any):
        """
        Persist parameter change to configuration file.
        
        Updates the config.py file by modifying the parameter value
        in the STRATEGY dictionary.
        
        Args:
            param_name: Name of the parameter
            value: New value
            
        Raises:
            IOError: If unable to read or write configuration file
        """
        try:
            # Read current file content
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find the parameter in STRATEGY dict and update value
            # Pattern: "param_name": value,
            pattern = rf'("{param_name}":\s*)([^,\n]+)'
            
            # Check if pattern exists
            if not re.search(pattern, content):
                raise ValueError(f"Could not find '{param_name}' in configuration file")
            
            # Format new value
            definition = self.PARAM_DEFINITIONS[param_name]
            if isinstance(definition["min"], int):
                new_value_str = str(int(value))
            else:
                new_value_str = str(float(value))
            
            # Replace value
            updated_content = re.sub(pattern, rf'\g<1>{new_value_str}', content)
            
            # Write back to file
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            logger.debug(f"Persisted parameter '{param_name}' to {self.config_path}")
            
        except FileNotFoundError:
            raise IOError(f"Configuration file not found: {self.config_path}")
        except Exception as e:
            raise IOError(f"Failed to persist configuration: {str(e)}")
    
    def reset_to_defaults(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Reset parameters to default values.
        
        Args:
            category: Optional category to reset (trend, zones, volume, orderflow, risk, monitoring)
                     If None, resets all parameters
            
        Returns:
            dict: Result with success status
        """
        try:
            # Determine which parameters to reset
            params_to_reset = {}
            for param_name, definition in self.PARAM_DEFINITIONS.items():
                if category is None or definition["category"] == category:
                    params_to_reset[param_name] = definition["default"]
            
            # Update parameters
            result = self.update_params(params_to_reset)
            
            if result["success"]:
                result["message"] = f"Reset {len(params_to_reset)} parameter(s) to defaults"
            
            return result
            
        except Exception as e:
            logger.error(f"Error resetting parameters: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to reset parameters: {str(e)}",
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
            }
