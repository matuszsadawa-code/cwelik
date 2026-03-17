"""
VWAP Standard Deviation Bands - Professional Implementation

VWAP (Volume Weighted Average Price) with statistical bands.
Used by institutional traders for mean reversion and trend following.

Theory:
- VWAP = fair value based on volume
- Price tends to revert to VWAP
- Standard deviation bands show statistical extremes
- 68% of prices within 1σ, 95% within 2σ, 99.7% within 3σ

Trading Applications:
- Price at +2σ = overbought, potential short
- Price at -2σ = oversold, potential long
- Price crossing VWAP = trend change
- Bands expanding = volatility increasing
- Bands contracting = volatility decreasing

Based on TradingView VWAP Stdev Bands v2 Mod
"""

import statistics
from typing import List, Dict, Optional
from utils.logger import get_logger

log = get_logger("analytics.vwap_bands")


class VWAPBands:
    """
    VWAP with Standard Deviation Bands.
    
    Professional-grade implementation matching institutional standards.
    """
    
    def __init__(self, stdev_multipliers: List[float] = None):
        """
        Initialize VWAP Bands calculator.
        
        Args:
            stdev_multipliers: List of standard deviation multipliers
                              Default: [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
        """
        self.stdev_multipliers = stdev_multipliers or [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
        log.info(f"VWAPBands initialized with multipliers: {self.stdev_multipliers}")
    
    def calculate(self, candles: List[Dict], period: int = None) -> Dict:
        """
        Calculate VWAP and standard deviation bands.
        
        Args:
            candles: List of candle dicts with OHLCV
            period: Lookback period (None = all candles, session VWAP)
        
        Returns:
            {
                'vwap': float,
                'stdev': float,
                'bands': {
                    'upper_0.5sd': float,
                    'upper_1sd': float,
                    'upper_2sd': float,
                    'upper_3sd': float,
                    'lower_0.5sd': float,
                    'lower_1sd': float,
                    'lower_2sd': float,
                    'lower_3sd': float,
                },
                'current_price': float,
                'deviation_from_vwap': float,  # in standard deviations
                'zone': str,  # 'EXTREME_HIGH', 'HIGH', 'NORMAL', 'LOW', 'EXTREME_LOW'
                'signal': str,  # 'OVERBOUGHT', 'OVERSOLD', 'NEUTRAL'
            }
        """
        if not candles or len(candles) < 2:
            return self._empty_result()
        
        # Use specified period or all candles
        if period and period < len(candles):
            candles = candles[-period:]
        
        # Calculate VWAP
        vwap = self._calculate_vwap(candles)
        
        # Calculate standard deviation of price from VWAP
        stdev = self._calculate_stdev(candles, vwap)
        
        # Calculate bands
        bands = {}
        for mult in self.stdev_multipliers:
            bands[f'upper_{mult}sd'] = vwap + (stdev * mult)
            bands[f'lower_{mult}sd'] = vwap - (stdev * mult)
        
        # Current price analysis
        current_price = candles[-1]['close']
        deviation = (current_price - vwap) / stdev if stdev > 0 else 0
        
        # Classify zone
        zone = self._classify_zone(deviation)
        signal = self._generate_signal(deviation)
        
        return {
            'vwap': round(vwap, 2),
            'stdev': round(stdev, 4),
            'bands': {k: round(v, 2) for k, v in bands.items()},
            'current_price': round(current_price, 2),
            'deviation_from_vwap': round(deviation, 2),
            'deviation_pct': round((current_price - vwap) / vwap * 100, 2),
            'zone': zone,
            'signal': signal,
            'band_width_pct': round((bands['upper_2sd'] - bands['lower_2sd']) / vwap * 100, 2),
        }
    
    def _calculate_vwap(self, candles: List[Dict]) -> float:
        """
        Calculate Volume Weighted Average Price.
        
        VWAP = Σ(Typical Price × Volume) / Σ(Volume)
        Typical Price = (High + Low + Close) / 3
        """
        cumulative_tpv = 0  # Typical Price × Volume
        cumulative_volume = 0
        
        for candle in candles:
            typical_price = (candle['high'] + candle['low'] + candle['close']) / 3
            volume = candle['volume']
            
            cumulative_tpv += typical_price * volume
            cumulative_volume += volume
        
        if cumulative_volume == 0:
            return candles[-1]['close']
        
        return cumulative_tpv / cumulative_volume
    
    def _calculate_stdev(self, candles: List[Dict], vwap: float) -> float:
        """
        Calculate standard deviation of price from VWAP.
        
        Uses typical price for consistency with VWAP calculation.
        """
        if len(candles) < 2:
            return 0
        
        deviations = []
        for candle in candles:
            typical_price = (candle['high'] + candle['low'] + candle['close']) / 3
            deviations.append(typical_price - vwap)
        
        return statistics.stdev(deviations)
    
    def _classify_zone(self, deviation: float) -> str:
        """
        Classify current price zone based on standard deviations from VWAP.
        
        Zones:
        - EXTREME_HIGH: > +2σ (top 2.5%)
        - HIGH: +1σ to +2σ (top 16%)
        - NORMAL: -1σ to +1σ (middle 68%)
        - LOW: -2σ to -1σ (bottom 16%)
        - EXTREME_LOW: < -2σ (bottom 2.5%)
        """
        if deviation > 2.0:
            return "EXTREME_HIGH"
        elif deviation > 1.0:
            return "HIGH"
        elif deviation > -1.0:
            return "NORMAL"
        elif deviation > -2.0:
            return "LOW"
        else:
            return "EXTREME_LOW"
    
    def _generate_signal(self, deviation: float) -> str:
        """
        Generate trading signal based on deviation.
        
        Signals:
        - OVERBOUGHT: > +2σ (mean reversion short opportunity)
        - OVERSOLD: < -2σ (mean reversion long opportunity)
        - NEUTRAL: within ±2σ
        """
        if deviation > 2.0:
            return "OVERBOUGHT"
        elif deviation < -2.0:
            return "OVERSOLD"
        else:
            return "NEUTRAL"
    
    def _empty_result(self) -> Dict:
        """Return empty result structure."""
        return {
            'vwap': 0,
            'stdev': 0,
            'bands': {},
            'current_price': 0,
            'deviation_from_vwap': 0,
            'deviation_pct': 0,
            'zone': 'UNKNOWN',
            'signal': 'NEUTRAL',
            'band_width_pct': 0,
        }
    
    def get_band_touch_analysis(self, candles: List[Dict], period: int = 20) -> Dict:
        """
        Analyze how price interacts with VWAP bands.
        
        Returns:
            {
                'touches_upper_2sd': int,
                'touches_lower_2sd': int,
                'time_above_vwap_pct': float,
                'time_below_vwap_pct': float,
                'mean_reversion_count': int,  # times price returned to VWAP from extremes
            }
        """
        if len(candles) < period:
            return {}
        
        recent = candles[-period:]
        result = self.calculate(recent)
        vwap = result['vwap']
        upper_2sd = result['bands']['upper_2sd']
        lower_2sd = result['bands']['lower_2sd']
        
        touches_upper = 0
        touches_lower = 0
        time_above = 0
        time_below = 0
        mean_reversions = 0
        
        was_extreme = False
        
        for candle in recent:
            close = candle['close']
            high = candle['high']
            low = candle['low']
            
            # Count touches
            if high >= upper_2sd:
                touches_upper += 1
            if low <= lower_2sd:
                touches_lower += 1
            
            # Time above/below VWAP
            if close > vwap:
                time_above += 1
            elif close < vwap:
                time_below += 1
            
            # Mean reversion detection
            is_extreme = high >= upper_2sd or low <= lower_2sd
            if was_extreme and not is_extreme:
                mean_reversions += 1
            was_extreme = is_extreme
        
        return {
            'touches_upper_2sd': touches_upper,
            'touches_lower_2sd': touches_lower,
            'time_above_vwap_pct': round(time_above / len(recent) * 100, 1),
            'time_below_vwap_pct': round(time_below / len(recent) * 100, 1),
            'mean_reversion_count': mean_reversions,
            'band_respect': 'HIGH' if mean_reversions >= 2 else 'MEDIUM' if mean_reversions == 1 else 'LOW',
        }
