"""
Multi-exchange candle aggregator.

Fetches candles from ByBit and Binance, validates cross-exchange,
and provides unified access for strategy engine.
"""

from typing import List, Dict, Optional
from datetime import datetime

from data.bybit_client import BybitClient
from data.binance_client import BinanceClient
from storage.database import Database
from config import SYMBOLS, TIMEFRAMES
from utils.logger import get_logger
from utils.cache import TTLCache

log = get_logger("data.candles")


class CandleManager:
    """Manages multi-timeframe candle data from both exchanges."""

    def __init__(self, bybit: BybitClient, binance: BinanceClient, db: Database):
        self.bybit = bybit
        self.binance = binance
        self.db = db
        # TTL cache: 60s default, reduces API calls significantly
        self._cache = TTLCache(default_ttl=60.0)
        log.info("CandleManager initialized with TTL cache")

    def get_candles(self, symbol: str, timeframe: str,
                    limit: int = 100, exchange: str = "cross") -> List[Dict]:
        """
        Get candles for symbol/timeframe with cross-exchange validation and caching.

        Args:
            symbol: e.g., 'BTCUSDT'
            timeframe: '5', '30', '240' (minutes)
            limit: number of candles
            exchange: 'bybit', 'binance', or 'cross' (default, uses primary + validates)

        Returns:
            List of candle dicts sorted oldest-first.
        """
        cache_key = f"{symbol}_{timeframe}_{exchange}_{limit}"
        
        # Try cache first (with 60s TTL)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Fetch from exchange
        if exchange == "bybit":
            candles = self._fetch_bybit(symbol, timeframe, limit)
        elif exchange == "binance":
            candles = self._fetch_binance(symbol, timeframe, limit)
        else:
            candles = self._fetch_cross_exchange(symbol, timeframe, limit)

        if candles:
            # Cache with 60s TTL (good balance between freshness and API reduction)
            self._cache.set(cache_key, candles, ttl=60.0)
            
            # Also cache to DB in background (for persistence)
            try:
                self.db.cache_candles(symbol, timeframe, exchange, candles)
            except Exception:
                pass

        return candles

    def get_current_price(self, symbol: str) -> float:
        """Get current price from most recent candle or ticker."""
        try:
            ticker = self.bybit.get_ticker(symbol)
            if ticker and ticker.get("last_price"):
                return ticker["last_price"]
        except Exception:
            pass

        try:
            ticker = self.binance.get_ticker(symbol)
            if ticker and ticker.get("last_price"):
                return ticker["last_price"]
        except Exception:
            pass

        return 0.0

    def _fetch_bybit(self, symbol: str, timeframe: str, limit: int) -> List[Dict]:
        """Fetch candles from ByBit."""
        try:
            candles = self.bybit.get_candles(symbol, timeframe, limit)
            if candles:
                log.debug(f"Fetched {len(candles)} candles from ByBit ({symbol}/{timeframe})")
            return candles
        except Exception as e:
            log.error(f"ByBit candle fetch error: {e}")
            return []

    def _fetch_binance(self, symbol: str, timeframe: str, limit: int) -> List[Dict]:
        """Fetch candles from Binance."""
        try:
            candles = self.binance.get_candles(symbol, timeframe, limit)
            if candles:
                log.debug(f"Fetched {len(candles)} candles from Binance ({symbol}/{timeframe})")
            return candles
        except Exception as e:
            log.error(f"Binance candle fetch error: {e}")
            return []

    def _fetch_cross_exchange(self, symbol: str, timeframe: str,
                               limit: int) -> List[Dict]:
        """
        Fetch from both exchanges, validate, and merge.

        Uses ByBit as primary, Binance for validation.
        Cross-exchange divergence > 0.5% triggers a warning.
        """
        bybit_candles = self._fetch_bybit(symbol, timeframe, limit)
        binance_candles = self._fetch_binance(symbol, timeframe, limit)

        # Use whichever is available
        if not bybit_candles and not binance_candles:
            log.warning(f"No candles from either exchange for {symbol}/{timeframe}")
            return []

        if not bybit_candles:
            return binance_candles
        if not binance_candles:
            return bybit_candles

        # Cross-validate: compare latest close prices
        bb_close = bybit_candles[-1]["close"]
        bn_close = binance_candles[-1]["close"]
        divergence_pct = abs(bb_close - bn_close) / bb_close * 100

        if divergence_pct > 0.5:
            log.warning(
                f"Cross-exchange divergence {divergence_pct:.3f}% for {symbol}: "
                f"ByBit={bb_close}, Binance={bn_close}"
            )

        # Merge: Use ByBit as primary, add Binance volume data
        merged = []
        bn_by_time = {c["open_time"]: c for c in binance_candles}

        for bb_candle in bybit_candles:
            candle = dict(bb_candle)
            bn_candle = bn_by_time.get(bb_candle["open_time"])

            if bn_candle:
                # Add cross-exchange data
                candle["binance_volume"] = bn_candle["volume"]
                candle["binance_close"] = bn_candle["close"]
                candle["taker_buy_volume"] = bn_candle.get("taker_buy_volume", 0)
                candle["taker_sell_volume"] = bn_candle.get("taker_sell_volume", 0)
                candle["total_volume"] = bb_candle["volume"] + bn_candle["volume"]
                candle["cross_validated"] = True
            else:
                candle["total_volume"] = bb_candle["volume"]
                candle["cross_validated"] = False

            candle["exchange"] = "cross"
            merged.append(candle)

        log.debug(
            f"Cross-exchange merge: {len(merged)} candles for {symbol}/{timeframe} "
            f"(divergence: {divergence_pct:.3f}%)"
        )
        return merged

    def refresh_all(self, symbols: List[str] = None):
        """Refresh candle data for all symbols and timeframes."""
        symbols = symbols or SYMBOLS
        for symbol in symbols:
            for tf_name, tf_value in TIMEFRAMES.items():
                try:
                    self.get_candles(symbol, tf_value, limit=100)
                except Exception as e:
                    log.error(f"Refresh error {symbol}/{tf_value}: {e}")
        log.info(f"Refreshed candle data for {len(symbols)} symbols")
