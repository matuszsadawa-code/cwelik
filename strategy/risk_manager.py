"""
Risk Manager — Zone-based SL, R:R-based TP calculation.

"SL at invalidation point (zone boundary). TP based on R:R from SL distance."
"""

from typing import Dict, List, Optional
from config import STRATEGY
from utils.logger import get_logger

log = get_logger("strategy.risk")


def _get_opposing_structural_levels(direction: str, current_price: float, advanced_data: Dict) -> List[float]:
    """Extract structural levels (FVGs, OBs, Liquidity Pools, Vol Profile) opposing the entry."""
    levels = []
    if not advanced_data:
        return levels
        
    ict = advanced_data.get("ict", {})
    
    # 1. FVGs
    for fvg in ict.get("fvg", []):
        if direction == "LONG" and fvg.get("bottom", 0) > current_price:
            levels.append(fvg["bottom"])
        elif direction == "SHORT" and fvg.get("top", float("inf")) < current_price:
            levels.append(fvg["top"])
            
    # 2. Order Blocks
    for ob in ict.get("order_blocks", []):
        if direction == "LONG" and ob.get("type") == "BEARISH" and ob.get("bottom", 0) > current_price:
            levels.append(ob["bottom"])
        elif direction == "SHORT" and ob.get("type") == "BULLISH" and ob.get("top", float("inf")) < current_price:
            levels.append(ob["top"])
            
    # 3. Liquidity Pools
    for pool in ict.get("liquidity_pools", []):
        price = pool.get("price_level")
        if price:
            if direction == "LONG" and price > current_price:
                levels.append(price)
            elif direction == "SHORT" and price < current_price:
                levels.append(price)

    # 4. Volume Profile
    vol_prof = advanced_data.get("volume_profile", {})
    if isinstance(vol_prof, dict):
        for key in ["poc", "vah", "val"]:
            level = vol_prof.get(key)
            if level:
                if direction == "LONG" and level > current_price:
                    levels.append(level)
                elif direction == "SHORT" and level < current_price:
                    levels.append(level)
                
    # Remove duplicates and sort by proximity to current price
    levels = list(set(levels))
    if direction == "LONG":
        levels.sort()
    else:
        levels.sort(reverse=True)
        
    return levels


