"""
Advanced Market Structure — Smart Money Concepts (SMC)

Implements institutional price delivery concepts:
- Order Blocks (OB): Last candle before impulsive move (institutional entry zone)
- Fair Value Gaps (FVG): Imbalanced price areas (gaps between candle wicks)
- Liquidity Grabs/Sweeps: Stop hunts above/below equal highs/lows
- Breaker Blocks: Failed order blocks that become mitigation zones
- Market Structure Shifts (MSS/BOS): Break of Structure / Change of Character

"Price delivers to liquidity, mitigates at order blocks, and fills FVGs."
"""

from typing import List, Dict, Optional
from utils.logger import get_logger

log = get_logger("strategy.structure")


class MarketStructureAnalyzer:
    """
    Advanced market structure analysis — SMC / ICT concepts.

    Complements the 4-step strategy with deeper price delivery understanding.
    """

    def __init__(self):
        log.info("MarketStructureAnalyzer initialized")

    # ─── ORDER BLOCKS ─────────────────────────────────────────────────

    def find_order_blocks(self, candles: List[Dict],
                           min_impulse_pct: float = 0.5) -> List[Dict]:
        """
        Find Order Blocks — the last opposing candle before an impulsive move.

        Bullish OB: Last bearish candle before a strong bullish impulse
        Bearish OB: Last bullish candle before a strong bearish impulse

        Institutional theory: this is where smart money entered.
        Price tends to return here before continuing.

        Args:
            candles: Candle list (oldest first)
            min_impulse_pct: Minimum impulse move to qualify (%)
        """
        if len(candles) < 5:
            return []

        order_blocks = []

        for i in range(2, len(candles) - 2):
            c_prev = candles[i - 1]
            c_curr = candles[i]
            c_next1 = candles[i + 1]
            c_next2 = candles[i + 2] if i + 2 < len(candles) else c_next1

            curr_body = c_curr["close"] - c_curr["open"]
            is_bearish_candle = curr_body < 0
            is_bullish_candle = curr_body > 0

            # Measure impulse after current candle
            if is_bearish_candle:
                # Check for bullish impulse after bearish candle → Bullish OB
                impulse_pct = (c_next2["close"] - c_curr["low"]) / c_curr["low"] * 100
                if impulse_pct >= min_impulse_pct:
                    order_blocks.append({
                        "type": "BULLISH_OB",
                        "ob_high": c_curr["high"],
                        "ob_low": c_curr["low"],
                        "ob_open": c_curr["open"],
                        "ob_close": c_curr["close"],
                        "impulse_pct": round(impulse_pct, 3),
                        "index": i,
                        "time": c_curr.get("open_time", 0),
                        "mitigated": False,
                        "strength": self._calc_ob_strength(candles, i, "BULLISH"),
                    })

            elif is_bullish_candle:
                # Check for bearish impulse after bullish candle → Bearish OB
                impulse_pct = (c_curr["high"] - c_next2["close"]) / c_curr["high"] * 100
                if impulse_pct >= min_impulse_pct:
                    order_blocks.append({
                        "type": "BEARISH_OB",
                        "ob_high": c_curr["high"],
                        "ob_low": c_curr["low"],
                        "ob_open": c_curr["open"],
                        "ob_close": c_curr["close"],
                        "impulse_pct": round(impulse_pct, 3),
                        "index": i,
                        "time": c_curr.get("open_time", 0),
                        "mitigated": False,
                        "strength": self._calc_ob_strength(candles, i, "BEARISH"),
                    })

        # Check mitigation (price already returned to OB)
        if candles:
            latest_price = candles[-1]["close"]
            for ob in order_blocks:
                if ob["type"] == "BULLISH_OB" and latest_price < ob["ob_low"]:
                    ob["mitigated"] = True
                elif ob["type"] == "BEARISH_OB" and latest_price > ob["ob_high"]:
                    ob["mitigated"] = True

        # Only return unmitigated (fresh) order blocks
        fresh_obs = [ob for ob in order_blocks if not ob["mitigated"]]

        log.debug(f"Found {len(fresh_obs)} fresh order blocks ({len(order_blocks)} total)")
        return fresh_obs

    # ─── FAIR VALUE GAPS (FVG) ────────────────────────────────────────

    def find_fvgs(self, candles: List[Dict],
                   atr_mult: float = 0.2) -> List[Dict]:
        """
        Find Fair Value Gaps — 3-candle pattern with price imbalance.

        Bullish FVG: Gap between candle 1's high and candle 3's low
                     (price moved so fast buyers couldn't fill in between)
        Bearish FVG: Gap between candle 1's low and candle 3's high
                     (price moved so fast sellers couldn't fill)

        FVGs tend to get filled (price returns to close the gap).
        Unfilled FVGs are magnets for price.

        Args:
            candles: Candle list (oldest first)
            atr_mult: Minimum gap size multiplier for ATR(14)
        """
        if len(candles) < 3:
            return []

        current_atr = self._calc_atr(candles, period=14)
        min_gap_size = current_atr * atr_mult

        fvgs = []

        for i in range(1, len(candles) - 1):
            c1 = candles[i - 1]
            c2 = candles[i]
            c3 = candles[i + 1]

            # Bullish FVG: C1.high < C3.low (gap up)
            if c3["low"] > c1["high"]:
                gap_size = c3["low"] - c1["high"]
                gap_pct = gap_size / c1["high"] * 100

                if gap_size >= min_gap_size:
                    fvgs.append({
                        "type": "BULLISH_FVG",
                        "gap_high": c3["low"],    # Top of gap
                        "gap_low": c1["high"],     # Bottom of gap
                        "gap_mid": (c3["low"] + c1["high"]) / 2,
                        "gap_pct": round(gap_pct, 4),
                        "impulse_candle_volume": c2["volume"],
                        "index": i,
                        "time": c2.get("open_time", 0),
                        "filled": False,
                        "partially_filled": False,
                    })

            # Bearish FVG: C1.low > C3.high (gap down)
            if c1["low"] > c3["high"]:
                gap_size = c1["low"] - c3["high"]
                gap_pct = gap_size / c1["low"] * 100

                if gap_size >= min_gap_size:
                    fvgs.append({
                        "type": "BEARISH_FVG",
                        "gap_high": c1["low"],     # Top of gap
                        "gap_low": c3["high"],     # Bottom of gap
                        "gap_mid": (c1["low"] + c3["high"]) / 2,
                        "gap_pct": round(gap_pct, 4),
                        "impulse_candle_volume": c2["volume"],
                        "index": i,
                        "time": c2.get("open_time", 0),
                        "filled": False,
                        "partially_filled": False,
                    })

        # Check fill status from subsequent candles
        if candles:
            for fvg in fvgs:
                subsequent = candles[fvg["index"] + 2:] if fvg["index"] + 2 < len(candles) else []
                for sc in subsequent:
                    if fvg["type"] == "BULLISH_FVG":
                        if sc["low"] <= fvg["gap_low"]:
                            fvg["filled"] = True
                            break
                        elif sc["low"] <= fvg["gap_mid"]:
                            fvg["partially_filled"] = True
                    else:  # BEARISH_FVG
                        if sc["high"] >= fvg["gap_high"]:
                            fvg["filled"] = True
                            break
                        elif sc["high"] >= fvg["gap_mid"]:
                            fvg["partially_filled"] = True

        unfilled = [f for f in fvgs if not f["filled"]]
        log.debug(f"Found {len(unfilled)} unfilled FVGs ({len(fvgs)} total)")
        return unfilled

    # ─── LIQUIDITY GRABS / SWEEPS ─────────────────────────────────────

    def detect_liquidity_grabs(self, candles: List[Dict],
                                lookback: int = 20) -> List[Dict]:
        """
        Detect Liquidity Grabs — price spikes beyond equal highs/lows
        then reverses (stop hunts).

        Liquidity rests above equal highs (sell stops)
        and below equal lows (buy stops).

        Smart money grabs this liquidity then reverses:
        - Sweep above highs → absorb buyers → reverse down
        - Sweep below lows → absorb sellers → reverse up
        """
        if len(candles) < lookback + 5:
            return []

        current_atr = self._calc_atr(candles, period=14)
        min_reversal_size = current_atr * 0.2

        grabs = []

        for i in range(lookback, len(candles) - 2):
            window = candles[i - lookback:i]
            c_grab = candles[i]
            c_after = candles[i + 1]
            c_after2 = candles[i + 2] if i + 2 < len(candles) else c_after

            window_high = max(c["high"] for c in window)
            window_low = min(c["low"] for c in window)

            # Bullish liquidity grab: sweep below lows then close back above
            if c_grab["low"] < window_low and c_grab["close"] > window_low:
                sweep_depth = (window_low - c_grab["low"]) / window_low * 100
                reversal = (c_after["close"] - c_grab["low"]) / c_grab["low"] * 100
                reversal_size = c_after["close"] - c_grab["low"]

                if reversal_size >= min_reversal_size:  # Meaningful reversal
                    grabs.append({
                        "type": "BULLISH_GRAB",
                        "grab_price": c_grab["low"],
                        "swept_level": round(window_low, 2),
                        "sweep_depth_pct": round(sweep_depth, 4),
                        "reversal_pct": round(reversal, 4),
                        "close_above_level": c_grab["close"] > window_low,
                        "index": i,
                        "time": c_grab.get("open_time", 0),
                        "volume": c_grab["volume"],
                        "description": "Sweep below lows → buy stop hunt → bullish reversal",
                    })

            # Bearish liquidity grab: sweep above highs then close back below
            if c_grab["high"] > window_high and c_grab["close"] < window_high:
                sweep_depth = (c_grab["high"] - window_high) / window_high * 100
                reversal = (c_grab["high"] - c_after["close"]) / c_grab["high"] * 100
                reversal_size = c_grab["high"] - c_after["close"]

                if reversal_size >= min_reversal_size:
                    grabs.append({
                        "type": "BEARISH_GRAB",
                        "grab_price": c_grab["high"],
                        "swept_level": round(window_high, 2),
                        "sweep_depth_pct": round(sweep_depth, 4),
                        "reversal_pct": round(reversal, 4),
                        "close_below_level": c_grab["close"] < window_high,
                        "index": i,
                        "time": c_grab.get("open_time", 0),
                        "volume": c_grab["volume"],
                        "description": "Sweep above highs → sell stop hunt → bearish reversal",
                    })

        log.debug(f"Detected {len(grabs)} liquidity grabs")
        return grabs

    # ─── BREAKER BLOCKS ───────────────────────────────────────────────

    def find_breaker_blocks(self, candles: List[Dict]) -> List[Dict]:
        """
        Find Breaker Blocks — failed order blocks.

        When an order block gets broken (mitigated), it becomes a breaker.
        A bullish OB that gets broken becomes a bearish breaker (resistance).
        A bearish OB that gets broken becomes a bullish breaker (support).
        """
        all_obs = self.find_order_blocks(candles, min_impulse_pct=0.3)
        # We want the mitigated ones for breakers — so search with flag
        breakers = []

        for i in range(2, len(candles) - 2):
            c = candles[i]
            body = c["close"] - c["open"]

            if abs(body) < 0.01:
                continue

            is_bearish = body < 0
            is_bullish = body > 0

            # Check if subsequent impulse happened and then failed
            if is_bearish and i + 4 < len(candles):
                impulse_up = (candles[i+2]["close"] - c["low"]) / c["low"] * 100
                then_down = (candles[i+2]["close"] - candles[i+4]["close"]) / candles[i+2]["close"] * 100

                if impulse_up > 0.3 and then_down > 0.3:
                    # Bullish OB that failed → bearish breaker
                    breakers.append({
                        "type": "BEARISH_BREAKER",
                        "high": c["high"],
                        "low": c["low"],
                        "index": i,
                        "time": c.get("open_time", 0),
                    })

            elif is_bullish and i + 4 < len(candles):
                impulse_down = (c["high"] - candles[i+2]["close"]) / c["high"] * 100
                then_up = (candles[i+4]["close"] - candles[i+2]["close"]) / candles[i+2]["close"] * 100

                if impulse_down > 0.3 and then_up > 0.3:
                    breakers.append({
                        "type": "BULLISH_BREAKER",
                        "high": c["high"],
                        "low": c["low"],
                        "index": i,
                        "time": c.get("open_time", 0),
                    })

        return breakers[-10:]  # Return most recent

    # ─── MARKET STRUCTURE SHIFTS ──────────────────────────────────────

    def detect_structure_shift(self, candles: List[Dict]) -> Dict:
        """
        Detect Market Structure Shift (MSS) / Change of Character (CHoCH).

        BOS (Break of Structure): Price breaks previous swing high/low in trend direction
        CHoCH: Price breaks previous swing in OPPOSITE direction → trend change

        This is key for timing entries — wait for CHoCH at a zone.
        """
        if len(candles) < 20:
            return {"shift_detected": False}

        from strategy.step1_trend import _identify_swings

        swings = _identify_swings(candles, lookback=2)
        highs = [s for s in swings if s["type"] == "high"]
        lows = [s for s in swings if s["type"] == "low"]

        if len(highs) < 3 or len(lows) < 3:
            return {"shift_detected": False}

        latest_price = candles[-1]["close"]

        # Check for CHoCH: did we break the last significant swing?
        last_swing_high = highs[-1]["price"]
        last_swing_low = lows[-1]["price"]
        prev_swing_high = highs[-2]["price"]
        prev_swing_low = lows[-2]["price"]

        # Bearish CHoCH: price breaks below last higher low
        bearish_choch = (
            prev_swing_low < lows[-2]["price"] if len(lows) > 2 else False
        ) or latest_price < last_swing_low

        # Bullish CHoCH: price breaks above last lower high
        bullish_choch = (
            prev_swing_high > highs[-2]["price"] if len(highs) > 2 else False
        ) or latest_price > last_swing_high

        return {
            "shift_detected": bearish_choch or bullish_choch,
            "shift_type": (
                "BULLISH_CHOCH" if bullish_choch and not bearish_choch
                else "BEARISH_CHOCH" if bearish_choch and not bullish_choch
                else "CONFLICTING" if bearish_choch and bullish_choch
                else "NONE"
            ),
            "last_swing_high": round(last_swing_high, 2),
            "last_swing_low": round(last_swing_low, 2),
            "current_price": round(latest_price, 2),
        }

    # ─── PRICE DELIVERY ANALYSIS ──────────────────────────────────────

    def analyze_price_delivery(self, candles: List[Dict],
                                current_price: float) -> Dict:
        """
        Comprehensive price delivery analysis.

        Price delivers from one liquidity pool to another,
        mitigating order blocks and filling FVGs along the way.

        This provides the complete SMC picture.
        """
        obs = self.find_order_blocks(candles)
        fvgs = self.find_fvgs(candles)
        grabs = self.detect_liquidity_grabs(candles)
        breakers = self.find_breaker_blocks(candles)
        structure = self.detect_structure_shift(candles)

        # Find nearest unfilled FVG
        nearest_fvg = None
        if fvgs:
            nearest_fvg = min(
                fvgs,
                key=lambda f: abs(f["gap_mid"] - current_price)
            )

        # Find nearest fresh OB
        nearest_ob = None
        if obs:
            nearest_ob = min(
                obs,
                key=lambda o: abs((o["ob_high"] + o["ob_low"]) / 2 - current_price)
            )

        # Determine where price is heading
        bullish_targets = []
        bearish_targets = []

        for fvg in fvgs:
            if fvg["type"] == "BULLISH_FVG" and fvg["gap_mid"] > current_price:
                bullish_targets.append({"type": "FVG_FILL", "price": fvg["gap_mid"]})
            elif fvg["type"] == "BEARISH_FVG" and fvg["gap_mid"] < current_price:
                bearish_targets.append({"type": "FVG_FILL", "price": fvg["gap_mid"]})

        for ob in obs:
            mid = (ob["ob_high"] + ob["ob_low"]) / 2
            if ob["type"] == "BULLISH_OB" and mid < current_price:
                bearish_targets.append({"type": "OB_MITIGATION", "price": mid})
            elif ob["type"] == "BEARISH_OB" and mid > current_price:
                bullish_targets.append({"type": "OB_MITIGATION", "price": mid})

        return {
            "order_blocks": obs[:5],
            "fair_value_gaps": fvgs[:5],
            "liquidity_grabs": grabs[-3:],
            "breaker_blocks": breakers[:5],
            "structure_shift": structure,
            "nearest_fvg": nearest_fvg,
            "nearest_ob": nearest_ob,
            "bullish_targets": sorted(bullish_targets, key=lambda t: t["price"])[:3],
            "bearish_targets": sorted(bearish_targets, key=lambda t: -t["price"])[:3],
            "total_unfilled_fvgs": len(fvgs),
            "total_fresh_obs": len(obs),
        }

    def _calc_atr(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate Average True Range (ATR)."""
        if not candles or len(candles) < 2:
            return 0.0
            
        true_ranges = []
        for i in range(1, len(candles)):
            c = candles[i]
            prev_c = candles[i-1]
            h_l = c["high"] - c["low"]
            h_pc = abs(c["high"] - prev_c["close"])
            l_pc = abs(c["low"] - prev_c["close"])
            true_ranges.append(max(h_l, h_pc, l_pc))
            
        if len(true_ranges) < period:
            return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0
            
        return sum(true_ranges[-period:]) / period

    def _calc_ob_strength(self, candles: List[Dict], idx: int,
                           ob_type: str) -> int:
        """Calculate Order Block strength score (0-100)."""
        if idx < 2 or idx >= len(candles) - 2:
            return 50

        c = candles[idx]
        body = abs(c["close"] - c["open"])
        total_range = c["high"] - c["low"]
        body_pct = body / total_range if total_range > 0 else 0

        # Impulse strength after OB
        impulse_candle = candles[idx + 1]
        impulse_body = abs(impulse_candle["close"] - impulse_candle["open"])
        impulse_range = impulse_candle["high"] - impulse_candle["low"]
        impulse_pct = impulse_body / impulse_range if impulse_range > 0 else 0

        # Volume comparison
        ob_vol = c["volume"]
        impulse_vol = impulse_candle["volume"]
        vol_ratio = impulse_vol / ob_vol if ob_vol > 0 else 1

        strength = min(100, int(
            30 +
            min(20, body_pct * 25) +
            min(25, impulse_pct * 30) +
            min(25, vol_ratio * 10)
        ))

        return strength
