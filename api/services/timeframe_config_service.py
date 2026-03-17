"""
Timeframe Configuration Service for OpenClaw Trading Dashboard

Manages timeframe selection for multi-timeframe analysis.

Features:
- Retrieve currently configured timeframes from config.py
- Update timeframe list with validation
- Validate minimum 2 timeframes selected
- Calculate estimated data fetch time
- Persist timeframe changes to configuration file
"""

import logging
import re
from typing import Dict, List, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class TimeframeConfigService:
    """
    Service for managing timeframe configuration.
    
    Responsibilities:
    - Load configured timeframes from config.py
    - Validate timeframe selections
    - Update timeframe configuration
    - Calculate estimated data fetch time
    - Persist changes to configuration file
    """
    
    # Available timeframes with metadata
    AVAILABLE_TIMEFRAMES = {
        "1": {
            "label": "1m",
            "minutes": 1,
            "description": "1 minute",
            "fetch_time_ms": 50,  # Estimated fetch time per symbol
        },
        "5": {
            "label": "5m",
            "minutes": 5,
            "description": "5 minutes",
            "fetch_time_ms": 45,
        },
        "15": {
            "label": "15m",
            "minutes": 15,
            "description": "15 minutes",
            "fetch_time_ms": 40,
        },
        "30": {
            "label": "30m",
            "minutes": 30,
            "description": "30 minutes",
            "fetch_time_ms": 40,
        },
        "60": {
            "label": "1h",
            "minutes": 60,
            "description": "1 hour",
            "fetch_time_ms": 35,
        },
        "240": {
            "label": "4h",
            "minutes": 240,
            "description": "4 hours",
            "fetch_time_ms": 30,
        },
        "1440": {
            "label": "1d",
            "minutes": 1440,
            "description": "1 day",
            "fetch_time_ms": 25,
        },
    }
    
    def __init__(self):
        """Initialize timeframe configuration service."""
        self.config_path = "config.py"
        logger.info("TimeframeConfigService initialized")
    
    def get_available_timeframes(self) -> Dict[str, Any]:
        """
        Get list of available timeframes with metadata.
        
        Returns:
            dict: Available timeframes
            {
                "timeframes": [
                    {
                        "value": "1",
                        "label": "1m",
                        "minutes": 1,
                        "description": "1 minute",
                        "fetch_time_ms": 50
                    },
                    ...
                ],
                "count": 7
            }
        """
        try:
            timeframes = []
            for value, metadata in self.AVAILABLE_TIMEFRAMES.items():
                timeframes.append({
                    "value": value,
                    "label": metadata["label"],
                    "minutes": metadata["minutes"],
                    "description": metadata["description"],
                    "fetch_time_ms": metadata["fetch_time_ms"]
                })
            
            # Sort by minutes
            timeframes.sort(key=lambda x: x["minutes"])
            
            logger.debug(f"Retrieved {len(timeframes)} available timeframes")
            return {
                "timeframes": timeframes,
                "count": len(timeframes)
            }
            
        except Exception as e:
            logger.error(f"Error loading available timeframes: {e}", exc_info=True)
            raise
    
    def get_configured_timeframes(self) -> Dict[str, Any]:
        """
        Get currently configured timeframes from configuration.
        
        Returns:
            dict: Configured timeframes with metadata
            {
                "timeframes": {
                    "trend": "240",
                    "zones": "30",
                    "confirmation": "5"
                },
                "timeframe_list": ["5", "30", "240"],
                "count": 3,
                "estimated_fetch_time_ms": 115
            }
        """
        try:
            import config
            
            # Get timeframes from config
            timeframes = config.TIMEFRAMES.copy()
            
            # Extract unique timeframe values
            timeframe_list = list(set(timeframes.values()))
            timeframe_list.sort(key=lambda x: int(x))
            
            # Calculate estimated fetch time
            estimated_time = self._calculate_fetch_time(timeframe_list)
            
            logger.debug(f"Retrieved {len(timeframe_list)} configured timeframes")
            return {
                "timeframes": timeframes,
                "timeframe_list": timeframe_list,
                "count": len(timeframe_list),
                "estimated_fetch_time_ms": estimated_time
            }
            
        except Exception as e:
            logger.error(f"Error loading configured timeframes: {e}", exc_info=True)
            raise
    
    def update_timeframes(self, timeframe_list: List[str]) -> Dict[str, Any]:
        """
        Update the configured timeframes.
        
        Args:
            timeframe_list: List of timeframe values to configure (e.g., ["5", "30", "240"])
            
        Returns:
            dict: Result with success status
            {
                "success": True,
                "timeframes": ["5", "30", "240"],
                "count": 3,
                "estimated_fetch_time_ms": 115,
                "message": "Timeframes updated successfully"
            }
            
        Raises:
            ValueError: If timeframe list is invalid
            IOError: If unable to persist changes
        """
        try:
            # Validate timeframes
            validation_error = self._validate_timeframes(timeframe_list)
            if validation_error:
                raise ValueError(validation_error)
            
            # Sort timeframes by minutes
            timeframe_list = sorted(timeframe_list, key=lambda x: int(x))
            
            # Map timeframes to roles (trend, zones, confirmation)
            timeframe_mapping = self._map_timeframes_to_roles(timeframe_list)
            
            # Update in-memory configuration
            self._update_in_memory(timeframe_mapping)
            
            # Persist to file
            self._persist_to_file(timeframe_mapping)
            
            # Calculate estimated fetch time
            estimated_time = self._calculate_fetch_time(timeframe_list)
            
            logger.info(f"Updated timeframes: {timeframe_list}")
            
            return {
                "success": True,
                "timeframes": timeframe_list,
                "timeframe_mapping": timeframe_mapping,
                "count": len(timeframe_list),
                "estimated_fetch_time_ms": estimated_time,
                "message": f"Updated timeframes successfully ({len(timeframe_list)} timeframes)",
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
            }
            
        except ValueError as e:
            logger.warning(f"Validation error updating timeframes: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
            }
        except Exception as e:
            logger.error(f"Error updating timeframes: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to update timeframes: {str(e)}",
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
            }
    
    def _validate_timeframes(self, timeframe_list: List[str]) -> str:
        """
        Validate timeframe list.
        
        Args:
            timeframe_list: List of timeframe values
            
        Returns:
            str: Error message if invalid, empty string if valid
        """
        # Check if list is provided
        if not timeframe_list or not isinstance(timeframe_list, list):
            return "Timeframes must be a non-empty list"
        
        # Check minimum count (Requirement 19.8)
        if len(timeframe_list) < 2:
            return "At least 2 timeframes must be selected"
        
        # Check maximum count (reasonable limit)
        if len(timeframe_list) > 7:
            return "Maximum 7 timeframes can be selected"
        
        # Check if all timeframes are valid
        for tf in timeframe_list:
            if tf not in self.AVAILABLE_TIMEFRAMES:
                return f"Invalid timeframe: {tf}. Available: {', '.join(self.AVAILABLE_TIMEFRAMES.keys())}"
        
        # Check for duplicates
        if len(timeframe_list) != len(set(timeframe_list)):
            return "Duplicate timeframes are not allowed"
        
        return ""
    
    def _map_timeframes_to_roles(self, timeframe_list: List[str]) -> Dict[str, str]:
        """
        Map timeframes to roles (trend, zones, confirmation).
        
        Strategy:
        - Highest timeframe → trend
        - Middle timeframe → zones
        - Lowest timeframe → confirmation
        
        Args:
            timeframe_list: Sorted list of timeframe values
            
        Returns:
            dict: Mapping of roles to timeframes
        """
        # Sort by minutes to ensure correct ordering
        sorted_tfs = sorted(timeframe_list, key=lambda x: int(x))
        
        if len(sorted_tfs) == 2:
            # 2 timeframes: use higher for trend/zones, lower for confirmation
            return {
                "trend": sorted_tfs[-1],
                "zones": sorted_tfs[-1],
                "confirmation": sorted_tfs[0]
            }
        else:
            # 3+ timeframes: use highest for trend, middle for zones, lowest for confirmation
            return {
                "trend": sorted_tfs[-1],
                "zones": sorted_tfs[len(sorted_tfs) // 2],
                "confirmation": sorted_tfs[0]
            }
    
    def _calculate_fetch_time(self, timeframe_list: List[str], num_symbols: int = 30) -> int:
        """
        Calculate estimated data fetch time for selected timeframes.
        
        Args:
            timeframe_list: List of timeframe values
            num_symbols: Number of symbols to fetch (default: 30)
            
        Returns:
            int: Estimated fetch time in milliseconds
        """
        total_time = 0
        
        for tf in timeframe_list:
            if tf in self.AVAILABLE_TIMEFRAMES:
                fetch_time_per_symbol = self.AVAILABLE_TIMEFRAMES[tf]["fetch_time_ms"]
                total_time += fetch_time_per_symbol
        
        # Multiply by number of symbols (assuming parallel fetching reduces time)
        # With async parallel fetching, time is roughly: max(timeframe_times) + overhead
        # For simplicity, we'll use average time per timeframe
        if timeframe_list:
            avg_time = total_time / len(timeframe_list)
            estimated_time = int(avg_time * num_symbols / 10)  # Parallel factor ~10x
        else:
            estimated_time = 0
        
        return estimated_time
    
    def _update_in_memory(self, timeframe_mapping: Dict[str, str]):
        """
        Update timeframes in the in-memory configuration.
        
        Args:
            timeframe_mapping: Mapping of roles to timeframes
        """
        import config
        config.TIMEFRAMES = timeframe_mapping.copy()
    
    def _persist_to_file(self, timeframe_mapping: Dict[str, str]):
        """
        Persist timeframe changes to configuration file.
        
        Updates the config.py file by modifying the TIMEFRAMES dictionary.
        
        Args:
            timeframe_mapping: Mapping of roles to timeframes
            
        Raises:
            IOError: If unable to read or write configuration file
        """
        try:
            # Read current file content
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find TIMEFRAMES dictionary and replace it
            # Pattern: TIMEFRAMES = {...}
            pattern = r'(TIMEFRAMES\s*=\s*\{)[^}]*(\})'
            
            # Check if pattern exists
            if not re.search(pattern, content):
                raise ValueError("Could not find 'TIMEFRAMES' in configuration file")
            
            # Format new timeframes dictionary
            timeframes_str = ',\n    '.join(
                f'"{role}": "{tf}"'
                for role, tf in timeframe_mapping.items()
            )
            new_dict = f'\n    {timeframes_str},\n'
            
            # Replace dictionary
            updated_content = re.sub(pattern, rf'\g<1>{new_dict}\g<2>', content)
            
            # Write back to file
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            logger.debug(f"Persisted timeframes to {self.config_path}")
            
        except FileNotFoundError:
            raise IOError(f"Configuration file not found: {self.config_path}")
        except Exception as e:
            raise IOError(f"Failed to persist configuration: {str(e)}")
