"""
Market data API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging

from api.models.market import MarketDataResponse
from api.auth import require_viewer, User
import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/symbols", response_model=List[str])
async def get_monitored_symbols(current_user: User = Depends(require_viewer)):
    """
    Get list of monitored trading symbols
    
    Requires: viewer role or higher
    
    Returns:
        List[str]: List of symbol names (e.g., ["BTCUSDT", "ETHUSDT"])
    """
    try:
        # Get symbols from config
        symbols = config.SYMBOLS
        
        logger.info(f"Retrieved {len(symbols)} monitored symbols")
        return symbols
    
    except Exception as e:
        logger.error(f"Failed to retrieve symbols: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve symbols: {str(e)}")
