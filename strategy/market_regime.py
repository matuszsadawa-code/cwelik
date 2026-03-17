"""
Market Regime Detector — Adaptive strategy parameters.

Detects current market state and adjusts strategy dynamically:
- TRENDING: Follow trend, wider TPs, allow B-quality signals
- RANGING: Mean-reversion at boundaries, tighter TPs
- VOLATILE: Wider SLs, faster analysis cycles, A/A+ only
- QUIET: Reduce scanning frequency, save resources

"There is a time to trade and a time to observe."
"""

import time
import math
from typing import Dict, List, Optional
from collections import deque

from utils.logger import get_logger

log = get_logger("strategy.regime")


class MarketRegimeDetector:
    """
    Detects current market regime for adaptive strategy.
    
    Uses multiple indicators:
    - ADX (trend strength via directional movement)
    - ATR ratio (volatility relative to norm)
    - Range width (compression detection)
    - Volume regime (expanding vs contracting)
    """

    # Regime types
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    QUIET = "QUIET"

    def __init__(self):
        self._regimes: Dict[str, Dict] = {}
        self._history: Dict[str, deque] = {}
        log.info("MarketRegimeDetector initialized")

    def detect_regime(self, symbol: str, candles: List[Dict],
                       lookback: int = 20) -> Dict:
        """
        Detect current market regime from candle data.
        
        Returns regime info with adaptive parameters.
        """
        if not candles or len(candles) < lookback + 5:
            return {"regime": self.QUIET, "confidence": 0, "adx": 25.0, "adjustments": {}}

        recent = candles[-lookback:]

        # ─── ADX (Average Directional Index) ─────────────
        adx = self._calc_adx(candles, lookback)

        # ─── ATR Ratio (current vs historical) ────────────
        atr_current = self._calc_atr(recent[-5:])
        atr_historical = self._calc_atr(recent)
        atr_ratio = atr_current / atr_historical if atr_historical > 0 else 1.0

        # ─── Range Width ──────────────────────────────────
        highs = [c["high"] for c in recent]
        lows = [c["low"] for c in recent]
        range_pct = (max(highs) - min(lows)) / min(lows) * 100 if min(lows) > 0 else 0

        # ─── Volume Regime ────────────────────────────────
        vols = [c["volume"] for c in recent]
        avg_vol = sum(vols) / len(vols)
        recent_vol = sum(vols[-5:]) / 5
        vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1.0

        # ─── Regime Classification ────────────────────────
        if adx > 30 and atr_ratio > 0.8:
            regime = self.TRENDING
            confidence = min(100, adx * 2)
        elif atr_ratio > 1.8 or range_pct > 5:
            regime = self.VOLATILE
            confidence = min(100, atr_ratio * 50)
        elif adx < 20 and range_pct < 2:
            if vol_ratio < 0.6:
                regime = self.QUIET
                confidence = min(100, (1 - vol_ratio) * 100)
            else:
                regime = self.RANGING
                confidence = min(100, (1 - adx / 50) * 100)
        else:
            regime = self.RANGING
            confidence = 50

        # ─── Adaptive Parameters ──────────────────────────
        adjustments = self._get_adjustments(regime, adx, atr_ratio, vol_ratio)

        result = {
            "regime": regime,
            "confidence": round(confidence, 1),
            "adx": round(adx, 2),
            "atr_ratio": round(atr_ratio, 3),
            "range_pct": round(range_pct, 3),
            "vol_ratio": round(vol_ratio, 3),
            "adjustments": adjustments,
        }

        # Store and track changes
        prev = self._regimes.get(symbol, {}).get("regime")
        self._regimes[symbol] = result

        if symbol not in self._history:
            self._history[symbol] = deque(maxlen=100)
        self._history[symbol].append({
            "time": time.time(),
            "regime": regime,
        })

        if prev and prev != regime:
            log.info(f"[REGIME CHANGE] {symbol}: {prev} -> {regime} (ADX:{adx:.0f}, ATR:{atr_ratio:.2f})")

        return result

    def _get_adjustments(self, regime: str, adx: float,
                          atr_ratio: float, vol_ratio: float) -> Dict:
        """
        Get strategy parameter adjustments for current regime.
        
        Returns multipliers and overrides:
        - sl_multiplier: Adjust SL distance (>1 = wider)
        - tp_multiplier: Adjust TP distance (>1 = wider)
        - confidence_bonus: Add/subtract from signal confidence
        - min_quality: Override minimum quality threshold
        - scan_interval_mult: Adjust scan frequency
        """
        if regime == self.TRENDING:
            return {
                "sl_multiplier": 1.2,      # Wider SL to ride the trend
                "tp_multiplier": 1.5,      # Wider TPs for trend runs
                "confidence_bonus": 10,    # Trend alignment = bonus
                "min_quality": "B",        # Allow B signals (trend support)
                "scan_interval_mult": 1.0,
                "description": "TRENDING: Wider TPs, ride the move. Follow trend signals.",
            }
        elif regime == self.VOLATILE:
            return {
                "sl_multiplier": 1.5,      # Much wider SL for volatility
                "tp_multiplier": 0.8,      # Tighter TPs, take profits fast
                "confidence_bonus": -10,   # Volatile = uncertain
                "min_quality": "A",        # Only high-quality in volatile
                "scan_interval_mult": 0.5, # Scan more often
                "description": "VOLATILE: Tighter TPs, wider SLs. A+ and A only.",
            }
        elif regime == self.RANGING:
            return {
                "sl_multiplier": 0.8,      # Tighter SL at range boundaries
                "tp_multiplier": 0.7,      # Smaller TPs within range
                "confidence_bonus": 5,     # Range = good for mean-reversion
                "min_quality": "B",        # B signals OK at boundaries
                "scan_interval_mult": 1.0,
                "description": "RANGING: Mean-reversion at boundaries. Tight TPs.",
            }
        else:  # QUIET
            return {
                "sl_multiplier": 1.0,
                "tp_multiplier": 1.0,
                "confidence_bonus": -5,    # Less opportunity = less confidence
                "min_quality": "A",        # Only high-quality in quiet
                "scan_interval_mult": 2.0, # Scan less often
                "description": "QUIET: Low activity. Conserve. Only A+/A.",
            }

    def _calc_adx(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate Average Directional Index (simplified)."""
        if len(candles) < period + 1:
            return 25  # Default moderate

        plus_dm_sum = 0
        minus_dm_sum = 0
        tr_sum = 0

        for i in range(1, min(period + 1, len(candles))):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_high = candles[i - 1]["high"]
            prev_low = candles[i - 1]["low"]
            prev_close = candles[i - 1]["close"]

            # True Range
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_sum += tr

            # Directional Movement
            up_move = high - prev_high
            down_move = prev_low - low

            if up_move > down_move and up_move > 0:
                plus_dm_sum += up_move
            if down_move > up_move and down_move > 0:
                minus_dm_sum += down_move

        if tr_sum == 0:
            return 25

        plus_di = (plus_dm_sum / tr_sum) * 100
        minus_di = (minus_dm_sum / tr_sum) * 100

        di_sum = plus_di + minus_di
        if di_sum == 0:
            return 0

        dx = abs(plus_di - minus_di) / di_sum * 100
        return dx  # Simplified ADX ≈ DX for single period

    def _calc_atr(self, candles: List[Dict]) -> float:
        """Calculate Average True Range."""
        if len(candles) < 2:
            return 0

        tr_values = []
        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i - 1]["close"]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_values.append(tr)

        return sum(tr_values) / len(tr_values) if tr_values else 0

    def get_regime(self, symbol: str) -> Optional[Dict]:
        """Get cached regime for symbol."""
        return self._regimes.get(symbol)

    def get_regime_history(self, symbol: str) -> List[Dict]:
        """Get regime change history."""
        return list(self._history.get(symbol, []))
