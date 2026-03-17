"""
STEP 3: Volume Confirms the Idea (5M Timeframe)

Market as auction: price advertises until participants engage.
Volume shows participation/interest.

For REVERSALS (what we trade):
  - Volume SHRINKS as price approaches zone → exhaustion → TRADE ✅
  - "Push into highs with DYING volume → reversal likely"

For BREAKOUTS (what we avoid):
  - Volume EXPANDS at extremes → breakout → SKIP ❌
  - "Push into highs with EXPANDING volume → breakout likely"
"""

from typing import List, Dict, Optional
from config import STRATEGY
from utils.logger import get_logger

log = get_logger("strategy.step3")


def confirm_volume_exhaustion(candles_5m: List[Dict],
                               zone_info: Dict) -> Optional[Dict]:
    """
    STEP 3: Analyze 5M volume for exhaustion signal.

    Args:
        candles_5m: List of 5M candles (oldest first), 20+ recommended.
        zone_info: From Step 2 — zone_type, zone_high, zone_low.

    Returns:
        {
            'exhaustion_confirmed': bool,
            'volume_trend': 'SHRINKING' | 'EXPANDING' | 'NEUTRAL',
            'volume_ratio': float (recent/earlier, < 1 = shrinking),
            'direction': 'LONG' | 'SHORT',
            'vwap_deviation': float,
            'candle_analysis': dict,
            'timeframe': '5M',
        }
    """
    if not candles_5m or len(candles_5m) < 20:
        log.warning("STEP 3: Insufficient candle data (need 20+)")
        return None

    if not zone_info:
        return None

    window_recent = STRATEGY["volume_window_recent"]
    window_earlier = STRATEGY["volume_window_earlier"]
    shrink_threshold = STRATEGY["volume_shrink_threshold"]

    # ─── Volume trend analysis ────────────────────────────────────────
    recent_candles = candles_5m[-window_recent:]
    earlier_candles = candles_5m[-(window_recent + window_earlier):-window_recent]

    if not earlier_candles:
        return None

    recent_volumes = [c["volume"] for c in recent_candles]
    earlier_volumes = [c["volume"] for c in earlier_candles]

    avg_recent = sum(recent_volumes) / len(recent_volumes)
    avg_earlier = sum(earlier_volumes) / len(earlier_volumes)

    # Prevent division by zero
    if avg_earlier == 0:
        log.warning("STEP 3: avg_earlier_volume is zero, cannot calculate volume ratio")
        return None

    volume_ratio = avg_recent / avg_earlier

    # ─── Determine volume trend ──────────────────────────────────────
    if volume_ratio < shrink_threshold:
        volume_trend = "SHRINKING"
        exhaustion_confirmed = True
    elif volume_ratio > 1.3:
        volume_trend = "EXPANDING"
        exhaustion_confirmed = False
    else:
        volume_trend = "NEUTRAL"
        exhaustion_confirmed = False

    # ─── Progressive volume analysis (rolling windows) ─────────────
    # Check if volume is progressively declining (stronger signal)
    progressive_decline = _check_progressive_decline(candles_5m, window_size=5)

    if progressive_decline and not exhaustion_confirmed:
        # Progressive decline is a weaker but still valid signal
        exhaustion_confirmed = True
        volume_trend = "SHRINKING_PROGRESSIVE"

    # ─── VWAP deviation ───────────────────────────────────────────────
    vwap = _calculate_vwap(recent_candles)
    current_price = candles_5m[-1]["close"]
    vwap_deviation = ((current_price - vwap) / vwap * 100) if vwap > 0 else 0

    # ─── Candle body analysis (buyer/seller exhaustion) ───────────────
    candle_analysis = _analyze_candle_bodies(recent_candles, zone_info["zone_type"])

    # ─── Determine direction ──────────────────────────────────────────
    if zone_info["zone_type"] == "DEMAND":
        direction = "LONG"
    elif zone_info["zone_type"] == "SUPPLY":
        direction = "SHORT"
    else:
        # Range — determine by price position relative to zone
        zone_mid = (zone_info["zone_high"] + zone_info["zone_low"]) / 2
        direction = "LONG" if current_price < zone_mid else "SHORT"

    # ─── Taker buy/sell ratio (if available from Binance data) ────────
    taker_analysis = _analyze_taker_ratio(recent_candles)

    log.info(
        f"STEP 3 result: volume {volume_trend} (ratio: {volume_ratio:.2f}), "
        f"exhaustion: {exhaustion_confirmed}, direction: {direction}"
    )

    return {
        "exhaustion_confirmed": exhaustion_confirmed,
        "volume_trend": volume_trend,
        "volume_ratio": round(volume_ratio, 4),
        "direction": direction,
        "avg_recent_volume": round(avg_recent, 4),
        "avg_earlier_volume": round(avg_earlier, 4),
        "progressive_decline": progressive_decline,
        "vwap": round(vwap, 2),
        "vwap_deviation": round(vwap_deviation, 4),
        "candle_analysis": candle_analysis,
        "taker_analysis": taker_analysis,
        "timeframe": "5M",
    }


