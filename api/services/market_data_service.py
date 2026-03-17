"""
Market Data Service for OpenClaw Trading Dashboard

Fetches real-time market data from exchanges (Binance and Bybit) and broadcasts
updates via WebSocket to all connected clients.

Features:
- Periodic market data updates (1-5 seconds depending on data type)
- CVD (Cumulative Volume Delta) calculation from trade flow
- Multi-exchange support (Binance and Bybit)
- Error handling and retry logic for exchange API failures
- Efficient async parallel fetching for multiple symbols
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone
from collections import defaultdict

from data.bybit_client_async import AsyncBybitClient
from data.binance_client_async import AsyncBinanceClient
from api.services.websocket_manager import ConnectionManager
from config import SYMBOLS

logger = logging.getLogger(__name__)


class MarketDataService:
    """
    Service for fetching and broadcasting real-time market data.
    
    Responsibilities:
    - Fetch ticker data (price, volume, 24h change) every 1 second
    - Fetch trade flow data for CVD calculation every 2 seconds
    - Calculate CVD (Cumulative Volume Delta) from trade flow
    - Broadcast market_data_update messages to WebSocket clients
    - Handle exchange API failures with retry logic
    """
    
    def __init__(self, connection_manager: ConnectionManager, symbols: List[str] = None):
        """
        Initialize market data service.
        
        Args:
            connection_manager: WebSocket connection manager for broadcasting
            symbols: List of symbols to monitor (defaults to config.SYMBOLS)
        """
        self.connection_manager = connection_manager
        self.symbols = symbols or SYMBOLS
        
        # Exchange clients
        self.bybit_client = AsyncBybitClient(use_demo=False)
        self.binance_client = AsyncBinanceClient()
        
        # Market data cache
        self.market_data: Dict[str, Dict] = {}
        
        # CVD tracking per symbol
        self.cvd: Dict[str, float] = defaultdict(float)
        self.last_trade_id: Dict[str, str] = {}
        
        # Service state
        self.running = False
        self.tasks: List[asyncio.Task] = []
        
        # Error tracking for circuit breaker pattern
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.max_errors_before_skip = 5
        
        logger.info(f"MarketDataService initialized with {len(self.symbols)} symbols")
    
    async def start(self):
        """Start the market data service background tasks."""
        if self.running:
            logger.warning("MarketDataService already running")
            return
        
        self.running = True
        
        # Initialize Binance valid symbols cache to prevent IP bans
        await self.binance_client.update_valid_symbols()
        
        # Start background tasks
        self.tasks = [
            asyncio.create_task(self._ticker_update_loop()),
            asyncio.create_task(self._trade_flow_update_loop()),
            asyncio.create_task(self._error_reset_loop()),
        ]
        
        logger.info("MarketDataService started")
    
    async def stop(self):
        """Stop the market data service and cleanup."""
        if not self.running:
            return
        
        self.running = False
        
        # Cancel all background tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Close exchange clients
        await self.bybit_client.close()
        await self.binance_client.close()
        
        logger.info("MarketDataService stopped")
    
    async def _ticker_update_loop(self):
        """
        Background task: Fetch ticker data every 1 second.
        
        Fetches price, volume, 24h change from both exchanges in parallel.
        """
        logger.info("Ticker update loop started (1s interval)")
        
        while self.running:
            try:
                await self._update_tickers()
                await asyncio.sleep(1.0)  # 1 second interval for price updates
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in ticker update loop: {e}")
                await asyncio.sleep(5.0)  # Back off on error
    
    async def _trade_flow_update_loop(self):
        """
        Background task: Fetch trade flow data every 2 seconds.
        
        Fetches recent trades and calculates CVD (Cumulative Volume Delta).
        """
        logger.info("Trade flow update loop started (2s interval)")
        
        while self.running:
            try:
                await self._update_trade_flow()
                await asyncio.sleep(2.0)  # 2 second interval for trade flow
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in trade flow update loop: {e}")
                await asyncio.sleep(5.0)  # Back off on error
    
    async def _error_reset_loop(self):
        """
        Background task: Reset error counts every 5 minutes.
        
        Implements circuit breaker recovery - allows retrying failed symbols.
        """
        while self.running:
            try:
                await asyncio.sleep(300.0)  # 5 minutes
                self.error_counts.clear()
                logger.debug("Error counts reset")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in error reset loop: {e}")
    
    async def _update_tickers(self):
        """
        Fetch ticker data for all symbols from both exchanges in parallel.
        
        Combines data from Binance and Bybit, preferring Bybit as primary source.
        """
        # Filter out symbols with too many errors (circuit breaker)
        active_symbols = [
            s for s in self.symbols 
            if self.error_counts.get(s, 0) < self.max_errors_before_skip
        ]
        
        if not active_symbols:
            logger.warning("All symbols have exceeded error threshold")
            return
        
        # Fetch from both exchanges in parallel
        bybit_tasks = [self._fetch_bybit_ticker(symbol) for symbol in active_symbols]
        binance_tasks = [self._fetch_binance_ticker(symbol) for symbol in active_symbols]
        
        bybit_results = await asyncio.gather(*bybit_tasks, return_exceptions=True)
        binance_results = await asyncio.gather(*binance_tasks, return_exceptions=True)
        
        # Process results and broadcast updates
        for i, symbol in enumerate(active_symbols):
            bybit_data = bybit_results[i] if not isinstance(bybit_results[i], Exception) else None
            binance_data = binance_results[i] if not isinstance(binance_results[i], Exception) else None
            
            # Prefer Bybit data, fallback to Binance
            ticker_data = bybit_data or binance_data
            
            if ticker_data:
                # Update cache
                self.market_data[symbol] = ticker_data
                
                # Broadcast to WebSocket clients
                await self._broadcast_market_data(symbol, ticker_data)
                
                # Reset error count on success
                if symbol in self.error_counts:
                    self.error_counts[symbol] = 0
            else:
                # Increment error count
                self.error_counts[symbol] += 1
                if self.error_counts[symbol] >= self.max_errors_before_skip:
                    logger.warning(f"Symbol {symbol} exceeded error threshold, temporarily skipping")
    
    async def _fetch_bybit_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Fetch ticker data from Bybit.
        
        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
            
        Returns:
            dict: Ticker data or None on error
        """
        try:
            ticker = await self.bybit_client.get_ticker(symbol)
            
            if not ticker or not ticker.get("last_price"):
                return None
            
            return {
                "symbol": symbol,
                "price": ticker["last_price"],
                "volume24h": ticker.get("volume_24h", 0),
                "change24h": ticker.get("price_change_pct", 0),
                "bid": ticker.get("bid", 0),
                "ask": ticker.get("ask", 0),
                "bidAskSpread": abs(ticker.get("ask", 0) - ticker.get("bid", 0)),
                "exchange": "bybit",
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
        except Exception as e:
            logger.debug(f"Bybit ticker fetch failed for {symbol}: {e}")
            return None
    
    async def _fetch_binance_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Fetch ticker data from Binance.
        
        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
            
        Returns:
            dict: Ticker data or None on error
        """
        try:
            ticker = await self.binance_client.get_ticker(symbol)
            
            if not ticker or not ticker.get("last_price"):
                return None
            
            return {
                "symbol": symbol,
                "price": ticker["last_price"],
                "volume24h": ticker.get("volume_24h", 0),
                "change24h": ticker.get("price_change_pct", 0),
                "bid": ticker.get("bid", 0),
                "ask": ticker.get("ask", 0),
                "bidAskSpread": abs(ticker.get("ask", 0) - ticker.get("bid", 0)),
                "exchange": "binance",
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
        except Exception as e:
            logger.debug(f"Binance ticker fetch failed for {symbol}: {e}")
            return None
    
    async def _update_trade_flow(self):
        """
        Fetch trade flow data for all symbols and calculate CVD.
        
        CVD (Cumulative Volume Delta) = Running sum of (buy volume - sell volume)
        Positive CVD = More buying pressure
        Negative CVD = More selling pressure
        """
        # Filter out symbols with too many errors
        active_symbols = [
            s for s in self.symbols 
            if self.error_counts.get(s, 0) < self.max_errors_before_skip
        ]
        
        if not active_symbols:
            return
        
        # Fetch trades from both exchanges in parallel
        bybit_tasks = [self._fetch_bybit_trades(symbol) for symbol in active_symbols]
        binance_tasks = [self._fetch_binance_trades(symbol) for symbol in active_symbols]
        
        bybit_results = await asyncio.gather(*bybit_tasks, return_exceptions=True)
        binance_results = await asyncio.gather(*binance_tasks, return_exceptions=True)
        
        # Process results and calculate CVD
        for i, symbol in enumerate(active_symbols):
            bybit_trades = bybit_results[i] if not isinstance(bybit_results[i], Exception) else []
            binance_trades = binance_results[i] if not isinstance(binance_results[i], Exception) else []
            
            # Combine trades from both exchanges
            all_trades = bybit_trades + binance_trades
            
            if all_trades:
                # Calculate CVD from trades
                cvd_delta = self._calculate_cvd_delta(symbol, all_trades)
                self.cvd[symbol] += cvd_delta
                
                # Update market data with CVD
                if symbol in self.market_data:
                    self.market_data[symbol]["cvd"] = round(self.cvd[symbol], 4)
                    
                    # Broadcast updated market data with CVD
                    await self._broadcast_market_data(symbol, self.market_data[symbol])
    
    async def _fetch_bybit_trades(self, symbol: str) -> List[Dict]:
        """Fetch recent trades from Bybit."""
        try:
            trades = await self.bybit_client.get_recent_trades(symbol, limit=100)
            return trades or []
        except Exception as e:
            logger.debug(f"Bybit trades fetch failed for {symbol}: {e}")
            return []
    
    async def _fetch_binance_trades(self, symbol: str) -> List[Dict]:
        """Fetch recent trades from Binance."""
        try:
            trades = await self.binance_client.get_recent_trades(symbol, limit=100)
            return trades or []
        except Exception as e:
            logger.debug(f"Binance trades fetch failed for {symbol}: {e}")
            return []
    
    def _calculate_cvd_delta(self, symbol: str, trades: List[Dict]) -> float:
        """
        Calculate CVD delta from new trades.
        
        CVD Delta = Sum of (buy volume - sell volume) for new trades only.
        
        Args:
            symbol: Trading pair symbol
            trades: List of trade dictionaries
            
        Returns:
            float: CVD delta to add to cumulative CVD
        """
        if not trades:
            return 0.0
        
        # Filter out trades we've already processed
        last_id = self.last_trade_id.get(symbol)
        new_trades = []
        
        for trade in trades:
            trade_id = trade.get("id", "")
            if last_id and trade_id <= last_id:
                continue
            new_trades.append(trade)
        
        if not new_trades:
            return 0.0
        
        # Update last trade ID
        self.last_trade_id[symbol] = new_trades[-1].get("id", "")
        
        # Calculate delta: buy volume - sell volume
        delta = 0.0
        for trade in new_trades:
            size = trade.get("size", 0)
            side = trade.get("side", "").upper()
            
            if side == "BUY":
                delta += size
            elif side == "SELL":
                delta -= size
        
        return delta
    
    async def _broadcast_market_data(self, symbol: str, data: Dict):
        """
        Broadcast market data update to all WebSocket clients.
        
        Args:
            symbol: Trading pair symbol
            data: Market data dictionary
        """
        message = {
            "type": "market_data_update",
            "data": {
                "symbol": data.get("symbol"),
                "price": data.get("price"),
                "volume24h": data.get("volume24h"),
                "change24h": data.get("change24h"),
                "bidAskSpread": data.get("bidAskSpread"),
                "cvd": data.get("cvd", 0),
                "timestamp": data.get("timestamp"),
            }
        }
        
        # Broadcast to all clients subscribed to market_data channel
        await self.connection_manager.broadcast(message, channel="market_data")
    
    def get_market_data(self, symbol: str) -> Optional[Dict]:
        """
        Get cached market data for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            dict: Market data or None if not available
        """
        return self.market_data.get(symbol)
    
    def get_all_market_data(self) -> Dict[str, Dict]:
        """
        Get all cached market data.
        
        Returns:
            dict: Dictionary mapping symbols to market data
        """
        return self.market_data.copy()
    
    def get_cvd(self, symbol: str) -> float:
        """
        Get current CVD for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            float: Current CVD value
        """
        return self.cvd.get(symbol, 0.0)
    
    def reset_cvd(self, symbol: str):
        """
        Reset CVD for a symbol to zero.
        
        Args:
            symbol: Trading pair symbol
        """
        self.cvd[symbol] = 0.0
        self.last_trade_id.pop(symbol, None)
        logger.info(f"CVD reset for {symbol}")
    
    def get_service_status(self) -> Dict:
        """
        Get service status for health monitoring.
        
        Returns:
            dict: Service status including running state, symbol count, error counts
        """
        return {
            "running": self.running,
            "symbols_monitored": len(self.symbols),
            "symbols_with_data": len(self.market_data),
            "symbols_with_errors": len([s for s in self.error_counts if self.error_counts[s] > 0]),
            "total_errors": sum(self.error_counts.values()),
            "cvd_tracked_symbols": len(self.cvd),
        }
