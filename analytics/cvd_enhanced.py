"""
Enhanced CVD Analysis for 5/15min Predictions
Implements divergence detection, momentum analysis, and multi-timeframe alignment.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from utils.logger import get_logger

log = get_logger("analytics.cvd_enhanced")


class EnhancedCVDAnalyzer:
    """Advanced CVD analysis for short-term predictions."""
    
    def __init__(self):
        self.divergence_lookback = 20
        self.momentum_period = 5
        self.acceleration_threshold = 1000  # Adjust based on asset
        
        log.info("EnhancedCVDAnalyzer initialized")
    
    def detect_divergence(self, prices: List[float], cvd_values: List[float]) -> Dict:
        """Detect bullish/bearish divergence between price and CVD.
        
        Args:
            prices: Recent price data (at least 20 bars)
            cvd_values: Recent CVD data (at least 20 bars)
            
        Returns:
            Dict with divergence type and confidence
        """
        if len(prices) < self.divergence_lookback or len(cvd_values) < self.divergence_lookback:
            return {"type": "INSUFFICIENT_DATA", "confidence": 0.0}
        
        # Use last N bars
        recent_prices = prices[-self.divergence_lookback:]
        recent_cvd = cvd_values[-self.divergence_lookback:]
        
        # Calculate trends (simple linear regression slope)
        price_trend = self._calculate_trend(recent_prices)
        cvd_trend = self._calculate_trend(recent_cvd)
        
        # Detect divergence
        if price_trend < -0.001 and cvd_trend > 0.001:
            # Price falling, CVD rising = Bullish divergence
            strength = abs(price_trend) + abs(cvd_trend)
            confidence = min(0.85, 0.65 + strength * 10)
            
            log.info(f"[BULLISH] BULLISH DIVERGENCE detected (confidence: {confidence:.2%})")
            return {
                "type": "BULLISH_DIVERGENCE",
                "confidence": confidence,
                "price_trend": price_trend,
                "cvd_trend": cvd_trend,
                "signal": "LONG"
            }
        
        elif price_trend > 0.001 and cvd_trend < -0.001:
            # Price rising, CVD falling = Bearish divergence
            strength = abs(price_trend) + abs(cvd_trend)
            confidence = min(0.85, 0.65 + strength * 10)
            
            log.info(f"[BEARISH] BEARISH DIVERGENCE detected (confidence: {confidence:.2%})")
            return {
                "type": "BEARISH_DIVERGENCE",
                "confidence": confidence,
                "price_trend": price_trend,
                "cvd_trend": cvd_trend,
                "signal": "SHORT"
            }
        
        else:
            return {
                "type": "NO_DIVERGENCE",
                "confidence": 0.0,
                "price_trend": price_trend,
                "cvd_trend": cvd_trend,
                "signal": "NEUTRAL"
            }
    
    def calculate_momentum(self, cvd_values: List[float]) -> Dict:
        """Calculate CVD momentum and acceleration.
        
        Args:
            cvd_values: Recent CVD data
            
        Returns:
            Dict with momentum, acceleration, and signal
        """
        if len(cvd_values) < self.momentum_period * 2:
            return {"type": "INSUFFICIENT_DATA", "momentum": 0, "acceleration": 0}
        
        # Current momentum (change over last N bars)
        current_momentum = cvd_values[-1] - cvd_values[-self.momentum_period]
        
        # Previous momentum
        previous_momentum = cvd_values[-self.momentum_period] - cvd_values[-self.momentum_period * 2]
        
        # Acceleration (change in momentum)
        acceleration = current_momentum - previous_momentum
        
        # Classify
        if acceleration > self.acceleration_threshold:
            signal = "ACCELERATING"
            strength = min(1.0, abs(acceleration) / (self.acceleration_threshold * 3))
            log.info(f"[ACCEL] CVD ACCELERATING (strength: {strength:.2%})")
        elif acceleration < -self.acceleration_threshold:
            signal = "DECELERATING"
            strength = min(1.0, abs(acceleration) / (self.acceleration_threshold * 3))
            log.info(f"[DECEL] CVD DECELERATING (strength: {strength:.2%})")
        else:
            signal = "STABLE"
            strength = 0.5
        
        return {
            "momentum": current_momentum,
            "acceleration": acceleration,
            "signal": signal,
            "strength": strength
        }
    
    def check_multi_timeframe_alignment(self, cvd_1m: float, cvd_5m: float, cvd_15m: float) -> Dict:
        """Check if CVD aligns across multiple timeframes.
        
        Args:
            cvd_1m: CVD value on 1-minute timeframe
            cvd_5m: CVD value on 5-minute timeframe
            cvd_15m: CVD value on 15-minute timeframe
            
        Returns:
            Dict with alignment status and confidence
        """
        # Determine direction for each timeframe
        signals = []
        
        if cvd_1m > 0:
            signals.append("BULLISH")
        elif cvd_1m < 0:
            signals.append("BEARISH")
        else:
            signals.append("NEUTRAL")
        
        if cvd_5m > 0:
            signals.append("BULLISH")
        elif cvd_5m < 0:
            signals.append("BEARISH")
        else:
            signals.append("NEUTRAL")
        
        if cvd_15m > 0:
            signals.append("BULLISH")
        elif cvd_15m < 0:
            signals.append("BEARISH")
        else:
            signals.append("NEUTRAL")
        
        # Check alignment
        if all(s == "BULLISH" for s in signals):
            log.info(f"[STRONG_BULL] STRONG BULLISH ALIGNMENT (all timeframes)")
            return {
                "alignment": "STRONG_BULLISH",
                "confidence": 0.90,
                "signal": "LONG",
                "timeframes": {"1m": cvd_1m, "5m": cvd_5m, "15m": cvd_15m}
            }
        
        elif all(s == "BEARISH" for s in signals):
            log.info(f"[STRONG_BEAR] STRONG BEARISH ALIGNMENT (all timeframes)")
            return {
                "alignment": "STRONG_BEARISH",
                "confidence": 0.90,
                "signal": "SHORT",
                "timeframes": {"1m": cvd_1m, "5m": cvd_5m, "15m": cvd_15m}
            }
        
        elif signals.count("BULLISH") >= 2:
            log.info(f"[MOD_BULL] MODERATE BULLISH ALIGNMENT (2/3 timeframes)")
            return {
                "alignment": "MODERATE_BULLISH",
                "confidence": 0.70,
                "signal": "LONG",
                "timeframes": {"1m": cvd_1m, "5m": cvd_5m, "15m": cvd_15m}
            }
        
        elif signals.count("BEARISH") >= 2:
            log.info(f"[MOD_BEAR] MODERATE BEARISH ALIGNMENT (2/3 timeframes)")
            return {
                "alignment": "MODERATE_BEARISH",
                "confidence": 0.70,
                "signal": "SHORT",
                "timeframes": {"1m": cvd_1m, "5m": cvd_5m, "15m": cvd_15m}
            }
        
        else:
            return {
                "alignment": "MIXED",
                "confidence": 0.50,
                "signal": "NEUTRAL",
                "timeframes": {"1m": cvd_1m, "5m": cvd_5m, "15m": cvd_15m}
            }
    
    def _calculate_trend(self, data: List[float]) -> float:
        """Calculate trend using simple linear regression with Min-Max scaling and clipping.
        
        Args:
            data: Time series data
            
        Returns:
            Slope of the trend line (positive = uptrend, negative = downtrend)
        """
        n = len(data)
        if n < 2:
            return 0.0
        
        y = np.array(data)
        
        # Clip outliers using percentiles to eliminate wick noise
        p5, p95 = np.percentile(y, [5, 95])
        if p95 > p5:  # ensure valid range
            y = np.clip(y, p5, p95)
            
        # Min-Max Scaling strictly between 0 and 1
        y_min, y_max = np.min(y), np.max(y)
        if y_max > y_min:
            y = (y - y_min) / (y_max - y_min)
            
        # Simple linear regression
        x = np.arange(n)
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        
        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        
        return slope
    
    def analyze_comprehensive(self, prices: List[float], cvd_1m: List[float], 
                             cvd_5m: List[float], cvd_15m: List[float]) -> Dict:
        """Comprehensive CVD analysis combining all techniques.
        
        Args:
            prices: Recent price data
            cvd_1m: CVD data on 1-minute timeframe
            cvd_5m: CVD data on 5-minute timeframe
            cvd_15m: CVD data on 15-minute timeframe
            
        Returns:
            Dict with comprehensive analysis and final signal
        """
        # 1. Divergence detection
        divergence = self.detect_divergence(prices, cvd_1m)
        
        # 2. Momentum analysis
        momentum = self.calculate_momentum(cvd_1m)
        
        # 3. Multi-timeframe alignment
        alignment = self.check_multi_timeframe_alignment(
            cvd_1m[-1] if cvd_1m else 0,
            cvd_5m[-1] if cvd_5m else 0,
            cvd_15m[-1] if cvd_15m else 0
        )
        
        # 4. Combine signals
        signals = []
        confidences = []
        
        if divergence["confidence"] > 0.6:
            signals.append(divergence["signal"])
            confidences.append(divergence["confidence"])
        
        if momentum["signal"] in ["ACCELERATING", "DECELERATING"]:
            # Accelerating CVD supports the current direction
            if momentum["signal"] == "ACCELERATING":
                if cvd_1m[-1] > 0:
                    signals.append("LONG")
                else:
                    signals.append("SHORT")
                confidences.append(momentum["strength"])
        
        if alignment["confidence"] > 0.6:
            signals.append(alignment["signal"])
            confidences.append(alignment["confidence"])
        
        # 5. Final decision
        if not signals:
            final_signal = "NEUTRAL"
            final_confidence = 0.0
        else:
            # Majority vote
            long_count = signals.count("LONG")
            short_count = signals.count("SHORT")
            
            if long_count > short_count:
                final_signal = "LONG"
                final_confidence = np.mean([c for s, c in zip(signals, confidences) if s == "LONG"])
            elif short_count > long_count:
                final_signal = "SHORT"
                final_confidence = np.mean([c for s, c in zip(signals, confidences) if s == "SHORT"])
            else:
                final_signal = "NEUTRAL"
                final_confidence = 0.5
        
        log.info(f"[CVD] CVD Comprehensive Analysis: {final_signal} (confidence: {final_confidence:.2%})")
        
        return {
            "signal": final_signal,
            "confidence": final_confidence,
            "divergence": divergence,
            "momentum": momentum,
            "alignment": alignment,
            "timestamp": datetime.utcnow().isoformat()
        }