def _check_progressive_decline(candles: List[Dict],
                                 window_size: int = 5) -> bool:
    """
    Check if volume is progressively declining over multiple windows.

    Stronger exhaustion signal than simple 2-window comparison.
    """
    if len(candles) < window_size * 3:
        return False

    windows = []
    for i in range(0, len(candles) - window_size + 1, window_size):
        window = candles[i:i + window_size]
        avg_vol = sum(c["volume"] for c in window) / len(window)
        windows.append(avg_vol)

    if len(windows) < 3:
        return False

    # Check if last 3 windows show declining volume
    last_3 = windows[-3:]
    return last_3[0] > last_3[1] > last_3[2]


def _calculate_vwap(candles: List[Dict]) -> float:
    """Calculate Volume Weighted Average Price."""
    total_vp = 0
    total_volume = 0

    for c in candles:
        typical_price = (c["high"] + c["low"] + c["close"]) / 3
        total_vp += typical_price * c["volume"]
        total_volume += c["volume"]

    return total_vp / total_volume if total_volume > 0 else 0


def _analyze_candle_bodies(candles: List[Dict],
                            zone_type: str) -> Dict:
    """
    Analyze candle body characteristics for exhaustion signals.

    Exhaustion signs:
    - Shrinking candle bodies (less momentum)
    - Long wicks (rejection)
    - Spinning tops / doji (indecision)
    """
    if not candles:
        return {}

    body_sizes = []
    wick_ratios = []
    doji_count = 0

    for c in candles:
        body = abs(c["close"] - c["open"])
        total_range = c["high"] - c["low"]

        if total_range > 0:
            body_pct = body / total_range
            body_sizes.append(body_pct)

            upper_wick = c["high"] - max(c["close"], c["open"])
            lower_wick = min(c["close"], c["open"]) - c["low"]
            wick_ratios.append((upper_wick + lower_wick) / total_range)

            # Doji: body < 10% of total range
            if body_pct < 0.1:
                doji_count += 1

    avg_body_pct = sum(body_sizes) / len(body_sizes) if body_sizes else 0
    avg_wick_ratio = sum(wick_ratios) / len(wick_ratios) if wick_ratios else 0

    # Shrinking bodies = exhaustion
    body_declining = False
    if len(body_sizes) >= 6:
        first_half = sum(body_sizes[:len(body_sizes)//2]) / (len(body_sizes)//2)
        second_half = sum(body_sizes[len(body_sizes)//2:]) / (len(body_sizes) - len(body_sizes)//2)
        body_declining = second_half < first_half * 0.8

    return {
        "avg_body_pct": round(avg_body_pct * 100, 2),
        "avg_wick_ratio": round(avg_wick_ratio * 100, 2),
        "doji_count": doji_count,
        "body_declining": body_declining,
        "exhaustion_signal": body_declining or doji_count >= 2,
    }


def _analyze_taker_ratio(candles: List[Dict]) -> Dict:
    """
    Analyze taker buy/sell ratio (from Binance enriched data).

    Taker buy volume > sell volume = aggressive buying.
    """
    taker_buys = []
    taker_sells = []

    for c in candles:
        tb = c.get("taker_buy_volume", 0)
        ts = c.get("taker_sell_volume", 0)
        if tb > 0 or ts > 0:
            taker_buys.append(tb)
            taker_sells.append(ts)

    if not taker_buys:
        return {"available": False}

    total_buy = sum(taker_buys)
    total_sell = sum(taker_sells)
    total = total_buy + total_sell

    return {
        "available": True,
        "taker_buy_pct": round(total_buy / total * 100, 2) if total > 0 else 50,
        "taker_sell_pct": round(total_sell / total * 100, 2) if total > 0 else 50,
        "taker_ratio": round(total_buy / total_sell, 4) if total_sell > 0 else 999,
        "buyer_dominant": total_buy > total_sell,
    }
