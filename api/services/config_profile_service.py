"""
Configuration Profile Management Service for OpenClaw Trading Dashboard

Manages configuration profiles for quick strategy switching.

Features:
- Save current configuration as named profile
- Load configuration from profile
- List available profiles
- Delete profiles
- Include default profiles (conservative, balanced, aggressive)
- Store profiles in database
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ConfigProfileService:
    """
    Service for managing configuration profiles.
    
    Responsibilities:
    - Save current configuration as profile
    - Load configuration from profile
    - List available profiles
    - Delete profiles
    - Provide default profiles
    - Store profiles in database
    """
    
    # Default configuration profiles
    DEFAULT_PROFILES = {
        "conservative": {
            "name": "Conservative",
            "description": "Low-risk configuration with strict filters",
            "feature_flags": {
                "vsa_analysis": True,
                "wyckoff_method": True,
                "market_profile": True,
                "liquidity_engineering": True,
                "smart_money_divergence": True,
                "mtf_confluence": True,
                "orderbook_imbalance": False,
                "institutional_flow": False,
                "volatility_regime": True,
                "seasonality": False,
                "ml_calibration": True,
                "dynamic_tp": True,
                "dynamic_sl": True,
                "correlation_optimization": True,
                "enhanced_risk_management": True,
                "news_sentiment": False,
                "microstructure": False,
                "backtesting": True,
                "ab_testing": False,
                "performance_dashboard": True
            },
            "strategy_params": {
                "min_quality_for_signal": "A+",
                "tp_rr_ratio": 2.5,
                "default_leverage": 10,
                "sl_buffer_pct": 0.8
            },
            "risk_settings": {
                "max_position_size": 5.0,
                "max_portfolio_exposure": 50.0,
                "max_drawdown_limit": 10.0,
                "max_daily_loss_limit": 3.0,
                "correlation_threshold": 0.6
            }
        },
        "balanced": {
            "name": "Balanced",
            "description": "Balanced risk-reward configuration",
            "feature_flags": {
                "vsa_analysis": True,
                "wyckoff_method": True,
                "market_profile": True,
                "liquidity_engineering": True,
                "smart_money_divergence": True,
                "mtf_confluence": True,
                "orderbook_imbalance": True,
                "institutional_flow": True,
                "volatility_regime": True,
                "seasonality": True,
                "ml_calibration": True,
                "dynamic_tp": True,
                "dynamic_sl": True,
                "correlation_optimization": True,
                "enhanced_risk_management": True,
                "news_sentiment": True,
                "microstructure": True,
                "backtesting": True,
                "ab_testing": True,
                "performance_dashboard": True
            },
            "strategy_params": {
                "min_quality_for_signal": "A",
                "tp_rr_ratio": 2.0,
                "default_leverage": 25,
                "sl_buffer_pct": 0.5
            },
            "risk_settings": {
                "max_position_size": 10.0,
                "max_portfolio_exposure": 100.0,
                "max_drawdown_limit": 20.0,
                "max_daily_loss_limit": 5.0,
                "correlation_threshold": 0.7
            }
        },
        "aggressive": {
            "name": "Aggressive",
            "description": "High-risk, high-reward configuration",
            "feature_flags": {
                "vsa_analysis": True,
                "wyckoff_method": True,
                "market_profile": True,
                "liquidity_engineering": True,
                "smart_money_divergence": True,
                "mtf_confluence": True,
                "orderbook_imbalance": True,
                "institutional_flow": True,
                "volatility_regime": True,
                "seasonality": True,
                "ml_calibration": True,
                "dynamic_tp": True,
                "dynamic_sl": True,
                "correlation_optimization": False,
                "enhanced_risk_management": True,
                "news_sentiment": True,
                "microstructure": True,
                "backtesting": True,
                "ab_testing": True,
                "performance_dashboard": True
            },
            "strategy_params": {
                "min_quality_for_signal": "B",
                "tp_rr_ratio": 3.0,
                "default_leverage": 50,
                "sl_buffer_pct": 0.3
            },
            "risk_settings": {
                "max_position_size": 20.0,
                "max_portfolio_exposure": 150.0,
                "max_drawdown_limit": 30.0,
                "max_daily_loss_limit": 10.0,
                "correlation_threshold": 0.8
            }
        }
    }
    
    def __init__(self, db=None):
        """
        Initialize configuration profile service.
        
        Args:
            db: Database instance for storing profiles
        """
        self.db = db
        self._ensure_profile_table()
        logger.info("ConfigProfileService initialized")
    
    def _ensure_profile_table(self):
        """Ensure configuration_profiles table exists in database."""
        if not self.db:
            return
        
        try:
            conn = self.db._get_conn()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS configuration_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    config_json TEXT NOT NULL,
                    is_default INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_profiles_name ON configuration_profiles(name)
            """)
            conn.commit()
            logger.debug("Configuration profiles table ensured")
        except Exception as e:
            logger.error(f"Error creating profiles table: {e}")
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """
        List all available configuration profiles.
        
        Returns:
            list: List of profiles with metadata
        """
        try:
            profiles = []
            
            # Add default profiles
            for profile_id, profile_data in self.DEFAULT_PROFILES.items():
                profiles.append({
                    "profile_id": profile_id,
                    "name": profile_data["name"],
                    "description": profile_data["description"],
                    "is_default": True,
                    "created_at": None
                })
            
            # Add custom profiles from database
            if self.db:
                custom_profiles = self._get_custom_profiles()
                profiles.extend(custom_profiles)
            
            logger.debug(f"Listed {len(profiles)} profiles")
            return profiles
            
        except Exception as e:
            logger.error(f"Error listing profiles: {e}", exc_info=True)
            return []
    
    def _get_custom_profiles(self) -> List[Dict[str, Any]]:
        """Get custom profiles from database."""
        try:
            conn = self.db._get_conn()
            rows = conn.execute("""
                SELECT profile_id, name, description, is_default, created_at
                FROM configuration_profiles
                ORDER BY created_at DESC
            """).fetchall()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching custom profiles: {e}")
            return []
    
    def get_profile(self, profile_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific configuration profile.
        
        Args:
            profile_name: Name or ID of the profile
            
        Returns:
            dict: Profile configuration or None if not found
        """
        try:
            # Check default profiles first
            if profile_name in self.DEFAULT_PROFILES:
                profile_data = self.DEFAULT_PROFILES[profile_name].copy()
                profile_data["profile_id"] = profile_name
                profile_data["is_default"] = True
                return profile_data
            
            # Check custom profiles in database
            if self.db:
                conn = self.db._get_conn()
                row = conn.execute("""
                    SELECT * FROM configuration_profiles
                    WHERE profile_id = ? OR name = ?
                """, (profile_name, profile_name)).fetchone()
                
                if row:
                    profile = dict(row)
                    # Parse config JSON
                    profile["config"] = json.loads(profile["config_json"])
                    return profile
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting profile {profile_name}: {e}", exc_info=True)
            return None
    
    def save_profile(
        self,
        name: str,
        description: Optional[str] = None,
        feature_flags: Optional[Dict] = None,
        strategy_params: Optional[Dict] = None,
        risk_settings: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Save current configuration as a named profile.
        
        Args:
            name: Profile name
            description: Optional profile description
            feature_flags: Feature flags configuration (if None, uses current)
            strategy_params: Strategy parameters (if None, uses current)
            risk_settings: Risk settings (if None, uses current)
            
        Returns:
            dict: Result with success status
        """
        try:
            if not self.db:
                raise ValueError("Database not available")
            
            # Validate name
            if not name or len(name) < 3:
                raise ValueError("Profile name must be at least 3 characters")
            
            if name in self.DEFAULT_PROFILES:
                raise ValueError("Cannot overwrite default profile")
            
            # Get current configuration if not provided
            if feature_flags is None:
                import config.feature_flags as ff
                feature_flags = {
                    name: config.get("enabled", False)
                    for name, config in ff.get_all_features().items()
                }
            
            if strategy_params is None:
                import config
                strategy_params = config.STRATEGY.copy()
            
            if risk_settings is None:
                # Get current risk settings
                risk_settings = {}
            
            # Create profile configuration
            profile_config = {
                "feature_flags": feature_flags,
                "strategy_params": strategy_params,
                "risk_settings": risk_settings
            }
            
            # Generate profile ID
            import uuid
            profile_id = str(uuid.uuid4())
            
            # Save to database
            conn = self.db._get_conn()
            now = datetime.now(timezone.utc).isoformat()
            
            conn.execute("""
                INSERT INTO configuration_profiles
                (profile_id, name, description, config_json, is_default, created_at, updated_at)
                VALUES (?, ?, ?, ?, 0, ?, ?)
            """, (
                profile_id,
                name,
                description or "",
                json.dumps(profile_config),
                now,
                now
            ))
            conn.commit()
            
            logger.info(f"Saved configuration profile: {name}")
            return {
                "success": True,
                "profile_id": profile_id,
                "name": name,
                "message": f"Profile '{name}' saved successfully"
            }
            
        except ValueError as e:
            logger.warning(f"Validation error saving profile: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error saving profile: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to save profile: {str(e)}"
            }
    
    def load_profile(self, profile_name: str) -> Dict[str, Any]:
        """
        Load configuration from a profile.
        
        Args:
            profile_name: Name or ID of the profile to load
            
        Returns:
            dict: Result with success status and loaded configuration
        """
        try:
            # Get profile
            profile = self.get_profile(profile_name)
            if not profile:
                raise ValueError(f"Profile not found: {profile_name}")
            
            # Extract configuration
            if profile.get("is_default"):
                config = {
                    "feature_flags": profile["feature_flags"],
                    "strategy_params": profile["strategy_params"],
                    "risk_settings": profile["risk_settings"]
                }
            else:
                config = profile["config"]
            
            logger.info(f"Loaded configuration profile: {profile_name}")
            return {
                "success": True,
                "profile_name": profile.get("name", profile_name),
                "config": config,
                "message": f"Profile '{profile_name}' loaded successfully"
            }
            
        except ValueError as e:
            logger.warning(f"Validation error loading profile: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error loading profile: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to load profile: {str(e)}"
            }
    
    def delete_profile(self, profile_name: str) -> Dict[str, Any]:
        """
        Delete a configuration profile.
        
        Args:
            profile_name: Name or ID of the profile to delete
            
        Returns:
            dict: Result with success status
        """
        try:
            if not self.db:
                raise ValueError("Database not available")
            
            # Cannot delete default profiles
            if profile_name in self.DEFAULT_PROFILES:
                raise ValueError("Cannot delete default profile")
            
            # Delete from database
            conn = self.db._get_conn()
            cursor = conn.execute("""
                DELETE FROM configuration_profiles
                WHERE profile_id = ? OR name = ?
            """, (profile_name, profile_name))
            conn.commit()
            
            if cursor.rowcount == 0:
                raise ValueError(f"Profile not found: {profile_name}")
            
            logger.info(f"Deleted configuration profile: {profile_name}")
            return {
                "success": True,
                "message": f"Profile '{profile_name}' deleted successfully"
            }
            
        except ValueError as e:
            logger.warning(f"Validation error deleting profile: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error deleting profile: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to delete profile: {str(e)}"
            }
