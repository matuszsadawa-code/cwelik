"""
Trading signals API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
import logging
import json

from api.models.trading import SignalResponse
from api.database import get_database_pool
from api.auth import require_viewer, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/active", response_model=List[SignalResponse])
async def get_active_signals(current_user: User = Depends(require_viewer)):
    """
    Get all active trading signals from database
    
    Requires: viewer role or higher
    
    Returns:
        List[SignalResponse]: List of active signals with current status
    """
    try:
        db_pool = get_database_pool()
        
        # Query active signals from database
        # Active signals are those without a corresponding closed outcome
        query = """
            SELECT 
                s.signal_id,
                s.symbol,
                s.signal_type,
                s.entry_price,
                s.entry_price as current_price,
                s.sl_price as stop_loss,
                s.tp_price as take_profit,
                0.0 as unrealized_pnl,
                0.0 as mfe,
                0.0 as mae,
                s.quality,
                s.confidence,
                'ACTIVE' as status,
                s.created_at,
                s.advanced_analytics
            FROM signals s
            LEFT JOIN signal_outcomes so ON s.signal_id = so.signal_id
            WHERE so.signal_id IS NULL
            ORDER BY s.created_at DESC
            LIMIT 100
        """
        
        results = db_pool.execute_query(query)
        
        # Convert to SignalResponse models
        signals = []
        for row in results:
            # Calculate time elapsed
            created_at = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
            time_elapsed = int((datetime.now() - created_at).total_seconds())
            
            # Parse advanced_analytics JSON if present
            feature_contributions = {}
            if row.get('advanced_analytics'):
                try:
                    analytics = json.loads(row['advanced_analytics'])
                    feature_contributions = analytics.get('feature_contributions', {})
                except (json.JSONDecodeError, TypeError):
                    pass
            
            signal = SignalResponse(
                signal_id=row['signal_id'],
                symbol=row['symbol'],
                direction=row['signal_type'],  # signal_type is LONG or SHORT
                entry_price=row['entry_price'],
                current_price=row['current_price'],
                stop_loss=row['stop_loss'],
                take_profit=row['take_profit'],
                unrealized_pnl=row['unrealized_pnl'],
                mfe=row['mfe'],
                mae=row['mae'],
                quality=row['quality'],
                confidence=row['confidence'] / 100.0 if row['confidence'] > 1 else row['confidence'],  # Convert percentage to decimal
                status=row['status'],
                created_at=created_at,
                time_elapsed=time_elapsed,
                feature_contributions=feature_contributions
            )
            signals.append(signal)
        
        logger.info(f"Retrieved {len(signals)} active signals")
        return signals
    
    except Exception as e:
        logger.error(f"Failed to retrieve active signals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve active signals: {str(e)}")
