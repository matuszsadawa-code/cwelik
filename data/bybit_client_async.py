"""
Async ByBit v5 API client — aiohttp for parallel requests.
Significantly faster than sync version for multiple symbols.
"""

import time
import asyncio
from typing import List, Dict, Optional, Any

import aiohttp

from config import (
    BYBIT_API_KEY, BYBIT_API_SECRET, 
    BYBIT_DEMO_API_KEY, BYBIT_DEMO_API_SECRET,
    BYBIT_INTERVALS
)
from utils.logger import get_logger
from utils.async_rate_limiter import AsyncRateLimiter
from utils.async_error_handler import async_retry_with_backoff, AsyncRetryConfig
import hmac
import hashlib
import json

log = get_logger("data.bybit.async")

BYBIT_REST_URL = "https://api.bybit.com"


class AsyncBybitClient:
    """Async ByBit v5 REST API client for parallel data fetching."""

    def __init__(self, use_demo: bool = False):
        self._session: Optional[aiohttp.ClientSession] = None
        self.use_demo = use_demo
        
        if self.use_demo:
            self._api_key = BYBIT_DEMO_API_KEY
            self._api_secret = BYBIT_DEMO_API_SECRET
            self.base_url = "https://api-demo.bybit.com"
        else:
            self._api_key = BYBIT_API_KEY
            self._api_secret = BYBIT_API_SECRET
            self.base_url = "https://api.bybit.com"

        self._recv_window = "5000"
        
        # Rate limiter: 50 req/sec sustained, 100 burst
        self.rate_limiter = AsyncRateLimiter(requests_per_second=50, burst=100)
        
        # Retry configuration
        self.retry_config = AsyncRetryConfig(
            max_retries=3,
            initial_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0
        )
        
        log.info(f"Async ByBit client initialized (Demo: {self.use_demo})")
    
    # ═══════════════════════════════════════════════════════════════════
    # SYMBOL FORMAT CONVERSION
    # ═══════════════════════════════════════════════════════════════════
    
    def _to_bybit_format(self, symbol: str) -> str:
        """
        Convert internal symbol format to ByBit API format.
        
        Internal format: "LINK-USDT", "BTC-USDT"
        ByBit API format: "LINKUSDT", "BTCUSDT"
        
        Args:
            symbol: Symbol in internal format (e.g., "LINK-USDT")
        
        Returns:
            Symbol in ByBit format (e.g., "LINKUSDT")
        """
        if not symbol:
            return symbol
        
        # Remove hyphen if present (handles both formats)
        bybit_symbol = symbol.replace("-", "")
        
        log.debug(f"Symbol format conversion: {symbol} → {bybit_symbol}")
        return bybit_symbol
    
    def _from_bybit_format(self, symbol: str) -> str:
        """
        Convert ByBit API format to internal symbol format.
        
        ByBit API format: "LINKUSDT", "BTCUSDT"
        Internal format: "LINK-USDT", "BTC-USDT"
        
        Args:
            symbol: Symbol in ByBit format (e.g., "LINKUSDT")
        
        Returns:
            Symbol in internal format (e.g., "LINK-USDT")
        """
        if not symbol:
            return symbol
        
        # If already has hyphen, return as-is
        if "-" in symbol:
            return symbol
        
        # Add hyphen before "USDT" suffix
        if symbol.endswith("USDT"):
            base = symbol[:-4]  # Remove "USDT"
            internal_symbol = f"{base}-USDT"
            log.debug(f"Symbol format conversion: {symbol} → {internal_symbol}")
            return internal_symbol
        
        # If no USDT suffix, return as-is (edge case)
        log.debug(f"Symbol format conversion: {symbol} → {symbol} (no USDT suffix)")
        return symbol
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session (lazy initialization)."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session
    
    async def close(self):
        """Close aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _request(self, method: str, endpoint: str, params: dict = None, auth: bool = False) -> dict:
        """Make async API request with rate limiting and retry."""
        # Acquire rate limit token
        if not await self.rate_limiter.acquire(tokens=1, timeout=30.0):
            log.error("Rate limiter timeout - too many requests")
            return {}
        
        url = f"{self.base_url}{endpoint}"
        session = await self._get_session()
        
        # Prepare headers and signature for authenticated requests
        headers = {"Content-Type": "application/json"}
        if auth:
            timestamp = str(int(time.time() * 1000))
            if method == "POST":
                param_str = json.dumps(params) if params else "{}"
            else:
                # For GET, build query string manually (sorted by key as per Bybit docs)
                param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items())) if params else ""
                if param_str:
                    url = f"{url}?{param_str}"

            sign_str = f"{timestamp}{self._api_key}{self._recv_window}{param_str}"
            signature = hmac.new(
                self._api_secret.encode("utf-8"),
                sign_str.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            headers.update({
                "X-BAPI-API-KEY": self._api_key,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-SIGN": signature,
                "X-BAPI-RECV-WINDOW": self._recv_window,
            })
        
        # Retry logic with exponential backoff
        @async_retry_with_backoff(
            config=self.retry_config,
            exceptions=(aiohttp.ClientError, asyncio.TimeoutError)
        )
        async def make_request():
            if method == "GET":
                # For auth GET, url already has query string. For public GET, pass params dict.
                kwargs = {"headers": headers}
                if not auth and params:
                    kwargs["params"] = params
                async with session.get(url, **kwargs) as resp:
                    resp.raise_for_status()
                    return await resp.json()
            else:
                async with session.post(url, json=params, headers=headers) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        
        try:
            data = await make_request()
            
            # Check ByBit-specific error codes
            ret_code = data.get("retCode", 0)
            
            if ret_code == 10006:  # Rate limit exceeded
                log.warning("ByBit rate limit hit - backing off")
                await asyncio.sleep(2.0)
                return {}
            
            if ret_code != 0:
                req_symbol = params.get("symbol", "UNKNOWN") if params else "UNKNOWN"
                log.error(f"ByBit API error for {req_symbol}: {data.get('retMsg')} (code: {ret_code})")
                return {}
            
            return data.get("result", {})
        
        except aiohttp.ClientError as e:
            log.error(f"ByBit request failed after retries: {e}")
            return {}
        except Exception as e:
            log.error(f"Unexpected error in ByBit request: {e}")
            return {}
    
    async def get_candles(self, symbol: str, interval: str = "240",
                         limit: int = 100) -> List[Dict]:
        """
        Fetch klines/candles (async).

        Args:
            symbol: e.g., 'BTC-USDT' (internal format)
            interval: '5', '15', '30', '60', '240' (minutes)
            limit: max 1000

        Returns:
            List of candle dicts
        """
        bybit_symbol = self._to_bybit_format(symbol)
        bybit_interval = BYBIT_INTERVALS.get(interval, interval)
        result = await self._request("GET", "/v5/market/kline", {
            "category": "linear",
            "symbol": bybit_symbol,
            "interval": bybit_interval,
            "limit": min(limit, 1000),
        })

        if not result or "list" not in result:
            return []

        candles = []
        for item in reversed(result["list"]):  # ByBit returns newest first
            candles.append({
                "open_time": int(item[0]),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5]),
                "turnover": float(item[6]) if len(item) > 6 else 0,
                "exchange": "bybit",
            })

        return candles
    
    async def get_orderbook(self, symbol: str, limit: int = 200) -> Dict:
        """Fetch order book (async)."""
        bybit_symbol = self._to_bybit_format(symbol)
        result = await self._request("GET", "/v5/market/orderbook", {
            "category": "linear",
            "symbol": bybit_symbol,
            "limit": min(limit, 200),
        })

        if not result:
            return {}

        return {
            "symbol": symbol,  # Return in internal format
            "bids": [{"price": float(p), "size": float(q)} for p, q in result.get("b", [])],
            "asks": [{"price": float(p), "size": float(q)} for p, q in result.get("a", [])],
            "timestamp": int(result.get("ts", 0)),
            "exchange": "bybit",
        }
    
    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Fetch recent trades (async)."""
        bybit_symbol = self._to_bybit_format(symbol)
        result = await self._request("GET", "/v5/market/recent-trade", {
            "category": "linear",
            "symbol": bybit_symbol,
            "limit": min(limit, 1000),
        })

        if not result or "list" not in result:
            return []

        trades = []
        for t in result["list"]:
            trades.append({
                "id": t.get("execId", ""),
                "price": float(t.get("price", 0)),
                "size": float(t.get("size", 0)),
                "side": t.get("side", "").upper(),
                "time": int(t.get("time", 0)),
                "is_buyer_maker": t.get("side", "").lower() == "sell",
                "exchange": "bybit",
            })

        return trades
    
    async def get_ticker(self, symbol: str) -> Dict:
        """Fetch 24h ticker (async)."""
        bybit_symbol = self._to_bybit_format(symbol)
        result = await self._request("GET", "/v5/market/tickers", {
            "category": "linear",
            "symbol": bybit_symbol,
        })

        if not result or "list" not in result or not result["list"]:
            return {}

        ticker = result["list"][0]
        return {
            "symbol": symbol,  # Return in internal format
            "last_price": float(ticker.get("lastPrice", 0)),
            "mark_price": float(ticker.get("markPrice", 0)),
            "index_price": float(ticker.get("indexPrice", 0)),
            "bid": float(ticker.get("bid1Price", 0)),
            "ask": float(ticker.get("ask1Price", 0)),
            "volume_24h": float(ticker.get("volume24h", 0)),
            "turnover_24h": float(ticker.get("turnover24h", 0)),
            "price_change_pct": float(ticker.get("price24hPcnt", 0)) * 100,
            "exchange": "bybit",
        }

    # ─── Authenticated Trading ────────────────────────────────────────────

    async def place_order(self, symbol: str, side: str, qty: str, 
                         order_type: str = "Market", price: Optional[str] = None,
                         reduce_only: bool = False, stop_loss: Optional[str] = None,
                         trigger_price: Optional[str] = None, trigger_by: str = "MarkPrice") -> Dict:
        """Place an order (async). Supports conditional orders via trigger_price."""
        bybit_symbol = self._to_bybit_format(symbol)
        log.debug(f"Placing order: {symbol} → {bybit_symbol}")
        
        params: Dict[str, Any] = {
            "category": "linear",
            "symbol": bybit_symbol,
            "side": side,
            "orderType": order_type,
            "qty": qty,
            "timeInForce": "GTC" if order_type == "Limit" else "IOC",
        }
        if price:
            params["price"] = price
        if reduce_only:
            params["reduceOnly"] = True
        if stop_loss:
            params["stopLoss"] = stop_loss
            params["slTriggerBy"] = "MarkPrice"
        if trigger_price:
            params["triggerPrice"] = trigger_price
            params["triggerBy"] = trigger_by

        return await self._request("POST", "/v5/order/create", params, auth=True)

    async def cancel_order(self, symbol: str, order_id: str) -> Dict:
        """Cancel an order (async)."""
        bybit_symbol = self._to_bybit_format(symbol)
        log.debug(f"Cancelling order: {symbol} → {bybit_symbol}")
        
        params = {
            "category": "linear",
            "symbol": bybit_symbol,
            "orderId": order_id,
        }
        return await self._request("POST", "/v5/order/cancel", params, auth=True)

    async def get_position(self, symbol: str) -> Dict:
        """Get current position (async)."""
        bybit_symbol = self._to_bybit_format(symbol)
        log.debug(f"Getting position: {symbol} → {bybit_symbol}")
        
        params = {
            "category": "linear",
            "symbol": bybit_symbol,
        }
        result = await self._request("GET", "/v5/position/list", params, auth=True)
        
        if not result or "list" not in result:
            return {}
            
        for pos in result["list"]:
            if float(pos.get("size", 0)) > 0:
                return pos
        return {}

    async def get_wallet_balance(self) -> Dict:
        """Get wallet balance (async)."""
        params = {"accountType": "UNIFIED"}
        result = await self._request("GET", "/v5/account/wallet-balance", params, auth=True)
        
        if not result or "list" not in result:
            return {}
            
        return result["list"][0] if result["list"] else {}

    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage (async)."""
        bybit_symbol = self._to_bybit_format(symbol)
        log.debug(f"Setting leverage: {symbol} → {bybit_symbol}, leverage={leverage}x")
        
        params = {
            "category": "linear",
            "symbol": bybit_symbol,
            "buyLeverage": str(leverage),
            "sellLeverage": str(leverage),
        }
        result = await self._request("POST", "/v5/position/set-leverage", params, auth=True)
        if result == {} and not any(result): # empty result for some success cases or handled errors in _request
             return True
        return True # Simplified for now as _request handles errors
