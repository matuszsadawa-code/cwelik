"""
Configuration models
"""

from pydantic import BaseModel, Field
from typing import Dict, Optional


class FeatureFlagsUpdate(BaseModel):
    """Update feature flag state"""
    flag_name: str = Field(description="Feature flag name")
    enabled: bool = Field(description="Enable or disable the feature")

    class Config:
        json_schema_extra = {
            "example": {
                "flag_name": "vsa",
                "enabled": True
            }
        }


class StrategyParametersUpdate(BaseModel):
    """Update strategy parameters"""
    parameters: Dict[str, float] = Field(description="Parameter name-value pairs")

    class Config:
        json_schema_extra = {
            "example": {
                "parameters": {
                    "trend_strength_threshold": 0.65,
                    "volume_confirmation_multiplier": 1.5
                }
            }
        }


class RiskSettingsUpdate(BaseModel):
    """Update risk management settings"""
    max_position_size: Optional[float] = Field(None, ge=0, description="Maximum position size")
    max_portfolio_exposure: Optional[float] = Field(None, ge=0, le=1, description="Maximum portfolio exposure (0-1)")
    max_drawdown_limit: Optional[float] = Field(None, le=0, description="Maximum drawdown limit (negative)")
    max_daily_loss_limit: Optional[float] = Field(None, le=0, description="Maximum daily loss limit")
    correlation_threshold: Optional[float] = Field(None, ge=0, le=1, description="Correlation threshold (0-1)")

    class Config:
        json_schema_extra = {
            "example": {
                "max_position_size": 10000.0,
                "max_portfolio_exposure": 0.8,
                "max_drawdown_limit": -0.15,
                "max_daily_loss_limit": -500.0,
                "correlation_threshold": 0.7
            }
        }
