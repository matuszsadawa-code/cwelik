"""
Configuration API routes for OpenClaw Trading Dashboard

Provides endpoints for configuration management including:
- Feature flags management
- Strategy parameters adjustment
- Risk settings configuration
- Symbol selection
- Timeframe configuration
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

from api.services.feature_flags_service import FeatureFlagsService
from api.services.strategy_params_service import StrategyParamsService
from api.services.risk_settings_service import RiskSettingsService
from api.services.symbol_config_service import SymbolConfigService
from api.services.timeframe_config_service import TimeframeConfigService
from api.services.config_profile_service import ConfigProfileService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/config", tags=["configuration"])

# Initialize services
feature_flags_service = None
strategy_params_service = None
risk_settings_service = None
symbol_config_service = None
timeframe_config_service = None
config_profile_service = None


def init_config_services(db=None):
    """Initialize configuration services"""
    global feature_flags_service, strategy_params_service, risk_settings_service
    global symbol_config_service, timeframe_config_service, config_profile_service
    
    feature_flags_service = FeatureFlagsService()
    strategy_params_service = StrategyParamsService()
    risk_settings_service = RiskSettingsService(db=db)
    symbol_config_service = SymbolConfigService(db=db)
    timeframe_config_service = TimeframeConfigService()
    config_profile_service = ConfigProfileService(db=db)
    
    logger.info("Configuration services initialized")


# ============================================================================
# Request/Response Models
# ============================================================================

class FeatureFlagUpdateRequest(BaseModel):
    """Request model for updating a feature flag"""
    flag_name: str = Field(..., description="Name of the feature flag to update")
    enabled: bool = Field(..., description="New enabled state (True/False)")


class FeatureFlagResponse(BaseModel):
    """Response model for a single feature flag"""
    name: str
    enabled: bool
    description: str
    confidenceBoost: int
    phase: int


class FeatureFlagsResponse(BaseModel):
    """Response model for all feature flags grouped by phase"""
    phase1: list[FeatureFlagResponse]
    phase2: list[FeatureFlagResponse]
    phase3: list[FeatureFlagResponse]
    phase4: list[FeatureFlagResponse]


class FeatureFlagUpdateResponse(BaseModel):
    """Response model for feature flag update operation"""
    success: bool
    flag: FeatureFlagResponse | None = None
    message: str | None = None
    error: str | None = None
    timestamp: int


# ============================================================================
# Feature Flags Endpoints
# ============================================================================

@router.get("/feature-flags", response_model=Dict[str, Any])
async def get_feature_flags():
    """
    Get all feature flags with current states and metadata.
    
    Returns feature flags grouped by phase (Phase 1-4) with:
    - name: Feature flag identifier
    - enabled: Current state (True/False)
    - description: Human-readable description
    - confidenceBoost: Performance impact (confidence boost value)
    - phase: Phase number (1-4)
    
    **Validates: Requirements 15.1**
    """
    try:
        if feature_flags_service is None:
            raise HTTPException(status_code=500, detail="Feature flags service not initialized")
        
        flags = feature_flags_service.get_all_flags()
        
        logger.debug(f"Retrieved feature flags: {sum(len(v) for v in flags.values())} total")
        
        return flags
        
    except Exception as e:
        logger.error(f"Error retrieving feature flags: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve feature flags: {str(e)}")


@router.put("/feature-flags", response_model=Dict[str, Any])
async def update_feature_flag(request: FeatureFlagUpdateRequest):
    """
    Update a feature flag state.
    
    Updates the specified feature flag's enabled state and persists the change
    to the configuration file.
    
    **Request Body:**
    - flag_name: Name of the feature flag (e.g., "vsa_analysis", "wyckoff_method")
    - enabled: New state (True to enable, False to disable)
    
    **Returns:**
    - success: Whether the update succeeded
    - flag: Updated flag state and metadata (if successful)
    - message: Success message (if successful)
    - error: Error message (if failed)
    - timestamp: Update timestamp in milliseconds
    
    **Validates: Requirements 15.2, 15.6, 15.7, 15.8**
    """
    try:
        if feature_flags_service is None:
            raise HTTPException(status_code=500, detail="Feature flags service not initialized")
        
        # Update flag
        result = feature_flags_service.update_flag(request.flag_name, request.enabled)
        
        # Check if update was successful
        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error")
            logger.warning(f"Feature flag update failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        logger.info(f"Feature flag '{request.flag_name}' updated: enabled={request.enabled}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating feature flag: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update feature flag: {str(e)}")


@router.get("/feature-flags/{flag_name}", response_model=Dict[str, Any])
async def get_feature_flag(flag_name: str):
    """
    Get state and metadata for a specific feature flag.
    
    **Path Parameters:**
    - flag_name: Name of the feature flag
    
    **Returns:**
    - name: Feature flag identifier
    - enabled: Current state (True/False)
    - description: Human-readable description
    - confidenceBoost: Performance impact (confidence boost value)
    - phase: Phase number (1-4)
    
    **Validates: Requirements 15.1, 15.9**
    """
    try:
        if feature_flags_service is None:
            raise HTTPException(status_code=500, detail="Feature flags service not initialized")
        
        flag = feature_flags_service.get_flag_state(flag_name)
        
        if flag is None:
            raise HTTPException(status_code=404, detail=f"Feature flag '{flag_name}' not found")
        
        return flag
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving feature flag: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve feature flag: {str(e)}")


@router.get("/feature-flags/enabled/list")
async def get_enabled_flags():
    """
    Get list of currently enabled feature flag names.
    
    **Returns:**
    - enabled_flags: List of enabled flag names
    - count: Number of enabled flags
    """
    try:
        if feature_flags_service is None:
            raise HTTPException(status_code=500, detail="Feature flags service not initialized")
        
        enabled_flags = feature_flags_service.get_enabled_flags()
        
        return {
            "enabled_flags": enabled_flags,
            "count": len(enabled_flags),
        }
        
    except Exception as e:
        logger.error(f"Error retrieving enabled flags: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve enabled flags: {str(e)}")



# ============================================================================
# Strategy Parameters Endpoints
# ============================================================================

class StrategyParamsUpdateRequest(BaseModel):
    """Request model for updating strategy parameters"""
    parameters: Dict[str, Any] = Field(..., description="Dictionary of parameter names and values")


@router.get("/strategy-params", response_model=Dict[str, Any])
async def get_strategy_params():
    """
    Get all strategy parameters with current values and metadata.
    
    Returns parameters grouped by category (trend, zones, volume, orderflow, risk, monitoring)
    with current value, default value, valid range, and description.
    
    **Validates: Requirements 16.1**
    """
    try:
        if strategy_params_service is None:
            raise HTTPException(status_code=500, detail="Strategy params service not initialized")
        
        params = strategy_params_service.get_all_params()
        logger.debug(f"Retrieved strategy parameters")
        return params
        
    except Exception as e:
        logger.error(f"Error retrieving strategy parameters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve parameters: {str(e)}")


@router.put("/strategy-params", response_model=Dict[str, Any])
async def update_strategy_params(request: StrategyParamsUpdateRequest):
    """
    Update strategy parameters.
    
    Updates multiple strategy parameters and persists changes to configuration file.
    Validates all parameter values against valid ranges before applying.
    
    **Request Body:**
    - parameters: Dictionary of parameter names and new values
    
    **Returns:**
    - success: Whether the update succeeded
    - updated: Updated parameter values and metadata (if successful)
    - message: Success message (if successful)
    - error: Error message (if failed)
    
    **Validates: Requirements 16.2, 16.3, 16.10**
    """
    try:
        if strategy_params_service is None:
            raise HTTPException(status_code=500, detail="Strategy params service not initialized")
        
        result = strategy_params_service.update_params(request.parameters)
        
        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error")
            logger.warning(f"Strategy params update failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        logger.info(f"Updated {len(request.parameters)} strategy parameters")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating strategy parameters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update parameters: {str(e)}")


@router.post("/strategy-params/reset")
async def reset_strategy_params(category: Optional[str] = None):
    """
    Reset strategy parameters to default values.
    
    **Query Parameters:**
    - category: Optional category to reset (trend, zones, volume, orderflow, risk, monitoring)
                If not provided, resets all parameters
    
    **Validates: Requirements 16.11**
    """
    try:
        if strategy_params_service is None:
            raise HTTPException(status_code=500, detail="Strategy params service not initialized")
        
        result = strategy_params_service.reset_to_defaults(category)
        
        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error")
            raise HTTPException(status_code=400, detail=error_msg)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting parameters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reset parameters: {str(e)}")


# ============================================================================
# Risk Settings Endpoints
# ============================================================================

class RiskSettingsUpdateRequest(BaseModel):
    """Request model for updating risk settings"""
    settings: Dict[str, float] = Field(..., description="Dictionary of risk setting names and values")


@router.get("/risk-settings", response_model=Dict[str, Any])
async def get_risk_settings():
    """
    Get all risk management settings with current values and utilization.
    
    Returns risk settings with metadata and current risk utilization metrics
    (portfolio exposure, current drawdown, daily loss, open positions).
    
    **Validates: Requirements 17.1**
    """
    try:
        if risk_settings_service is None:
            raise HTTPException(status_code=500, detail="Risk settings service not initialized")
        
        settings = risk_settings_service.get_all_settings()
        logger.debug("Retrieved risk settings")
        return settings
        
    except Exception as e:
        logger.error(f"Error retrieving risk settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve settings: {str(e)}")


@router.put("/risk-settings", response_model=Dict[str, Any])
async def update_risk_settings(request: RiskSettingsUpdateRequest):
    """
    Update risk management settings.
    
    Updates risk settings and checks if current positions violate new settings.
    Returns warnings if violations are detected.
    
    **Request Body:**
    - settings: Dictionary of risk setting names and new values
    
    **Returns:**
    - success: Whether the update succeeded
    - updated: Updated setting values and metadata (if successful)
    - warnings: List of position violations (if any)
    - message: Success message (if successful)
    - error: Error message (if failed)
    
    **Validates: Requirements 17.2, 17.10**
    """
    try:
        if risk_settings_service is None:
            raise HTTPException(status_code=500, detail="Risk settings service not initialized")
        
        result = risk_settings_service.update_settings(request.settings)
        
        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error")
            logger.warning(f"Risk settings update failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        logger.info(f"Updated {len(request.settings)} risk settings")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating risk settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")


# ============================================================================
# Symbol Configuration Endpoints
# ============================================================================

class SymbolUpdateRequest(BaseModel):
    """Request model for updating monitored symbols"""
    symbols: List[str] = Field(..., description="List of symbol names to monitor")


@router.get("/symbols/available", response_model=Dict[str, Any])
async def get_available_symbols():
    """
    Get list of available symbols from exchanges.
    
    Returns available symbols with performance metrics to aid selection.
    
    **Validates: Requirements 18.1**
    """
    try:
        if symbol_config_service is None:
            raise HTTPException(status_code=500, detail="Symbol config service not initialized")
        
        symbols = symbol_config_service.get_available_symbols()
        logger.debug(f"Retrieved {symbols['count']} available symbols")
        return symbols
        
    except Exception as e:
        logger.error(f"Error retrieving available symbols: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve symbols: {str(e)}")


@router.get("/symbols/monitored", response_model=Dict[str, Any])
async def get_monitored_symbols():
    """
    Get currently monitored symbols from configuration.
    
    Returns fixed symbols, dynamic configuration, and all monitored symbols.
    
    **Validates: Requirements 18.2**
    """
    try:
        if symbol_config_service is None:
            raise HTTPException(status_code=500, detail="Symbol config service not initialized")
        
        symbols = symbol_config_service.get_monitored_symbols()
        logger.debug(f"Retrieved {symbols['count']} monitored symbols")
        return symbols
        
    except Exception as e:
        logger.error(f"Error retrieving monitored symbols: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve symbols: {str(e)}")


@router.put("/symbols/monitored", response_model=Dict[str, Any])
async def update_monitored_symbols(request: SymbolUpdateRequest):
    """
    Update the list of monitored symbols.
    
    Updates the monitored symbols list and persists to configuration file.
    
    **Request Body:**
    - symbols: List of symbol names to monitor (e.g., ["BTCUSDT", "ETHUSDT"])
    
    **Returns:**
    - success: Whether the update succeeded
    - symbols: Updated symbol list (if successful)
    - count: Number of symbols (if successful)
    - message: Success message (if successful)
    - error: Error message (if failed)
    
    **Validates: Requirements 18.3, 18.9**
    """
    try:
        if symbol_config_service is None:
            raise HTTPException(status_code=500, detail="Symbol config service not initialized")
        
        result = symbol_config_service.update_monitored_symbols(request.symbols)
        
        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error")
            logger.warning(f"Symbol update failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        logger.info(f"Updated monitored symbols: {result['count']} symbols")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating monitored symbols: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update symbols: {str(e)}")


@router.get("/symbols/{symbol}/performance", response_model=Dict[str, Any])
async def get_symbol_performance(symbol: str):
    """
    Get detailed performance metrics for a specific symbol.
    
    **Path Parameters:**
    - symbol: Symbol name (e.g., BTCUSDT)
    
    **Returns:**
    Detailed performance metrics including win rate, profit factor, total P&L, etc.
    """
    try:
        if symbol_config_service is None:
            raise HTTPException(status_code=500, detail="Symbol config service not initialized")
        
        performance = symbol_config_service.get_symbol_performance(symbol)
        return performance
        
    except Exception as e:
        logger.error(f"Error retrieving symbol performance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve performance: {str(e)}")


# ============================================================================
# Timeframe Configuration Endpoints
# ============================================================================

class TimeframeUpdateRequest(BaseModel):
    """Request model for updating timeframes"""
    timeframes: Dict[str, str] = Field(
        ...,
        description="Dictionary of timeframe assignments (trend, zones, confirmation)"
    )


@router.get("/timeframes", response_model=Dict[str, Any])
async def get_timeframes():
    """
    Get configured timeframes.
    
    Returns currently configured timeframes with estimated data fetch time.
    
    **Validates: Requirements 19.1**
    """
    try:
        if timeframe_config_service is None:
            raise HTTPException(status_code=500, detail="Timeframe config service not initialized")
        
        timeframes = timeframe_config_service.get_configured_timeframes()
        logger.debug(f"Retrieved {timeframes['count']} configured timeframes")
        return timeframes
        
    except Exception as e:
        logger.error(f"Error retrieving timeframes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve timeframes: {str(e)}")


@router.get("/timeframes/available", response_model=Dict[str, Any])
async def get_available_timeframes():
    """
    Get list of available timeframes.
    
    Returns all available timeframes with metadata.
    """
    try:
        if timeframe_config_service is None:
            raise HTTPException(status_code=500, detail="Timeframe config service not initialized")
        
        timeframes = timeframe_config_service.get_available_timeframes()
        return timeframes
        
    except Exception as e:
        logger.error(f"Error retrieving available timeframes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve timeframes: {str(e)}")


@router.put("/timeframes", response_model=Dict[str, Any])
async def update_timeframes(request: TimeframeUpdateRequest):
    """
    Update timeframe configuration.
    
    Updates timeframe assignments and validates minimum requirements (at least 2 unique timeframes).
    
    **Request Body:**
    - timeframes: Dictionary of timeframe assignments
                 {"trend": "240", "zones": "30", "confirmation": "5"}
    
    **Returns:**
    - success: Whether the update succeeded
    - timeframes: Updated timeframe assignments (if successful)
    - enabled: List of unique enabled timeframes (if successful)
    - count: Number of unique timeframes (if successful)
    - estimated_fetch_time: Estimated data fetch time in seconds (if successful)
    - message: Success message (if successful)
    - error: Error message (if failed)
    
    **Validates: Requirements 19.2, 19.8, 19.9**
    """
    try:
        if timeframe_config_service is None:
            raise HTTPException(status_code=500, detail="Timeframe config service not initialized")
        
        result = timeframe_config_service.update_timeframes(request.timeframes)
        
        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error")
            logger.warning(f"Timeframe update failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        logger.info(f"Updated timeframes: {result['count']} unique timeframes")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating timeframes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update timeframes: {str(e)}")


# ============================================================================
# Configuration Profile Endpoints
# ============================================================================

class ProfileSaveRequest(BaseModel):
    """Request model for saving a configuration profile"""
    name: str = Field(..., description="Profile name")
    description: Optional[str] = Field(None, description="Profile description")


@router.get("/profiles", response_model=Dict[str, Any])
async def list_profiles():
    """
    List all available configuration profiles.
    
    Returns list of profiles including default profiles (conservative, balanced, aggressive)
    and custom user-created profiles.
    
    **Validates: Requirements 25.2**
    """
    try:
        if config_profile_service is None:
            raise HTTPException(status_code=500, detail="Config profile service not initialized")
        
        profiles = config_profile_service.list_profiles()
        logger.debug(f"Listed {len(profiles)} configuration profiles")
        return {"profiles": profiles, "count": len(profiles)}
        
    except Exception as e:
        logger.error(f"Error listing profiles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list profiles: {str(e)}")


@router.post("/profiles", response_model=Dict[str, Any])
async def save_profile(request: ProfileSaveRequest):
    """
    Save current configuration as a named profile.
    
    Saves the current feature flags, strategy parameters, and risk settings
    as a named profile for quick switching.
    
    **Request Body:**
    - name: Profile name (minimum 3 characters)
    - description: Optional profile description
    
    **Returns:**
    - success: Whether the save succeeded
    - profile_id: Generated profile ID (if successful)
    - name: Profile name (if successful)
    - message: Success message (if successful)
    - error: Error message (if failed)
    
    **Validates: Requirements 25.1, 25.11**
    """
    try:
        if config_profile_service is None:
            raise HTTPException(status_code=500, detail="Config profile service not initialized")
        
        result = config_profile_service.save_profile(
            name=request.name,
            description=request.description
        )
        
        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error")
            logger.warning(f"Profile save failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        logger.info(f"Saved configuration profile: {request.name}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save profile: {str(e)}")


@router.get("/profiles/{name}", response_model=Dict[str, Any])
async def get_profile(name: str):
    """
    Load a configuration profile.
    
    Retrieves the configuration from a named profile.
    
    **Path Parameters:**
    - name: Profile name or ID
    
    **Returns:**
    - success: Whether the load succeeded
    - profile_name: Profile name (if successful)
    - config: Profile configuration (if successful)
    - message: Success message (if successful)
    - error: Error message (if failed)
    
    **Validates: Requirements 25.3**
    """
    try:
        if config_profile_service is None:
            raise HTTPException(status_code=500, detail="Config profile service not initialized")
        
        result = config_profile_service.load_profile(name)
        
        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error")
            logger.warning(f"Profile load failed: {error_msg}")
            raise HTTPException(status_code=404, detail=error_msg)
        
        logger.info(f"Loaded configuration profile: {name}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load profile: {str(e)}")


@router.delete("/profiles/{name}", response_model=Dict[str, Any])
async def delete_profile(name: str):
    """
    Delete a configuration profile.
    
    Deletes a custom configuration profile. Cannot delete default profiles.
    
    **Path Parameters:**
    - name: Profile name or ID
    
    **Returns:**
    - success: Whether the delete succeeded
    - message: Success message (if successful)
    - error: Error message (if failed)
    
    **Validates: Requirements 25.4**
    """
    try:
        if config_profile_service is None:
            raise HTTPException(status_code=500, detail="Config profile service not initialized")
        
        result = config_profile_service.delete_profile(name)
        
        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error")
            logger.warning(f"Profile delete failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        logger.info(f"Deleted configuration profile: {name}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete profile: {str(e)}")