def calculate_risk(direction: str, zone_info: Dict,
                   current_price: float, vwap: Optional[float] = None,
                   advanced_data: Optional[Dict] = None,
                   regime_adjustments: Optional[Dict] = None) -> Dict:
    """
    Calculate entry, stop loss, and multiple take profit levels.

    Zone-based SL: placed below demand zone / above supply zone + buffer.
    TP1 (Risk-Off): Nearest valid structural target or VWAP, min R:R 1:1.
    TP2 (Structural): Deeper structural target, min R:R 2:1.
    
    If no structural targets exist, falls back to static R:R ratios.

    Args:
        direction: 'LONG' or 'SHORT'
        zone_info: From Step 2 — zone_high, zone_low
        current_price: Current market price
        vwap: VWAP price (Volume Weighted Average Price) — guide's primary TP target
        advanced_data: Dictionary of advanced confirmations (ICT, Volume Profile, etc.)
        regime_adjustments: Volatility regime adjustments (sl_buffer_multiplier, etc.)

    Returns:
        {
            'entry_price': float,
            'sl_price': float,
            'tp1_price': float,
            'tp2_price': float,
            'sl_distance_pct': float,
            'rr_ratio': float (TP2 R:R),
            'vwap_tp_valid': bool,
            'zone_boundary': float
        }
    """
    buffer_pct = STRATEGY.get("sl_buffer_pct", 0.5) / 100
    
    # Apply volatility regime adjustment to SL buffer
    if regime_adjustments and hasattr(regime_adjustments, 'sl_buffer_multiplier'):
        buffer_pct *= regime_adjustments.sl_buffer_multiplier
        log.info(f"  [REGIME] SL buffer adjusted: {STRATEGY.get('sl_buffer_pct', 0.5)}% -> {buffer_pct * 100:.2f}% (multiplier: {regime_adjustments.sl_buffer_multiplier:.1f}x)")
    
    # Fallback R:Rs
    fallback_tp1_rr = 1.0  # Safe risk-off
    fallback_tp2_rr = STRATEGY.get("tp_rr_ratio", 2.0)  # Primary target

    entry_price = current_price
    vwap_tp_valid = False

    # Calculate SL
    if direction == "LONG":
        zone_boundary = zone_info["zone_low"]
        sl_price = zone_boundary * (1 - buffer_pct)
        sl_distance = entry_price - sl_price
    else:
        zone_boundary = zone_info["zone_high"]
        sl_price = zone_boundary * (1 + buffer_pct)
        sl_distance = sl_price - entry_price

    if sl_distance <= 0:
        sl_distance = entry_price * 0.005  # Fallback 0.5% SL

    # Fetch ordered structural levels
    structural_levels = _get_opposing_structural_levels(direction, entry_price, advanced_data)
    
    # Insert VWAP into structural levels if it aligns
    if vwap:
        if direction == "LONG" and vwap > entry_price:
            structural_levels.append(vwap)
        elif direction == "SHORT" and vwap < entry_price:
            structural_levels.append(vwap)
            
    # Sort again to ensure VWAP is properly placed in distance order
    if direction == "LONG":
        structural_levels.sort()
    else:
        structural_levels.sort(reverse=True)

    tp1_price = None
    tp2_price = None
    
    # Find TP1 (Min 1.0 R:R)
    for lvl in structural_levels:
        dist = abs(lvl - entry_price)
        rr = dist / sl_distance
        if rr >= 1.0:
            tp1_price = lvl
            if lvl == vwap:
                vwap_tp_valid = True
            log.info(f"  [TP1] Structural target found: ${tp1_price:.2f} (R:R {rr:.1f}:1)")
            break
            
    # Find TP2 (Min 2.0 R:R and further than TP1)
    for lvl in structural_levels:
        dist = abs(lvl - entry_price)
        rr = dist / sl_distance
        
        tp1_dist = abs(tp1_price - entry_price) if tp1_price is not None else 0
        if rr >= 2.0 and (tp1_price is None or dist > tp1_dist):
            tp2_price = lvl
            if lvl == vwap:
                vwap_tp_valid = True
            log.info(f"  [TP2] Structural target found: ${tp2_price:.2f} (R:R {rr:.1f}:1)")
            break

    # Apply Fallbacks if structural targets weren't found or weren't far enough
    if direction == "LONG":
        if not tp1_price:
            tp1_price = entry_price + sl_distance * fallback_tp1_rr
            log.info(f"  [TP1] Fallback applied: ${tp1_price:.2f} (R:R {fallback_tp1_rr:.1f}:1)")
        if not tp2_price:
            tp2_price = entry_price + sl_distance * fallback_tp2_rr
            log.info(f"  [TP2] Fallback applied: ${tp2_price:.2f} (R:R {fallback_tp2_rr:.1f}:1)")
    else:
        if not tp1_price:
            tp1_price = entry_price - sl_distance * fallback_tp1_rr
            log.info(f"  [TP1] Fallback applied: ${tp1_price:.2f} (R:R {fallback_tp1_rr:.1f}:1)")
        if not tp2_price:
            tp2_price = entry_price - sl_distance * fallback_tp2_rr
            log.info(f"  [TP2] Fallback applied: ${tp2_price:.2f} (R:R {fallback_tp2_rr:.1f}:1)")

    sl_distance_pct = (sl_distance / entry_price * 100) if entry_price > 0 else 0
    tp2_distance = abs(tp2_price - entry_price)
    actual_tp2_rr = tp2_distance / sl_distance if sl_distance > 0 else 0

    return {
        "entry_price": entry_price,
        "sl_price": sl_price,
        "tp1_price": tp1_price,
        "tp2_price": tp2_price,
        "sl_distance": sl_distance,
        "sl_distance_pct": round(sl_distance_pct, 4),
        "rr_ratio": round(actual_tp2_rr, 2),  # Use TP2 for the main R:R reference
        "vwap_tp_valid": vwap_tp_valid,
        "zone_boundary": zone_boundary,
    }

