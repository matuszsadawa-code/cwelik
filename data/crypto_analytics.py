"""
Crypto-Specific Analytics — Liquidation Zones, Funding, OI, Liquidity Sweeps.

Crypto-native data not available in traditional markets:
- Liquidation Zone Mapping: Estimated liquidation clusters by leverage
- Funding Rate Analysis: Sentiment and cost-of-carry indicator
- Open Interest Analysis: Positioning changes and crowd behavior
- Long/Short Ratio: Retail vs smart money positioning
- Liquidity Sweep Detection: Price wicking into liquidation zones
- Liquidation Cascade Detection: Chain liquidation events

"In crypto, liquidations ARE the liquidity. Price hunts leveraged positions."
"""

import time
import math
from typing import List, Dict, Optional
from collections import defaultdict
from datetime import datetime

from data.bybit_client import BybitClient
from data.binance_client import BinanceClient
from utils.logger import get_logger

log = get_logger("data.crypto")


class CryptoAnalytics:
    """
    Crypto-specific market analytics.

    Combines liquidation mapping, funding analysis, OI tracking,
    and liquidation cascade detection for crypto futures.
    """

    def __init__(self, bybit: BybitClient, binance: BinanceClient):
        self.bybit = bybit
        self.binance = binance

        # Liquidation zone estimates per symbol
        self._liquidation_zones: Dict[str, Dict] = {}
        # Funding rate history
        self._funding_history: Dict[str, List[Dict]] = defaultdict(list)
        # OI history
        self._oi_history: Dict[str, List[Dict]] = defaultdict(list)
        # Long/short ratio history
        self._ls_history: Dict[str, List[Dict]] = defaultdict(list)
        # Detected sweeps
        self._sweeps: Dict[str, List[Dict]] = defaultdict(list)

        log.info("CryptoAnalytics initialized")

    # ═══════════════════════════════════════════════════════════════════
    # LIQUIDATION ZONE MAPPING
    # ═══════════════════════════════════════════════════════════════════

    def estimate_liquidation_zones(self, symbol: str,
                                    current_price: float,
                                    leverages: List[int] = None) -> Dict:
        """
        Estimate liquidation price zones for common leverage levels.

        In crypto futures, leveraged positions get liquidated when price
        moves against them by (1/leverage)%. These zones act as magnets
        because:
        1. Cascading liquidations push price further
        2. Smart money targets these zones for easy fills
        3. They represent resting stop orders

        Example at $100,000 BTC:
        - 100x longs liquidated ~$99,000 (1% move)
        - 50x longs liquidated ~$98,000 (2% move)
        - 25x longs liquidated ~$96,000 (4% move)
        - 10x longs liquidated ~$90,000 (10% move)
        """
        if leverages is None:
            leverages = [100, 75, 50, 25, 20, 15, 10, 5, 3]

        long_liquidations = []
        short_liquidations = []

        for lev in leverages:
            # Maintenance margin ~0.5% for most exchanges
            maintenance_pct = 0.5

            # Long liquidation: price drops by ~(1/lev - maintenance) * 100%
            long_liq_pct = (1 / lev) * 100 - maintenance_pct
            long_liq_price = current_price * (1 - long_liq_pct / 100)

            # Short liquidation: price rises by ~(1/lev - maintenance) * 100%
            short_liq_pct = (1 / lev) * 100 - maintenance_pct
            short_liq_price = current_price * (1 + short_liq_pct / 100)

            # Estimate relative density (more people use lower leverage)
            density = self._estimate_leverage_density(lev)

            long_liquidations.append({
                "leverage": lev,
                "liquidation_price": round(long_liq_price, 2),
                "distance_pct": round(long_liq_pct, 3),
                "estimated_density": density,
                "zone_low": round(long_liq_price * 0.999, 2),
                "zone_high": round(long_liq_price * 1.001, 2),
            })

            short_liquidations.append({
                "leverage": lev,
                "liquidation_price": round(short_liq_price, 2),
                "distance_pct": round(short_liq_pct, 3),
                "estimated_density": density,
                "zone_low": round(short_liq_price * 0.999, 2),
                "zone_high": round(short_liq_price * 1.001, 2),
            })

        # Identify highest-density zones (most liquidations clustered)
        all_zones = long_liquidations + short_liquidations
        hottest = sorted(all_zones, key=lambda z: -z["estimated_density"])[:5]

        result = {
            "current_price": current_price,
            "long_liquidation_zones": long_liquidations,
            "short_liquidation_zones": short_liquidations,
            "hottest_zones": hottest,
            "nearest_long_liq": long_liquidations[0] if long_liquidations else None,
            "nearest_short_liq": short_liquidations[0] if short_liquidations else None,
        }

        self._liquidation_zones[symbol] = result
        return result

    def detect_liquidation_sweep(self, symbol: str, candles: List[Dict],
                                  current_price: float) -> List[Dict]:
        """
        Detect Liquidity Sweeps into liquidation zones.

        A sweep occurs when price rapidly wicks into a liquidation zone
        and then reverses. This is smart money hunting liquidations:

        1. Price moves to liquidation cluster
        2. Cascading liquidations fire (forced market orders)
        3. Smart money absorbs the forced flow at favorable prices
        4. Price reverses as selling/buying pressure exhausts

        The wick into and reversal from a liquidation zone is
        one of the highest-probability entry signals in crypto.
        """
        zones = self._liquidation_zones.get(symbol)
        if not zones or not candles or len(candles) < 5:
            return []

        sweeps = []

        for i in range(2, len(candles)):
            c = candles[i]
            c_prev = candles[i - 1]

            # Check long liquidation sweeps (price drops into zone, then bounces)
            for lz in zones.get("long_liquidation_zones", []):
                zone_price = lz["liquidation_price"]
                zone_low = lz["zone_low"]
                zone_high = lz["zone_high"]

                # Wick into zone: low touches zone but close is above
                if c["low"] <= zone_high and c["close"] > zone_high:
                    wick_depth = (c["close"] - c["low"]) / c["close"] * 100
                    reversal = c["close"] > c["open"]

                    sweeps.append({
                        "type": "LONG_LIQ_SWEEP",
                        "leverage_targeted": lz["leverage"],
                        "zone_price": zone_price,
                        "sweep_low": c["low"],
                        "close_price": c["close"],
                        "wick_depth_pct": round(wick_depth, 4),
                        "reversed": reversal,
                        "volume": c["volume"],
                        "index": i,
                        "time": c.get("open_time", 0),
                        "signal": "BULLISH" if reversal else "CONTINUATION_DOWN",
                        "description": (
                            f"Price swept {lz['leverage']}x long liquidations at "
                            f"${zone_price:.0f} and reversed → bullish"
                            if reversal else
                            f"Price swept {lz['leverage']}x long liquidations — "
                            f"cascade may continue"
                        ),
                    })

            # Check short liquidation sweeps (price spikes into zone, then drops)
            for sz in zones.get("short_liquidation_zones", []):
                zone_price = sz["liquidation_price"]
                zone_low = sz["zone_low"]
                zone_high = sz["zone_high"]

                if c["high"] >= zone_low and c["close"] < zone_low:
                    wick_depth = (c["high"] - c["close"]) / c["close"] * 100
                    reversal = c["close"] < c["open"]

                    sweeps.append({
                        "type": "SHORT_LIQ_SWEEP",
                        "leverage_targeted": sz["leverage"],
                        "zone_price": zone_price,
                        "sweep_high": c["high"],
                        "close_price": c["close"],
                        "wick_depth_pct": round(wick_depth, 4),
                        "reversed": reversal,
                        "volume": c["volume"],
                        "index": i,
                        "time": c.get("open_time", 0),
                        "signal": "BEARISH" if reversal else "CONTINUATION_UP",
                        "description": (
                            f"Price swept {sz['leverage']}x short liquidations at "
                            f"${zone_price:.0f} and reversed → bearish"
                            if reversal else
                            f"Price swept {sz['leverage']}x short liquidations — "
                            f"cascade may continue"
                        ),
                    })

        self._sweeps[symbol] = sweeps
        return sweeps

    def detect_liquidation_cascade(self, symbol: str,
                                    trades: List[Dict],
                                    candles: List[Dict]) -> Dict:
        """
        Detect liquidation cascades — chain liquidation events.

        Signs of a cascade:
        - Rapid price movement in one direction
        - Spike in volume (forced liquidation = market orders)
        - Increasing trade velocity
        - Long lower/upper wicks followed by continuation

        Cascades create the biggest moves in crypto. Detecting them
        early = catching the move.
        """
        if not trades or not candles or len(candles) < 5:
            return {"cascade_detected": False}

        recent_candles = candles[-5:]

        # Check for directional acceleration
        moves = []
        for i in range(1, len(recent_candles)):
            move_pct = (recent_candles[i]["close"] - recent_candles[i-1]["close"]) / recent_candles[i-1]["close"] * 100
            moves.append(move_pct)

        # All moves same direction + accelerating = cascade
        all_down = all(m < 0 for m in moves)
        all_up = all(m > 0 for m in moves)
        accelerating = len(moves) >= 3 and abs(moves[-1]) > abs(moves[-2]) > abs(moves[-3])

        # Volume spike
        avg_vol = sum(c["volume"] for c in candles[:-5]) / max(1, len(candles) - 5) if len(candles) > 5 else 1
        recent_vol = sum(c["volume"] for c in recent_candles) / len(recent_candles)
        vol_spike = recent_vol / avg_vol if avg_vol > 0 else 1

        # Trade velocity
        cutoff = time.time() * 1000 - 60 * 1000  # Last minute
        recent_trades = [t for t in trades if t.get("time", 0) > cutoff]
        velocity = len(recent_trades)

        cascade_score = 0
        if all_down or all_up:
            cascade_score += 30
        if accelerating:
            cascade_score += 30
        if vol_spike > 2:
            cascade_score += 20
        if velocity > 100:
            cascade_score += 20

        cascade_detected = cascade_score >= 60

        return {
            "cascade_detected": cascade_detected,
            "cascade_score": cascade_score,
            "direction": "LONG_CASCADE" if all_down else "SHORT_CASCADE" if all_up else "NONE",
            "volume_spike": round(vol_spike, 2),
            "accelerating": accelerating,
            "trade_velocity": velocity,
            "total_move_pct": round(sum(moves), 4) if moves else 0,
            "interpretation": (
                "🚨 LIQUIDATION CASCADE DETECTED — forced selling driving price down"
                if cascade_detected and all_down else
                "🚨 SHORT SQUEEZE CASCADE — forced buying driving price up"
                if cascade_detected and all_up else
                "No cascade detected"
            ),
        }

    # ═══════════════════════════════════════════════════════════════════
    # FUNDING RATE ANALYSIS
    # ═══════════════════════════════════════════════════════════════════

    def update_funding(self, symbol: str):
        """
        Update funding rate analysis.

        Funding rate = periodic payment between longs and shorts.
        - Positive funding: Longs pay shorts → market over-leveraged long
        - Negative funding: Shorts pay longs → market over-leveraged short
        - Extreme funding = contrarian signal (crowded trade)
        """
        bb_funding = self.bybit.get_funding_rate(symbol)
        bn_funding = self.binance.get_funding_rate(symbol)

        rates = []
        if bb_funding:
            rates.append(bb_funding.get("funding_rate", 0))
        if bn_funding:
            rates.append(bn_funding.get("funding_rate", 0))

        if not rates:
            return

        avg_rate = sum(rates) / len(rates)
        self._funding_history[symbol].append({
            "timestamp": time.time(),
            "rate": avg_rate,
            "bybit_rate": bb_funding.get("funding_rate", 0) if bb_funding else None,
            "binance_rate": bn_funding.get("funding_rate", 0) if bn_funding else None,
        })

        # Keep last 100 readings
        if len(self._funding_history[symbol]) > 100:
            self._funding_history[symbol] = self._funding_history[symbol][-100:]

    def get_funding_analysis(self, symbol: str) -> Dict:
        """Get funding rate analysis with sentiment interpretation."""
        history = self._funding_history.get(symbol, [])
        if not history:
            return {"rate": 0, "sentiment": "UNKNOWN"}

        current = history[-1]["rate"]
        avg_rate = sum(h["rate"] for h in history) / len(history) if history else 0

        # Annualized funding cost
        annualized = current * 3 * 365 * 100  # 3 payments/day * 365 days

        # Extreme detection
        if current > 0.001:  # >0.1%
            sentiment = "EXTREME_BULLISH"
            contrarian = "Crowded longs — contrarian BEARISH signal"
        elif current > 0.0005:
            sentiment = "MODERATELY_BULLISH"
            contrarian = "Longs paying — moderate bullish bias"
        elif current < -0.001:
            sentiment = "EXTREME_BEARISH"
            contrarian = "Crowded shorts — contrarian BULLISH signal"
        elif current < -0.0005:
            sentiment = "MODERATELY_BEARISH"
            contrarian = "Shorts paying — moderate bearish bias"
        else:
            sentiment = "NEUTRAL"
            contrarian = "Balanced positioning"

        return {
            "current_rate": round(current, 6),
            "avg_rate": round(avg_rate, 6),
            "annualized_pct": round(annualized, 2),
            "sentiment": sentiment,
            "contrarian_signal": contrarian,
            "is_extreme": abs(current) > 0.001,
            "readings": len(history),
        }

    # ═══════════════════════════════════════════════════════════════════
    # OPEN INTEREST ANALYSIS
    # ═══════════════════════════════════════════════════════════════════

    def update_open_interest(self, symbol: str):
        """
        Update Open Interest tracking.

        OI = total open positions in the market.
        - Rising OI + rising price → new longs entering (bullish)
        - Rising OI + falling price → new shorts entering (bearish)
        - Falling OI + rising price → shorts closing (weak rally)
        - Falling OI + falling price → longs closing (weak selloff)
        """
        bb_oi = self.bybit.get_open_interest(symbol, limit=1)
        bn_oi = self.binance.get_open_interest(symbol)

        oi_values = []
        if bb_oi:
            oi_values.append(bb_oi[0]["open_interest"] if isinstance(bb_oi, list) and bb_oi else 0)
        if bn_oi:
            oi_values.append(bn_oi.get("open_interest", 0))

        total_oi = sum(oi_values)
        if total_oi > 0:
            self._oi_history[symbol].append({
                "timestamp": time.time(),
                "oi": total_oi,
                "bybit_oi": oi_values[0] if len(oi_values) > 0 else 0,
                "binance_oi": oi_values[1] if len(oi_values) > 1 else 0,
            })

        if len(self._oi_history[symbol]) > 100:
            self._oi_history[symbol] = self._oi_history[symbol][-100:]

    def get_oi_analysis(self, symbol: str,
                         price_change_pct: float = 0) -> Dict:
        """Get OI analysis with price correlation interpretation."""
        history = self._oi_history.get(symbol, [])
        if len(history) < 2:
            return {"oi": 0, "interpretation": "INSUFFICIENT_DATA"}

        current_oi = history[-1]["oi"]
        prev_oi = history[-2]["oi"] if len(history) > 1 else current_oi
        oldest_oi = history[0]["oi"]

        oi_change_pct = ((current_oi - prev_oi) / prev_oi * 100) if prev_oi > 0 else 0
        oi_trend_pct = ((current_oi - oldest_oi) / oldest_oi * 100) if oldest_oi > 0 else 0
        oi_rising = oi_change_pct > 0.5

        # Interpret with price direction
        if oi_rising and price_change_pct > 0:
            interpretation = "NEW_LONGS"
            signal = "BULLISH"
        elif oi_rising and price_change_pct < 0:
            interpretation = "NEW_SHORTS"
            signal = "BEARISH"
        elif not oi_rising and price_change_pct > 0:
            interpretation = "SHORT_COVERING"
            signal = "WEAK_BULLISH"
        elif not oi_rising and price_change_pct < 0:
            interpretation = "LONG_CLOSING"
            signal = "WEAK_BEARISH"
        else:
            interpretation = "NEUTRAL"
            signal = "NEUTRAL"

        return {
            "current_oi": round(current_oi, 2),
            "oi_change_pct": round(oi_change_pct, 4),
            "oi_trend_pct": round(oi_trend_pct, 4),
            "oi_rising": oi_rising,
            "interpretation": interpretation,
            "signal": signal,
            "readings": len(history),
        }

    # ═══════════════════════════════════════════════════════════════════
    # LONG/SHORT RATIO
    # ═══════════════════════════════════════════════════════════════════

    def update_long_short_ratio(self, symbol: str):
        """
        Update Long/Short ratio data.

        Shows what percentage of traders are long vs short.
        Contrarian indicator — extreme readings = potential reversal.
        """
        try:
            ls_data = self.binance.get_long_short_ratio(symbol, period="5m", limit=10)
            if ls_data:
                for item in ls_data:
                    self._ls_history[symbol].append(item)
                # Deduplicate by timestamp
                seen = set()
                unique = []
                for item in self._ls_history[symbol]:
                    ts = item.get("timestamp", 0)
                    if ts not in seen:
                        seen.add(ts)
                        unique.append(item)
                self._ls_history[symbol] = unique[-100:]
        except Exception as e:
            log.debug(f"L/S ratio update error for {symbol}: {e}")

    def get_long_short_analysis(self, symbol: str) -> Dict:
        """Get L/S ratio analysis with contrarian signals."""
        history = self._ls_history.get(symbol, [])
        if not history:
            return {"ratio": 1.0, "sentiment": "UNKNOWN"}

        latest = history[-1]
        ratio = latest.get("long_short_ratio", 1.0)
        long_pct = latest.get("long_account", 0.5)
        short_pct = latest.get("short_account", 0.5)

        # Trend
        if len(history) >= 5:
            recent_avg = sum(h.get("long_short_ratio", 1) for h in history[-5:]) / 5
            older_avg = sum(h.get("long_short_ratio", 1) for h in history[:5]) / min(5, len(history))
            trend = "INCREASING_LONGS" if recent_avg > older_avg * 1.05 else "INCREASING_SHORTS" if recent_avg < older_avg * 0.95 else "STABLE"
        else:
            trend = "INSUFFICIENT_DATA"

        # Contrarian signal at extremes
        if ratio > 2.0:
            contrarian = "EXTREME_LONG — contrarian SHORT signal"
        elif ratio > 1.5:
            contrarian = "HEAVY_LONG — caution for longs"
        elif ratio < 0.5:
            contrarian = "EXTREME_SHORT — contrarian LONG signal"
        elif ratio < 0.67:
            contrarian = "HEAVY_SHORT — caution for shorts"
        else:
            contrarian = "BALANCED"

        return {
            "ratio": round(ratio, 4),
            "long_pct": round(long_pct * 100, 2),
            "short_pct": round(short_pct * 100, 2),
            "trend": trend,
            "contrarian": contrarian,
            "is_extreme": ratio > 2.0 or ratio < 0.5,
        }

    # ═══════════════════════════════════════════════════════════════════
    # COMPREHENSIVE CRYPTO ANALYSIS
    # ═══════════════════════════════════════════════════════════════════

    def get_full_analysis(self, symbol: str, current_price: float,
                           candles: List[Dict] = None,
                           trades: List[Dict] = None) -> Dict:
        """
        Get complete crypto-specific analysis for a symbol.

        Combines all crypto-native indicators into one view.
        """
        # Update all data
        self.update_funding(symbol)
        self.update_open_interest(symbol)
        self.update_long_short_ratio(symbol)

        # Liquidation zones
        liq_zones = self.estimate_liquidation_zones(symbol, current_price)

        # Detect sweeps if candles available
        sweeps = []
        cascade = {"cascade_detected": False}
        if candles:
            sweeps = self.detect_liquidation_sweep(symbol, candles, current_price)
        if trades and candles:
            cascade = self.detect_liquidation_cascade(symbol, trades, candles)

        # Price change for OI interpretation
        price_change = 0
        if candles and len(candles) >= 2:
            price_change = (candles[-1]["close"] - candles[-2]["close"]) / candles[-2]["close"] * 100

        funding = self.get_funding_analysis(symbol)
        oi = self.get_oi_analysis(symbol, price_change)
        ls_ratio = self.get_long_short_analysis(symbol)

        # Composite signal
        bullish = 0
        bearish = 0

        if funding.get("sentiment") in ("EXTREME_BEARISH",):
            bullish += 1  # Contrarian
        elif funding.get("sentiment") in ("EXTREME_BULLISH",):
            bearish += 1  # Contrarian

        if oi.get("signal") == "BULLISH":
            bullish += 1
        elif oi.get("signal") == "BEARISH":
            bearish += 1

        if ls_ratio.get("is_extreme") and ls_ratio.get("ratio", 1) < 0.5:
            bullish += 1  # Contrarian
        elif ls_ratio.get("is_extreme") and ls_ratio.get("ratio", 1) > 2.0:
            bearish += 1  # Contrarian

        return {
            "symbol": symbol,
            "current_price": current_price,
            "liquidation_zones": liq_zones,
            "liquidation_sweeps": sweeps[-5:],
            "liquidation_cascade": cascade,
            "funding": funding,
            "open_interest": oi,
            "long_short_ratio": ls_ratio,
            "crypto_bias": "BULLISH" if bullish > bearish else "BEARISH" if bearish > bullish else "NEUTRAL",
            "bullish_crypto_signals": bullish,
            "bearish_crypto_signals": bearish,
        }

    def _estimate_leverage_density(self, leverage: int) -> float:
        """
        Estimate relative density of positions at each leverage tier.

        Based on exchange data patterns:
        - Most retail uses 10-25x
        - High-risk users use 50-100x
        - Conservative traders use 3-5x
        """
        density_map = {
            3: 5, 5: 10, 10: 25, 15: 20, 20: 18,
            25: 15, 50: 8, 75: 3, 100: 1,
        }
        return density_map.get(leverage, 5)
