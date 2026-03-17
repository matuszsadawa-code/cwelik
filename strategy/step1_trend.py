"""
STEP 1: Identify Overall Trend (4H Timeframe)

Determines directional bias:
- BULLISH: 3+ Higher Highs, 2+ Higher Lows → Only LONGS
- BEARISH: 3+ Lower Lows, 2+ Lower Highs → Only SHORTS
- RANGE: 3 equal highs, 3 equal lows → Both directions at extremes
- UNCLEAR: No pattern → AVOID ALL TRADES

"Markets spend more time continuing trends than forming new ones."
"""

from typing import List, Dict, Optional
from config import STRATEGY
from utils.logger import get_logger

log = get_logger("strategy.step1")


def identify_trend(candles_4h: List[Dict]) -> Optional[Dict]:
    """
    STEP 1: Analyze 4H candles to identify market structure.

    Args:
        candles_4h: List of 4H candles (oldest first), minimum 20 recommended.

    Returns:
        {
            'direction': 'BULLISH' | 'BEARISH' | 'RANGE' | 'UNCLEAR',
            'confidence': 0-100,
            'structure': str description,
            'swing_highs': list,
            'swing_lows': list,
            'hh_count': int,
            'hl_count': int,
            'll_count': int,
            'lh_count': int,
            'timeframe': '4H',
        }
    """
    if not candles_4h or len(candles_4h) < 20:
        log.warning("STEP 1: Insufficient candle data (need 20+)")
        return None

    # ─── Identify swing points ────────────────────────────────────────
    swings = _identify_swings(candles_4h)
    swing_highs = [s for s in swings if s["type"] == "high"]
    swing_lows = [s for s in swings if s["type"] == "low"]

    if len(swing_highs) < 3 or len(swing_lows) < 3:
        return {
            "direction": "UNCLEAR",
            "confidence": 0,
            "structure": f"Insufficient swings: {len(swing_highs)} highs, {len(swing_lows)} lows",
            "swing_highs": swing_highs,
            "swing_lows": swing_lows,
            "hh_count": 0, "hl_count": 0, "ll_count": 0, "lh_count": 0,
            "timeframe": "4H",
        }

    # ─── Count Higher Highs / Higher Lows (bullish) ───────────────────
    recent_highs = swing_highs[-5:]
    recent_lows = swing_lows[-5:]

    hh_count = 0  # Higher Highs
    lh_count = 0  # Lower Highs
    hl_count = 0  # Higher Lows
    ll_count = 0  # Lower Lows

    for i in range(1, len(recent_highs)):
        if recent_highs[i]["price"] > recent_highs[i - 1]["price"]:
            hh_count += 1
        elif recent_highs[i]["price"] < recent_highs[i - 1]["price"]:
            lh_count += 1

    for i in range(1, len(recent_lows)):
        if recent_lows[i]["price"] > recent_lows[i - 1]["price"]:
            hl_count += 1
        elif recent_lows[i]["price"] < recent_lows[i - 1]["price"]:
            ll_count += 1

    # ─── Determine trend ──────────────────────────────────────────────
    min_hh = STRATEGY["min_hh_for_bullish"]
    min_hl = STRATEGY["min_hl_for_bullish"]
    min_ll = STRATEGY["min_ll_for_bearish"]
    min_lh = STRATEGY["min_lh_for_bearish"]

    if hh_count >= min_hh and hl_count >= min_hl:
        direction = "BULLISH"
        confidence = min(100, (hh_count + hl_count) * 15 + 20)
        structure = f"{hh_count} HH, {hl_count} HL — Strong uptrend"
    elif ll_count >= min_ll and lh_count >= min_lh:
        direction = "BEARISH"
        confidence = min(100, (ll_count + lh_count) * 15 + 20)
        structure = f"{ll_count} LL, {lh_count} LH — Strong downtrend"
    elif _is_range(recent_highs, recent_lows):
        direction = "RANGE"
        confidence = 65
        range_high = max(h["price"] for h in recent_highs)
        range_low = min(l["price"] for l in recent_lows)
        structure = f"Balanced range ${range_low:.0f} - ${range_high:.0f}"
    else:
        direction = "UNCLEAR"
        confidence = 0
        structure = f"No clear structure: {hh_count}HH {hl_count}HL {ll_count}LL {lh_count}LH"

    log.info(f"STEP 1 result: {direction} ({confidence}%) — {structure}")

    return {
        "direction": direction,
        "confidence": confidence,
        "structure": structure,
        "swing_highs": swing_highs,
        "swing_lows": swing_lows,
        "hh_count": hh_count,
        "hl_count": hl_count,
        "ll_count": ll_count,
        "lh_count": lh_count,
        "timeframe": "4H",
    }


def _identify_swings(candles: List[Dict], lookback: int = 2) -> List[Dict]:
    """
    Identify swing highs and lows.

    A swing high is a candle whose high is higher than the N candles
    before and after it. Similar for swing lows.
    """
    swings = []

    for i in range(lookback, len(candles) - lookback):
        high = candles[i]["high"]
        low = candles[i]["low"]

        # Check swing high
        is_swing_high = all(
            high > candles[i - j]["high"] for j in range(1, lookback + 1)
        ) and all(
            high > candles[i + j]["high"] for j in range(1, lookback + 1)
        )

        # Check swing low
        is_swing_low = all(
            low < candles[i - j]["low"] for j in range(1, lookback + 1)
        ) and all(
            low < candles[i + j]["low"] for j in range(1, lookback + 1)
        )

        if is_swing_high:
            swings.append({
                "type": "high",
                "price": high,
                "index": i,
                "time": candles[i].get("open_time", 0),
            })

        if is_swing_low:
            swings.append({
                "type": "low",
                "price": low,
                "index": i,
                "time": candles[i].get("open_time", 0),
            })

    return swings


def _is_range(highs: List[Dict], lows: List[Dict]) -> bool:
    """
    Check if market is in a balanced range.

    Range = last 3 highs roughly equal AND last 3 lows roughly equal.
    """
    tolerance = STRATEGY["range_tolerance_pct"]

    if len(highs) < 3 or len(lows) < 3:
        return False

    recent_highs = [h["price"] for h in highs[-3:]]
    recent_lows = [l["price"] for l in lows[-3:]]

    high_range_pct = (max(recent_highs) - min(recent_highs)) / max(recent_highs) * 100
    low_range_pct = (max(recent_lows) - min(recent_lows)) / max(recent_lows) * 100

    return high_range_pct < tolerance and low_range_pct < tolerance
