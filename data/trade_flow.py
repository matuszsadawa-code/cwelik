"""
Trade Flow Analyzer — Delta, pressure, clusters, absorption.

Replicates Bookmap-like trade bubbles analysis:
- Green bubbles: Market BUY orders hitting the ask (aggressive)
- Red bubbles: Market SELL orders hitting the bid (aggressive)
- Delta: Cumulative buy vs sell volume
- Clusters: Large market buy/sell groups
- Absorption: Large resting orders absorbing aggressive flow
"""

import time
import threading
from typing import List, Dict, Optional, Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta

from data.bybit_client import BybitClient
from data.binance_client import BinanceClient
from config import STRATEGY
from utils.logger import get_logger

log = get_logger("data.tradeflow")


class TradeFlowAnalyzer:
    """
    Real-time trade flow analysis — Bookmap-like bubbles/delta.

    Collects aggressive trades and provides:
    - Cumulative delta (buy volume - sell volume)
    - Buy/sell pressure ratio
    - Trade cluster detection (large groups)
    - Delta flip detection (momentum change)
    """

    def __init__(self, bybit: BybitClient, binance: BinanceClient):
        self.bybit = bybit
        self.binance = binance

        # Trade history per symbol (last N minutes)
        self._trades: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        # Rolling delta per symbol
        self._delta: Dict[str, float] = defaultdict(float)
        # Delta history for flip detection
        self._delta_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        # Detected clusters
        self._clusters: Dict[str, List[Dict]] = defaultdict(list)

        log.info("TradeFlowAnalyzer initialized")

    def process_trades_batch(self, symbol: str, trades: List[Dict]):
        """Process a batch of trades from WebSocket (no REST call needed)."""
        for trade in trades:
            self._trades[symbol].append(trade)
        if trades:
            self._calculate_delta(symbol)
            self._detect_clusters(symbol)

    def update(self, symbol: str):
        """Fetch recent trades from both exchanges and analyze."""
        # Fetch from both exchanges
        bb_trades = self.bybit.get_recent_trades(symbol, limit=500)
        bn_trades = self.binance.get_agg_trades(symbol, limit=500)

        # Merge all trades
        all_trades = sorted(
            bb_trades + bn_trades,
            key=lambda t: t.get("time", 0)
        )

        if not all_trades:
            return

        # Store trades
        for trade in all_trades:
            self._trades[symbol].append(trade)

        # Calculate delta
        self._calculate_delta(symbol)

        # Detect clusters
        self._detect_clusters(symbol)

    async def async_update(self, symbol: str):
        """Fetch recent trades from both exchanges and analyze (async)."""
        import asyncio
        bb_task = self.bybit.get_recent_trades(symbol, limit=500)
        
        if hasattr(self.binance, 'get_recent_trades'):
            bn_task = self.binance.get_recent_trades(symbol, limit=500)
        else:
            bn_task = self.binance.get_agg_trades(symbol, limit=500)
            
        bb_trades, bn_trades = await asyncio.gather(bb_task, bn_task, return_exceptions=True)
        if isinstance(bb_trades, Exception): bb_trades = []
        if isinstance(bn_trades, Exception): bn_trades = []

        # Merge all trades
        all_trades = sorted(
            bb_trades + bn_trades,
            key=lambda t: t.get("time", 0)
        )

        if not all_trades:
            return

        # Store trades
        for trade in all_trades:
            self._trades[symbol].append(trade)

        # Calculate delta
        self._calculate_delta(symbol)

        # Detect clusters
        self._detect_clusters(symbol)

    def get_delta(self, symbol: str, window_minutes: int = 5) -> Dict:
        """
        Get cumulative delta for the last N minutes.

        Delta = Buy volume - Sell volume
        Positive delta = buyers dominant (bullish)
        Negative delta = sellers dominant (bearish)
        """
        trades = list(self._trades.get(symbol, []))
        if not trades:
            return {"delta": 0, "buy_volume": 0, "sell_volume": 0}

        cutoff = time.time() * 1000 - window_minutes * 60 * 1000
        recent = [t for t in trades if t.get("time", 0) > cutoff]

        buy_vol = sum(t["size"] for t in recent if t.get("side") == "BUY")
        sell_vol = sum(t["size"] for t in recent if t.get("side") == "SELL")
        delta = buy_vol - sell_vol

        return {
            "delta": round(delta, 4),
            "buy_volume": round(buy_vol, 4),
            "sell_volume": round(sell_vol, 4),
            "total_volume": round(buy_vol + sell_vol, 4),
            "buy_pct": round(buy_vol / (buy_vol + sell_vol) * 100, 2) if (buy_vol + sell_vol) > 0 else 50,
            "sell_pct": round(sell_vol / (buy_vol + sell_vol) * 100, 2) if (buy_vol + sell_vol) > 0 else 50,
            "trade_count": len(recent),
            "window_minutes": window_minutes,
        }

    def get_pressure(self, symbol: str) -> Dict:
        """
        Get buy/sell pressure analysis.

        Compares aggressive buy vs sell intensity over multiple windows.
        """
        short = self.get_delta(symbol, window_minutes=1)
        medium = self.get_delta(symbol, window_minutes=5)
        long = self.get_delta(symbol, window_minutes=15)

        # Determine overall pressure
        if short["delta"] > 0 and medium["delta"] > 0:
            pressure = "BUY_PRESSURE"
        elif short["delta"] < 0 and medium["delta"] < 0:
            pressure = "SELL_PRESSURE"
        elif short["delta"] > 0 and medium["delta"] < 0:
            pressure = "BUY_REVERSAL"  # Short-term buying into medium-term selling
        elif short["delta"] < 0 and medium["delta"] > 0:
            pressure = "SELL_REVERSAL"  # Short-term selling into medium-term buying
        else:
            pressure = "NEUTRAL"

        return {
            "pressure": pressure,
            "short_term": short,
            "medium_term": medium,
            "long_term": long,
        }

    def get_clusters(self, symbol: str, lookback_minutes: int = 30) -> List[Dict]:
        """
        Get detected trade clusters (Bookmap-like bubbles).

        A cluster is a group of trades in a short time window with
        large total volume — like the green/red bubbles in Bookmap.
        """
        cutoff = time.time() - lookback_minutes * 60
        return [
            c for c in self._clusters.get(symbol, [])
            if c.get("time_end", 0) > cutoff
        ]

    def detect_delta_flip(self, symbol: str) -> Dict:
        """
        Detect delta flip — momentum changing from buy to sell or vice versa.

        This is a key order flow signal: when cumulative delta flips sign,
        it indicates a shift in who's in control.
        """
        history = list(self._delta_history.get(symbol, []))
        if len(history) < 10:
            return {"flip_detected": False}

        recent_deltas = [h["delta"] for h in history[-10:]]
        older_deltas = [h["delta"] for h in history[-20:-10]] if len(history) >= 20 else [h["delta"] for h in history[:10]]

        avg_recent = sum(recent_deltas) / len(recent_deltas)
        avg_older = sum(older_deltas) / len(older_deltas) if older_deltas else 0

        # Flip: sign change from older to recent
        flip_to_positive = avg_older < 0 and avg_recent > 0
        flip_to_negative = avg_older > 0 and avg_recent < 0

        return {
            "flip_detected": flip_to_positive or flip_to_negative,
            "flip_direction": "POSITIVE" if flip_to_positive else "NEGATIVE" if flip_to_negative else "NONE",
            "recent_avg_delta": round(avg_recent, 4),
            "older_avg_delta": round(avg_older, 4),
            "interpretation": (
                "Buyers taking control (bullish flip)" if flip_to_positive
                else "Sellers taking control (bearish flip)" if flip_to_negative
                else "No momentum shift"
            ),
        }

    def get_aggressive_flow(self, symbol: str, window_minutes: int = 5) -> Dict:
        """
        Analyze aggressive order flow — who's hitting the market.

        In Bookmap terms:
        - Green bubbles = aggressive market BUY orders (hitting the ask)
        - Red bubbles = aggressive market SELL orders (hitting the bid)
        """
        trades = list(self._trades.get(symbol, []))
        cutoff = time.time() * 1000 - window_minutes * 60 * 1000
        recent = [t for t in trades if t.get("time", 0) > cutoff]

        if not recent:
            return {}

        # Separate by side
        buys = [t for t in recent if t.get("side") == "BUY"]
        sells = [t for t in recent if t.get("side") == "SELL"]

        # Large trades (> 2x average)
        avg_size = sum(t["size"] for t in recent) / len(recent) if recent else 0
        large_buys = [t for t in buys if t["size"] > avg_size * 2]
        large_sells = [t for t in sells if t["size"] > avg_size * 2]

        return {
            "total_trades": len(recent),
            "buy_count": len(buys),
            "sell_count": len(sells),
            "buy_volume": round(sum(t["size"] for t in buys), 4),
            "sell_volume": round(sum(t["size"] for t in sells), 4),
            "large_buy_count": len(large_buys),
            "large_sell_count": len(large_sells),
            "large_buy_volume": round(sum(t["size"] for t in large_buys), 4),
            "large_sell_volume": round(sum(t["size"] for t in large_sells), 4),
            "avg_trade_size": round(avg_size, 4),
            "aggressiveness": (
                "BUYERS_AGGRESSIVE" if len(large_buys) > len(large_sells) * 1.5
                else "SELLERS_AGGRESSIVE" if len(large_sells) > len(large_buys) * 1.5
                else "BALANCED"
            ),
        }

    def _calculate_delta(self, symbol: str):
        """Calculate and store rolling delta."""
        delta_data = self.get_delta(symbol, window_minutes=5)
        self._delta[symbol] = delta_data["delta"]
        self._delta_history[symbol].append({
            "timestamp": time.time(),
            "delta": delta_data["delta"],
            "buy_vol": delta_data["buy_volume"],
            "sell_vol": delta_data["sell_volume"],
        })

    def _detect_clusters(self, symbol: str):
        """
        Detect trade clusters — groups of large trades in short time windows.

        Like Bookmap bubbles: a cluster of green/red shows aggressive
        market orders at a specific price level.
        """
        trades = list(self._trades.get(symbol, []))
        if len(trades) < 5:
            return

        window_ms = STRATEGY["cluster_time_window_sec"] * 1000
        min_trades = STRATEGY["cluster_min_trades"]

        # Group trades by time windows
        clusters = []
        i = 0
        while i < len(trades):
            window_start = trades[i].get("time", 0)
            window_end = window_start + window_ms

            window_trades = []
            j = i
            while j < len(trades) and trades[j].get("time", 0) <= window_end:
                window_trades.append(trades[j])
                j += 1

            if len(window_trades) >= min_trades:
                buy_vol = sum(t["size"] for t in window_trades if t.get("side") == "BUY")
                sell_vol = sum(t["size"] for t in window_trades if t.get("side") == "SELL")
                is_buy_cluster = buy_vol > sell_vol

                avg_price = sum(t["price"] for t in window_trades) / len(window_trades)

                clusters.append({
                    "symbol": symbol,
                    "exchange": "cross",
                    "cluster_type": "BUY_CLUSTER" if is_buy_cluster else "SELL_CLUSTER",
                    "price": round(avg_price, 2),
                    "total_volume": round(buy_vol + sell_vol, 4),
                    "buy_volume": round(buy_vol, 4),
                    "sell_volume": round(sell_vol, 4),
                    "trade_count": len(window_trades),
                    "is_aggressive_buy": is_buy_cluster,
                    "time_start": window_start / 1000,
                    "time_end": (window_trades[-1].get("time", 0)) / 1000,
                })

            i = max(j, i + 1)

        self._clusters[symbol] = clusters
