"""
Volume Spread Analysis (VSA) Module

Analyzes the relationship between volume and price spread to detect:
- Market maker manipulation
- No Demand/No Supply conditions
- Buying/Selling Climax
- Stopping Volume (absorption)

VSA helps identify when smart money is accumulating or distributing.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional
from statistics import mean


@dataclass
class VSASignal:
    """Individual VSA signal detection"""
    signal_type: str  # NO_DEMAND, NO_SUPPLY, BUYING_CLIMAX, SELLING_CLIMAX, STOPPING_VOLUME
    confidence: float  # 0-100
    volume_ratio: float  # Volume vs average
    spread_ratio: float  # Spread vs average
    close_position: float  # 0-1 (position of close in candle range)
    timestamp: datetime
    candle_index: int  # Position in candle array


@dataclass
class VSAAnalysis:
    """Complete VSA analysis result"""
    signals: List[VSASignal]
    dominant_signal: Optional[VSASignal]
    vsa_score: float  # 0-100 aggregate score
    bias: str  # BULLISH, BEARISH, NEUTRAL


class VolumeSpreadAnalyzer:
    """
    Volume Spread Analysis (VSA) implementation.
    
    VSA analyzes the relationship between volume and price spread to detect
    market maker manipulation and genuine supply/demand imbalances.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize VSA analyzer.
        
        Args:
            config: Optional configuration overrides
        """
        self.config = config or {
            "high_volume_threshold": 1.5,  # 1.5x average volume
            "narrow_spread_threshold": 0.7,  # 70% of average spread
            "wide_spread_threshold": 1.3,  # 130% of average spread
            "close_top_threshold": 0.8,  # Close in top 80% of range
            "close_bottom_threshold": 0.2,  # Close in bottom 20% of range
            "stopping_volume_multiplier": 2.0,  # 2x volume for absorption
            "lookback_period": 20,  # Candles for average calculation
        }
        self.history: Dict[str, List[VSASignal]] = {}
    
    def analyze(self, candles: List[Dict], symbol: str = "UNKNOWN") -> VSAAnalysis:
        """
        Analyze volume-spread relationship for manipulation detection.
        
        Args:
            candles: OHLCV candle data (list of dicts with keys: open, high, low, close, volume)
            symbol: Trading symbol for history tracking
            
        Returns:
            VSAAnalysis with signals and confidence scores
        """
        if not candles or len(candles) < self.config["lookback_period"]:
            return VSAAnalysis(
                signals=[],
                dominant_signal=None,
                vsa_score=50.0,  # Neutral when insufficient data
                bias="NEUTRAL"
            )
        
        signals = []
        lookback = self.config["lookback_period"]
        
        # Calculate averages for comparison
        recent_candles = candles[-lookback:]
        avg_volume = mean([c.get('volume', 0) for c in recent_candles])
        avg_spread = mean([self.calculate_spread(c) for c in recent_candles])
        
        # Analyze recent candles for VSA signals
        analysis_window = candles[-5:]  # Analyze last 5 candles
        
        for idx, candle in enumerate(analysis_window):
            candle_idx = len(candles) - len(analysis_window) + idx
            
            # Check for No Demand
            no_demand = self.detect_no_demand(candle, avg_volume, avg_spread, candle_idx)
            if no_demand:
                signals.append(no_demand)
            
            # Check for No Supply
            no_supply = self.detect_no_supply(candle, avg_volume, avg_spread, candle_idx)
            if no_supply:
                signals.append(no_supply)
            
            # Check for Buying Climax
            buying_climax = self.detect_buying_climax(candle, avg_volume, avg_spread, candle_idx)
            if buying_climax:
                signals.append(buying_climax)
            
            # Check for Selling Climax
            selling_climax = self.detect_selling_climax(candle, avg_volume, avg_spread, candle_idx)
            if selling_climax:
                signals.append(selling_climax)
        
        # Check for Stopping Volume (requires multiple candles)
        stopping_volume = self.detect_stopping_volume(candles)
        if stopping_volume:
            signals.append(stopping_volume)
        
        # Store signals in history
        if symbol not in self.history:
            self.history[symbol] = []
        self.history[symbol].extend(signals)
        
        # Keep only recent history (last 100 signals)
        self.history[symbol] = self.history[symbol][-100:]
        
        # Determine dominant signal and calculate aggregate score
        dominant_signal = self._get_dominant_signal(signals)
        vsa_score = self._calculate_vsa_score(signals, dominant_signal)
        bias = self._determine_bias(signals, dominant_signal)
        
        return VSAAnalysis(
            signals=signals,
            dominant_signal=dominant_signal,
            vsa_score=vsa_score,
            bias=bias
        )
    
    def calculate_spread(self, candle: Dict) -> float:
        """
        Calculate price spread (high - low).
        
        Args:
            candle: OHLC candle data
            
        Returns:
            Price spread
        """
        return candle.get('high', 0) - candle.get('low', 0)
    
    def _calculate_close_position(self, candle: Dict) -> float:
        """
        Calculate where close is positioned in the candle range (0-1).
        
        0 = close at low
        1 = close at high
        0.5 = close at midpoint
        
        Args:
            candle: OHLC candle data
            
        Returns:
            Close position (0-1)
        """
        high = candle.get('high', 0)
        low = candle.get('low', 0)
        close = candle.get('close', 0)
        
        if high == low:
            return 0.5
        
        return (close - low) / (high - low)
    
    def detect_no_demand(self, candle: Dict, avg_volume: float, avg_spread: float, 
                        candle_idx: int) -> Optional[VSASignal]:
        """
        Detect No Demand: high volume + narrow spread + close in lower half.
        
        Indicates selling pressure being absorbed but no buying interest.
        Bearish signal.
        
        Args:
            candle: Current candle
            avg_volume: Average volume for comparison
            avg_spread: Average spread for comparison
            candle_idx: Index of candle in array
            
        Returns:
            VSASignal if detected, None otherwise
        """
        volume = candle.get('volume', 0)
        spread = self.calculate_spread(candle)
        close_pos = self._calculate_close_position(candle)
        
        # High volume + narrow spread + close in lower half
        high_volume = volume >= avg_volume * self.config["high_volume_threshold"]
        narrow_spread = spread <= avg_spread * self.config["narrow_spread_threshold"]
        close_low = close_pos <= 0.5
        
        if high_volume and narrow_spread and close_low:
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
            spread_ratio = spread / avg_spread if avg_spread > 0 else 1.0
            
            # Confidence based on how extreme the conditions are
            confidence = min(100, (
                (volume_ratio - 1.0) * 20 +  # Volume contribution
                (1.0 - spread_ratio) * 30 +  # Narrow spread contribution
                (0.5 - close_pos) * 50  # Close position contribution
            ))
            
            return VSASignal(
                signal_type="NO_DEMAND",
                confidence=max(50, confidence),
                volume_ratio=volume_ratio,
                spread_ratio=spread_ratio,
                close_position=close_pos,
                timestamp=datetime.utcnow(),
                candle_index=candle_idx
            )
        
        return None
    
    def detect_no_supply(self, candle: Dict, avg_volume: float, avg_spread: float,
                        candle_idx: int) -> Optional[VSASignal]:
        """
        Detect No Supply: high volume + narrow spread + close in upper half.
        
        Indicates buying pressure being absorbed but no selling interest.
        Bullish signal.
        
        Args:
            candle: Current candle
            avg_volume: Average volume for comparison
            avg_spread: Average spread for comparison
            candle_idx: Index of candle in array
            
        Returns:
            VSASignal if detected, None otherwise
        """
        volume = candle.get('volume', 0)
        spread = self.calculate_spread(candle)
        close_pos = self._calculate_close_position(candle)
        
        # High volume + narrow spread + close in upper half
        high_volume = volume >= avg_volume * self.config["high_volume_threshold"]
        narrow_spread = spread <= avg_spread * self.config["narrow_spread_threshold"]
        close_high = close_pos >= 0.5
        
        if high_volume and narrow_spread and close_high:
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
            spread_ratio = spread / avg_spread if avg_spread > 0 else 1.0
            
            # Confidence based on how extreme the conditions are
            confidence = min(100, (
                (volume_ratio - 1.0) * 20 +  # Volume contribution
                (1.0 - spread_ratio) * 30 +  # Narrow spread contribution
                (close_pos - 0.5) * 50  # Close position contribution
            ))
            
            return VSASignal(
                signal_type="NO_SUPPLY",
                confidence=max(50, confidence),
                volume_ratio=volume_ratio,
                spread_ratio=spread_ratio,
                close_position=close_pos,
                timestamp=datetime.utcnow(),
                candle_index=candle_idx
            )
        
        return None
    
    def detect_buying_climax(self, candle: Dict, avg_volume: float, avg_spread: float,
                            candle_idx: int) -> Optional[VSASignal]:
        """
        Detect Buying Climax: high volume + wide spread + close at top.
        
        Indicates exhaustion of buying pressure. Often marks a top.
        Bearish reversal signal.
        
        Args:
            candle: Current candle
            avg_volume: Average volume for comparison
            avg_spread: Average spread for comparison
            candle_idx: Index of candle in array
            
        Returns:
            VSASignal if detected, None otherwise
        """
        volume = candle.get('volume', 0)
        spread = self.calculate_spread(candle)
        close_pos = self._calculate_close_position(candle)
        
        # High volume + wide spread + close at top
        high_volume = volume >= avg_volume * self.config["high_volume_threshold"]
        wide_spread = spread >= avg_spread * self.config["wide_spread_threshold"]
        close_at_top = close_pos >= self.config["close_top_threshold"]
        
        if high_volume and wide_spread and close_at_top:
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
            spread_ratio = spread / avg_spread if avg_spread > 0 else 1.0
            
            # Confidence based on extremity
            confidence = min(100, (
                (volume_ratio - 1.0) * 25 +  # Volume contribution
                (spread_ratio - 1.0) * 25 +  # Wide spread contribution
                (close_pos - 0.8) * 100  # Close at top contribution
            ))
            
            return VSASignal(
                signal_type="BUYING_CLIMAX",
                confidence=max(60, confidence),
                volume_ratio=volume_ratio,
                spread_ratio=spread_ratio,
                close_position=close_pos,
                timestamp=datetime.utcnow(),
                candle_index=candle_idx
            )
        
        return None
    
    def detect_selling_climax(self, candle: Dict, avg_volume: float, avg_spread: float,
                             candle_idx: int) -> Optional[VSASignal]:
        """
        Detect Selling Climax: high volume + wide spread + close at bottom.
        
        Indicates exhaustion of selling pressure. Often marks a bottom.
        Bullish reversal signal.
        
        Args:
            candle: Current candle
            avg_volume: Average volume for comparison
            avg_spread: Average spread for comparison
            candle_idx: Index of candle in array
            
        Returns:
            VSASignal if detected, None otherwise
        """
        volume = candle.get('volume', 0)
        spread = self.calculate_spread(candle)
        close_pos = self._calculate_close_position(candle)
        
        # High volume + wide spread + close at bottom
        high_volume = volume >= avg_volume * self.config["high_volume_threshold"]
        wide_spread = spread >= avg_spread * self.config["wide_spread_threshold"]
        close_at_bottom = close_pos <= self.config["close_bottom_threshold"]
        
        if high_volume and wide_spread and close_at_bottom:
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
            spread_ratio = spread / avg_spread if avg_spread > 0 else 1.0
            
            # Confidence based on extremity
            confidence = min(100, (
                (volume_ratio - 1.0) * 25 +  # Volume contribution
                (spread_ratio - 1.0) * 25 +  # Wide spread contribution
                (0.2 - close_pos) * 100  # Close at bottom contribution
            ))
            
            return VSASignal(
                signal_type="SELLING_CLIMAX",
                confidence=max(60, confidence),
                volume_ratio=volume_ratio,
                spread_ratio=spread_ratio,
                close_position=close_pos,
                timestamp=datetime.utcnow(),
                candle_index=candle_idx
            )
        
        return None
    
    def detect_stopping_volume(self, candles: List[Dict]) -> Optional[VSASignal]:
        """
        Detect Stopping Volume: very high volume with price reversal (absorption).
        
        Indicates smart money absorbing supply/demand at key levels.
        Direction depends on context (bullish if stopping downmove, bearish if stopping upmove).
        
        Args:
            candles: Recent candle data
            
        Returns:
            VSASignal if detected, None otherwise
        """
        if len(candles) < 3:
            return None
        
        lookback = min(self.config["lookback_period"], len(candles) - 1)
        recent = candles[-lookback-1:-1]  # Exclude current candle
        current = candles[-1]
        
        avg_volume = mean([c.get('volume', 0) for c in recent])
        current_volume = current.get('volume', 0)
        
        # Very high volume (2x+ average)
        if current_volume < avg_volume * self.config["stopping_volume_multiplier"]:
            return None
        
        # Check for price reversal
        prev_candle = candles[-2]
        current_close = current.get('close', 0)
        prev_close = prev_candle.get('close', 0)
        prev_open = prev_candle.get('open', 0)
        
        # Determine if there's a reversal
        prev_direction = "UP" if prev_close > prev_open else "DOWN"
        current_direction = "UP" if current_close > current.get('open', 0) else "DOWN"
        
        # Stopping volume occurs when direction reverses with high volume
        if prev_direction != current_direction:
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            spread = self.calculate_spread(current)
            avg_spread = mean([self.calculate_spread(c) for c in recent])
            spread_ratio = spread / avg_spread if avg_spread > 0 else 1.0
            close_pos = self._calculate_close_position(current)
            
            # Confidence based on volume extremity
            confidence = min(100, (volume_ratio - 1.0) * 30 + 40)
            
            return VSASignal(
                signal_type="STOPPING_VOLUME",
                confidence=max(60, confidence),
                volume_ratio=volume_ratio,
                spread_ratio=spread_ratio,
                close_position=close_pos,
                timestamp=datetime.utcnow(),
                candle_index=len(candles) - 1
            )
        
        return None
    
    def _get_dominant_signal(self, signals: List[VSASignal]) -> Optional[VSASignal]:
        """
        Get the most significant signal from the list.
        
        Args:
            signals: List of detected signals
            
        Returns:
            Dominant signal or None
        """
        if not signals:
            return None
        
        # Sort by confidence and recency (prefer recent high-confidence signals)
        sorted_signals = sorted(
            signals,
            key=lambda s: (s.confidence, s.candle_index),
            reverse=True
        )
        
        return sorted_signals[0]
    
    def _calculate_vsa_score(self, signals: List[VSASignal], 
                            dominant_signal: Optional[VSASignal]) -> float:
        """
        Calculate aggregate VSA score (0-100).
        
        Higher score = stronger signal quality.
        
        Args:
            signals: All detected signals
            dominant_signal: Most significant signal
            
        Returns:
            VSA score (0-100)
        """
        if not signals:
            return 50.0  # Neutral
        
        if not dominant_signal:
            return 50.0
        
        # Base score from dominant signal confidence
        base_score = dominant_signal.confidence
        
        # Boost if multiple signals agree
        signal_types = [s.signal_type for s in signals]
        bullish_signals = sum(1 for t in signal_types if t in ["NO_SUPPLY", "SELLING_CLIMAX"])
        bearish_signals = sum(1 for t in signal_types if t in ["NO_DEMAND", "BUYING_CLIMAX"])
        
        # Agreement boost (max +10)
        if bullish_signals > bearish_signals:
            agreement_boost = min(10, bullish_signals * 3)
        elif bearish_signals > bullish_signals:
            agreement_boost = min(10, bearish_signals * 3)
        else:
            agreement_boost = 0
        
        final_score = min(100, base_score + agreement_boost)
        return round(final_score, 2)
    
    def _determine_bias(self, signals: List[VSASignal], 
                       dominant_signal: Optional[VSASignal]) -> str:
        """
        Determine overall VSA bias (BULLISH, BEARISH, NEUTRAL).
        
        Args:
            signals: All detected signals
            dominant_signal: Most significant signal
            
        Returns:
            Bias string
        """
        if not signals or not dominant_signal:
            return "NEUTRAL"
        
        # Count bullish vs bearish signals
        bullish_count = sum(1 for s in signals if s.signal_type in ["NO_SUPPLY", "SELLING_CLIMAX"])
        bearish_count = sum(1 for s in signals if s.signal_type in ["NO_DEMAND", "BUYING_CLIMAX"])
        
        # Weight by confidence
        bullish_weight = sum(s.confidence for s in signals if s.signal_type in ["NO_SUPPLY", "SELLING_CLIMAX"])
        bearish_weight = sum(s.confidence for s in signals if s.signal_type in ["NO_DEMAND", "BUYING_CLIMAX"])
        
        # Determine bias
        if bullish_weight > bearish_weight * 1.2:  # 20% threshold
            return "BULLISH"
        elif bearish_weight > bullish_weight * 1.2:
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    def get_confidence_score(self, signal: VSASignal) -> float:
        """
        Get confidence score for a specific VSA signal.
        
        Args:
            signal: VSA signal
            
        Returns:
            Confidence score (0-100)
        """
        return signal.confidence
