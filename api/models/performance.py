"""
Performance metrics models
"""

from pydantic import BaseModel, Field
from datetime import datetime


class PerformanceMetricsResponse(BaseModel):
    """Real-time performance metrics"""
    win_rate: float = Field(ge=0, le=100, description="Win rate percentage")
    profit_factor: float = Field(ge=0, description="Profit factor (wins/losses)")
    sharpe_ratio: float = Field(description="Sharpe ratio")
    max_drawdown: float = Field(le=0, description="Maximum drawdown percentage")
    current_drawdown: float = Field(le=0, description="Current drawdown percentage")
    daily_pnl: float = Field(description="Daily P&L")
    weekly_pnl: float = Field(description="Weekly P&L")
    monthly_pnl: float = Field(description="Monthly P&L")
    total_trades: int = Field(ge=0, description="Total number of trades")
    active_positions: int = Field(ge=0, description="Number of active positions")
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "win_rate": 58.5,
                "profit_factor": 1.85,
                "sharpe_ratio": 1.42,
                "max_drawdown": -12.5,
                "current_drawdown": -3.2,
                "daily_pnl": 250.0,
                "weekly_pnl": 1500.0,
                "monthly_pnl": 6800.0,
                "total_trades": 145,
                "active_positions": 3,
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
