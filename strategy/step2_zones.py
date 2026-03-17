"""
STEP 2: Find High Probability Zones (30M Timeframe)

Trade where big money already acted:
- Demand Zones: Rally → Base → Rally (for longs)
- Supply Zones: Drop → Base → Drop (for shorts)
- Liquidity Pools: Equal highs/lows, session extremes

"Enter where I saw big buyers/sellers previously."
"""

from typing import List, Dict, Optional
from config import STRATEGY
from utils.logger import get_logger

log = get_logger("strategy.step2")


def find_zones(candles_30m: List[Dict], trend_direction: str,
               current_price: float) -> Optional[Dict]:
    """
    STEP 2: Find supply/demand zones on 30M timeframe.

    Args:
        candles_30m: List of 30M candles (oldest first), 50+ recommended.
        trend_direction: From Step 1 — 'BULLISH', 'BEARISH', 'RANGE', 'UNCLEAR'
        current_price: Current market price for distance calculation.

    Returns:
        {
            'zone_type': 'DEMAND' | 'SUPPLY',
            'zone_high': float,
            'zone_low': float,
            'zone_mid': float,
            'strength': 0-100,
            'pattern': str,
            'distance_pct': float,
            'freshness': int (0 = untested, 1+ = number of retests),
            'timeframe': '30M',
        }
    """
    if not candles_30m or len(candles_30m) < 50:
        log.warning("STEP 2: Insufficient candle data (need 50+)")
        return None

    if trend_direction == "UNCLEAR":
        log.info("STEP 2: Trend UNCLEAR — skipping zone search")
        return None

    max_distance = STRATEGY["max_zone_distance_pct"]

    # ─── Find zones based on trend ────────────────────────────────────
    all_zones = []

    if trend_direction in ("BULLISH", "RANGE"):
        demand_zones = _find_demand_zones(candles_30m)
        all_zones.extend(demand_zones)

    if trend_direction in ("BEARISH", "RANGE"):
        supply_zones = _find_supply_zones(candles_30m)
        all_zones.extend(supply_zones)

    # Add break-retest zones (guide: broken supply→demand, broken demand→supply)
    br_zones = _find_break_retest_zones(candles_30m, trend_direction)
    all_zones.extend(br_zones)

    # Add liquidity pool zones
    liq_zones = _find_liquidity_pools(candles_30m, trend_direction)
    all_zones.extend(liq_zones)

    if not all_zones:
        log.info("STEP 2: No zones found")
        return None

    # ─── Filter by distance to current price ──────────────────────────
    valid_zones = []
    for zone in all_zones:
        # Use zone boundary for distance calculation (not mid-price)
        # For DEMAND zones (LONG), use zone_high (entry point)
        # For SUPPLY zones (SHORT), use zone_low (entry point)
        if zone["zone_type"] == "DEMAND":
            reference_price = zone["zone_high"]  # Entry at top of demand zone
        else:  # SUPPLY
            reference_price = zone["zone_low"]   # Entry at bottom of supply zone
        
        distance_pct = abs(current_price - reference_price) / current_price * 100
        zone["distance_pct"] = round(distance_pct, 3)
        zone["zone_mid"] = round((zone["zone_high"] + zone["zone_low"]) / 2, 2)

        if distance_pct <= max_distance:
            valid_zones.append(zone)

    if not valid_zones:
        log.info(f"STEP 2: {len(all_zones)} zones found but none within {max_distance}% of price ${current_price:.2f}")
        return None

    # ─── Select best zone (closest + strongest) ──────────────────────
    # Score = strength - distance penalty
    for zone in valid_zones:
        zone["score"] = zone["strength"] - zone["distance_pct"] * 10

    best_zone = max(valid_zones, key=lambda z: z["score"])

    log.info(
        f"STEP 2 result: {best_zone['zone_type']} zone at "
        f"${best_zone['zone_low']:.2f}-${best_zone['zone_high']:.2f} "
        f"(strength: {best_zone['strength']}, distance: {best_zone['distance_pct']:.2f}%)"
    )

    return best_zone


