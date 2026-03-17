"""
Signal Tracking Service for OpenClaw Trading Dashboard

Tracks active signals with real-time MFE/MAE calculations and broadcasts
updates via WebSocket to all connected clients.

Features:
- Query active signals from database every 5 seconds
- Calculate current MFE (Maximum Favorable Excursion) and MAE (Maximum Adverse Excursion)
- Calculate time elapsed since signal creation
- Calculate current unrealized PnL for each signal
- Broadcast signal_update messages via WebSocket
- Track MFE/MAE history per signal in memory
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from collections import defaultdict

from storage.database import Database
from api.services.websocket_manager import ConnectionManager
from api.services.market_data_service import MarketDataService
from config import SYMBOLS

logger = logging.getLogger(__name__)


class SignalTrackingService:
    """
    Service for tracking active signals with MFE/MAE calculations.
    
    Responsibilities:
    - Query active signals from database every 5 seconds
    - Fetch current market price for each signal's symbol
    - Calculate MFE (Maximum Favorable Excursion): Best unrealized profit since signal creation (MFE >= 0)
    - Calculate MAE (Maximum Adverse Excursion): Worst unrealized loss since signal creation (MAE <= 0)
    - Calculate time elapsed since signal creation (in seconds/minutes)
    - Calculate current unrealized PnL based on entry price vs current price
    - Broadcast signal_update messages via WebSocket to all connected clients
    """
    
    def __init__(self, connection_manager: ConnectionManager, 
                 market_data_service: MarketDataService,
                 database: Database = None):
        """
        Initialize signal tracking service.
        
        Args:
            connection_manager: WebSocket connection manager for broadcasting
            market_data_service: Market data service for current prices
            database: Database instance (creates new if None)
        """
        self.connection_manager = connection_manager
        self.market_data_service = market_data_service
        self.database = database or Database()
        
        # MFE/MAE tracking per signal (in-memory cache)
        # Format: {signal_id: {"mfe": float, "mae": float}}
        self.mfe_mae_history: Dict[str, Dict[str, float]] = defaultdict(lambda: {"mfe": 0.0, "mae": 0.0})
        
        # Service state
        self.running = False
        self.task: Optional[asyncio.Task] = None
        
        logger.info("SignalTrackingService initialized")
    
    async def start(self):
        """Start the signal tracking service background task."""
        if self.running:
            logger.warning("SignalTrackingService already running")
            return
        
        self.running = True
        
        # Start background task
        self.task = asyncio.create_task(self._signal_tracking_loop())
        
        logger.info("SignalTrackingService started")
    
    async def stop(self):
        """Stop the signal tracking service and cleanup."""
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
        
        logger.info("SignalTrackingService stopped")
    
    async def _signal_tracking_loop(self):
        """
        Background task: Track active signals every 5 seconds.
        
        Queries database for active signals, calculates MFE/MAE/PnL,
        and broadcasts updates via WebSocket.
        """
        logger.info("Signal tracking loop started (5s interval)")
        
        while self.running:
            try:
                await self._update_all_signals()
                await asyncio.sleep(5.0)  # 5 second interval
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in signal tracking loop: {e}", exc_info=True)
                await asyncio.sleep(5.0)  # Continue on error
    
    async def _update_all_signals(self):
        """
        Query active signals and calculate metrics for each.
        
        Fetches all open signals from database, gets current prices,
        calculates MFE/MAE/PnL, and broadcasts updates.
        """
        try:
            # Query active signals from database (signals without outcomes)
            active_signals = self.database.get_open_signals()
            
            if not active_signals:
                logger.debug("No active signals to track")
                return
            
            logger.debug(f"Tracking {len(active_signals)} active signals")
            
            # Process each signal
            for signal in active_signals:
                await self._process_signal(signal)
                
        except Exception as e:
            logger.error(f"Error updating signals: {e}", exc_info=True)
    
    async def _process_signal(self, signal: Dict):
        """
        Process a single signal: calculate metrics and broadcast update.
        
        Args:
            signal: Signal dictionary from database
        """
        try:
            signal_id = signal["signal_id"]
            symbol = signal["symbol"]
            signal_type = signal["signal_type"]  # LONG or SHORT
            entry_price = signal["entry_price"]
            
            # Get current market price
            current_price = await self._get_current_price(symbol)
            
            if current_price is None:
                logger.warning(f"No current price available for {symbol}, skipping signal {signal_id}")
                return
            
            # Calculate unrealized PnL
            unrealized_pnl = self._calculate_unrealized_pnl(
                signal_type=signal_type,
                entry_price=entry_price,
                current_price=current_price
            )
            
            # Update MFE/MAE
            mfe, mae = self._update_mfe_mae(signal_id, unrealized_pnl)
            
            # Calculate time elapsed since signal creation
            time_elapsed = self._calculate_time_elapsed(signal["created_at"])
            
            # Build signal update message
            signal_data = {
                "signalId": signal_id,
                "symbol": symbol,
                "direction": signal_type,
                "entryPrice": entry_price,
                "currentPrice": current_price,
                "unrealizedPnL": round(unrealized_pnl, 4),
                "mfe": round(mfe, 4),
                "mae": round(mae, 4),
                "quality": signal["quality"],
                "confidence": signal["confidence"],
                "status": "ACTIVE",
                "timeElapsed": time_elapsed,
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
            
            # Broadcast to WebSocket clients
            await self._broadcast_signal_update(signal_data)
            
            logger.debug(f"Signal {signal_id} updated: PnL={unrealized_pnl:.2%}, MFE={mfe:.2%}, MAE={mae:.2%}")
            
        except Exception as e:
            logger.error(f"Error processing signal {signal.get('signal_id', 'unknown')}: {e}", exc_info=True)
    
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
    
    def _calculate_unrealized_pnl(self, signal_type: str, entry_price: float, current_price: float) -> float:
        """
        Calculate unrealized PnL percentage.
        
        For LONG: PnL = (current_price - entry_price) / entry_price
        For SHORT: PnL = (entry_price - current_price) / entry_price
        
        Args:
            signal_type: "LONG" or "SHORT"
            entry_price: Entry price
            current_price: Current market price
            
        Returns:
            float: Unrealized PnL as decimal (e.g., 0.05 = 5%)
        """
        if signal_type == "LONG":
            pnl = (current_price - entry_price) / entry_price
        elif signal_type == "SHORT":
            pnl = (entry_price - current_price) / entry_price
        else:
            logger.warning(f"Unknown signal type: {signal_type}")
            pnl = 0.0
        
        return pnl
    
    def _update_mfe_mae(self, signal_id: str, current_pnl: float) -> tuple[float, float]:
        """
        Update MFE and MAE for a signal.
        
        MFE (Maximum Favorable Excursion): Best unrealized profit (MFE >= 0)
        MAE (Maximum Adverse Excursion): Worst unrealized loss (MAE <= 0)
        
        Args:
            signal_id: Signal ID
            current_pnl: Current unrealized PnL
            
        Returns:
            tuple: (mfe, mae)
        """
        # Get current MFE/MAE from history
        history = self.mfe_mae_history[signal_id]
        current_mfe = history["mfe"]
        current_mae = history["mae"]
        
        # Update MFE: track maximum profit (always >= 0)
        if current_pnl > current_mfe:
            history["mfe"] = current_pnl
            current_mfe = current_pnl
        
        # Update MAE: track maximum loss (always <= 0)
        if current_pnl < current_mae:
            history["mae"] = current_pnl
            current_mae = current_pnl
        
        return current_mfe, current_mae
    
    def _calculate_time_elapsed(self, created_at: str) -> int:
        """
        Calculate time elapsed since signal creation in seconds.
        
        Args:
            created_at: ISO format timestamp string
            
        Returns:
            int: Time elapsed in seconds
        """
        try:
            created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            elapsed = (now - created_time).total_seconds()
            return int(elapsed)
        except Exception as e:
            logger.error(f"Error calculating time elapsed: {e}")
            return 0
    
    async def _broadcast_signal_update(self, signal_data: Dict):
        """
        Broadcast signal update to all WebSocket clients.
        
        Args:
            signal_data: Signal data dictionary
        """
        message = {
            "type": "signal_update",
            "data": signal_data
        }
        
        # Broadcast to all clients subscribed to signals channel
        await self.connection_manager.broadcast(message, channel="signals")
    
    def get_signal_metrics(self, signal_id: str) -> Optional[Dict]:
        """
        Get cached MFE/MAE metrics for a signal.
        
        Args:
            signal_id: Signal ID
            
        Returns:
            dict: MFE/MAE metrics or None if not tracked
        """
        if signal_id in self.mfe_mae_history:
            return self.mfe_mae_history[signal_id].copy()
        return None
    
    def reset_signal_metrics(self, signal_id: str):
        """
        Reset MFE/MAE metrics for a signal.
        
        Args:
            signal_id: Signal ID
        """
        if signal_id in self.mfe_mae_history:
            del self.mfe_mae_history[signal_id]
            logger.info(f"Reset metrics for signal {signal_id}")
    
    def get_service_status(self) -> Dict:
        """
        Get service status for health monitoring.
        
        Returns:
            dict: Service status including running state and tracked signal count
        """
        return {
            "running": self.running,
            "signals_tracked": len(self.mfe_mae_history),
        }
