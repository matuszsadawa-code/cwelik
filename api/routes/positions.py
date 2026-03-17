"""
Trading positions API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
import logging

from api.models.trading import PositionResponse
from api.database import get_database_pool
from api.auth import require_viewer, require_trader, User
from api.utils.services import get_position_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/positions", tags=["positions"])


@router.get("/open", response_model=List[PositionResponse])
async def get_open_positions(current_user: User = Depends(require_viewer)):
    """
    Get all open trading positions from database
    
    Requires: viewer role or higher
    
    Returns:
        List[PositionResponse]: List of open positions with current P&L
    """
    try:
        db_pool = get_database_pool()
        
        # Query open positions from executions table
        # Open positions have status = 'OPEN'
        query = """
            SELECT 
                e.execution_id as position_id,
                e.symbol,
                e.direction,
                e.qty as size,
                e.entry_price,
                e.entry_price as current_price,
                0.0 as unrealized_pnl,
                0.0 as unrealized_pnl_percent,
                e.sl_price as stop_loss,
                e.tp_price as take_profit,
                2.0 as risk_reward_ratio,
                e.created_at as opened_at
            FROM executions e
            WHERE e.status = 'OPEN'
            ORDER BY e.created_at DESC
            LIMIT 100
        """
        
        results = db_pool.execute_query(query)
        
        # Convert to PositionResponse models
        positions = []
        for row in results:
            # Calculate duration
            opened_at = datetime.fromisoformat(row['opened_at'].replace('Z', '+00:00'))
            duration = int((datetime.now() - opened_at).total_seconds())
            
            # Calculate risk-reward ratio if stop_loss and take_profit are available
            risk_reward_ratio = 2.0  # Default
            if row['stop_loss'] and row['take_profit']:
                risk = abs(row['entry_price'] - row['stop_loss'])
                reward = abs(row['take_profit'] - row['entry_price'])
                if risk > 0:
                    risk_reward_ratio = reward / risk
            
            position = PositionResponse(
                position_id=row['position_id'],
                symbol=row['symbol'],
                side=row['direction'],  # direction is LONG or SHORT
                size=row['size'],
                entry_price=row['entry_price'],
                current_price=row['current_price'],
                unrealized_pnl=row['unrealized_pnl'],
                unrealized_pnl_percent=row['unrealized_pnl_percent'],
                stop_loss=row['stop_loss'] or 0.0,
                take_profit=row['take_profit'] or 0.0,
                risk_reward_ratio=risk_reward_ratio,
                duration=duration,
                opened_at=opened_at
            )
            positions.append(position)
        
        logger.info(f"Retrieved {len(positions)} open positions")
        return positions
    
    except Exception as e:
        logger.error(f"Failed to retrieve open positions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve open positions: {str(e)}")


@router.post("/{position_id}/close")
async def close_position(position_id: str, current_user: User = Depends(require_trader)):
    """
    Close an open position manually
    
    Requires: trader role or higher
    
    Args:
        position_id: Position ID to close
        current_user: Authenticated user (trader or admin)
        
    Returns:
        Success message with closed position details
    """
    try:
        # Get position service
        position_service = get_position_service()
        
        if not position_service:
            raise HTTPException(
                status_code=503,
                detail="Position service not available"
            )
        
        # Close position using service
        result = await position_service.close_position(
            position_id=position_id,
            reason=f"MANUAL_CLOSE_BY_{current_user.username}"
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=404 if "not found" in result["message"].lower() else 500,
                detail=result["message"]
            )
        
        logger.info(
            f"Position closed manually by {current_user.username}: "
            f"{position_id} ({result['data']['symbol']})"
        )
        
        return {
            "status": "success",
            "message": result["message"],
            "position_id": position_id,
            "symbol": result["data"]["symbol"],
            "exit_price": result["data"]["exit_price"],
            "final_pnl": result["data"]["final_pnl"],
            "closed_by": current_user.username
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to close position {position_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to close position: {str(e)}"
        )
