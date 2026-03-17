"""
Level 2 Order Book Manager with heatmap, imbalance, and wall detection.

Replicates Bookmap-like analysis using ByBit + Binance orderbook data:
- Heatmap: aggregated bid/ask levels by price clusters
- Imbalance: bid vs ask volume ratio at each level
- Wall detection: large resting orders (iceberg/wall identification)
- Absorption detection: large orders getting filled without price movement
"""

import time
import threading
from typing import List, Dict, Optional
from collections import defaultdict
from datetime import datetime

from data.bybit_client import BybitClient
from data.binance_client import BinanceClient
from utils.logger import get_logger

log = get_logger("data.orderbook")


class OrderBookManager:
    """
    Manages L2 order book from both exchanges.

    Provides Bookmap-like analytics:
    - Heatmap data (aggregated volume by price clusters)
    - Bid/ask imbalance per level and overall
    - Large order detection (walls, icebergs)
    - Spread tracking
    """

    def __init__(self, bybit: BybitClient, binance: BinanceClient):
        self.bybit = bybit
        self.binance = binance

        # Current orderbook state per symbol
        self._books: Dict[str, Dict] = {}
        # Historical snapshots for absorption detection
        self._history: Dict[str, List[Dict]] = defaultdict(list)
        self._history_max = 60  # Keep last 60 snapshots

        log.info("OrderBookManager initialized")

    def update(self, symbol: str):
        """Fetch fresh orderbook from both exchanges and merge."""
        bb_book = self.bybit.get_orderbook(symbol, limit=200)
        bn_book = self.binance.get_orderbook(symbol, limit=500)

        if not bb_book and not bn_book:
            return

        merged = self._merge_orderbooks(bb_book, bn_book, symbol)
        self._books[symbol] = merged

        # Store history for absorption detection
        self._history[symbol].append({
            "timestamp": time.time(),
            "bid_total": merged.get("bid_total", 0),
            "ask_total": merged.get("ask_total", 0),
            "best_bid": merged.get("best_bid", 0),
            "best_ask": merged.get("best_ask", 0),
            "imbalance": merged.get("imbalance_ratio", 1.0),
        })
        if len(self._history[symbol]) > self._history_max:
            self._history[symbol] = self._history[symbol][-self._history_max:]

    async def async_update(self, symbol: str):
        """Fetch fresh orderbook from both exchanges and merge (async)."""
        import asyncio
        bb_task = self.bybit.get_orderbook(symbol, limit=200)
        bn_task = self.binance.get_orderbook(symbol, limit=500)
        
        bb_book, bn_book = await asyncio.gather(bb_task, bn_task, return_exceptions=True)
        if isinstance(bb_book, Exception): bb_book = {}
        if isinstance(bn_book, Exception): bn_book = {}

        if not bb_book and not bn_book:
            return

        merged = self._merge_orderbooks(bb_book, bn_book, symbol)
        self._books[symbol] = merged

        # Store history for absorption detection
        self._history[symbol].append({
            "timestamp": time.time(),
            "bid_total": merged.get("bid_total", 0),
            "ask_total": merged.get("ask_total", 0),
            "best_bid": merged.get("best_bid", 0),
            "best_ask": merged.get("best_ask", 0),
            "imbalance": merged.get("imbalance_ratio", 1.0),
        })
        if len(self._history[symbol]) > self._history_max:
            self._history[symbol] = self._history[symbol][-self._history_max:]

    def get_orderbook(self, symbol: str) -> Dict:
        """Get current merged orderbook for symbol."""
        return self._books.get(symbol, {})

    def get_heatmap(self, symbol: str, bucket_size_pct: float = 0.1,
                    levels: int = 50) -> Dict:
        """
        Generate heatmap data — aggregated volume by price clusters.

        Like Bookmap's color bars: darker = more orders at that level.

        Returns:
            {
                'bid_heatmap': [{'price_level': float, 'volume': float, 'intensity': float}],
                'ask_heatmap': [{'price_level': float, 'volume': float, 'intensity': float}],
                'max_volume': float,
            }
        """
        book = self._books.get(symbol, {})
        if not book:
            return {}

        mid_price = (book.get("best_bid", 0) + book.get("best_ask", 0)) / 2
        if mid_price == 0:
            return {}

        bucket_size = mid_price * bucket_size_pct / 100

        # Aggregate bid volumes into price buckets
        bid_buckets = defaultdict(float)
        for bid in book.get("bids", []):
            bucket = round(bid["price"] / bucket_size) * bucket_size
            bid_buckets[bucket] += bid["size"]

        # Aggregate ask volumes into price buckets
        ask_buckets = defaultdict(float)
        for ask in book.get("asks", []):
            bucket = round(ask["price"] / bucket_size) * bucket_size
            ask_buckets[bucket] += ask["size"]

        max_vol = max(
            list(bid_buckets.values()) + list(ask_buckets.values()) + [1]
        )

        bid_heatmap = sorted([
            {
                "price_level": price,
                "volume": vol,
                "intensity": round(vol / max_vol, 4),
            }
            for price, vol in bid_buckets.items()
        ], key=lambda x: -x["price_level"])[:levels]

        ask_heatmap = sorted([
            {
                "price_level": price,
                "volume": vol,
                "intensity": round(vol / max_vol, 4),
            }
            for price, vol in ask_buckets.items()
        ], key=lambda x: x["price_level"])[:levels]

        return {
            "bid_heatmap": bid_heatmap,
            "ask_heatmap": ask_heatmap,
            "max_volume": max_vol,
            "mid_price": mid_price,
        }

    def get_imbalance(self, symbol: str, levels: int = 10) -> Dict:
        """
        Calculate bid/ask imbalance at multiple depth levels.

        Returns:
            {
                'overall_ratio': float (>1 = more bids, <1 = more asks),
                'top_5_ratio': float,
                'top_10_ratio': float,
                'top_20_ratio': float,
                'level_imbalances': [{level, bid_vol, ask_vol, ratio}],
                'dominance': 'BUYERS' | 'SELLERS' | 'NEUTRAL',
            }
        """
        book = self._books.get(symbol, {})
        if not book:
            return {}

        bids = book.get("bids", [])
        asks = book.get("asks", [])

        def calc_ratio(n):
            b = sum(b["size"] for b in bids[:n]) if len(bids) >= n else sum(b["size"] for b in bids)
            a = sum(a["size"] for a in asks[:n]) if len(asks) >= n else sum(a["size"] for a in asks)
            return round(b / a, 4) if a > 0 else 999

        overall = calc_ratio(len(bids))
        top5 = calc_ratio(5)
        top10 = calc_ratio(10)
        top20 = calc_ratio(20)

        # Per-level imbalance (matched bid vs ask at same distance from mid)
        level_imbalances = []
        for i in range(min(levels, len(bids), len(asks))):
            b_vol = bids[i]["size"]
            a_vol = asks[i]["size"]
            ratio = round(b_vol / a_vol, 4) if a_vol > 0 else 999
            level_imbalances.append({
                "level": i,
                "bid_price": bids[i]["price"],
                "ask_price": asks[i]["price"],
                "bid_volume": b_vol,
                "ask_volume": a_vol,
                "ratio": ratio,
            })

        # Determine dominance
        if top10 > 1.5:
            dominance = "BUYERS"
        elif top10 < 0.67:
            dominance = "SELLERS"
        else:
            dominance = "NEUTRAL"

        return {
            "overall_ratio": overall,
            "top_5_ratio": top5,
            "top_10_ratio": top10,
            "top_20_ratio": top20,
            "level_imbalances": level_imbalances,
            "dominance": dominance,
        }

    def get_large_orders(self, symbol: str, min_multiplier: float = 5.0) -> Dict:
        """
        Detect large resting orders (walls) in the orderbook.

        A wall is an order that is significantly larger than the average
        order at nearby levels (like dark bars in Bookmap).

        Args:
            min_multiplier: order must be this many times larger than average

        Returns:
            {
                'bid_walls': [{'price', 'size', 'multiplier'}],
                'ask_walls': [{'price', 'size', 'multiplier'}],
                'largest_bid': {'price', 'size'},
                'largest_ask': {'price', 'size'},
            }
        """
        book = self._books.get(symbol, {})
        if not book:
            return {}

        bids = book.get("bids", [])
        asks = book.get("asks", [])

        def find_walls(orders):
            if not orders:
                return []
            avg_size = sum(o["size"] for o in orders) / len(orders)
            if avg_size == 0:
                return []
            walls = []
            for o in orders:
                mult = o["size"] / avg_size
                if mult >= min_multiplier:
                    walls.append({
                        "price": o["price"],
                        "size": o["size"],
                        "multiplier": round(mult, 2),
                    })
            return walls

        bid_walls = find_walls(bids)
        ask_walls = find_walls(asks)

        largest_bid = max(bids, key=lambda x: x["size"]) if bids else {}
        largest_ask = max(asks, key=lambda x: x["size"]) if asks else {}

        return {
            "bid_walls": bid_walls,
            "ask_walls": ask_walls,
            "largest_bid": largest_bid,
            "largest_ask": largest_ask,
            "total_bid_walls": len(bid_walls),
            "total_ask_walls": len(ask_walls),
        }

    def detect_absorption(self, symbol: str, lookback: int = 10) -> Dict:
        """
        Detect absorption — large orders getting filled without price movement.

        Absorption = volume at a level decreases significantly but price
        doesn't break through. The resting order absorbed aggressive orders.

        This is a key Bookmap signal for support/resistance confirmation.
        """
        history = self._history.get(symbol, [])
        if len(history) < lookback + 1:
            return {"detected": False}

        recent = history[-lookback:]
        older = history[-lookback * 2:-lookback] if len(history) >= lookback * 2 else history[:lookback]

        if not older:
            return {"detected": False}

        # Check if bid volume decreased significantly but price held
        avg_old_bid = sum(h["bid_total"] for h in older) / len(older)
        avg_new_bid = sum(h["bid_total"] for h in recent) / len(recent)
        avg_old_ask = sum(h["ask_total"] for h in older) / len(older)
        avg_new_ask = sum(h["ask_total"] for h in recent) / len(recent)

        price_old = sum(h["best_bid"] for h in older) / len(older)
        price_new = sum(h["best_bid"] for h in recent) / len(recent)
        price_change_pct = abs(price_new - price_old) / price_old * 100 if price_old > 0 else 0

        bid_change_pct = ((avg_new_bid - avg_old_bid) / avg_old_bid * 100) if avg_old_bid > 0 else 0
        ask_change_pct = ((avg_new_ask - avg_old_ask) / avg_old_ask * 100) if avg_old_ask > 0 else 0

        # Bid absorption: bids decreased (absorbed by sellers) but price didn't drop
        bid_absorption = bid_change_pct < -20 and price_change_pct < 0.5
        # Ask absorption: asks decreased (absorbed by buyers) but price didn't rise
        ask_absorption = ask_change_pct < -20 and price_change_pct < 0.5

        return {
            "detected": bid_absorption or ask_absorption,
            "bid_absorption": bid_absorption,
            "ask_absorption": ask_absorption,
            "bid_volume_change_pct": round(bid_change_pct, 2),
            "ask_volume_change_pct": round(ask_change_pct, 2),
            "price_change_pct": round(price_change_pct, 4),
            "interpretation": (
                "Buyers absorbing sell pressure (support)" if bid_absorption
                else "Sellers absorbing buy pressure (resistance)" if ask_absorption
                else "No absorption detected"
            ),
        }

    def _merge_orderbooks(self, bb_book: Dict, bn_book: Dict, symbol: str) -> Dict:
        """Merge orderbooks from both exchanges."""
        if not bb_book:
            return bn_book or {}
        if not bn_book:
            return bb_book

        # Combine bids and asks, sorted by price
        all_bids = {}
        for bid in bb_book.get("bids", []) + bn_book.get("bids", []):
            price = round(bid["price"], 2)
            all_bids[price] = all_bids.get(price, 0) + bid["size"]

        all_asks = {}
        for ask in bb_book.get("asks", []) + bn_book.get("asks", []):
            price = round(ask["price"], 2)
            all_asks[price] = all_asks.get(price, 0) + ask["size"]

        bids = sorted(
            [{"price": p, "size": s} for p, s in all_bids.items()],
            key=lambda x: -x["price"]
        )
        asks = sorted(
            [{"price": p, "size": s} for p, s in all_asks.items()],
            key=lambda x: x["price"]
        )

        best_bid = bids[0]["price"] if bids else 0
        best_ask = asks[0]["price"] if asks else 0
        bid_total = sum(b["size"] for b in bids)
        ask_total = sum(a["size"] for a in asks)

        return {
            "bids": bids,
            "asks": asks,
            "timestamp": int(time.time() * 1000),
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": best_ask - best_bid if best_bid and best_ask else 0,
            "bid_total": bid_total,
            "ask_total": ask_total,
            "imbalance_ratio": round(bid_total / ask_total, 4) if ask_total > 0 else 999,
            "exchange": "cross",
            "bybit_levels": len(bb_book.get("bids", [])) + len(bb_book.get("asks", [])),
            "binance_levels": len(bn_book.get("bids", [])) + len(bn_book.get("asks", [])),
        }
