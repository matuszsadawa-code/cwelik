"""
Trading signal and position models
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, Dict


class SignalResponse(BaseModel):
    """Active trading signal"""
    signal_id: str
    symbol: str
    direction: Literal['LONG', 'SHORT']
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    unrealized_pnl: float
    mfe: float = Field(description="Maximum Favorable Excursion")
    mae: float = Field(description="Maximum Adverse Excursion")
    quality: Literal['A+', 'A', 'B', 'C']
    confidence: float = Field(ge=0, le=1)
    status: Literal['ACTIVE', 'CLOSED']
    created_at: datetime
    time_elapsed: int = Field(description="Seconds since signal creation")
    feature_contributions: Dict[str, float] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "signal_id": "sig_123",
                "symbol": "BTCUSDT",
                "direction": "LONG",
                "entry_price": 45000.0,
                "current_price": 45500.0,
                "stop_loss": 44500.0,
                "take_profit": 46000.0,
                "unrealized_pnl": 1.11,
                "mfe": 1.5,
                "mae": -0.3,
                "quality": "A",
                "confidence": 0.85,
                "status": "ACTIVE",
                "created_at": "2024-01-01T12:00:00Z",
                "time_elapsed": 3600,
                "feature_contributions": {"vsa": 0.3, "wyckoff": 0.25}
            }
        }


class PositionResponse(BaseModel):
    """Open trading position"""
    position_id: str
    symbol: str
    side: Literal['LONG', 'SHORT']
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    duration: int = Field(description="Seconds since position opened")
    opened_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "position_id": "pos_456",
                "symbol": "ETHUSDT",
                "side": "LONG",
                "size": 10.0,
                "entry_price": 2500.0,
                "current_price": 2550.0,
                "unrealized_pnl": 500.0,
                "unrealized_pnl_percent": 2.0,
                "stop_loss": 2450.0,
                "take_profit": 2600.0,
                "risk_reward_ratio": 2.0,
                "duration": 7200,
                "opened_at": "2024-01-01T10:00:00Z"
            }
        }
