"""
API route handlers for OpenClaw Trading Dashboard
"""

from .auth import router as auth_router
from .market import router as market_router
from .signals import router as signals_router
from .positions import router as positions_router
from .analytics import router as analytics_router
from .config import router as config_router
from .trades import router as trades_router

__all__ = [
    "auth_router",
    "market_router",
    "signals_router",
    "positions_router",
    "analytics_router",
    "config_router",
    "trades_router",
]
