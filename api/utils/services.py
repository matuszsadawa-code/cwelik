"""
Service accessor utilities for API routes

Provides access to global service instances from routes.
"""

from typing import Optional
from api.services.position_service import PositionService


# Global service references (set by main.py)
_position_service: Optional[PositionService] = None


def set_position_service(service: PositionService):
    """Set the global position service instance"""
    global _position_service
    _position_service = service


def get_position_service() -> Optional[PositionService]:
    """Get the global position service instance"""
    return _position_service