def _find_demand_zones(candles: List[Dict]) -> List[Dict]:
    """
    Find Demand zones: Rally → Base → Rally pattern.

    Institutional buying: price rallied, consolidated (base), then rallied again.
    The base is where institutions accumulated — price is likely to bounce here again.
    """
    zones = []
    base_range_pct = STRATEGY["base_max_range_pct"]

    for i in range(10, len(candles) - 10):
        # ─── Rally before (strong upward move) ───────────────────────
        rally_start = candles[max(0, i - 10)]
        rally_end = candles[i]
        rally_pct = (rally_end["close"] - rally_start["close"]) / rally_start["close"] * 100

        if rally_pct < 0.5:  # Need at least 0.5% rally
            continue

        # ─── Base (consolidation, low volatility) ────────────────────
        if i + 5 > len(candles):
            continue
        base_candles = candles[i:i + 5]
        base_high = max(c["high"] for c in base_candles)
        base_low = min(c["low"] for c in base_candles)
        base_range = (base_high - base_low) / base_low * 100

        if base_range > base_range_pct:
            continue  # Not a tight enough base

        # ─── Rally after (continuation upward) ───────────────────────
        if i + 10 >= len(candles):
            continue
        after_close = candles[i + 10]["close"]
        base_avg = (base_high + base_low) / 2
        after_rally_pct = (after_close - base_avg) / base_avg * 100

        if after_rally_pct < 0.3:
            continue  # Need positive continuation

        # ─── Volume analysis in base ─────────────────────────────────
        base_vol = sum(c["volume"] for c in base_candles) / len(base_candles)
        pre_vol = sum(c["volume"] for c in candles[max(0, i-5):i]) / max(1, min(5, i))
        vol_ratio = base_vol / pre_vol if pre_vol > 0 else 1

        # Higher volume in base = stronger accumulation
        strength = min(100, int(
            40 +  # Base strength
            min(30, rally_pct * 5) +  # Rally magnitude bonus
            min(20, after_rally_pct * 5) +  # Continuation bonus
            min(10, vol_ratio * 5)  # Volume bonus
        ))

        if strength >= STRATEGY["zone_min_strength"]:
            # Guide: DEMAND zone = bottom wick (min low) → top body (max open/close)
            demand_low = min(c["low"] for c in base_candles)  # Bottom wick
            demand_high = max(max(c["open"], c["close"]) for c in base_candles)  # Top body
            zones.append({
                "zone_type": "DEMAND",
                "zone_high": round(demand_high, 2),
                "zone_low": round(demand_low, 2),
                "strength": strength,
                "pattern": "Rally→Base→Rally",
                "rally_pct": round(rally_pct, 2),
                "continuation_pct": round(after_rally_pct, 2),
                "freshness": 0,
                "timeframe": "30M",
            })

    return zones


def _find_supply_zones(candles: List[Dict]) -> List[Dict]:
    """
    Find Supply zones: Drop → Base → Drop pattern.

    Institutional selling: price dropped, consolidated (base), then dropped again.
    The base is where institutions distributed — price is likely to reverse here again.
    """
    zones = []
    base_range_pct = STRATEGY["base_max_range_pct"]

    for i in range(10, len(candles) - 10):
        # ─── Drop before (strong downward move) ──────────────────────
        drop_start = candles[max(0, i - 10)]
        drop_end = candles[i]
        drop_pct = (drop_start["close"] - drop_end["close"]) / drop_start["close"] * 100

        if drop_pct < 0.5:
            continue

        # ─── Base (consolidation) ────────────────────────────────────
        if i + 5 > len(candles):
            continue
        base_candles = candles[i:i + 5]
        base_high = max(c["high"] for c in base_candles)
        base_low = min(c["low"] for c in base_candles)
        base_range = (base_high - base_low) / base_low * 100

        if base_range > base_range_pct:
            continue

        # ─── Drop after (continuation downward) ─────────────────────
        if i + 10 >= len(candles):
            continue
        after_close = candles[i + 10]["close"]
        base_avg = (base_high + base_low) / 2
        after_drop_pct = (base_avg - after_close) / base_avg * 100

        if after_drop_pct < 0.3:
            continue

        # ─── Volume analysis ─────────────────────────────────────────
        base_vol = sum(c["volume"] for c in base_candles) / len(base_candles)
        pre_vol = sum(c["volume"] for c in candles[max(0, i-5):i]) / max(1, min(5, i))
        vol_ratio = base_vol / pre_vol if pre_vol > 0 else 1

        strength = min(100, int(
            40 + min(30, drop_pct * 5) + min(20, after_drop_pct * 5) + min(10, vol_ratio * 5)
        ))

        if strength >= STRATEGY["zone_min_strength"]:
            # Guide: SUPPLY zone = bottom body (min open/close) → top wick (max high)
            supply_low = min(min(c["open"], c["close"]) for c in base_candles)  # Bottom body
            supply_high = max(c["high"] for c in base_candles)  # Top wick
            zones.append({
                "zone_type": "SUPPLY",
                "zone_high": round(supply_high, 2),
                "zone_low": round(supply_low, 2),
                "strength": strength,
                "pattern": "Drop→Base→Drop",
                "drop_pct": round(drop_pct, 2),
                "continuation_pct": round(after_drop_pct, 2),
                "freshness": 0,
                "timeframe": "30M",
            })

    return zones


