"""
Advanced Order Flow Analytics — CVD, DOM, Tape, Market Pulse, Liquidity View.

Complete institutional order flow analysis suite:
- CVD (Cumulative Volume Delta): Running buy-sell balance.
- DOM (Depth of Market): Active limit order analysis.
- Tape Reading: Real-time transaction analysis (time & sales).
- Market Pulse: Composite order flow health indicator.
- Liquidity View: Where resting orders cluster (support/resistance).
- Absorption Detector: Large resting orders eating aggressive flow.
- Stacking Detector: Limit orders building up at a level.

"The order book tells you what COULD happen. The tape tells you what IS happening."
"""

import time
from typing import List, Dict, Optional, Deque
from collections import defaultdict, deque
from datetime import datetime

from utils.logger import get_logger

log = get_logger("data.advanced_of")


class AdvancedOrderFlow:
    """
    Complete order flow analytics engine.

    Combines all order flow data into actionable signals.
    """

    def __init__(self):
        # CVD history per symbol
        self._cvd: Dict[str, deque] = defaultdict(lambda: deque(maxlen=5000))
        self._cvd_value: Dict[str, float] = defaultdict(float)

        # Tape (time & sales) per symbol
        self._tape: Dict[str, deque] = defaultdict(lambda: deque(maxlen=5000))
        self._large_prints: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))

        # DOM snapshots
        self._dom_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=120))

        # Liquidity levels
        self._liquidity_levels: Dict[str, Dict] = {}

        # Market pulse history
        self._pulse: Dict[str, deque] = defaultdict(lambda: deque(maxlen=300))

        log.info("AdvancedOrderFlow initialized")

    # ═══════════════════════════════════════════════════════════════════
    # CVD — Cumulative Volume Delta
    # ═══════════════════════════════════════════════════════════════════

    def update_cvd(self, symbol: str, trades: List[Dict]):
        """
        Update Cumulative Volume Delta from trade data.

        CVD = running sum of (buy_volume - sell_volume)
        Rising CVD = aggressive buying dominating → bullish
        Falling CVD = aggressive selling dominating → bearish
        CVD divergence from price = potential reversal

        Key patterns:
        - Price up + CVD up = healthy trend (confirmed)
        - Price up + CVD flat/down = DIVERGENCE (weakening, potential reversal)
        - Price down + CVD down = healthy downtrend
        - Price down + CVD flat/up = DIVERGENCE (selling exhausting)
        """
        for trade in trades:
            size = trade.get("size", 0)
            side = trade.get("side", "").upper()

            if side == "BUY":
                self._cvd_value[symbol] += size
            elif side == "SELL":
                self._cvd_value[symbol] -= size

            self._cvd[symbol].append({
                "timestamp": trade.get("time", time.time() * 1000),
                "cvd": self._cvd_value[symbol],
                "trade_size": size,
                "side": side,
            })

    def get_cvd(self, symbol: str, window_minutes: int = 30) -> Dict:
        """
        Get CVD analysis with trend and divergence detection.
        """
        history = list(self._cvd[symbol])
        if not history:
            return {"cvd": 0, "trend": "UNKNOWN"}

        cutoff = time.time() * 1000 - window_minutes * 60 * 1000
        recent = [h for h in history if h["timestamp"] > cutoff]

        if len(recent) < 2:
            return {"cvd": self._cvd_value[symbol], "trend": "INSUFFICIENT_DATA"}

        current_cvd = recent[-1]["cvd"]
        start_cvd = recent[0]["cvd"]
        cvd_change = current_cvd - start_cvd

        # Split into halves for trend analysis
        mid = len(recent) // 2
        first_half_delta = recent[mid]["cvd"] - recent[0]["cvd"]
        second_half_delta = recent[-1]["cvd"] - recent[mid]["cvd"]

        # CVD trend
        if cvd_change > 0:
            cvd_trend = "RISING"
        elif cvd_change < 0:
            cvd_trend = "FALLING"
        else:
            cvd_trend = "FLAT"

        # Acceleration (is the delta strengthening or weakening?)
        if abs(second_half_delta) > abs(first_half_delta) * 1.3:
            acceleration = "ACCELERATING"
        elif abs(second_half_delta) < abs(first_half_delta) * 0.7:
            acceleration = "DECELERATING"
        else:
            acceleration = "STEADY"

        # Peak and trough in window
        cvd_values = [h["cvd"] for h in recent]
        max_cvd = max(cvd_values)
        min_cvd = min(cvd_values)

        return {
            "cvd": round(current_cvd, 4),
            "cvd_change": round(cvd_change, 4),
            "trend": cvd_trend,
            "acceleration": acceleration,
            "max_cvd": round(max_cvd, 4),
            "min_cvd": round(min_cvd, 4),
            "range": round(max_cvd - min_cvd, 4),
            "first_half_delta": round(first_half_delta, 4),
            "second_half_delta": round(second_half_delta, 4),
            "data_points": len(recent),
            "window_minutes": window_minutes,
        }

    def detect_cvd_divergence(self, symbol: str,
                               price_data: List[Dict]) -> Dict:
        """
        Detect CVD-Price divergence — key reversal signal.

        Bullish divergence: Price makes lower low, CVD makes higher low
        Bearish divergence: Price makes higher high, CVD makes lower high
        """
        cvd_history = list(self._cvd[symbol])
        if len(cvd_history) < 20 or len(price_data) < 20:
            return {"divergence": "NONE"}

        recent_prices = [c.get("close", 0) for c in price_data[-20:]]
        recent_cvd = [h["cvd"] for h in cvd_history[-20:]]

        # Split into two halves to compare
        price_first = min(recent_prices[:10])
        price_second = min(recent_prices[10:])
        cvd_first = min(recent_cvd[:10])
        cvd_second = min(recent_cvd[10:])

        price_high_first = max(recent_prices[:10])
        price_high_second = max(recent_prices[10:])
        cvd_high_first = max(recent_cvd[:10])
        cvd_high_second = max(recent_cvd[10:])

        # Bullish divergence: price lower low, CVD higher low
        bullish_div = price_second < price_first and cvd_second > cvd_first
        # Bearish divergence: price higher high, CVD lower high
        bearish_div = price_high_second > price_high_first and cvd_high_second < cvd_high_first

        return {
            "divergence": (
                "BULLISH" if bullish_div and not bearish_div
                else "BEARISH" if bearish_div and not bullish_div
                else "BOTH" if bullish_div and bearish_div
                else "NONE"
            ),
            "bullish_divergence": bullish_div,
            "bearish_divergence": bearish_div,
            "interpretation": (
                "Price making new lows but sellers weakening → reversal up likely" if bullish_div
                else "Price making new highs but buyers weakening → reversal down likely" if bearish_div
                else "No divergence detected"
            ),
        }

    # ═══════════════════════════════════════════════════════════════════
    # DOM — Depth of Market Analysis
    # ═══════════════════════════════════════════════════════════════════

    def update_dom(self, symbol: str, orderbook: Dict):
        """
        Update DOM (Depth of Market) analysis from orderbook snapshot.

        DOM shows:
        - Where limit orders are stacking (institutional intent)
        - Thin vs thick areas (volatility potential)
        - Order pulling/spoofing patterns
        """
        if not orderbook:
            return

        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])

        # Analyze depth distribution
        bid_levels = len(bids)
        ask_levels = len(asks)

        # Volume-weighted average distance from best bid/ask
        best_bid = bids[0]["price"] if bids else 0
        best_ask = asks[0]["price"] if asks else 0
        mid = (best_bid + best_ask) / 2 if best_bid and best_ask else 0

        # Cumulative depth at different distances
        cum_bids_01 = sum(b["size"] for b in bids if abs(b["price"] - best_bid) / best_bid < 0.001) if best_bid else 0
        cum_bids_05 = sum(b["size"] for b in bids if abs(b["price"] - best_bid) / best_bid < 0.005) if best_bid else 0
        cum_bids_10 = sum(b["size"] for b in bids if abs(b["price"] - best_bid) / best_bid < 0.01) if best_bid else 0
        cum_asks_01 = sum(a["size"] for a in asks if abs(a["price"] - best_ask) / best_ask < 0.001) if best_ask else 0
        cum_asks_05 = sum(a["size"] for a in asks if abs(a["price"] - best_ask) / best_ask < 0.005) if best_ask else 0
        cum_asks_10 = sum(a["size"] for a in asks if abs(a["price"] - best_ask) / best_ask < 0.01) if best_ask else 0

        snapshot = {
            "timestamp": time.time(),
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid": mid,
            "spread": best_ask - best_bid,
            "spread_bps": ((best_ask - best_bid) / mid * 10000) if mid else 0,
            "bid_levels": bid_levels,
            "ask_levels": ask_levels,
            "cum_bid_01pct": round(cum_bids_01, 4),
            "cum_bid_05pct": round(cum_bids_05, 4),
            "cum_bid_1pct": round(cum_bids_10, 4),
            "cum_ask_01pct": round(cum_asks_01, 4),
            "cum_ask_05pct": round(cum_asks_05, 4),
            "cum_ask_1pct": round(cum_asks_10, 4),
            "depth_imbalance_01": round(cum_bids_01 / cum_asks_01, 4) if cum_asks_01 > 0 else 999,
            "depth_imbalance_05": round(cum_bids_05 / cum_asks_05, 4) if cum_asks_05 > 0 else 999,
            "depth_imbalance_1": round(cum_bids_10 / cum_asks_10, 4) if cum_asks_10 > 0 else 999,
        }

        self._dom_history[symbol].append(snapshot)

    def get_dom_analysis(self, symbol: str) -> Dict:
        """Get current DOM state and analysis."""
        history = list(self._dom_history[symbol])
        if not history:
            return {}

        current = history[-1]

        # Detect pulling/stacking by comparing recent DOM changes
        if len(history) >= 5:
            recent_5 = history[-5:]
            bid_trend = recent_5[-1]["cum_bid_05pct"] - recent_5[0]["cum_bid_05pct"]
            ask_trend = recent_5[-1]["cum_ask_05pct"] - recent_5[0]["cum_ask_05pct"]

            if bid_trend > 0 and ask_trend < 0:
                dom_signal = "BID_STACKING"  # Bids increasing, asks decreasing → bullish
            elif bid_trend < 0 and ask_trend > 0:
                dom_signal = "ASK_STACKING"  # Asks increasing, bids decreasing → bearish
            elif bid_trend < 0 and ask_trend < 0:
                dom_signal = "THINNING"  # Liquidity pulling → volatility incoming
            else:
                dom_signal = "NEUTRAL"
        else:
            dom_signal = "INSUFFICIENT_DATA"
            bid_trend = 0
            ask_trend = 0

        return {
            **current,
            "dom_signal": dom_signal,
            "bid_depth_trend": round(bid_trend, 4),
            "ask_depth_trend": round(ask_trend, 4),
            "interpretation": {
                "BID_STACKING": "Limit buy orders building — institutional buying intent",
                "ASK_STACKING": "Limit sell orders building — institutional selling intent",
                "THINNING": "Both sides pulling orders — expect volatility spike",
                "NEUTRAL": "Normal market conditions",
            }.get(dom_signal, ""),
        }

    # ═══════════════════════════════════════════════════════════════════
    # TAPE READING — Time & Sales Analysis
    # ═══════════════════════════════════════════════════════════════════

    def process_tape(self, symbol: str, trades: List[Dict]):
        """
        Process trade tape — time & sales analysis.

        Reads the raw tape for:
        - Large print detection (institutional activity)
        - Momentum bursts (rapid succession of one-sided trades)
        - Exhaustion (decreasing trade sizes over time)
        - Iceberg detection (repeated fills at same price)
        """
        for trade in trades:
            self._tape[symbol].append({
                "price": trade.get("price", 0),
                "size": trade.get("size", 0),
                "side": trade.get("side", ""),
                "time": trade.get("time", 0),
                "exchange": trade.get("exchange", ""),
            })

            # Track large prints
            avg_size = self._get_avg_trade_size(symbol)
            if avg_size > 0 and trade.get("size", 0) > avg_size * 5:
                self._large_prints[symbol].append(trade)

    def get_tape_analysis(self, symbol: str,
                           window_minutes: int = 5) -> Dict:
        """
        Get tape reading analysis for recent window.
        """
        tape = list(self._tape[symbol])
        cutoff = time.time() * 1000 - window_minutes * 60 * 1000
        recent = [t for t in tape if t.get("time", 0) > cutoff]

        if len(recent) < 5:
            return {"trades_analyzed": 0}

        # Trade velocity (trades per minute)
        time_span = (recent[-1]["time"] - recent[0]["time"]) / 60000
        trade_velocity = len(recent) / time_span if time_span > 0 else 0

        # Size analysis
        sizes = [t["size"] for t in recent]
        avg_size = sum(sizes) / len(sizes)
        max_size = max(sizes)

        # Momentum analysis: consecutive one-sided trades
        buy_streaks = []
        sell_streaks = []
        current_streak = 1
        current_side = recent[0].get("side", "")

        for i in range(1, len(recent)):
            if recent[i].get("side") == current_side:
                current_streak += 1
            else:
                if current_side == "BUY":
                    buy_streaks.append(current_streak)
                else:
                    sell_streaks.append(current_streak)
                current_side = recent[i].get("side", "")
                current_streak = 1

        max_buy_streak = max(buy_streaks) if buy_streaks else 0
        max_sell_streak = max(sell_streaks) if sell_streaks else 0

        # Iceberg detection: many fills at same price
        price_counts = defaultdict(int)
        for t in recent:
            price_counts[round(t["price"], 2)] += 1
        suspected_icebergs = [
            {"price": price, "fills": count}
            for price, count in price_counts.items()
            if count >= 10
        ]

        # Large prints (institutional activity)
        large_prints = list(self._large_prints[symbol])
        recent_large = [lp for lp in large_prints if lp.get("time", 0) > cutoff]

        # Exhaustion: decreasing sizes in last N trades
        last_20_sizes = sizes[-20:] if len(sizes) >= 20 else sizes
        first_10 = sum(last_20_sizes[:len(last_20_sizes)//2]) / max(1, len(last_20_sizes)//2)
        second_10 = sum(last_20_sizes[len(last_20_sizes)//2:]) / max(1, len(last_20_sizes) - len(last_20_sizes)//2)
        exhaustion = second_10 < first_10 * 0.6

        return {
            "trades_analyzed": len(recent),
            "trade_velocity": round(trade_velocity, 2),
            "avg_size": round(avg_size, 4),
            "max_size": round(max_size, 4),
            "max_buy_streak": max_buy_streak,
            "max_sell_streak": max_sell_streak,
            "suspected_icebergs": suspected_icebergs[:5],
            "large_prints_count": len(recent_large),
            "large_prints": recent_large[-5:],
            "exhaustion_detected": exhaustion,
            "momentum": (
                "BUY_MOMENTUM" if max_buy_streak > max_sell_streak * 1.5
                else "SELL_MOMENTUM" if max_sell_streak > max_buy_streak * 1.5
                else "BALANCED"
            ),
        }

    # ═══════════════════════════════════════════════════════════════════
    # MARKET PULSE — Composite Health Indicator
    # ═══════════════════════════════════════════════════════════════════

    def update_pulse(self, symbol: str, orderbook: Dict,
                      trades: List[Dict], price: float):
        """
        Update Market Pulse — composite indicator of market activity/health.

        Combines:
        - Trade velocity
        - Orderbook depth
        - Spread
        - Delta momentum
        - Large order activity

        Score: 0-100 (0 = dead market, 100 = extreme activity)
        """
        if not orderbook or not trades:
            return

        cutoff = time.time() * 1000 - 60 * 1000  # Last 1 min
        recent_trades = [t for t in trades if t.get("time", 0) > cutoff]

        # Components
        velocity = len(recent_trades) / 1  # Trades per minute
        spread_bps = (
            (orderbook.get("best_ask", 0) - orderbook.get("best_bid", 0))
            / price * 10000
        ) if price > 0 else 0

        depth = orderbook.get("bid_total", 0) + orderbook.get("ask_total", 0)
        buy_vol = sum(t["size"] for t in recent_trades if t.get("side") == "BUY")
        sell_vol = sum(t["size"] for t in recent_trades if t.get("side") == "SELL")
        delta = buy_vol - sell_vol

        # Composite score
        velocity_score = min(30, velocity * 0.3)                  # 0-30
        spread_score = max(0, 20 - spread_bps * 2)                # 0-20
        depth_score = min(20, depth * 0.0001)                     # 0-20
        activity_score = min(30, (buy_vol + sell_vol) * 0.1)      # 0-30

        pulse_score = min(100, velocity_score + spread_score + depth_score + activity_score)

        pulse_data = {
            "timestamp": time.time(),
            "score": round(pulse_score, 1),
            "velocity": round(velocity, 1),
            "spread_bps": round(spread_bps, 2),
            "delta": round(delta, 4),
            "buy_volume": round(buy_vol, 4),
            "sell_volume": round(sell_vol, 4),
            "depth": round(depth, 4),
            "condition": (
                "EXTREME" if pulse_score > 80
                else "ACTIVE" if pulse_score > 60
                else "NORMAL" if pulse_score > 40
                else "QUIET" if pulse_score > 20
                else "DEAD"
            ),
        }

        self._pulse[symbol].append(pulse_data)

    def get_pulse(self, symbol: str) -> Dict:
        """Get current Market Pulse reading."""
        history = list(self._pulse[symbol])
        if not history:
            return {"score": 0, "condition": "NO_DATA"}

        current = history[-1]

        # Trend over last 5 readings
        if len(history) >= 5:
            avg_recent = sum(h["score"] for h in history[-5:]) / 5
            avg_older = sum(h["score"] for h in history[-10:-5]) / max(1, min(5, len(history) - 5))
            trend = "INCREASING" if avg_recent > avg_older * 1.1 else "DECREASING" if avg_recent < avg_older * 0.9 else "STABLE"
        else:
            trend = "INSUFFICIENT_DATA"

        return {
            **current,
            "trend": trend,
        }

    # ═══════════════════════════════════════════════════════════════════
    # LIQUIDITY VIEW — Where Resting Orders Cluster
    # ═══════════════════════════════════════════════════════════════════

    def update_liquidity_view(self, symbol: str, orderbook: Dict,
                               current_price: float):
        """
        Build Liquidity View — aggregate where resting orders cluster.

        Shows:
        - Dense bid zones (support)
        - Dense ask zones (resistance)
        - Thin zones (potential fast-move areas)
        - Liquidity cliffs (sharp dropoff in depth)
        """
        if not orderbook:
            return

        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])

        if not bids or not asks:
            return

        # Group by 0.1% price buckets
        bucket_pct = 0.001
        bid_buckets = defaultdict(float)
        ask_buckets = defaultdict(float)

        for b in bids:
            bucket = round(b["price"] / (current_price * bucket_pct)) * (current_price * bucket_pct)
            bid_buckets[bucket] += b["size"]

        for a in asks:
            bucket = round(a["price"] / (current_price * bucket_pct)) * (current_price * bucket_pct)
            ask_buckets[bucket] += a["size"]

        # Find dense zones (high liquidity)
        all_volumes = list(bid_buckets.values()) + list(ask_buckets.values())
        avg_vol = sum(all_volumes) / len(all_volumes) if all_volumes else 0

        dense_bids = sorted(
            [{"price": p, "volume": v, "type": "SUPPORT"}
             for p, v in bid_buckets.items() if v > avg_vol * 2],
            key=lambda x: -x["volume"]
        )[:10]

        dense_asks = sorted(
            [{"price": p, "volume": v, "type": "RESISTANCE"}
             for p, v in ask_buckets.items() if v > avg_vol * 2],
            key=lambda x: -x["volume"]
        )[:10]

        # Thin zones (low liquidity — potential fast moves)
        thin_bids = [
            {"price": p, "volume": v}
            for p, v in bid_buckets.items() if v < avg_vol * 0.3
        ]
        thin_asks = [
            {"price": p, "volume": v}
            for p, v in ask_buckets.items() if v < avg_vol * 0.3
        ]

        # Liquidity cliff: sharp drop in volume between adjacent buckets
        cliffs = []
        sorted_bids = sorted(bid_buckets.items(), key=lambda x: -x[0])
        for i in range(1, len(sorted_bids)):
            prev_vol = sorted_bids[i-1][1]
            curr_vol = sorted_bids[i][1]
            if prev_vol > 0 and curr_vol < prev_vol * 0.3:
                cliffs.append({
                    "price": sorted_bids[i][0],
                    "type": "BID_CLIFF",
                    "drop_pct": round((prev_vol - curr_vol) / prev_vol * 100, 1),
                })

        self._liquidity_levels[symbol] = {
            "dense_bids": dense_bids,
            "dense_asks": dense_asks,
            "thin_bid_zones": len(thin_bids),
            "thin_ask_zones": len(thin_asks),
            "cliffs": cliffs[:5],
            "strongest_support": dense_bids[0] if dense_bids else None,
            "strongest_resistance": dense_asks[0] if dense_asks else None,
            "total_bid_liquidity": round(sum(bid_buckets.values()), 4),
            "total_ask_liquidity": round(sum(ask_buckets.values()), 4),
        }

    def get_liquidity_view(self, symbol: str) -> Dict:
        """Get current liquidity view for symbol."""
        return self._liquidity_levels.get(symbol, {})

    # ═══════════════════════════════════════════════════════════════════
    # COMPOSITE ORDER FLOW SUMMARY
    # ═══════════════════════════════════════════════════════════════════

    def get_complete_orderflow(self, symbol: str,
                                price_data: List[Dict] = None) -> Dict:
        """
        Get the complete order flow picture for a symbol.

        Combines ALL OF analytics into one comprehensive view.
        """
        cvd = self.get_cvd(symbol)
        cvd_divergence = self.detect_cvd_divergence(symbol, price_data or [])
        dom = self.get_dom_analysis(symbol)
        tape = self.get_tape_analysis(symbol)
        pulse = self.get_pulse(symbol)
        liquidity = self.get_liquidity_view(symbol)

        # Determine overall bias
        bullish_signals = 0
        bearish_signals = 0

        if cvd.get("trend") == "RISING":
            bullish_signals += 1
        elif cvd.get("trend") == "FALLING":
            bearish_signals += 1

        if dom.get("dom_signal") == "BID_STACKING":
            bullish_signals += 1
        elif dom.get("dom_signal") == "ASK_STACKING":
            bearish_signals += 1

        if tape.get("momentum") == "BUY_MOMENTUM":
            bullish_signals += 1
        elif tape.get("momentum") == "SELL_MOMENTUM":
            bearish_signals += 1

        if cvd_divergence.get("divergence") == "BULLISH":
            bullish_signals += 1
        elif cvd_divergence.get("divergence") == "BEARISH":
            bearish_signals += 1

        if bullish_signals > bearish_signals + 1:
            overall = "STRONG_BULLISH"
        elif bullish_signals > bearish_signals:
            overall = "LEAN_BULLISH"
        elif bearish_signals > bullish_signals + 1:
            overall = "STRONG_BEARISH"
        elif bearish_signals > bullish_signals:
            overall = "LEAN_BEARISH"
        else:
            overall = "NEUTRAL"

        return {
            "symbol": symbol,
            "overall_bias": overall,
            "bullish_signals": bullish_signals,
            "bearish_signals": bearish_signals,
            "cvd": cvd,
            "cvd_divergence": cvd_divergence,
            "dom": dom,
            "tape": tape,
            "pulse": pulse,
            "liquidity": liquidity,
        }

    def _get_avg_trade_size(self, symbol: str) -> float:
        """Get rolling average trade size."""
        tape = list(self._tape[symbol])
        if not tape:
            return 0
        last_100 = tape[-100:]
        return sum(t["size"] for t in last_100) / len(last_100)
