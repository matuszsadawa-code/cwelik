"""
Feature Flags Service for OpenClaw Trading Dashboard

Manages the 20 advanced trading feature flags with configuration persistence.

Features:
- Retrieve current feature flag states from config/feature_flags.py
- Update individual feature flag states
- Validate flag names before updating
- Persist flag changes to configuration file
- Return performance impact data (confidence boost) if available
- Group flags by phase (Phase 1-4)
"""

import logging
import os
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class FeatureFlagsService:
    """
    Service for managing feature flags configuration.
    
    Responsibilities:
    - Load feature flags from config/feature_flags.py
    - Validate flag names against available features
    - Update flag states (enabled/disabled)
    - Persist changes to configuration file
    - Return flag metadata (description, phase, performance impact)
    """
    
    def __init__(self):
        """Initialize feature flags service."""
        self.config_path = "config/feature_flags.py"
        logger.info("FeatureFlagsService initialized")
    
    def get_all_flags(self) -> Dict[str, Any]:
        """
        Get all feature flags with their current states and metadata.
        
        Returns:
            dict: Feature flags grouped by phase with metadata
            {
                "phase1": [
                    {
                        "name": "vsa_analysis",
                        "enabled": False,
                        "description": "Volume Spread Analysis...",
                        "confidenceBoost": 10,
                        "phase": 1
                    },
                    ...
                ],
                "phase2": [...],
                "phase3": [...],
                "phase4": [...]
            }
        """
        try:
            # Import feature flags dynamically
            import config.feature_flags as ff
            
            # Build response grouped by phase
            result = {
                "phase1": self._build_phase_flags(ff.PHASE_1_FEATURES, 1),
                "phase2": self._build_phase_flags(ff.PHASE_2_FEATURES, 2),
                "phase3": self._build_phase_flags(ff.PHASE_3_FEATURES, 3),
                "phase4": self._build_phase_flags(ff.PHASE_4_FEATURES, 4),
            }
            
            logger.debug(f"Retrieved {sum(len(v) for v in result.values())} feature flags")
            return result
            
        except Exception as e:
            logger.error(f"Error loading feature flags: {e}", exc_info=True)
            raise
    
    def _build_phase_flags(self, phase_features: Dict, phase_number: int) -> List[Dict]:
        """
        Build list of flag dictionaries for a phase.
        
        Args:
            phase_features: Dictionary of features in the phase
            phase_number: Phase number (1-4)
            
        Returns:
            list: List of flag dictionaries with metadata
        """
        flags = []
        for name, config in phase_features.items():
            flags.append({
                "name": name,
                "enabled": config.get("enabled", False),
                "description": config.get("description", ""),
                "confidenceBoost": config.get("confidence_boost", 0),
                "phase": phase_number,
            })
        return flags
    
    def get_flag_state(self, flag_name: str) -> Optional[Dict]:
        """
        Get state and metadata for a specific feature flag.
        
        Args:
            flag_name: Name of the feature flag
            
        Returns:
            dict: Flag state and metadata, or None if not found
        """
        try:
            import config.feature_flags as ff
            
            all_features = ff.get_all_features()
            
            if flag_name not in all_features:
                return None
            
            feature = all_features[flag_name]
            phase = self._get_flag_phase(flag_name)
            
            return {
                "name": flag_name,
                "enabled": feature.get("enabled", False),
                "description": feature.get("description", ""),
                "confidenceBoost": feature.get("confidence_boost", 0),
                "phase": phase,
            }
            
        except Exception as e:
            logger.error(f"Error getting flag state for {flag_name}: {e}")
            return None
    
    def _get_flag_phase(self, flag_name: str) -> int:
        """
        Determine which phase a flag belongs to.
        
        Args:
            flag_name: Name of the feature flag
            
        Returns:
            int: Phase number (1-4) or 0 if not found
        """
        try:
            import config.feature_flags as ff
            
            if flag_name in ff.PHASE_1_FEATURES:
                return 1
            elif flag_name in ff.PHASE_2_FEATURES:
                return 2
            elif flag_name in ff.PHASE_3_FEATURES:
                return 3
            elif flag_name in ff.PHASE_4_FEATURES:
                return 4
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Error determining phase for {flag_name}: {e}")
            return 0
    
    def update_flag(self, flag_name: str, enabled: bool) -> Dict[str, Any]:
        """
        Update a feature flag state and persist to configuration file.
        
        Args:
            flag_name: Name of the feature flag to update
            enabled: New enabled state (True/False)
            
        Returns:
            dict: Result with success status and updated flag state
            {
                "success": True,
                "flag": {...},
                "message": "Feature flag updated successfully"
            }
            
        Raises:
            ValueError: If flag name is invalid
            IOError: If unable to persist changes
        """
        try:
            # Validate flag name
            if not self._validate_flag_name(flag_name):
                raise ValueError(f"Invalid feature flag name: {flag_name}")
            
            # Update in-memory configuration
            self._update_in_memory(flag_name, enabled)
            
            # Persist to file
            self._persist_to_file(flag_name, enabled)
            
            # Get updated flag state
            updated_flag = self.get_flag_state(flag_name)
            
            logger.info(f"Feature flag '{flag_name}' updated: enabled={enabled}")
            
            return {
                "success": True,
                "flag": updated_flag,
                "message": f"Feature flag '{flag_name}' updated successfully",
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
            
        except ValueError as e:
            logger.warning(f"Validation error updating flag: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
        except Exception as e:
            logger.error(f"Error updating feature flag: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to update feature flag: {str(e)}",
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
    
    def _validate_flag_name(self, flag_name: str) -> bool:
        """
        Validate that flag name exists in configuration.
        
        Args:
            flag_name: Name of the feature flag
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            import config.feature_flags as ff
            all_features = ff.get_all_features()
            return flag_name in all_features
        except Exception as e:
            logger.error(f"Error validating flag name: {e}")
            return False
    
    def _update_in_memory(self, flag_name: str, enabled: bool):
        """
        Update feature flag in the in-memory configuration.
        
        Args:
            flag_name: Name of the feature flag
            enabled: New enabled state
        """
        import config.feature_flags as ff
        
        # Find and update the flag in the appropriate phase
        for phase_features in [ff.PHASE_1_FEATURES, ff.PHASE_2_FEATURES, 
                               ff.PHASE_3_FEATURES, ff.PHASE_4_FEATURES]:
            if flag_name in phase_features:
                phase_features[flag_name]["enabled"] = enabled
                return
        
        raise ValueError(f"Feature flag '{flag_name}' not found in any phase")
    
    def _persist_to_file(self, flag_name: str, enabled: bool):
        """
        Persist feature flag change to configuration file.
        
        Updates the config/feature_flags.py file by modifying the "enabled" value
        for the specified flag.
        
        Args:
            flag_name: Name of the feature flag
            enabled: New enabled state
            
        Raises:
            IOError: If unable to read or write configuration file
        """
        try:
            # Read current file content
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find the flag definition and update enabled value
            # Pattern: "flag_name": { ... "enabled": True/False, ... }
            pattern = rf'("{flag_name}":\s*\{{[^}}]*"enabled":\s*)(True|False)'
            
            # Check if pattern exists
            if not re.search(pattern, content):
                raise ValueError(f"Could not find '{flag_name}' in configuration file")
            
            # Replace enabled value
            new_value = "True" if enabled else "False"
            updated_content = re.sub(pattern, rf'\g<1>{new_value}', content)
            
            # Write back to file
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            logger.debug(f"Persisted flag '{flag_name}' to {self.config_path}")
            
        except FileNotFoundError:
            raise IOError(f"Configuration file not found: {self.config_path}")
        except Exception as e:
            raise IOError(f"Failed to persist configuration: {str(e)}")
    
    def get_enabled_flags(self) -> List[str]:
        """
        Get list of currently enabled feature flag names.
        
        Returns:
            list: List of enabled flag names
        """
        try:
            import config.feature_flags as ff
            enabled_features = ff.get_enabled_features()
            return list(enabled_features.keys())
        except Exception as e:
            logger.error(f"Error getting enabled flags: {e}")
            return []
    
    def get_service_status(self) -> Dict:
        """
        Get service status for health monitoring.
        
        Returns:
            dict: Service status including configuration file accessibility
        """
        config_exists = os.path.exists(self.config_path)
        config_writable = os.access(self.config_path, os.W_OK) if config_exists else False
        
        return {
            "config_file_exists": config_exists,
            "config_file_writable": config_writable,
            "config_path": self.config_path,
        }
