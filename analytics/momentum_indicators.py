"""
Momentum Indicators - RSI, MACD, Stochastic

Professional momentum analysis for trend strength and reversal detection.

Indicators:
- RSI (Relative Strength Index): Overbought/oversold detection
- MACD (Moving Average Convergence Divergence): Trend momentum
- Stochastic: Price position within range
- Rate of Change (ROC): Velocity of price movement
"""

import statistics
from typing import List, Dict, Optional
from utils.logger import get_logger

log = get_logger("analytics.momentum")


class MomentumIndicators:
    """
    Professional momentum indicator suite.
    
    Complements CVD momentum with traditional technical indicators.
    """
    
    def __init__(self):
        log.info("MomentumIndicators initialized")
    
    def calculate_all(self, candles: List[Dict]) -> Dict:
        """
        Calculate all momentum indicators.
        
        Returns:
            {
                'rsi': {...},
                'macd': {...},
                'stochastic': {...},
                'roc': {...},
                'momentum_score': float,  # Composite 0-100
                'signal': str,  # 'BULLISH', 'BEARISH', 'NEUTRAL'
            }
        """
        if len(candles) < 50:
            return {}
        
        rsi = self.calculate_rsi(candles)
        macd = self.calculate_macd(candles)
        stoch = self.calculate_stochastic(candles)
        roc = self.calculate_roc(candles)
        
        # Composite momentum score
        momentum_score = self._calculate_composite_score(rsi, macd, stoch, roc)
        signal = self._generate_signal(momentum_score, rsi, macd)
        
        return {
            'rsi': rsi,
            'macd': macd,
            'stochastic': stoch,
            'roc': roc,
            'momentum_score': round(momentum_score, 1),
            'signal': signal,
        }
    
    def calculate_rsi(self, candles: List[Dict], period: int = 14) -> Dict:
        """
        Calculate RSI (Relative Strength Index).
        
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        
        Interpretation:
        - RSI > 70: Overbought
        - RSI < 30: Oversold
        - RSI 50: Neutral
        """
        if len(candles) < period + 1:
            return {}
        
        closes = [c['close'] for c in candles]
        
        # Calculate price changes
        changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        gains = [max(0, change) for change in changes]
        losses = [abs(min(0, change)) for change in changes]
        
        # Initial averages
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # Smoothed averages (Wilder's method)
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Classify
        if rsi > 70:
            zone = "OVERBOUGHT"
            signal = "BEARISH"
        elif rsi < 30:
            zone = "OVERSOLD"
            signal = "BULLISH"
        else:
            zone = "NEUTRAL"
            signal = "NEUTRAL"
        
        return {
            'value': round(rsi, 2),
            'zone': zone,
            'signal': signal,
            'period': period,
        }
    
    def calculate_macd(self, candles: List[Dict],
                       fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        MACD Line = EMA(12) - EMA(26)
        Signal Line = EMA(9) of MACD Line
        Histogram = MACD Line - Signal Line
        
        Interpretation:
        - MACD > Signal: Bullish
        - MACD < Signal: Bearish
        - Histogram expanding: Momentum increasing
        - Histogram contracting: Momentum decreasing
        """
        if len(candles) < slow + signal:
            return {}
        
        closes = [c['close'] for c in candles]
        
        ema_fast = self._calculate_ema(closes, fast)
        ema_slow = self._calculate_ema(closes, slow)
        
        macd_line = ema_fast - ema_slow
        
        # Calculate signal line (EMA of MACD)
        macd_values = []
        for i in range(len(closes)):
            if i >= slow - 1:
                fast_val = self._calculate_ema(closes[:i+1], fast)
                slow_val = self._calculate_ema(closes[:i+1], slow)
                macd_values.append(fast_val - slow_val)
        
        if len(macd_values) < signal:
            return {}
        
        signal_line = self._calculate_ema(macd_values, signal)
        histogram = macd_line - signal_line
        
        # Previous histogram for trend
        if len(macd_values) >= signal + 1:
            prev_signal = self._calculate_ema(macd_values[:-1], signal)
            prev_histogram = macd_values[-2] - prev_signal
            histogram_trend = "EXPANDING" if abs(histogram) > abs(prev_histogram) else "CONTRACTING"
        else:
            histogram_trend = "UNKNOWN"
        
        # Signal
        if macd_line > signal_line and histogram > 0:
            macd_signal = "BULLISH"
        elif macd_line < signal_line and histogram < 0:
            macd_signal = "BEARISH"
        else:
            macd_signal = "NEUTRAL"
        
        return {
            'macd_line': round(macd_line, 4),
            'signal_line': round(signal_line, 4),
            'histogram': round(histogram, 4),
            'histogram_trend': histogram_trend,
            'signal': macd_signal,
        }
    
    def calculate_stochastic(self, candles: List[Dict], period: int = 14) -> Dict:
        """
        Calculate Stochastic Oscillator.
        
        %K = (Current Close - Lowest Low) / (Highest High - Lowest Low) * 100
        %D = 3-period SMA of %K
        
        Interpretation:
        - %K > 80: Overbought
        - %K < 20: Oversold
        """
        if len(candles) < period:
            return {}
        
        recent = candles[-period:]
        
        current_close = recent[-1]['close']
        lowest_low = min(c['low'] for c in recent)
        highest_high = max(c['high'] for c in recent)
        
        if highest_high == lowest_low:
            return {}
        
        k = (current_close - lowest_low) / (highest_high - lowest_low) * 100
        
        # %D (3-period SMA of %K)
        if len(candles) >= period + 2:
            k_values = []
            for i in range(3):
                window = candles[-(period + 2 - i):-(2 - i) if i < 2 else None]
                c_close = window[-1]['close']
                l_low = min(c['low'] for c in window)
                h_high = max(c['high'] for c in window)
                if h_high != l_low:
                    k_values.append((c_close - l_low) / (h_high - l_low) * 100)
            
            d = sum(k_values) / len(k_values) if k_values else k
        else:
            d = k
        
        # Signal
        if k > 80:
            zone = "OVERBOUGHT"
            stoch_signal = "BEARISH"
        elif k < 20:
            zone = "OVERSOLD"
            stoch_signal = "BULLISH"
        else:
            zone = "NEUTRAL"
            stoch_signal = "NEUTRAL"
        
        return {
            'k': round(k, 2),
            'd': round(d, 2),
            'zone': zone,
            'signal': stoch_signal,
        }
    
    def calculate_roc(self, candles: List[Dict], period: int = 12) -> Dict:
        """
        Calculate Rate of Change (ROC).
        
        ROC = (Current Price - Price N periods ago) / Price N periods ago * 100
        
        Measures velocity of price movement.
        """
        if len(candles) < period + 1:
            return {}
        
        current = candles[-1]['close']
        previous = candles[-(period + 1)]['close']
        
        roc = (current - previous) / previous * 100
        
        # Signal
        if roc > 5:
            roc_signal = "STRONG_BULLISH"
        elif roc > 0:
            roc_signal = "BULLISH"
        elif roc < -5:
            roc_signal = "STRONG_BEARISH"
        elif roc < 0:
            roc_signal = "BEARISH"
        else:
            roc_signal = "NEUTRAL"
        
        return {
            'value': round(roc, 2),
            'signal': roc_signal,
            'period': period,
        }
    
    def _calculate_ema(self, values: List[float], period: int) -> float:
        """Calculate Exponential Moving Average."""
        if len(values) < period:
            return sum(values) / len(values)
        
        multiplier = 2 / (period + 1)
        ema = sum(values[:period]) / period
        
        for value in values[period:]:
            ema = (value - ema) * multiplier + ema
        
        return ema
    
    def _calculate_composite_score(self, rsi: Dict, macd: Dict,
                                   stoch: Dict, roc: Dict) -> float:
        """
        Calculate composite momentum score (0-100).
        
        Combines all indicators into single score.
        """
        score = 50  # Neutral baseline
        
        # RSI contribution
        if rsi:
            rsi_val = rsi['value']
            if rsi_val > 70:
                score += (rsi_val - 70) / 30 * 15  # Max +15
            elif rsi_val < 30:
                score -= (30 - rsi_val) / 30 * 15  # Max -15
        
        # MACD contribution
        if macd:
            if macd['signal'] == 'BULLISH':
                score += 10
            elif macd['signal'] == 'BEARISH':
                score -= 10
        
        # Stochastic contribution
        if stoch:
            k_val = stoch['k']
            if k_val > 80:
                score += (k_val - 80) / 20 * 10
            elif k_val < 20:
                score -= (20 - k_val) / 20 * 10
        
        # ROC contribution
        if roc:
            roc_val = roc['value']
            score += min(15, max(-15, roc_val))
        
        return max(0, min(100, score))
    
    def _generate_signal(self, momentum_score: float,
                        rsi: Dict, macd: Dict) -> str:
        """Generate overall momentum signal."""
        if momentum_score > 65:
            return "BULLISH"
        elif momentum_score < 35:
            return "BEARISH"
        else:
            return "NEUTRAL"
