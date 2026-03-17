"""
Volatility Regime Adaptive System

Classifies market volatility regime and automatically adjusts strategy parameters
for optimal performance in different market conditions.

Implements:
- Historical Volatility (HV) calculation
- Volatility regime classification (LOW, NORMAL, HIGH, EXTREME)
- Volatility compression detection (low volatility before big moves)
- Regime-specific parameter adjustments
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional
import numpy as np
from utils.logger import get_logger

log = get_logger("strategy.volatility_regime")


# Configuration
VOLATILITY_REGIME_CONFIG = {
    "low_volatility_threshold": 15,  # <15% = LOW
    "normal_volatility_range": (15, 30),  # 15-30% = NORMAL
    "high_volatility_range": (30, 50),  # 30-50% = HIGH
    "extreme_volatility_threshold": 50,  # >50% = EXTREME
    "compression_duration_days": 5,  # Min 5 days for compression
    "compression_percentile": 20,  # Below 20th percentile
    "hv_lookback_days": 30,  # 30 days for HV calculation
    "percentile_lookback_days": 90,  # 90 days for percentile ranking
    
    # Regime-specific adjustments
    "low_regime": {
        "min_quality": "A+",
        "sl_buffer_multiplier": 1.0,
        "leverage_multiplier": 1.0,
        "confidence_threshold": 75,
        "position_size_multiplier": 1.0,
    },
    "normal_regime": {
        "min_quality": "A",
        "sl_buffer_multiplier": 1.0,
        "leverage_multiplier": 1.0,
        "confidence_threshold": 70,
        "position_size_multiplier": 1.0,
    },
    "high_regime": {
        "min_quality": "A",
        "sl_buffer_multiplier": 1.5,
        "leverage_multiplier": 0.75,
        "confidence_threshold": 70,
        "position_size_multiplier": 0.8,
    },
    "extreme_regime": {
        "min_quality": "A+",
        "sl_buffer_multiplier": 2.0,
        "leverage_multiplier": 0.5,
        "confidence_threshold": 80,
        "position_size_multiplier": 0.5,
    },
}


@dataclass
class VolatilityMetrics:
    """Volatility metrics for a symbol"""
    hv: float  # Historical Volatility (annualized %)
    hv_percentile: float  # 0-100 percentile rank
    atr: float  # Average True Range
    bollinger_width: float  # Bollinger Band width
    returns_std: float  # Standard deviation of returns


@dataclass
class VolatilityRegime:
    """Current volatility regime classification"""
    regime: str  # LOW, NORMAL, HIGH, EXTREME
    volatility: float  # Current HV value
    timestamp: datetime
    adjustments: 'RegimeAdjustments'


@dataclass
class VolatilityCompression:
    """Volatility compression detection"""
    detected: bool
    duration_days: int
    current_volatility: float
    avg_volatility: float
    compression_ratio: float  # current/avg
    breakout_probability: float  # 0-1
    confidence_boost: float  # Confidence adjustment for breakout signals


@dataclass
class RegimeAdjustments:
    """Parameter adjustments for current regime"""
    min_quality: str  # Adjusted quality threshold
    sl_buffer_multiplier: float  # Multiply SL buffer
    leverage_multiplier: float  # Multiply leverage
    confidence_threshold: float  # Adjusted confidence threshold
    position_size_multiplier: float  # Multiply position size


class VolatilityRegimeAdapter:
    """
    Volatility Regime Adaptive System
    
    Classifies volatility regime and adjusts strategy parameters automatically.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or VOLATILITY_REGIME_CONFIG
        self.regime_history: Dict[str, List[VolatilityRegime]] = {}
        self.volatility_history: Dict[str, List[float]] = {}
        log.info("VolatilityRegimeAdapter initialized")
    
    def calculate_volatility(self, candles: List[Dict], symbol: str = "UNKNOWN") -> VolatilityMetrics:
        """
        Calculate Historical Volatility (HV) and related metrics.
        
        Args:
            candles: OHLCV candle data (should be daily or 4H for HV calculation)
            symbol: Symbol name for tracking
            
        Returns:
            VolatilityMetrics with HV, ATR, Bollinger width, etc.
        """
        if not candles or len(candles) < 20:
            log.warning(f"Insufficient candles for volatility calculation: {len(candles)}")
            return VolatilityMetrics(
                hv=0.0,
                hv_percentile=50.0,
                atr=0.0,
                bollinger_width=0.0,
                returns_std=0.0
            )
        
        # Calculate log returns
        closes = [c['close'] for c in candles]
        returns = []
        for i in range(1, len(closes)):
            if closes[i-1] > 0:
                ret = np.log(closes[i] / closes[i-1])
                returns.append(ret)
        
        if not returns:
            return VolatilityMetrics(
                hv=0.0,
                hv_percentile=50.0,
                atr=0.0,
                bollinger_width=0.0,
                returns_std=0.0
            )
        
        # Historical Volatility (annualized)
        returns_std = np.std(returns)
        # Annualize: std * sqrt(periods per year)
        # For 4H candles: 6 per day * 365 = 2190
        # For daily: 365
        # Assume 4H candles for now (adjust based on timeframe)
        periods_per_year = 365  # Conservative estimate
        hv = returns_std * np.sqrt(periods_per_year) * 100  # Convert to percentage
        
        # Calculate ATR (Average True Range)
        atr = self._calculate_atr(candles[-14:])  # 14-period ATR
        
        # Calculate Bollinger Band width
        bb_width = self._calculate_bollinger_width(closes[-20:])
        
        # Calculate percentile rank
        hv_percentile = self._calculate_percentile(symbol, hv)
        
        # Store in history
        if symbol not in self.volatility_history:
            self.volatility_history[symbol] = []
        self.volatility_history[symbol].append(hv)
        # Keep last 90 days
        if len(self.volatility_history[symbol]) > 90:
            self.volatility_history[symbol] = self.volatility_history[symbol][-90:]
        
        return VolatilityMetrics(
            hv=hv,
            hv_percentile=hv_percentile,
            atr=atr,
            bollinger_width=bb_width,
            returns_std=returns_std
        )
    
    def _calculate_atr(self, candles: List[Dict]) -> float:
        """Calculate Average True Range"""
        if len(candles) < 2:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(candles)):
            high = candles[i]['high']
            low = candles[i]['low']
            prev_close = candles[i-1]['close']
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        return np.mean(true_ranges) if true_ranges else 0.0
    
    def _calculate_bollinger_width(self, closes: List[float]) -> float:
        """Calculate Bollinger Band width (normalized)"""
        if len(closes) < 20:
            return 0.0
        
        sma = np.mean(closes)
        std = np.std(closes)
        
        # Width = (upper - lower) / middle
        # Upper = SMA + 2*std, Lower = SMA - 2*std
        if sma > 0:
            width = (4 * std) / sma * 100  # Percentage
            return width
        return 0.0
    
    def _calculate_percentile(self, symbol: str, current_hv: float) -> float:
        """Calculate percentile rank of current HV"""
        if symbol not in self.volatility_history or len(self.volatility_history[symbol]) < 10:
            return 50.0  # Default to median
        
        history = self.volatility_history[symbol]
        below = sum(1 for hv in history if hv < current_hv)
        percentile = (below / len(history)) * 100
        return percentile
    
    def classify_regime(self, volatility: float) -> str:
        """
        Classify volatility regime.
        
        Args:
            volatility: Historical Volatility (annualized %)
            
        Returns:
            Regime: LOW, NORMAL, HIGH, EXTREME
        """
        if volatility < self.config["low_volatility_threshold"]:
            return "LOW"
        elif volatility < self.config["normal_volatility_range"][1]:
            return "NORMAL"
        elif volatility < self.config["high_volatility_range"][1]:
            return "HIGH"
        else:
            return "EXTREME"
    
    def detect_volatility_compression(self, candles: List[Dict], symbol: str = "UNKNOWN") -> VolatilityCompression:
        """
        Detect volatility compression (low volatility before big move).
        
        Criteria:
        - Volatility below 20th percentile
        - Duration >5 days
        - Bollinger Bands squeezing
        
        Args:
            candles: Recent candle data
            symbol: Symbol name
            
        Returns:
            VolatilityCompression with detection status and confidence boost
        """
        if len(candles) < self.config["compression_duration_days"]:
            return VolatilityCompression(
                detected=False,
                duration_days=0,
                current_volatility=0.0,
                avg_volatility=0.0,
                compression_ratio=1.0,
                breakout_probability=0.0,
                confidence_boost=0.0
            )
        
        # Calculate current volatility
        metrics = self.calculate_volatility(candles, symbol)
        current_hv = metrics.hv
        
        # Check if below compression percentile
        if metrics.hv_percentile > self.config["compression_percentile"]:
            return VolatilityCompression(
                detected=False,
                duration_days=0,
                current_volatility=current_hv,
                avg_volatility=0.0,
                compression_ratio=1.0,
                breakout_probability=0.0,
                confidence_boost=0.0
            )
        
        # Count consecutive days below threshold
        if symbol not in self.volatility_history or len(self.volatility_history[symbol]) < 10:
            avg_volatility = current_hv
        else:
            avg_volatility = np.mean(self.volatility_history[symbol])
        
        # Calculate compression duration (simplified - check recent history)
        duration_days = 0
        if symbol in self.volatility_history:
            recent_history = self.volatility_history[symbol][-10:]
            threshold = np.percentile(self.volatility_history[symbol], self.config["compression_percentile"])
            for hv in reversed(recent_history):
                if hv < threshold:
                    duration_days += 1
                else:
                    break
        
        # Check if compression duration meets threshold
        min_duration = self.config["compression_duration_days"]
        detected = duration_days >= min_duration
        
        # Calculate compression ratio
        compression_ratio = current_hv / avg_volatility if avg_volatility > 0 else 1.0
        
        # Calculate breakout probability (lower compression = higher probability)
        # Probability increases with duration and compression depth
        if detected:
            duration_factor = min(duration_days / 10, 1.0)  # Max at 10 days
            compression_factor = max(0, 1.0 - compression_ratio)  # Lower ratio = higher factor
            breakout_probability = (duration_factor * 0.5 + compression_factor * 0.5)
            
            # Confidence boost: +15% for compression >5 days
            confidence_boost = 15.0
        else:
            breakout_probability = 0.0
            confidence_boost = 0.0
        
        return VolatilityCompression(
            detected=detected,
            duration_days=duration_days,
            current_volatility=current_hv,
            avg_volatility=avg_volatility,
            compression_ratio=compression_ratio,
            breakout_probability=breakout_probability,
            confidence_boost=confidence_boost
        )
    
    def get_regime_adjustments(self, regime: str) -> RegimeAdjustments:
        """
        Get parameter adjustments for current regime.
        
        Args:
            regime: Volatility regime (LOW, NORMAL, HIGH, EXTREME)
            
        Returns:
            RegimeAdjustments with modified parameters
        """
        regime_key = f"{regime.lower()}_regime"
        adjustments = self.config.get(regime_key, self.config["normal_regime"])
        
        return RegimeAdjustments(
            min_quality=adjustments["min_quality"],
            sl_buffer_multiplier=adjustments["sl_buffer_multiplier"],
            leverage_multiplier=adjustments["leverage_multiplier"],
            confidence_threshold=adjustments["confidence_threshold"],
            position_size_multiplier=adjustments["position_size_multiplier"]
        )
    
    def analyze(self, candles: List[Dict], symbol: str = "UNKNOWN") -> Dict:
        """
        Complete volatility regime analysis.
        
        Args:
            candles: OHLCV candle data
            symbol: Symbol name
            
        Returns:
            Dictionary with regime, metrics, compression, and adjustments
        """
        # Calculate volatility metrics
        metrics = self.calculate_volatility(candles, symbol)
        
        # Classify regime
        regime = self.classify_regime(metrics.hv)
        
        # Get adjustments
        adjustments = self.get_regime_adjustments(regime)
        
        # Detect compression
        compression = self.detect_volatility_compression(candles, symbol)
        
        # Create regime object
        regime_obj = VolatilityRegime(
            regime=regime,
            volatility=metrics.hv,
            timestamp=datetime.now(),
            adjustments=adjustments
        )
        
        # Store in history
        if symbol not in self.regime_history:
            self.regime_history[symbol] = []
        self.regime_history[symbol].append(regime_obj)
        # Keep last 30 regimes
        if len(self.regime_history[symbol]) > 30:
            self.regime_history[symbol] = self.regime_history[symbol][-30:]
        
        return {
            "regime": regime,
            "metrics": metrics,
            "compression": compression,
            "adjustments": adjustments,
            "regime_obj": regime_obj
        }
