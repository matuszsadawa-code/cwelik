"""
ByBit v5 API client — REST + WebSocket for market data.

Provides: candles, orderbook, recent trades, real-time streaming.
"""

import time
import json
import hmac
import hashlib
import threading
from typing import List, Dict, Optional, Callable
from datetime import datetime

import requests

from config import (
    BYBIT_API_KEY, BYBIT_API_SECRET, BYBIT_INTERVALS
)
from utils.logger import get_logger
from utils.rate_limiter import RateLimiter
from utils.error_handler import retry_with_backoff, RetryConfig

log = get_logger("data.bybit")

BYBIT_REST_URL = "https://api.bybit.com"
BYBIT_WS_PUBLIC = "wss://stream.bybit.com/v5/public/linear"


class BybitClient:
    """ByBit v5 REST API client for futures market data."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Rate limiter: 50 req/sec sustained, 100 burst
        self.rate_limiter = RateLimiter(requests_per_second=50, burst=100)
        
        # Retry configuration
        self.retry_config = RetryConfig(
            max_retries=3,
            initial_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0
        )
        
        log.info("ByBit client initialized with rate limiting and retry logic")

    def _request(self, method: str, endpoint: str, params: dict = None) -> dict:
        """Make authenticated or public API request with rate limiting and retry."""
        url = f"{BYBIT_REST_URL}{endpoint}"
        
        # Acquire rate limit token (wait if necessary)
        if not self.rate_limiter.acquire(tokens=1, timeout=30.0):
            log.error("Rate limiter timeout - too many requests")
            return {}
        
        # Retry logic with exponential backoff
        @retry_with_backoff(
            config=self.retry_config,
            exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
        )
        def make_request():
            if method == "GET":
                resp = self.session.get(url, params=params, timeout=10)
            else:
                resp = self.session.post(url, json=params, timeout=10)
            
            resp.raise_for_status()
            return resp.json()
        
        try:
            data = make_request()
            
            # Check ByBit-specific error codes
            ret_code = data.get("retCode", 0)
            
            if ret_code == 10006:  # Rate limit exceeded
                log.warning("ByBit rate limit hit - backing off")
                time.sleep(2.0)  # Extra backoff for rate limit
                return {}
            
            if ret_code != 0:
                log.error(f"ByBit API error: {data.get('retMsg')} (code: {ret_code})")
                return {}
            
            return data.get("result", {})
        
        except requests.exceptions.RequestException as e:
            log.error(f"ByBit request failed after retries: {e}")
            return {}
        except Exception as e:
            log.error(f"Unexpected error in ByBit request: {e}")
            return {}

    # ─── Candles / Klines ─────────────────────────────────────────────────

    def get_candles(self, symbol: str, interval: str = "240",
                    limit: int = 100) -> List[Dict]:
        """
        Fetch klines/candles.

        Args:
            symbol: e.g., 'BTCUSDT'
            interval: '5', '15', '30', '60', '240' (minutes)
            limit: max 1000

        Returns:
            List of candle dicts with: open_time, open, high, low, close, volume, turnover
        """
        symbol = symbol.replace("-", "")  # normalize: BTC-USDT → BTCUSDT
        bybit_interval = BYBIT_INTERVALS.get(interval, interval)
        result = self._request("GET", "/v5/market/kline", {
            "category": "linear",
            "symbol": symbol,
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

    # ─── Order Book ───────────────────────────────────────────────────────

    def get_orderbook(self, symbol: str, limit: int = 200) -> Dict:
        """
        Get L2 orderbook snapshot.

        Returns:
            {
                'bids': [{'price': float, 'size': float}, ...],
                'asks': [{'price': float, 'size': float}, ...],
                'timestamp': int,
                'best_bid': float,
                'best_ask': float,
                'spread': float,
                'bid_total': float,
                'ask_total': float,
                'imbalance_ratio': float,
            }
        """
        symbol = symbol.replace("-", "")  # normalize: BTC-USDT → BTCUSDT
        result = self._request("GET", "/v5/market/orderbook", {
            "category": "linear",
            "symbol": symbol,
            "limit": min(limit, 200),
        })

        if not result:
            return {}

        bids = [{"price": float(b[0]), "size": float(b[1])} for b in result.get("b", [])]
        asks = [{"price": float(a[0]), "size": float(a[1])} for a in result.get("a", [])]

        best_bid = bids[0]["price"] if bids else 0
        best_ask = asks[0]["price"] if asks else 0
        spread = best_ask - best_bid if best_bid and best_ask else 0

        bid_total = sum(b["size"] for b in bids)
        ask_total = sum(a["size"] for a in asks)
        imbalance = bid_total / ask_total if ask_total > 0 else 999

        return {
            "bids": bids,
            "asks": asks,
            "timestamp": int(result.get("ts", time.time() * 1000)),
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread,
            "bid_total": bid_total,
            "ask_total": ask_total,
            "imbalance_ratio": round(imbalance, 4),
            "exchange": "bybit",
        }

    # ─── Recent Trades ────────────────────────────────────────────────────

    def get_recent_trades(self, symbol: str, limit: int = 500) -> List[Dict]:
        """
        Get recent trades.

        Returns list of:
            {'price', 'size', 'side', 'time', 'is_buyer_maker'}
        """
        symbol = symbol.replace("-", "")  # normalize: BTC-USDT → BTCUSDT
        result = self._request("GET", "/v5/market/recent-trade", {
            "category": "linear",
            "symbol": symbol,
            "limit": min(limit, 1000),
        })

        if not result or "list" not in result:
            return []

        trades = []
        for t in result["list"]:
            trades.append({
                "price": float(t.get("price", 0)),
                "size": float(t.get("size", 0)),
                "side": t.get("side", "").upper(),  # 'BUY' or 'SELL'
                "time": int(t.get("time", 0)),
                "is_buyer_maker": t.get("side", "").lower() == "sell",
                "exchange": "bybit",
            })

        return trades

    # ─── Ticker ───────────────────────────────────────────────────────────

    def get_ticker(self, symbol: str) -> Dict:
        """Get current ticker data."""
        symbol = symbol.replace("-", "")  # normalize: BTC-USDT → BTCUSDT
        result = self._request("GET", "/v5/market/tickers", {
            "category": "linear",
            "symbol": symbol,
        })

        if not result or "list" not in result or not result["list"]:
            return {}

        t = result["list"][0]
        return {
            "symbol": t.get("symbol"),
            "last_price": float(t.get("lastPrice", 0)),
            "mark_price": float(t.get("markPrice", 0)),
            "index_price": float(t.get("indexPrice", 0)),
            "high_24h": float(t.get("highPrice24h", 0)),
            "low_24h": float(t.get("lowPrice24h", 0)),
            "volume_24h": float(t.get("volume24h", 0)),
            "turnover_24h": float(t.get("turnover24h", 0)),
            "price_change_pct": float(t.get("price24hPcnt", 0)) * 100,
            "funding_rate": float(t.get("fundingRate", 0)),
            "open_interest": float(t.get("openInterest", 0)),
            "exchange": "bybit",
        }

    def get_all_tickers(self) -> List[Dict]:
        """
        Fetch all tickers from Bybit.
        
        Returns:
            List of ticker dicts with symbol, last_price, price_change_pct, volume_24h
        """
        result = self._request("GET", "/v5/market/tickers", {
            "category": "linear",
        })

        if not result or "list" not in result:
            log.warning("Failed to fetch all tickers from Bybit")
            return []

        tickers = []
        for t in result["list"]:
            try:
                tickers.append({
                    "symbol": t.get("symbol", ""),
                    "last_price": float(t.get("lastPrice", 0)),
                    "price_change_pct": float(t.get("price24hPcnt", 0)) * 100,
                    "volume_24h": float(t.get("volume24h", 0)),
                    "turnover_24h": float(t.get("turnover24h", 0)),
                })
            except (ValueError, TypeError) as e:
                log.debug(f"Error parsing ticker {t.get('symbol')}: {e}")
                continue

        log.info(f"Fetched {len(tickers)} tickers from Bybit")
        return tickers

    def get_top_gainers(self, limit: int = 10) -> List[str]:
        """
        Get top N gainers by 24h price change (USDT pairs only).
        
        Args:
            limit: Number of top gainers to return
            
        Returns:
            List of symbol names (e.g., ['BTCUSDT', 'ETHUSDT', ...])
        """
        tickers = self.get_all_tickers()
        
        # Filter for USDT pairs only
        usdt_tickers = [t for t in tickers if t["symbol"].endswith("USDT")]
        
        # Sort by price change percentage (descending - highest gains first)
        sorted_tickers = sorted(usdt_tickers, key=lambda x: x["price_change_pct"], reverse=True)
        
        # Get top N
        top_gainers = sorted_tickers[:limit]
        
        symbols = [t["symbol"] for t in top_gainers]
        
        if symbols:
            top_stats = ", ".join([f"{s} (+{t['price_change_pct']:.2f}%)" for s, t in zip(symbols, top_gainers)])
        log.info(f"Top {limit} gainers: {top_stats}")
        
        return symbols

    def get_top_losers(self, limit: int = 10) -> List[str]:
        """
        Get top N losers by 24h price change (USDT pairs only).
        
        Args:
            limit: Number of top losers to return
            
        Returns:
            List of symbol names (e.g., ['BTCUSDT', 'ETHUSDT', ...])
        """
        tickers = self.get_all_tickers()
        
        # Filter for USDT pairs only
        usdt_tickers = [t for t in tickers if t["symbol"].endswith("USDT")]
        
        # Sort by price change percentage (ascending - highest losses first)
        sorted_tickers = sorted(usdt_tickers, key=lambda x: x["price_change_pct"])
        
        # Get top N
        top_losers = sorted_tickers[:limit]
        
        symbols = [t["symbol"] for t in top_losers]
        
        if symbols:
            top_loss_stats = ", ".join([f"{s} ({t['price_change_pct']:.2f}%)" for s, t in zip(symbols, top_losers)])
        log.info(f"Top {limit} losers: {top_loss_stats}")
        
        return symbols

    # ─── Open Interest ────────────────────────────────────────────────────

    def get_open_interest(self, symbol: str, interval: str = "5min",
                          limit: int = 50) -> List[Dict]:
        """Get open interest history."""
        symbol = symbol.replace("-", "")  # normalize: BTC-USDT → BTCUSDT
        result = self._request("GET", "/v5/market/open-interest", {
            "category": "linear",
            "symbol": symbol,
            "intervalTime": interval,
            "limit": min(limit, 200),
        })

        if not result or "list" not in result:
            return []

        return [
            {
                "timestamp": int(item.get("timestamp", 0)),
                "open_interest": float(item.get("openInterest", 0)),
            }
            for item in reversed(result["list"])
        ]

    # ─── Funding Rate ─────────────────────────────────────────────────────

    def get_funding_rate(self, symbol: str) -> Dict:
        """Get current funding rate."""
        symbol = symbol.replace("-", "")  # normalize: BTC-USDT → BTCUSDT
        result = self._request("GET", "/v5/market/funding/history", {
            "category": "linear",
            "symbol": symbol,
            "limit": 1,
        })

        if not result or "list" not in result or not result["list"]:
            return {}

        item = result["list"][0]
        return {
            "symbol": symbol,
            "funding_rate": float(item.get("fundingRate", 0)),
            "funding_rate_timestamp": int(item.get("fundingRateTimestamp", 0)),
        }


class BybitWebSocket:
    """ByBit v5 WebSocket for real-time market data streaming."""

    def __init__(self):
        self._ws = None
        self._callbacks: Dict[str, List[Callable]] = {}
        self._running = False
        self._thread = None
        self._subscriptions = []
        log.info("ByBit WebSocket client initialized")

    def subscribe_orderbook(self, symbol: str, depth: int = 200,
                            callback: Callable = None):
        """Subscribe to orderbook updates."""
        topic = f"orderbook.{depth}.{symbol}"
        self._subscriptions.append(topic)
        if callback:
            self._callbacks.setdefault(topic, []).append(callback)

    def subscribe_trades(self, symbol: str, callback: Callable = None):
        """Subscribe to public trades."""
        topic = f"publicTrade.{symbol}"
        self._subscriptions.append(topic)
        if callback:
            self._callbacks.setdefault(topic, []).append(callback)

    def subscribe_kline(self, symbol: str, interval: str = "5",
                        callback: Callable = None):
        """Subscribe to kline/candle updates."""
        topic = f"kline.{interval}.{symbol}"
        self._subscriptions.append(topic)
        if callback:
            self._callbacks.setdefault(topic, []).append(callback)

    def subscribe_ticker(self, symbol: str, callback: Callable = None):
        """Subscribe to ticker updates."""
        topic = f"tickers.{symbol}"
        self._subscriptions.append(topic)
        if callback:
            self._callbacks.setdefault(topic, []).append(callback)

    def start(self):
        """Start WebSocket connection in background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_ws, daemon=True)
        self._thread.start()
        log.info(f"ByBit WS started with {len(self._subscriptions)} subscriptions")

    def stop(self):
        """Stop WebSocket connection."""
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        log.info("ByBit WS stopped")

    def _run_ws(self):
        """WebSocket main loop."""
        import websocket

        def on_message(ws, message):
            try:
                data = json.loads(message)
                topic = data.get("topic", "")

                # Call registered callbacks
                for cb_topic, callbacks in self._callbacks.items():
                    if topic.startswith(cb_topic.split(".")[0]):
                        for cb in callbacks:
                            try:
                                cb(data)
                            except Exception as e:
                                log.error(f"WS callback error: {e}")

            except json.JSONDecodeError:
                pass

        def on_open(ws):
            log.info("ByBit WS connected")
            if self._subscriptions:
                # ByBit limits each 'subscribe' message to 20 topics
                chunk_size = 20
                for i in range(0, len(self._subscriptions), chunk_size):
                    chunk = self._subscriptions[i:i + chunk_size]
                    sub_msg = {
                        "op": "subscribe",
                        "args": chunk
                    }
                    ws.send(json.dumps(sub_msg))
                    log.info(f"Subscribed to chunk: {chunk}")

        def on_error(ws, error):
            log.error(f"ByBit WS error: {error}")

        def on_close(ws, code, msg):
            log.warning(f"ByBit WS closed: {code} {msg}")

        while self._running:
            try:
                self._ws = websocket.WebSocketApp(
                    BYBIT_WS_PUBLIC,
                    on_message=on_message,
                    on_open=on_open,
                    on_error=on_error,
                    on_close=on_close,
                )
                self._ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as e:
                log.error(f"ByBit WS connection error: {e}")

            if self._running:
                log.info("ByBit WS reconnecting in 5s...")
                time.sleep(5)
