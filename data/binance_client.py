"""
Binance Futures API client — REST + WebSocket for market data.

Provides: candles, orderbook, aggregated trades, ticker, open interest.
"""

import time
import json
import threading
from typing import List, Dict, Optional, Callable
from datetime import datetime

import requests

from config import (
    BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_INTERVALS
)
from utils.logger import get_logger
from utils.rate_limiter import RateLimiter
from utils.error_handler import retry_with_backoff, RetryConfig

log = get_logger("data.binance")

BINANCE_FUTURES_REST = "https://fapi.binance.com"
BINANCE_FUTURES_WS = "wss://fstream.binance.com/ws"


class BinanceClient:
    """Binance Futures REST API client for market data."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-MBX-APIKEY": BINANCE_API_KEY,
        })
        
        # Rate limiter: 20 req/sec sustained, 50 burst (conservative for Binance 1200/min limit)
        self.rate_limiter = RateLimiter(requests_per_second=20, burst=50)
        
        # Retry configuration
        self.retry_config = RetryConfig(
            max_retries=3,
            initial_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0
        )
        
        log.info("Binance client initialized with rate limiting and retry logic")

    def _request(self, endpoint: str, params: dict = None) -> any:
        """Make GET request to Binance Futures API with rate limiting and retry."""
        url = f"{BINANCE_FUTURES_REST}{endpoint}"
        
        # Acquire rate limit token
        if not self.rate_limiter.acquire(tokens=1, timeout=30.0):
            log.error("Rate limiter timeout - too many requests")
            return None
        
        # Retry logic with exponential backoff
        @retry_with_backoff(
            config=self.retry_config,
            exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
        )
        def make_request():
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        
        try:
            data = make_request()
            
            # Check for Binance-specific errors
            if isinstance(data, dict) and "code" in data:
                error_code = data.get("code")
                
                # Rate limit errors
                if error_code in [-1003, 429]:
                    log.warning(f"Binance rate limit hit (code: {error_code}) - backing off")
                    time.sleep(2.0)
                    return None
                
                log.error(f"Binance API error {error_code}: {data.get('msg', 'Unknown error')}")
                return None
            
            return data
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 418:  # IP banned
                log.error(f"Binance IP banned: {e.response.text[:200]}")
            elif e.response.status_code == 429:  # Rate limit
                log.warning("Binance rate limit exceeded")
            else:
                log.error(f"Binance HTTP error {e.response.status_code}: {e.response.text[:200]}")
            return None
        
        except requests.exceptions.RequestException as e:
            log.error(f"Binance request failed after retries: {e}")
            return None
        
        except Exception as e:
            log.error(f"Unexpected error in Binance request: {e}")
            return None

    # ─── Candles / Klines ─────────────────────────────────────────────────

    def get_candles(self, symbol: str, interval: str = "240",
                    limit: int = 100) -> List[Dict]:
        """
        Fetch klines/candles.

        Args:
            symbol: e.g., 'BTCUSDT'
            interval: '5', '15', '30', '60', '240' (minutes — auto-mapped)
            limit: max 1500
        """
        symbol = symbol.replace("-", "")  # normalize: BTC-USDT → BTCUSDT
        binance_interval = BINANCE_INTERVALS.get(interval, interval)
        data = self._request("/fapi/v1/klines", {
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
                "turnover": float(item[7]),  # Quote asset volume
                "taker_buy_volume": float(item[9]),
                "taker_sell_volume": float(item[5]) - float(item[9]),
                "exchange": "binance",
            })

        return candles

    # ─── Order Book ───────────────────────────────────────────────────────

    def get_orderbook(self, symbol: str, limit: int = 500) -> Dict:
        """
        Get L2 orderbook snapshot.

        Binance supports depth limits: 5, 10, 20, 50, 100, 500, 1000
        """
        symbol = symbol.replace("-", "")  # normalize: BTC-USDT → BTCUSDT
        # Map to supported limit
        valid_limits = [5, 10, 20, 50, 100, 500, 1000]
        actual_limit = min((l for l in valid_limits if l >= limit), default=1000)

        data = self._request("/fapi/v1/depth", {
            "symbol": symbol,
            "limit": actual_limit,
        })

        if not data:
            return {}

        bids = [{"price": float(b[0]), "size": float(b[1])} for b in data.get("bids", [])]
        asks = [{"price": float(a[0]), "size": float(a[1])} for a in data.get("asks", [])]

        best_bid = bids[0]["price"] if bids else 0
        best_ask = asks[0]["price"] if asks else 0
        spread = best_ask - best_bid if best_bid and best_ask else 0

        bid_total = sum(b["size"] for b in bids)
        ask_total = sum(a["size"] for a in asks)
        imbalance = bid_total / ask_total if ask_total > 0 else 999

        return {
            "bids": bids,
            "asks": asks,
            "timestamp": int(data.get("T", time.time() * 1000)),
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread,
            "bid_total": bid_total,
            "ask_total": ask_total,
            "imbalance_ratio": round(imbalance, 4),
            "exchange": "binance",
        }

    # ─── Aggregated Trades ────────────────────────────────────────────────

    def get_agg_trades(self, symbol: str, limit: int = 500) -> List[Dict]:
        """
        Get aggregated trades (compressed trades at same price/side).

        Returns list of trade dicts.
        """
        symbol = symbol.replace("-", "")  # normalize: BTC-USDT → BTCUSDT
        data = self._request("/fapi/v1/aggTrades", {
            "symbol": symbol,
            "limit": min(limit, 1000),
        })

        if not data:
            return []

        trades = []
        for t in data:
            is_buyer_maker = t.get("m", False)
            trades.append({
                "price": float(t.get("p", 0)),
                "size": float(t.get("q", 0)),
                "side": "SELL" if is_buyer_maker else "BUY",
                "time": int(t.get("T", 0)),
                "is_buyer_maker": is_buyer_maker,
                "agg_trade_id": t.get("a"),
                "exchange": "binance",
            })

        return trades

    # ─── Ticker ───────────────────────────────────────────────────────────

    def get_ticker(self, symbol: str) -> Dict:
        """Get 24h ticker data."""
        symbol = symbol.replace("-", "")  # normalize: BTC-USDT → BTCUSDT
        data = self._request("/fapi/v1/ticker/24hr", {"symbol": symbol})

        if not data:
            return {}

        return {
            "symbol": data.get("symbol"),
            "last_price": float(data.get("lastPrice", 0)),
            "mark_price": float(data.get("lastPrice", 0)),
            "high_24h": float(data.get("highPrice", 0)),
            "low_24h": float(data.get("lowPrice", 0)),
            "volume_24h": float(data.get("volume", 0)),
            "turnover_24h": float(data.get("quoteVolume", 0)),
            "price_change_pct": float(data.get("priceChangePercent", 0)),
            "weighted_avg_price": float(data.get("weightedAvgPrice", 0)),
            "exchange": "binance",
        }

    # ─── Open Interest ────────────────────────────────────────────────────

    def get_open_interest(self, symbol: str) -> Dict:
        """Get current open interest."""
        symbol = symbol.replace("-", "")  # normalize: BTC-USDT → BTCUSDT
        data = self._request("/fapi/v1/openInterest", {"symbol": symbol})

        if not data:
            return {}

        return {
            "symbol": data.get("symbol"),
            "open_interest": float(data.get("openInterest", 0)),
            "timestamp": int(data.get("time", 0)),
        }

    # ─── Funding Rate ─────────────────────────────────────────────────────

    def get_funding_rate(self, symbol: str) -> Dict:
        """Get current funding rate."""
        symbol = symbol.replace("-", "")  # normalize: BTC-USDT → BTCUSDT
        data = self._request("/fapi/v1/fundingRate", {
            "symbol": symbol,
            "limit": 1,
        })

        if not data or not data:
            return {}

        item = data[0] if isinstance(data, list) else data
        return {
            "symbol": symbol,
            "funding_rate": float(item.get("fundingRate", 0)),
            "funding_rate_timestamp": int(item.get("fundingTime", 0)),
        }

    # ─── Long/Short Ratio ─────────────────────────────────────────────────

    def get_long_short_ratio(self, symbol: str, period: str = "5m",
                              limit: int = 30) -> List[Dict]:
        """Get top trader long/short ratio."""
        symbol = symbol.replace("-", "")  # normalize: BTC-USDT → BTCUSDT
        data = self._request("/futures/data/topLongShortAccountRatio", {
            "symbol": symbol,
            "period": period,
            "limit": limit,
        })

        if not data:
            return []

        return [
            {
                "timestamp": int(item.get("timestamp", 0)),
                "long_account": float(item.get("longAccount", 0)),
                "short_account": float(item.get("shortAccount", 0)),
                "long_short_ratio": float(item.get("longShortRatio", 0)),
            }
            for item in data
        ]


class BinanceWebSocket:
    """Binance Futures WebSocket for real-time streaming."""

    def __init__(self):
        self._ws = None
        self._callbacks: Dict[str, List[Callable]] = {}
        self._running = False
        self._thread = None
        self._streams = []
        log.info("Binance WebSocket client initialized")

    def subscribe_orderbook(self, symbol: str, speed: str = "100ms",
                            callback: Callable = None):
        """Subscribe to depth/orderbook diff stream."""
        stream = f"{symbol.lower()}@depth@{speed}"
        self._streams.append(stream)
        if callback:
            self._callbacks.setdefault("depthUpdate", []).append(callback)

    def subscribe_agg_trades(self, symbol: str, callback: Callable = None):
        """Subscribe to aggregated trades stream."""
        stream = f"{symbol.lower()}@aggTrade"
        self._streams.append(stream)
        if callback:
            self._callbacks.setdefault("aggTrade", []).append(callback)

    def subscribe_kline(self, symbol: str, interval: str = "5m",
                        callback: Callable = None):
        """Subscribe to kline/candle stream."""
        stream = f"{symbol.lower()}@kline_{interval}"
        self._streams.append(stream)
        if callback:
            self._callbacks.setdefault("kline", []).append(callback)

    def subscribe_ticker(self, symbol: str, callback: Callable = None):
        """Subscribe to mini ticker stream."""
        stream = f"{symbol.lower()}@miniTicker"
        self._streams.append(stream)
        if callback:
            self._callbacks.setdefault("24hrMiniTicker", []).append(callback)

    def subscribe_book_ticker(self, symbol: str, callback: Callable = None):
        """Subscribe to best bid/ask stream (fastest updates)."""
        stream = f"{symbol.lower()}@bookTicker"
        self._streams.append(stream)
        if callback:
            self._callbacks.setdefault("bookTicker", []).append(callback)

    def start(self):
        """Start WebSocket connection in background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_ws, daemon=True)
        self._thread.start()
        log.info(f"Binance WS started with {len(self._streams)} streams")

    def stop(self):
        """Stop WebSocket connection."""
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        log.info("Binance WS stopped")

    def _run_ws(self):
        """WebSocket main loop with combined streams."""
        import websocket

        streams_path = "/".join(self._streams)
        ws_url = f"wss://fstream.binance.com/stream?streams={streams_path}"

        def on_message(ws, message):
            try:
                data = json.loads(message)
                # Combined stream format: {"stream": "...", "data": {...}}
                payload = data.get("data", data)
                event_type = payload.get("e", "")

                if event_type in self._callbacks:
                    for cb in self._callbacks[event_type]:
                        try:
                            cb(payload)
                        except Exception as e:
                            log.error(f"WS callback error: {e}")

            except json.JSONDecodeError:
                pass

        def on_open(ws):
            log.info("Binance WS connected")

        def on_error(ws, error):
            log.error(f"Binance WS error: {error}")

        def on_close(ws, code, msg):
            log.warning(f"Binance WS closed: {code} {msg}")

        while self._running:
            try:
                self._ws = websocket.WebSocketApp(
                    ws_url,
                    on_message=on_message,
                    on_open=on_open,
                    on_error=on_error,
                    on_close=on_close,
                )
                self._ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as e:
                log.error(f"Binance WS connection error: {e}")

            if self._running:
                log.info("Binance WS reconnecting in 5s...")
                time.sleep(5)
