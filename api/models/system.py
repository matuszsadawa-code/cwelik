"""
System health models
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict


class SystemHealthResponse(BaseModel):
    """System health metrics"""
    api_success_rate: Dict[str, float] = Field(description="API success rate per exchange")
    api_response_time: Dict[str, float] = Field(description="API response time per exchange (ms)")
    ws_connected: Dict[str, bool] = Field(description="WebSocket connection status per exchange")
    db_query_time: float = Field(description="Database query time (ms)")
    signal_processing_latency: float = Field(description="Signal processing latency (ms)")
    last_update: datetime = Field(description="Last successful data update")
    uptime: int = Field(description="System uptime in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "api_success_rate": {"binance": 99.5, "bybit": 98.8},
                "api_response_time": {"binance": 120.5, "bybit": 145.2},
                "ws_connected": {"binance": True, "bybit": True},
                "db_query_time": 15.3,
                "signal_processing_latency": 45.2,
                "last_update": "2024-01-01T12:00:00Z",
                "uptime": 86400
            }
        }
