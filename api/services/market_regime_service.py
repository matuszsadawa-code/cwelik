"""
Market Regime Service for OpenClaw Trading Dashboard

Calculates market regime (TRENDING, RANGING, VOLATILE, QUIET) every 60 seconds
and broadcasts updates via WebSocket to all connected clients.

Features:
- Market regime classification using ADX and volatility analysis
- Regime confidence score calculation (0-100%)
- Volatility percentile relative to historical volatility
- Trend strength indicator (ADX)
- Periodic regime updates every 60 seconds
- Multi-symbol support with parallel processing
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from collections import defaultdict, deque

from data.candle_manager_async import AsyncCandleManager
from api.services.websocket_manager import ConnectionManager
from strategy.market_regime import MarketRegimeDetector
from config import SYMBOLS

logger = logging.getLogger(__name__)


class MarketRegimeService:
    """
    Service for calculating and broadcasting market regime updates.
    
    Responsibilities:
    - Calculate market regime every 60 seconds
    - Classify regime as TRENDING, RANGING, VOLATILE, or QUIET
    - Calculate regime confidence score (0-100%)
    - Calculate volatility percentile relative to historical data
    - Calculate trend strength using ADX
    - Broadcast regime_update messages via WebSocket
    """
    
    def __init__(self, connection_manager: ConnectionManager, 
                 candle_manager: AsyncCandleManager,
                 symbols: List[str] = None):
        """
        Initialize market regime service.
        
        Args:
            connection_manager: WebSocket connection manager for broadcasting
            candle_manager: Async candle manager for fetching historical data
            symbols: List of symbols to monitor (defaults to config.SYMBOLS)
        """
        self.connection_manager = connection_manager
        self.candle_manager = candle_manager
        self.symbols = symbols or SYMBOLS
        
        # Market regime detector
        self.regime_detector = MarketRegimeDetector()
        
        # Regime cache per symbol
        self.regimes: Dict[str, Dict] = {}
        
        # Volatility history for percentile calculation (last 100 periods)
        self.volatility_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Service state
        self.running = False
        self.task: Optional[asyncio.Task] = None
        
        logger.info(f"MarketRegimeService initialized with {len(self.symbols)} symbols")
    
    async def start(self):
        """Start the market regime service background task."""
        if self.running:
            logger.warning("MarketRegimeService already running")
            return
        
        self.running = True
        
        # Start background task
        self.task = asyncio.create_task(self._regime_update_loop())
        
        logger.info("MarketRegimeService started")
    
    async def stop(self):
        """Stop the market regime service and cleanup."""
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
        
        logger.info("MarketRegimeService stopped")
    
    async def _regime_update_loop(self):
        """
        Background task: Calculate market regime every 60 seconds.
        
        Fetches candle data, calculates regime, and broadcasts updates.
        """
        logger.info("Market regime update loop started (60s interval)")
        
        while self.running:
            try:
                await self._update_all_regimes()
                await asyncio.sleep(60.0)  # 60 second interval
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in regime update loop: {e}", exc_info=True)
                await asyncio.sleep(60.0)  # Continue on error
    
    async def _update_all_regimes(self):
        """
        Calculate market regime for all symbols in parallel.
        
        Fetches candle data, runs regime detection, calculates metrics,
        and broadcasts updates via WebSocket.
        """
        # Fetch candles for all symbols in parallel
        tasks = [self._update_regime_for_symbol(symbol) for symbol in self.symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error updating regime for {self.symbols[i]}: {result}")
    
    async def _update_regime_for_symbol(self, symbol: str):
        """
        Calculate and broadcast market regime for a single symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
        """
        try:
            # Fetch candle data (1h timeframe, 100 periods for analysis)
            candles = await self.candle_manager.get_candles(
                symbol=symbol,
                timeframe="1h",
                limit=100
            )
            
            if not candles or len(candles) < 20:
                logger.warning(f"Insufficient candle data for {symbol}")
                return
            
            # Detect market regime using existing detector
            regime_info = self.regime_detector.detect_regime(
                symbol=symbol,
                candles=candles,
                lookback=20
            )
            
            # Calculate additional metrics
            volatility_percentile = self._calculate_volatility_percentile(
                symbol=symbol,
                current_atr_ratio=regime_info.get("atr_ratio", 1.0)
            )
            
            trend_strength = regime_info.get("adx", 0)
            
            # Build regime update message
            regime_data = {
                "symbol": symbol,
                "regime": regime_info.get("regime", "QUIET"),
                "confidence": regime_info.get("confidence", 0),
                "volatilityPercentile": round(volatility_percentile, 2),
                "trendStrength": round(trend_strength, 2),
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
            
            # Cache regime data
            self.regimes[symbol] = regime_data
            
            # Broadcast to WebSocket clients
            await self._broadcast_regime_update(regime_data)
            
            logger.debug(f"Regime updated for {symbol}: {regime_data['regime']} "
                        f"(confidence: {regime_data['confidence']}%, "
                        f"ADX: {trend_strength:.1f})")
            
        except Exception as e:
            logger.error(f"Error updating regime for {symbol}: {e}", exc_info=True)
    
    def _calculate_volatility_percentile(self, symbol: str, current_atr_ratio: float) -> float:
        """
        Calculate volatility percentile relative to historical volatility.
        
        Percentile indicates where current volatility ranks compared to
        recent history (0-100%, where 100% = highest volatility).
        
        Args:
            symbol: Trading pair symbol
            current_atr_ratio: Current ATR ratio from regime detection
            
        Returns:
            float: Volatility percentile (0-100)
        """
        # Add current volatility to history
        self.volatility_history[symbol].append(current_atr_ratio)
        
        # Need at least 10 data points for meaningful percentile
        if len(self.volatility_history[symbol]) < 10:
            return 50.0  # Default to median
        
        # Calculate percentile: how many historical values are below current?
        history = list(self.volatility_history[symbol])
        below_count = sum(1 for v in history if v < current_atr_ratio)
        percentile = (below_count / len(history)) * 100
        
        return percentile
    
    async def _broadcast_regime_update(self, regime_data: Dict):
        """
        Broadcast regime update to all WebSocket clients.
        
        Args:
            regime_data: Regime data dictionary
        """
        message = {
            "type": "regime_update",
            "data": regime_data
        }
        
        # Broadcast to all clients subscribed to regime channel
        await self.connection_manager.broadcast(message, channel="regime")
    
    def get_regime(self, symbol: str) -> Optional[Dict]:
        """
        Get cached regime data for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            dict: Regime data or None if not available
        """
        return self.regimes.get(symbol)
    
    def get_all_regimes(self) -> Dict[str, Dict]:
        """
        Get all cached regime data.
        
        Returns:
            dict: Dictionary mapping symbols to regime data
        """
        return self.regimes.copy()
    
    def get_service_status(self) -> Dict:
        """
        Get service status for health monitoring.
        
        Returns:
            dict: Service status including running state and symbol count
        """
        return {
            "running": self.running,
            "symbols_monitored": len(self.symbols),
            "symbols_with_regime": len(self.regimes),
        }
