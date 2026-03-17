"""
Async Binance Futures API client — aiohttp for parallel requests.
"""

import asyncio
from typing import List, Dict, Optional, Any

import aiohttp

from config import BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_INTERVALS
from utils.logger import get_logger
from utils.async_rate_limiter import AsyncRateLimiter
from utils.async_error_handler import async_retry_with_backoff, AsyncRetryConfig
import hmac
import hashlib
import time
from urllib.parse import urlencode

log = get_logger("data.binance.async")

BINANCE_FUTURES_REST = "https://fapi.binance.com"


class AsyncBinanceClient:
    """Async Binance Futures REST API client for parallel data fetching."""

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiter: 5 req/sec sustained, 10 burst (conservative to avoid IP bans)
        self.rate_limiter = AsyncRateLimiter(requests_per_second=5, burst=10)
        
        # Retry configuration
        self.retry_config = AsyncRetryConfig(
            max_retries=3,
            initial_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0
        )
        
        # Cache for valid symbols to avoid 400 Bad Request spam
        self.valid_symbols: set = set()
        
        log.info("Async Binance client initialized")
    
    async def update_valid_symbols(self):
        """Fetch and cache all valid futures symbols to prevent IP bans from invalid requests."""
        if self.valid_symbols:
            return  # Already cached
            
        try:
            # We don't use _request here to avoid recursive dependencies or rate limits, 
            # and because we only do this once at startup
            session = await self._get_session()
            async with session.get(f"{BINANCE_FUTURES_REST}/fapi/v1/exchangeInfo") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.valid_symbols = {s["symbol"] for s in data.get("symbols", []) if s["status"] == "TRADING"}
                    log.info(f"Binance valid symbols cached: {len(self.valid_symbols)} pairs")
        except Exception as e:
            log.error(f"Failed to update Binance valid symbols: {e}")
            # Set empty set to avoid repeated failures
            self.valid_symbols = set()
            
    async def is_valid_symbol(self, symbol: str) -> bool:
        """Check if symbol is valid without triggering update."""
        symbol = symbol.replace("-", "")  # normalize before cache lookup
        # If cache is empty, fail open (assume valid)
        if not self.valid_symbols:
            return True
        return symbol in self.valid_symbols
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session (lazy initialization)."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Content-Type": "application/json",
                    "X-MBX-APIKEY": BINANCE_API_KEY,
                },
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session
    
    async def close(self):
        """Close aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, auth: bool = False) -> Any:
        """Make async request with rate limiting and retry."""
        # Acquire rate limit token
        if not await self.rate_limiter.acquire(tokens=1, timeout=30.0):
            log.error("Rate limiter timeout - too many requests")
            return None
        
        params = params or {}
        if auth:
            params["timestamp"] = int(time.time() * 1000)
            query_string = urlencode(params)
            signature = hmac.new(
                BINANCE_API_SECRET.encode("utf-8"),
                query_string.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            params["signature"] = signature

        url = f"{BINANCE_FUTURES_REST}{endpoint}"
        session = await self._get_session()
        
        # Retry logic with exponential backoff
        @async_retry_with_backoff(
            config=self.retry_config,
            exceptions=(aiohttp.ClientError, asyncio.TimeoutError)
        )
        async def make_request():
            if method == "GET":
                async with session.get(url, params=params) as resp:
                    resp.raise_for_status()
                    return await resp.json()
            else:
                async with session.post(url, params=params) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        
        try:
            data = await make_request()
            
            # Check for Binance-specific errors
            if isinstance(data, dict) and "code" in data:
                error_code = data.get("code")
                
                # Rate limit errors
                if error_code in [-1003, 429]:
                    log.warning(f"Binance rate limit hit (code: {error_code}) - backing off")
                    await asyncio.sleep(2.0)
                    return None
                
                log.error(f"Binance API error {error_code}: {data.get('msg', 'Unknown error')}")
                return None
            
            return data
        
        except aiohttp.ClientResponseError as e:
            if e.status == 418:  # IP banned
                log.error(f"Binance IP banned: {e.message}")
            elif e.status == 429:  # Rate limit
                log.warning("Binance rate limit exceeded")
            else:
                log.error(f"Binance HTTP error {e.status}: {e.message}")
            return None
        
        except aiohttp.ClientError as e:
            log.error(f"Binance request failed after retries: {e}")
            return None
        
        except Exception as e:
            log.error(f"Unexpected error in Binance request: {e}")
            return None
    
    async def get_candles(self, symbol: str, interval: str = "4h",
                         limit: int = 100) -> List[Dict]:
        """Fetch klines/candles (async)."""
        symbol = symbol.replace("-", "")
        if not await self.is_valid_symbol(symbol):
            return []
            
        binance_interval = BINANCE_INTERVALS.get(interval, interval)
        data = await self._request("GET", "/fapi/v1/klines", {
            "symbol": symbol,
            "interval": binance_interval,
            "limit": min(limit, 1500),
        })

        if not data:
            return []

        candles = []
        for item in data:
            candles.append({
                "open_time": int(item[0]),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5]),
                "close_time": int(item[6]),
                "turnover": float(item[7]),
                "exchange": "binance",
            })

        return candles
    
    async def get_orderbook(self, symbol: str, limit: int = 100) -> Dict:
        """Fetch order book (async)."""
        symbol = symbol.replace("-", "")
        if not await self.is_valid_symbol(symbol):
            return {}
            
        data = await self._request("GET", "/fapi/v1/depth", {
            "symbol": symbol,
            "limit": min(limit, 1000),
        })

        if not data:
            return {}

        return {
            "symbol": symbol,
            "bids": [{"price": float(p), "size": float(q)} for p, q in data.get("bids", [])],
            "asks": [{"price": float(p), "size": float(q)} for p, q in data.get("asks", [])],
            "timestamp": data.get("E", 0),
            "exchange": "binance",
        }
    
    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Fetch recent trades (async)."""
        symbol = symbol.replace("-", "")
        if not await self.is_valid_symbol(symbol):
            return []
            
        data = await self._request("GET", "/fapi/v1/aggTrades", {
            "symbol": symbol,
            "limit": min(limit, 1000),
        })

        if not data:
            return []

        trades = []
        for t in data:
            trades.append({
                "id": str(t.get("a", "")),
                "price": float(t.get("p", 0)),
                "size": float(t.get("q", 0)),
                "side": "SELL" if t.get("m", False) else "BUY",
                "time": int(t.get("T", 0)),
                "is_buyer_maker": t.get("m", False),
                "exchange": "binance",
            })

        return trades
    
    async def get_ticker(self, symbol: str) -> Dict:
        """Fetch 24h ticker (async)."""
        symbol = symbol.replace("-", "")
        if not await self.is_valid_symbol(symbol):
            return {}
            
        data = await self._request("GET", "/fapi/v1/ticker/24hr", {
            "symbol": symbol,
        })

        if not data:
            return {}

        return {
            "symbol": symbol,
            "last_price": float(data.get("lastPrice", 0)),
            "bid": float(data.get("bidPrice", 0)),
            "ask": float(data.get("askPrice", 0)),
            "volume_24h": float(data.get("volume", 0)),
            "turnover_24h": float(data.get("quoteVolume", 0)),
            "price_change_pct": float(data.get("priceChangePercent", 0)),
            "exchange": "binance",
        }
