"""
Market data models
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Tuple


class MarketDataResponse(BaseModel):
    """Real-time market data snapshot"""
    symbol: str
    price: float
    volume24h: float
    change24h: float
    bid_ask_spread: float
    cvd: float
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTCUSDT",
                "price": 45000.50,
                "volume24h": 1234567890.0,
                "change24h": 2.5,
                "bid_ask_spread": 0.10,
                "cvd": 15000.0,
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


class OrderBookResponse(BaseModel):
    """Order book snapshot with bid/ask levels"""
    symbol: str
    bids: List[Tuple[float, float]] = Field(description="List of [price, size] tuples")
    asks: List[Tuple[float, float]] = Field(description="List of [price, size] tuples")
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTCUSDT",
                "bids": [[45000.0, 1.5], [44999.0, 2.0]],
                "asks": [[45001.0, 1.2], [45002.0, 1.8]],
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
