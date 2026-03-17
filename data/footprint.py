"""
Footprint Chart & Volume Profile — Auction Market Theory

Implements the core AMT concept: price advertises, volume shows acceptance.

Components:
- Volume Profile: Volume at each price level (POC, VAH, VAL)
- Footprint Chart: Bid vs Ask volume at each price (delta per level)
- TPO (Time/Price Opportunity): Time spent at each level
- Volume Clusters: High-activity price zones

"Price auctions up to find sellers, down to find buyers.
 It gravitates toward the price where the most business is done (POC)."
"""

import time
from typing import List, Dict, Optional
from collections import defaultdict

from utils.logger import get_logger

log = get_logger("data.footprint")


class FootprintAnalyzer:
    """
    Footprint chart + Volume Profile analysis.

    Footprint = Shows buy vs sell volume at EACH price level.
    Like looking inside a candle to see who's doing business at each tick.
    """

    def __init__(self):
        # Accumulated volume profiles per symbol (rolling)
        self._profiles: Dict[str, Dict[float, Dict]] = defaultdict(lambda: defaultdict(
            lambda: {"buy_vol": 0, "sell_vol": 0, "total_vol": 0, "trade_count": 0, "tpo_count": 0}
        ))
        # Recent footprint data per candle
        self._footprints: Dict[str, List[Dict]] = defaultdict(list)
        # TPO periods
        self._tpo_data: Dict[str, Dict[float, int]] = defaultdict(lambda: defaultdict(int))
        log.info("FootprintAnalyzer initialized")

    def process_trades(self, symbol: str, trades: List[Dict],
                       tick_size: float = None):
        """
        Process trades to build footprint data.

        Args:
            symbol: e.g., 'BTCUSDT'
            trades: List of trade dicts with 'price', 'size', 'side'
            tick_size: Price increment for grouping (auto-detected if None)
        """
        if not trades:
            return

        # Auto-detect tick size from trades
        if tick_size is None:
            tick_size = self._auto_tick_size(trades)

        profile = self._profiles[symbol]

        for trade in trades:
            price = trade.get("price", 0)
            size = trade.get("size", 0)
            side = trade.get("side", "").upper()

            # Round to tick
            level = round(price / tick_size) * tick_size

            profile[level]["total_vol"] += size
            profile[level]["trade_count"] += 1

            if side == "BUY":
                profile[level]["buy_vol"] += size
            else:
                profile[level]["sell_vol"] += size

    def process_candle_footprint(self, symbol: str, candle: Dict,
                                  trades: List[Dict], tick_size: float = None):
        """
        Build a footprint for a specific candle — buy vs sell at each level within the candle.

        This is what you see in a footprint chart:
        Each candle is broken into price rows showing:
          [Sell Volume @ Price | Buy Volume]
          [Sell Volume @ Price | Buy Volume]
        """
        if not trades or not candle:
            return

        if tick_size is None:
            tick_size = self._auto_tick_size(trades)

        candle_low = candle.get("low", 0)
        candle_high = candle.get("high", 0)

        # Filter trades within candle range
        candle_trades = [
            t for t in trades
            if candle_low <= t.get("price", 0) <= candle_high
        ]

        levels = defaultdict(lambda: {"bid": 0, "ask": 0, "total": 0, "count": 0})

        for t in candle_trades:
            level = round(t["price"] / tick_size) * tick_size
            size = t.get("size", 0)
            side = t.get("side", "").upper()

            levels[level]["total"] += size
            levels[level]["count"] += 1

            if side == "BUY":
                levels[level]["ask"] += size  # Buyers lifting the ask
            else:
                levels[level]["bid"] += size  # Sellers hitting the bid

        # Calculate delta at each level
        footprint_levels = []
        for price_level in sorted(levels.keys()):
            data = levels[price_level]
            delta = data["ask"] - data["bid"]
            footprint_levels.append({
                "price": price_level,
                "bid_volume": round(data["bid"], 4),
                "ask_volume": round(data["ask"], 4),
                "delta": round(delta, 4),
                "total_volume": round(data["total"], 4),
                "trade_count": data["count"],
                "imbalance": "BUY" if delta > 0 else "SELL" if delta < 0 else "NEUTRAL",
            })

        footprint = {
            "symbol": symbol,
            "candle_time": candle.get("open_time", 0),
            "open": candle.get("open", 0),
            "high": candle_high,
            "low": candle_low,
            "close": candle.get("close", 0),
            "levels": footprint_levels,
            "total_delta": round(sum(l["delta"] for l in footprint_levels), 4),
            "poc_price": max(footprint_levels, key=lambda l: l["total_volume"])["price"] if footprint_levels else 0,
            "imbalance_count": {
                "buy_levels": sum(1 for l in footprint_levels if l["imbalance"] == "BUY"),
                "sell_levels": sum(1 for l in footprint_levels if l["imbalance"] == "SELL"),
            },
        }

        self._footprints[symbol].append(footprint)
        # Keep last 100 footprints
        if len(self._footprints[symbol]) > 100:
            self._footprints[symbol] = self._footprints[symbol][-100:]

        return footprint

    def get_volume_profile(self, symbol: str, levels: int = 30) -> Dict:
        """
        Get Volume Profile — Auction Market Theory core.

        Identifies:
        - POC (Point of Control): Price with most volume (fair value)
        - VAH (Value Area High): Upper 70% boundary
        - VAL (Value Area Low): Lower 70% boundary
        - HVN (High Volume Nodes): Acceptance / balance zones
        - LVN (Low Volume Nodes): Rejection / fast-move zones
        """
        profile = self._profiles.get(symbol)
        if not profile:
            return {}

        sorted_levels = sorted(profile.items(), key=lambda x: x[0])
        if not sorted_levels:
            return {}

        total_vol = sum(v["total_vol"] for _, v in sorted_levels)
        if total_vol == 0:
            return {}

        # POC: highest volume level
        poc_price, poc_data = max(sorted_levels, key=lambda x: x[1]["total_vol"])

        # Value Area (70% of volume around POC)
        vah, val = self._calculate_value_area(sorted_levels, poc_price, total_vol)

        # HVN and LVN detection
        avg_vol = total_vol / len(sorted_levels)
        hvn = [{"price": p, "volume": v["total_vol"]}
               for p, v in sorted_levels if v["total_vol"] > avg_vol * 1.5]
        lvn = [{"price": p, "volume": v["total_vol"]}
               for p, v in sorted_levels if v["total_vol"] < avg_vol * 0.5]

        # Delta profile (buy vs sell at each level)
        delta_profile = [
            {
                "price": p,
                "buy_vol": round(v["buy_vol"], 4),
                "sell_vol": round(v["sell_vol"], 4),
                "delta": round(v["buy_vol"] - v["sell_vol"], 4),
                "total_vol": round(v["total_vol"], 4),
            }
            for p, v in sorted_levels[-levels:]
        ]

        return {
            "poc": round(poc_price, 2),
            "poc_volume": round(poc_data["total_vol"], 4),
            "vah": round(vah, 2),
            "val": round(val, 2),
            "value_area_width_pct": round((vah - val) / poc_price * 100, 4) if poc_price > 0 else 0,
            "total_volume": round(total_vol, 4),
            "hvn": hvn[:10],
            "lvn": lvn[:10],
            "delta_profile": delta_profile,
            "profile_shape": self._classify_profile_shape(sorted_levels, poc_price),
        }

    def get_recent_footprints(self, symbol: str, count: int = 10) -> List[Dict]:
        """Get most recent footprint charts."""
        return self._footprints.get(symbol, [])[-count:]

    def get_footprint_imbalance(self, symbol: str) -> Dict:
        """
        Analyze footprint imbalances across recent candles.

        Imbalance = when one side dominates at specific levels.
        Stacked imbalances (3+ consecutive buy or sell dominant levels)
        indicate strong institutional activity.
        """
        footprints = self._footprints.get(symbol, [])
        if not footprints:
            return {}

        latest = footprints[-1] if footprints else None
        if not latest:
            return {}

        levels = latest.get("levels", [])

        # Detect stacked imbalances
        buy_stack = 0
        sell_stack = 0
        max_buy_stack = 0
        max_sell_stack = 0

        for level in levels:
            if level["imbalance"] == "BUY" and abs(level["delta"]) > level["total_volume"] * 0.3:
                buy_stack += 1
                sell_stack = 0
                max_buy_stack = max(max_buy_stack, buy_stack)
            elif level["imbalance"] == "SELL" and abs(level["delta"]) > level["total_volume"] * 0.3:
                sell_stack += 1
                buy_stack = 0
                max_sell_stack = max(max_sell_stack, sell_stack)
            else:
                buy_stack = 0
                sell_stack = 0

        stacked = max_buy_stack >= 3 or max_sell_stack >= 3

        return {
            "stacked_imbalances_detected": stacked,
            "max_buy_stack": max_buy_stack,
            "max_sell_stack": max_sell_stack,
            "dominant_side": "BUYERS" if max_buy_stack > max_sell_stack else "SELLERS" if max_sell_stack > max_buy_stack else "BALANCED",
            "total_delta": latest.get("total_delta", 0),
            "buy_levels": latest.get("imbalance_count", {}).get("buy_levels", 0),
            "sell_levels": latest.get("imbalance_count", {}).get("sell_levels", 0),
        }

    def update_tpo(self, symbol: str, candles: List[Dict],
                    tick_size: float = None):
        """
        Update TPO (Time Price Opportunity) data.

        TPO counts how many time periods price spent at each level.
        More TPOs = market accepted that price. Fewer TPOs = rejection.
        """
        if not candles:
            return

        if tick_size is None:
            tick_size = self._auto_tick_size_from_candles(candles)

        for candle in candles:
            low = candle.get("low", 0)
            high = candle.get("high", 0)

            level = round(low / tick_size) * tick_size
            while level <= high:
                self._tpo_data[symbol][level] += 1
                level += tick_size

    def get_tpo_profile(self, symbol: str) -> Dict:
        """Get TPO-based profile — time acceptance at each level."""
        tpo = self._tpo_data.get(symbol)
        if not tpo:
            return {}

        sorted_levels = sorted(tpo.items(), key=lambda x: x[0])
        max_tpo = max(tpo.values())
        poc_price = max(tpo, key=tpo.get)

        return {
            "poc": round(poc_price, 2),
            "max_tpo_count": max_tpo,
            "total_levels": len(sorted_levels),
            "high_acceptance": [
                {"price": round(p, 2), "tpo_count": c}
                for p, c in sorted_levels if c > max_tpo * 0.7
            ][:10],
            "low_acceptance": [
                {"price": round(p, 2), "tpo_count": c}
                for p, c in sorted_levels if c < max_tpo * 0.3
            ][:10],
        }

    def _calculate_value_area(self, sorted_levels, poc_price, total_vol,
                               pct: float = 0.70):
        """Calculate Value Area (70% of volume around POC)."""
        target_vol = total_vol * pct
        accumulated = 0

        # Start from POC and expand outward
        prices = [p for p, _ in sorted_levels]
        poc_idx = min(range(len(prices)), key=lambda i: abs(prices[i] - poc_price))

        included = {poc_idx}
        accumulated = sorted_levels[poc_idx][1]["total_vol"]

        lo, hi = poc_idx, poc_idx

        while accumulated < target_vol and (lo > 0 or hi < len(sorted_levels) - 1):
            up_vol = sorted_levels[hi + 1][1]["total_vol"] if hi + 1 < len(sorted_levels) else 0
            dn_vol = sorted_levels[lo - 1][1]["total_vol"] if lo > 0 else 0

            if up_vol >= dn_vol and hi + 1 < len(sorted_levels):
                hi += 1
                accumulated += up_vol
            elif lo > 0:
                lo -= 1
                accumulated += dn_vol
            else:
                break

        vah = sorted_levels[hi][0]
        val = sorted_levels[lo][0]
        return vah, val

    def _classify_profile_shape(self, sorted_levels, poc_price) -> str:
        """
        Classify volume profile shape:
        - P-shape: Volume concentrated at top (long accumulation)
        - b-shape: Volume concentrated at bottom (short accumulation)
        - D-shape: Even distribution (balanced/range)
        - B-shape: Bimodal (two POCs, rotation)
        """
        if len(sorted_levels) < 5:
            return "UNKNOWN"

        n = len(sorted_levels)
        top_vol = sum(v["total_vol"] for _, v in sorted_levels[n*2//3:])
        bottom_vol = sum(v["total_vol"] for _, v in sorted_levels[:n//3])
        mid_vol = sum(v["total_vol"] for _, v in sorted_levels[n//3:n*2//3])
        total = top_vol + bottom_vol + mid_vol

        if total == 0:
            return "UNKNOWN"

        top_pct = top_vol / total
        bot_pct = bottom_vol / total
        mid_pct = mid_vol / total

        if top_pct > 0.5:
            return "P-SHAPE"  # Bullish accumulation at top
        elif bot_pct > 0.5:
            return "b-SHAPE"  # Bearish accumulation at bottom
        elif mid_pct > 0.5:
            return "D-SHAPE"  # Balanced / rotational
        elif top_pct > 0.35 and bot_pct > 0.35:
            return "B-SHAPE"  # Bimodal rotation
        else:
            return "D-SHAPE"

    def _auto_tick_size(self, trades: List[Dict]) -> float:
        """Auto-detect appropriate tick size from trades."""
        if not trades:
            return 1.0
        prices = sorted(set(t.get("price", 0) for t in trades))
        if len(prices) < 2:
            return 1.0
        diffs = [prices[i+1] - prices[i] for i in range(min(100, len(prices)-1)) if prices[i+1] != prices[i]]
        if not diffs:
            return 1.0
        avg_price = sum(prices) / len(prices)
        # Use ~0.01% of price or minimum diff, whichever is larger
        return max(min(diffs), avg_price * 0.0001)

    def _auto_tick_size_from_candles(self, candles: List[Dict]) -> float:
        """Auto-detect tick size from candle data."""
        if not candles:
            return 1.0
        avg_price = sum(c.get("close", 0) for c in candles) / len(candles)
        return max(0.01, avg_price * 0.0005)
