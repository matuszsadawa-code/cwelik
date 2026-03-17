"""
Position Management Service for OpenClaw Trading Dashboard

Tracks open positions with real-time P&L calculations and broadcasts
updates via WebSocket to all connected clients.

Features:
- Query open positions from database every 5 seconds
- Calculate current unrealized PnL and PnL percentage
- Calculate position duration
- Calculate total portfolio exposure and portfolio-level unrealized PnL
- Broadcast position_update messages via WebSocket
- Provide REST endpoint for manual position closure
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

from storage.database import Database
from api.services.websocket_manager import ConnectionManager
from api.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class PositionService:
    """
    Service for tracking open positions with real-time P&L calculations.
    
    Responsibilities:
    - Query open positions from executions table every 5 seconds
    - Fetch current market price for each position's symbol
    - Calculate unrealized PnL (absolute and percentage)
    - Calculate position duration (time since opened)
    - Calculate total portfolio exposure (sum of all position sizes)
    - Calculate portfolio-level unrealized PnL (sum of all position PnLs)
    - Broadcast position_update messages via WebSocket
    - Handle manual position closure requests
    """
    
    def __init__(self, connection_manager: ConnectionManager,
                 market_data_service: MarketDataService,
                 database: Database = None):
        """
        Initialize position service.
        
        Args:
            connection_manager: WebSocket connection manager for broadcasting
            market_data_service: Market data service for current prices
            database: Database instance (creates new if None)
        """
        self.connection_manager = connection_manager
        self.market_data_service = market_data_service
        self.database = database or Database()
        
        # Service state
        self.running = False
        self.task: Optional[asyncio.Task] = None
        
        logger.info("PositionService initialized")
    
    async def start(self):
        """Start the position tracking service background task."""
        if self.running:
            logger.warning("PositionService already running")
            return
        
        self.running = True
        
        # Start background task
        self.task = asyncio.create_task(self._position_tracking_loop())
        
        logger.info("PositionService started")
    
    async def stop(self):
        """Stop the position tracking service and cleanup."""
        if not self.running:
            return
        
        self.running = False
        
        # Cancel background task
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("PositionService stopped")
    
    async def _position_tracking_loop(self):
        """
        Background task: Track open positions every 5 seconds.
        
        Queries database for open positions, calculates P&L metrics,
        and broadcasts updates via WebSocket.
        """
        logger.info("Position tracking loop started (5s interval)")
        
        while self.running:
            try:
                await self._update_all_positions()
                await asyncio.sleep(5.0)  # 5 second interval
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in position tracking loop: {e}", exc_info=True)
                await asyncio.sleep(5.0)  # Continue on error
    
    async def _update_all_positions(self):
        """
        Query open positions and calculate metrics for each.
        
        Fetches all open positions from executions table, gets current prices,
        calculates P&L metrics, and broadcasts updates.
        """
        try:
            # Query open positions from database (status = 'OPEN' or 'FILLED')
            open_positions = self.database.get_executions(status="OPEN")
            
            if not open_positions:
                logger.debug("No open positions to track")
                # Broadcast empty portfolio update
                await self._broadcast_portfolio_update([], 0.0, 0.0)
                return
            
            logger.debug(f"Tracking {len(open_positions)} open positions")
            
            # Process each position
            position_updates = []
            total_exposure = 0.0
            total_unrealized_pnl = 0.0
            
            for position in open_positions:
                position_data = await self._process_position(position)
                if position_data:
                    position_updates.append(position_data)
                    total_exposure += position_data["size"]
                    total_unrealized_pnl += position_data["unrealizedPnL"]
            
            # Broadcast individual position updates
            for position_data in position_updates:
                await self._broadcast_position_update(position_data)
            
            # Broadcast portfolio-level update
            await self._broadcast_portfolio_update(
                position_updates,
                total_exposure,
                total_unrealized_pnl
            )
                
        except Exception as e:
            logger.error(f"Error updating positions: {e}", exc_info=True)
    
    async def _process_position(self, position: Dict) -> Optional[Dict]:
        """
        Process a single position: calculate metrics.
        
        Args:
            position: Position dictionary from database
            
        Returns:
            dict: Position data with calculated metrics or None if error
        """
        try:
            execution_id = position["execution_id"]
            symbol = position["symbol"]
            direction = position["direction"]  # LONG or SHORT
            entry_price = position["entry_price"]
            size = position["qty"]
            leverage = position.get("leverage", 1)
            sl_price = position.get("sl_price")
            tp_price = position.get("tp_price")
            
            # Get current market price
            current_price = await self._get_current_price(symbol)
            
            if current_price is None:
                logger.warning(f"No current price for {symbol}, skipping position {execution_id}")
                return None
            
            # Calculate unrealized PnL
            unrealized_pnl_pct = self._calculate_unrealized_pnl(
                direction=direction,
                entry_price=entry_price,
                current_price=current_price,
                leverage=leverage
            )
            
            # Calculate unrealized PnL in absolute terms (percentage of position size)
            unrealized_pnl_abs = unrealized_pnl_pct * size / 100
            
            # Calculate position duration
            duration = self._calculate_duration(position["created_at"])
            
            # Calculate risk-reward ratio
            rr_ratio = self._calculate_rr_ratio(
                direction=direction,
                entry_price=entry_price,
                sl_price=sl_price,
                tp_price=tp_price
            )
            
            # Build position data
            position_data = {
                "positionId": execution_id,
                "symbol": symbol,
                "side": direction,
                "size": size,
                "entryPrice": entry_price,
                "currentPrice": current_price,
                "unrealizedPnL": round(unrealized_pnl_abs, 4),
                "unrealizedPnLPercent": round(unrealized_pnl_pct, 4),
                "stopLoss": sl_price,
                "takeProfit": tp_price,
                "riskRewardRatio": round(rr_ratio, 2) if rr_ratio else None,
                "duration": duration,
                "openedAt": position["created_at"],
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
            
            logger.debug(
                f"Position {execution_id} updated: "
                f"PnL={unrealized_pnl_pct:.2f}%, Duration={duration}s"
            )
            
            return position_data
            
        except Exception as e:
            logger.error(f"Error processing position {position.get('execution_id', 'unknown')}: {e}", exc_info=True)
            return None
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current market price for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
            
        Returns:
            float: Current price or None if not available
        """
        # Get price from market data service cache
        market_data = self.market_data_service.get_market_data(symbol)
        
        if market_data and "price" in market_data:
            return float(market_data["price"])
        
        return None
    
    def _calculate_unrealized_pnl(self, direction: str, entry_price: float,
                                   current_price: float, leverage: int = 1) -> float:
        """
        Calculate unrealized PnL percentage with leverage.
        
        For LONG: PnL = (current_price - entry_price) / entry_price * leverage * 100
        For SHORT: PnL = (entry_price - current_price) / entry_price * leverage * 100
        
        Args:
            direction: "LONG" or "SHORT"
            entry_price: Entry price
            current_price: Current market price
            leverage: Position leverage (default: 1)
            
        Returns:
            float: Unrealized PnL as percentage
        """
        if direction == "LONG":
            pnl = (current_price - entry_price) / entry_price * leverage * 100
        elif direction == "SHORT":
            pnl = (entry_price - current_price) / entry_price * leverage * 100
        else:
            logger.warning(f"Unknown direction: {direction}")
            pnl = 0.0
        
        return pnl
    
    def _calculate_duration(self, created_at: str) -> int:
        """
        Calculate position duration in seconds.
        
        Args:
            created_at: ISO format timestamp string
            
        Returns:
            int: Duration in seconds
        """
        try:
            created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            duration = (now - created_time).total_seconds()
            return int(duration)
        except Exception as e:
            logger.error(f"Error calculating duration: {e}")
            return 0
    
    def _calculate_rr_ratio(self, direction: str, entry_price: float,
                            sl_price: Optional[float], tp_price: Optional[float]) -> Optional[float]:
        """
        Calculate risk-reward ratio.
        
        R:R = (TP - Entry) / (Entry - SL) for LONG
        R:R = (Entry - TP) / (SL - Entry) for SHORT
        
        Args:
            direction: "LONG" or "SHORT"
            entry_price: Entry price
            sl_price: Stop loss price
            tp_price: Take profit price
            
        Returns:
            float: Risk-reward ratio or None if cannot calculate
        """
        if not sl_price or not tp_price:
            return None
        
        try:
            if direction == "LONG":
                reward = tp_price - entry_price
                risk = entry_price - sl_price
            elif direction == "SHORT":
                reward = entry_price - tp_price
                risk = sl_price - entry_price
            else:
                return None
            
            if risk <= 0:
                return None
            
            return reward / risk
        except Exception as e:
            logger.error(f"Error calculating R:R ratio: {e}")
            return None
    
    async def _broadcast_position_update(self, position_data: Dict):
        """
        Broadcast individual position update to WebSocket clients.
        
        Args:
            position_data: Position data dictionary
        """
        message = {
            "type": "position_update",
            "data": position_data
        }
        
        # Broadcast to all clients subscribed to positions channel
        await self.connection_manager.broadcast(message, channel="positions")
    
    async def _broadcast_portfolio_update(self, positions: List[Dict],
                                          total_exposure: float,
                                          total_unrealized_pnl: float):
        """
        Broadcast portfolio-level update to WebSocket clients.
        
        Args:
            positions: List of position data dictionaries
            total_exposure: Total portfolio exposure (sum of position sizes)
            total_unrealized_pnl: Total portfolio unrealized PnL
        """
        message = {
            "type": "portfolio_update",
            "data": {
                "totalPositions": len(positions),
                "totalExposure": round(total_exposure, 4),
                "totalUnrealizedPnL": round(total_unrealized_pnl, 4),
                "positions": positions,
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
        }
        
        # Broadcast to all clients subscribed to positions channel
        await self.connection_manager.broadcast(message, channel="positions")
    
    async def close_position(self, position_id: str, reason: str = "MANUAL_CLOSE") -> Dict:
        """
        Close a position manually.
        
        Args:
            position_id: Position execution ID
            reason: Closure reason (default: MANUAL_CLOSE)
            
        Returns:
            dict: Result with success status and message
        """
        try:
            # Get position from database
            positions = self.database.get_executions(status="OPEN")
            position = next((p for p in positions if p["execution_id"] == position_id), None)
            
            if not position:
                return {
                    "success": False,
                    "message": f"Position {position_id} not found or already closed"
                }
            
            # Get current price for exit
            symbol = position["symbol"]
            current_price = await self._get_current_price(symbol)
            
            if current_price is None:
                return {
                    "success": False,
                    "message": f"Cannot get current price for {symbol}"
                }
            
            # Calculate final PnL
            direction = position["direction"]
            entry_price = position["entry_price"]
            leverage = position.get("leverage", 1)
            
            final_pnl = self._calculate_unrealized_pnl(
                direction=direction,
                entry_price=entry_price,
                current_price=current_price,
                leverage=leverage
            )
            
            # Calculate duration
            duration = self._calculate_duration(position["created_at"])
            
            # Update position in database
            now = datetime.now(timezone.utc).isoformat()
            updated_position = {
                "execution_id": position_id,
                "signal_id": position.get("signal_id"),
                "symbol": symbol,
                "direction": direction,
                "mode": position.get("mode", "paper"),
                "leverage": leverage,
                "qty": position["qty"],
                "entry_price": entry_price,
                "fill_price": position.get("fill_price"),
                "sl_price": position.get("sl_price"),
                "tp_price": position.get("tp_price"),
                "status": "CLOSED",
                "exit_price": current_price,
                "exit_reason": reason,
                "realised_pnl": final_pnl,
                "mfe": position.get("mfe", 0),
                "mae": position.get("mae", 0),
                "tp_hit": 0,
                "sl_hit": 0,
                "duration_minutes": duration / 60,
                "orders": position.get("orders_json"),
                "created_at": position["created_at"],
                "closed_at": now,
            }
            
            self.database.save_execution(updated_position)
            
            # Broadcast position closure
            closure_message = {
                "type": "position_closed",
                "data": {
                    "positionId": position_id,
                    "symbol": symbol,
                    "exitPrice": current_price,
                    "exitReason": reason,
                    "finalPnL": round(final_pnl, 4),
                    "duration": duration,
                    "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                }
            }
            await self.connection_manager.broadcast(closure_message, channel="positions")
            
            logger.info(
                f"Position {position_id} closed manually: "
                f"{symbol} @ ${current_price:.2f}, PnL={final_pnl:.2f}%"
            )
            
            return {
                "success": True,
                "message": f"Position {position_id} closed successfully",
                "data": {
                    "position_id": position_id,
                    "symbol": symbol,
                    "exit_price": current_price,
                    "final_pnl": round(final_pnl, 4),
                }
            }
            
        except Exception as e:
            logger.error(f"Error closing position {position_id}: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Error closing position: {str(e)}"
            }
    
    def get_service_status(self) -> Dict:
        """
        Get service status for health monitoring.
        
        Returns:
            dict: Service status including running state
        """
        return {
            "running": self.running,
        }