def _find_liquidity_pools(candles: List[Dict],
                           trend_direction: str) -> List[Dict]:
    """
    Find liquidity pools where resting orders accumulate:
    - Equal highs (sell stops above)
    - Equal lows (buy stops below)
    - Session highs/lows
    """
    zones = []

    # Find equal highs (within 0.1% of each other)
    highs = [(i, c["high"]) for i, c in enumerate(candles)]
    for i in range(len(highs)):
        equal_count = 0
        for j in range(i + 1, len(highs)):
            diff_pct = abs(highs[i][1] - highs[j][1]) / highs[i][1] * 100
            if diff_pct < 0.1:
                equal_count += 1

        if equal_count >= 2:  # 3+ equal highs
            price = highs[i][1]
            zones.append({
                "zone_type": "SUPPLY" if trend_direction == "BEARISH" else "DEMAND",
                "zone_high": round(price * 1.001, 2),
                "zone_low": round(price * 0.999, 2),
                "strength": 55 + equal_count * 5,
                "pattern": f"Liquidity Pool ({equal_count + 1} equal highs)",
                "freshness": 0,
                "timeframe": "30M",
            })

    # Find equal lows
    lows = [(i, c["low"]) for i, c in enumerate(candles)]
    for i in range(len(lows)):
        equal_count = 0
        for j in range(i + 1, len(lows)):
            diff_pct = abs(lows[i][1] - lows[j][1]) / lows[i][1] * 100
            if diff_pct < 0.1:
                equal_count += 1

        if equal_count >= 2:
            price = lows[i][1]
            zones.append({
                "zone_type": "DEMAND" if trend_direction == "BULLISH" else "SUPPLY",
                "zone_high": round(price * 1.001, 2),
                "zone_low": round(price * 0.999, 2),
                "strength": 55 + equal_count * 5,
                "pattern": f"Liquidity Pool ({equal_count + 1} equal lows)",
                "freshness": 0,
                "timeframe": "30M",
            })

    return zones


def _find_break_retest_zones(candles: List[Dict],
                              trend_direction: str) -> List[Dict]:
    """
    Find Break-Retest zones per guide:
    - Broken supply → new demand (in bullish market)
    - Broken demand → new supply (in bearish market)

    Price breaks through a zone, then returns to test it from the other side.
    The zone flips its role.
    """
    zones = []

    if len(candles) < 30:
        return zones

    # First identify all potential S&D levels via swing points
    swing_levels = []
    for i in range(2, len(candles) - 2):
        c = candles[i]

        # Swing high
        is_sh = (c["high"] > candles[i-1]["high"] and c["high"] > candles[i-2]["high"]
                 and c["high"] > candles[i+1]["high"] and c["high"] > candles[i+2]["high"])
        if is_sh:
            swing_levels.append({"price": c["high"], "type": "high", "index": i})

        # Swing low
        is_sl = (c["low"] < candles[i-1]["low"] and c["low"] < candles[i-2]["low"]
                 and c["low"] < candles[i+1]["low"] and c["low"] < candles[i+2]["low"])
        if is_sl:
            swing_levels.append({"price": c["low"], "type": "low", "index": i})

    # Check for break-retest: price breaks a level then returns to test it
    for level in swing_levels:
        lvl_price = level["price"]
        lvl_idx = level["index"]

        if lvl_idx + 10 >= len(candles):
            continue

        # Check if price broke through and then returned
        broke_above = False
        broke_below = False
        retest_from_above = False
        retest_from_below = False

        for j in range(lvl_idx + 1, min(lvl_idx + 20, len(candles))):
            c = candles[j]
            if c["close"] > lvl_price * 1.002:  # Broke above
                broke_above = True
            if c["close"] < lvl_price * 0.998:  # Broke below
                broke_below = True

        # Bullish break-retest: broke above a swing high (supply broken → new demand)
        if trend_direction == "BULLISH" and broke_above and level["type"] == "high":
            # Check if price returned near this level
            for j in range(lvl_idx + 5, min(lvl_idx + 30, len(candles))):
                c = candles[j]
                diff_pct = abs(c["low"] - lvl_price) / lvl_price * 100
                if diff_pct < 0.5 and c["close"] > lvl_price:
                    retest_from_above = True
                    break

            if retest_from_above:
                zones.append({
                    "zone_type": "DEMAND",
                    "zone_high": round(lvl_price * 1.002, 2),
                    "zone_low": round(lvl_price * 0.998, 2),
                    "strength": 70,
                    "pattern": "Break-Retest (Supply→Demand)",
                    "freshness": 0,
                    "timeframe": "30M",
                })

        # Bearish break-retest: broke below a swing low (demand broken → new supply)
        if trend_direction == "BEARISH" and broke_below and level["type"] == "low":
            for j in range(lvl_idx + 5, min(lvl_idx + 30, len(candles))):
                c = candles[j]
                diff_pct = abs(c["high"] - lvl_price) / lvl_price * 100
                if diff_pct < 0.5 and c["close"] < lvl_price:
                    retest_from_below = True
                    break

            if retest_from_below:
                zones.append({
                    "zone_type": "SUPPLY",
                    "zone_high": round(lvl_price * 1.002, 2),
                    "zone_low": round(lvl_price * 0.998, 2),
                    "strength": 70,
                    "pattern": "Break-Retest (Demand→Supply)",
                    "freshness": 0,
                    "timeframe": "30M",
                })

    log.debug(f"Found {len(zones)} break-retest zones")
    return zones
