"""
STEP 4: Order Flow for Confirmation (5M Timeframe)

"Not just one side dying — the other must take control."

Using REAL order book + trade flow data (Bookmap-like analysis):
1. Weak side gets absorbed or exhausted
2. Strong side steps in aggressively
3. Price holds above/below trigger

For LONGS:
  - Sellers stop hitting aggressively
  - Demand absorbs passive offers
  - Aggressive buyers show up → delta flip (positive)
  - Price holds above trigger

For SHORTS:
  - Buyers exhaust or get absorbed
  - Supply defends
  - Aggressive sellers step in → delta flip (negative)
  - Price holds below trigger
"""

from typing import Dict, Optional
from data.orderbook import OrderBookManager
from data.trade_flow import TradeFlowAnalyzer
from config import STRATEGY
from utils.logger import get_logger

log = get_logger("strategy.step4")


def confirm_orderflow(symbol: str, direction: str,
                      orderbook: OrderBookManager,
                      trade_flow: TradeFlowAnalyzer) -> Optional[Dict]:
    """
    STEP 4: Confirm control shift using order flow analysis.

    Args:
        symbol: e.g., 'BTCUSDT'
        direction: From Step 3 — 'LONG' or 'SHORT'
        orderbook: OrderBookManager with current data
        trade_flow: TradeFlowAnalyzer with current data

    Returns:
        {
            'control_shift_confirmed': bool,
            'signals': List[str],
            'score': int (0-100),
            'delta_data': dict,
            'imbalance_data': dict,
            'absorption_data': dict,
            'cluster_data': dict,
            'aggressive_flow': dict,
            'consolidation_detected': bool,
            'structure_shift_detected': bool,
            'timeframe': '5M',
        }
    """
    signals = []
    score = 0

    # ─── 1. Delta Analysis — detect delta flip ───────────────────────
    delta_data = trade_flow.get_delta(symbol, window_minutes=5)
    delta_flip = trade_flow.detect_delta_flip(symbol)

    if direction == "LONG":
        if delta_data.get("delta", 0) > 0:
            signals.append("POSITIVE_DELTA")
            score += 15
        if delta_flip.get("flip_detected") and delta_flip.get("flip_direction") == "POSITIVE":
            signals.append("DELTA_FLIP_BULLISH")
            score += 25  # Strong signal
    else:  # SHORT
        if delta_data.get("delta", 0) < 0:
            signals.append("NEGATIVE_DELTA")
            score += 15
        if delta_flip.get("flip_detected") and delta_flip.get("flip_direction") == "NEGATIVE":
            signals.append("DELTA_FLIP_BEARISH")
            score += 25

    # ─── 2. Absorption Detection ──────────────────────────────────────
    absorption_data = orderbook.detect_absorption(symbol)

    if absorption_data.get("detected"):
        if direction == "LONG" and absorption_data.get("bid_absorption"):
            # Bids absorbing sell pressure = strong support
            signals.append("BID_ABSORPTION")
            score += 20
        elif direction == "SHORT" and absorption_data.get("ask_absorption"):
            # Asks absorbing buy pressure = strong resistance
            signals.append("ASK_ABSORPTION")
            score += 20

    # ─── 3. Imbalance Analysis ────────────────────────────────────────
    imbalance_data = orderbook.get_imbalance(symbol)
    imbalance_threshold = STRATEGY["imbalance_threshold"]

    if imbalance_data:
        if direction == "LONG" and imbalance_data.get("dominance") == "BUYERS":
            signals.append("BUYER_DOMINANCE")
            score += 15
        elif direction == "SHORT" and imbalance_data.get("dominance") == "SELLERS":
            signals.append("SELLER_DOMINANCE")
            score += 15

        top10_ratio = imbalance_data.get("top_10_ratio", 1)
        if direction == "LONG" and top10_ratio > imbalance_threshold:
            signals.append("STRONG_BID_IMBALANCE")
            score += 10
        elif direction == "SHORT" and top10_ratio < (1 / imbalance_threshold):
            signals.append("STRONG_ASK_IMBALANCE")
            score += 10

    # ─── 4. Trade Cluster Detection (Bookmap Bubbles) ─────────────────
    clusters = trade_flow.get_clusters(symbol, lookback_minutes=10)
    cluster_data = {"buy_clusters": 0, "sell_clusters": 0, "total": len(clusters)}

    for cluster in clusters:
        if cluster.get("is_aggressive_buy"):
            cluster_data["buy_clusters"] += 1
        else:
            cluster_data["sell_clusters"] += 1

    if direction == "LONG" and cluster_data["buy_clusters"] > cluster_data["sell_clusters"]:
        signals.append("AGGRESSIVE_BUY_CLUSTERS")
        score += 15
    elif direction == "SHORT" and cluster_data["sell_clusters"] > cluster_data["buy_clusters"]:
        signals.append("AGGRESSIVE_SELL_CLUSTERS")
        score += 15

    # ─── 5. Aggressive Flow Analysis ──────────────────────────────────
    aggressive_flow = trade_flow.get_aggressive_flow(symbol, window_minutes=5)

    if aggressive_flow:
        if direction == "LONG" and aggressive_flow.get("aggressiveness") == "BUYERS_AGGRESSIVE":
            signals.append("BUYERS_STEPPING_IN")
            score += 15
        elif direction == "SHORT" and aggressive_flow.get("aggressiveness") == "SELLERS_AGGRESSIVE":
            signals.append("SELLERS_STEPPING_IN")
            score += 15

    # ─── 6. Pressure Analysis ─────────────────────────────────────────
    pressure = trade_flow.get_pressure(symbol)
    if pressure:
        if direction == "LONG" and pressure.get("pressure") == "BUY_PRESSURE":
            signals.append("SUSTAINED_BUY_PRESSURE")
            score += 10
        elif direction == "SHORT" and pressure.get("pressure") == "SELL_PRESSURE":
            signals.append("SUSTAINED_SELL_PRESSURE")
            score += 10
        elif direction == "LONG" and pressure.get("pressure") == "BUY_REVERSAL":
            signals.append("BUY_REVERSAL_DEVELOPING")
            score += 5

    # ─── 7. Wall Detection ────────────────────────────────────────────
    walls = orderbook.get_large_orders(symbol)
    if walls:
        if direction == "LONG" and walls.get("total_bid_walls", 0) > 0:
            signals.append("BID_WALL_SUPPORT")
            score += 5
        elif direction == "SHORT" and walls.get("total_ask_walls", 0) > 0:
            signals.append("ASK_WALL_RESISTANCE")
            score += 5

    # ─── FINAL: Determine control shift ──────────────────────────────
    # Control shift confirmed if score >= 50 (multiple signals align)
    control_shift_confirmed = score >= 50

    log.info(
        f"STEP 4 result: score={score}/100, confirmed={control_shift_confirmed}, "
        f"signals={signals}"
    )

    return {
        "control_shift_confirmed": control_shift_confirmed,
        "signals": signals,
        "score": min(100, score),
        "delta_data": delta_data,
        "delta_flip": delta_flip,
        "imbalance_data": imbalance_data,
        "absorption_data": absorption_data,
        "cluster_data": cluster_data,
        "aggressive_flow": aggressive_flow,
        "pressure": pressure,
        "walls": walls,
        "timeframe": "5M",
    }
