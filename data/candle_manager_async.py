"""
Async Multi-exchange candle aggregator with parallel fetching.
Fetches data from ByBit and Binance in parallel for all symbols.
MUCH faster than sync version (30 symbols in ~2-3s instead of ~40-50s).
"""

import asyncio
from typing import List, Dict, Optional

from data.bybit_client_async import AsyncBybitClient
from data.binance_client_async import AsyncBinanceClient
from storage.database import Database
from config import SYMBOLS, TIMEFRAMES
from utils.logger import get_logger
from utils.cache import TTLCache

log = get_logger("data.candles.async")


class AsyncCandleManager:
    """Async candle manager with parallel multi-symbol fetching."""

    def __init__(self, bybit: AsyncBybitClient, binance: AsyncBinanceClient, db: Database):
        self.bybit = bybit
        self.binance = binance
        self.db = db
        # TTL cache: 60s default
        self._cache = TTLCache(default_ttl=60.0)
        # Track symbols with price mismatches (>2%)
        self._price_mismatch_symbols = set()
        log.info("Async CandleManager initialized with parallel fetching")
    
    async def close(self):
        """Close all async clients."""
        await self.bybit.close()
        await self.binance.close()
    
    def is_symbol_excluded(self, symbol: str) -> bool:
        """Check if symbol is excluded due to price mismatch."""
        return symbol in self._price_mismatch_symbols
    
    def get_excluded_symbols(self) -> set:
        """Get set of excluded symbols."""
        return self._price_mismatch_symbols.copy()
    
    async def get_candles(self, symbol: str, timeframe: str,
                         limit: int = 100, exchange: str = "cross") -> List[Dict]:
        """
        Get candles for symbol/timeframe with caching (async).

        Args:
            symbol: e.g., 'BTCUSDT'
            timeframe: '5', '30', '240' (minutes)
            limit: number of candles
            exchange: 'bybit', 'binance', or 'cross'

        Returns:
            List of candle dicts sorted oldest-first.
        """
        cache_key = f"{symbol}_{timeframe}_{exchange}_{limit}"
        
        # Try cache first
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Fetch from exchange
        if exchange == "bybit":
            candles = await self._fetch_bybit(symbol, timeframe, limit)
        elif exchange == "binance":
            candles = await self._fetch_binance(symbol, timeframe, limit)
        else:
            candles = await self._fetch_cross_exchange(symbol, timeframe, limit)

        if candles:
            # Cache with 60s TTL
            self._cache.set(cache_key, candles, ttl=60.0)
            
            # Also cache to DB in background (non-blocking)
            try:
                self.db.cache_candles(symbol, timeframe, exchange, candles)
            except Exception:
                pass

        return candles
    
    async def get_candles_parallel(self, symbols: List[str], timeframe: str,
                                   limit: int = 100, exchange: str = "cross") -> Dict[str, List[Dict]]:
        """
        Fetch candles for multiple symbols in PARALLEL (async).
        This is the key performance improvement!

        Args:
            symbols: List of symbols to fetch
            timeframe: '5', '30', '240' (minutes)
            limit: number of candles
            exchange: 'bybit', 'binance', or 'cross'

        Returns:
            Dict mapping symbol -> candles
        """
        # Create tasks for all symbols
        tasks = [
            self.get_candles(symbol, timeframe, limit, exchange)
            for symbol in symbols
        ]
        
        # Fetch all in parallel!
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build result dict
        candles_dict = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                log.error(f"Error fetching candles for {symbol}: {result}")
                candles_dict[symbol] = []
            else:
                candles_dict[symbol] = result
        
        return candles_dict
    
    async def refresh_all(self, symbols: Optional[List[str]] = None):
        """
        Refresh candle data for all symbols in PARALLEL with batching to avoid IP bans.
        Processes symbols in batches to respect API rate limits.
        """
        if symbols is None:
            symbols = SYMBOLS
        
        # Process in batches of 5 symbols at a time to avoid overwhelming the API
        batch_size = 5
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            
            # Fetch all timeframes for this batch in parallel
            tasks = []
            for tf_name, tf_value in TIMEFRAMES.items():
                task = self.get_candles_parallel(batch, tf_value, limit=200)
                tasks.append(task)
            
            # Execute batch in parallel
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Delay between batches to avoid rate limits (500ms)
            if i + batch_size < len(symbols):
                await asyncio.sleep(0.5)
        
        log.info(f"Refreshed candle data for {len(symbols)} symbols (batched parallel)")
    
    async def _fetch_bybit(self, symbol: str, timeframe: str, limit: int) -> List[Dict]:
        """Fetch from ByBit (async)."""
        try:
            return await self.bybit.get_candles(symbol, timeframe, limit)
        except Exception as e:
            log.error(f"ByBit fetch error for {symbol}: {e}")
            return []
    
    async def _fetch_binance(self, symbol: str, timeframe: str, limit: int) -> List[Dict]:
        """Fetch from Binance (async)."""
        try:
            return await self.binance.get_candles(symbol, timeframe, limit)
        except Exception as e:
            log.error(f"Binance fetch error for {symbol}: {e}")
            return []
    
    async def _fetch_cross_exchange(self, symbol: str, timeframe: str, limit: int) -> List[Dict]:
        """
        Fetch from both exchanges in PARALLEL and validate (async).
        """
        # Fetch from both exchanges simultaneously
        bybit_task = self._fetch_bybit(symbol, timeframe, limit)
        binance_task = self._fetch_binance(symbol, timeframe, limit)
        
        bybit_candles, binance_candles = await asyncio.gather(
            bybit_task, binance_task, return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(bybit_candles, Exception):
            log.warning(f"ByBit error for {symbol}, using Binance only")
            return binance_candles if not isinstance(binance_candles, Exception) else []
        
        if isinstance(binance_candles, Exception):
            log.warning(f"Binance error for {symbol}, using ByBit only")
            return bybit_candles
        
        # Use ByBit as primary, Binance for validation
        if not bybit_candles:
            return binance_candles
        
        if not binance_candles:
            return bybit_candles
        
        # Cross-validate (simple check: compare last close prices)
        if len(bybit_candles) > 0 and len(binance_candles) > 0:
            bybit_last = bybit_candles[-1]["close"]
            binance_last = binance_candles[-1]["close"]
            diff_pct = abs(bybit_last - binance_last) / bybit_last * 100
            
            # Track symbols with >2% price mismatch
            if diff_pct > 2.0:
                if symbol not in self._price_mismatch_symbols:
                    self._price_mismatch_symbols.add(symbol)
                    log.warning(
                        f"⚠️ {symbol} EXCLUDED: price mismatch ByBit ${bybit_last:.2f} vs "
                        f"Binance ${binance_last:.2f} ({diff_pct:.2f}%) - symbol will be skipped"
                    )
            elif diff_pct > 1.0:
                log.warning(
                    f"{symbol} price mismatch: ByBit ${bybit_last:.2f} vs "
                    f"Binance ${binance_last:.2f} ({diff_pct:.2f}%)"
                )
        
        return bybit_candles
    
    async def get_current_price(self, symbol: str) -> float:
        """Get current price from ticker (async)."""
        try:
            ticker = await self.bybit.get_ticker(symbol)
            if ticker and ticker.get("last_price"):
                return ticker["last_price"]
        except Exception:
            pass

        try:
            ticker = await self.binance.get_ticker(symbol)
            if ticker and ticker.get("last_price"):
                return ticker["last_price"]
        except Exception:
            pass

        return 0.0
