"""
Wyckoff Method Analysis Module

Identifies accumulation/distribution phases and key Wyckoff events:
- Phases: ACCUMULATION, MARKUP, DISTRIBUTION, MARKDOWN
- Events: Spring, Upthrust, SOS (Sign of Strength), SOW (Sign of Weakness),
          LPS (Last Point of Support), LPSY (Last Point of Supply)

Wyckoff Method helps identify when smart money is accumulating or distributing
before major price moves.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional
from statistics import mean


@dataclass
class WyckoffEvent:
    """Individual Wyckoff event detection"""
    event_type: str  # SPRING, UPTHRUST, SOS, SOW, LPS, LPSY
    price: float
    confidence: float  # 0-100
    timestamp: datetime
    description: str
    candle_index: int  # Position in candle array


@dataclass
class WyckoffPhase:
    """Wyckoff phase identification"""
    phase: str  # ACCUMULATION, MARKUP, DISTRIBUTION, MARKDOWN
    confidence: float  # 0-100
    events: List[WyckoffEvent]
    duration_candles: int
    volume_profile: str  # INCREASING, DECREASING, STABLE


@dataclass
class WyckoffAnalysis:
    """Complete Wyckoff analysis result"""
    phase: WyckoffPhase
    recent_events: List[WyckoffEvent]
    phase_score: float  # 0-100 aggregate score
    bias: str  # BULLISH, BEARISH, NEUTRAL


class WyckoffAnalyzer:
    """
    Wyckoff Method implementation.
    
    Identifies market phases and key events to detect accumulation/distribution
    by smart money before major price moves.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Wyckoff analyzer.
        
        Args:
            config: Optional configuration overrides
        """
        self.config = config or {
            "accumulation_volume_decrease": 0.7,  # Volume drops to 70% in accumulation
            "distribution_volume_increase": 1.3,  # Volume rises to 130% in distribution
            "spring_penetration_pct": 0.5,  # Spring penetrates support by 0.5%
            "spring_reversal_pct": 1.0,  # Must reverse 1% above support
            "upthrust_penetration_pct": 0.5,  # Upthrust penetrates resistance by 0.5%
            "sos_volume_multiplier": 1.5,  # SOS requires 1.5x volume
            "phase_min_candles": 20,  # Minimum candles to confirm phase
        }
        self.phase_history: Dict[str, WyckoffPhase] = {}
    
    def analyze(self, candles: List[Dict], volume: List[float], 
                symbol: str = "UNKNOWN") -> WyckoffAnalysis:
        """
        Perform complete Wyckoff analysis.
        
        Args:
            candles: OHLCV candle data
            volume: Volume data (can be extracted from candles if not provided separately)
            symbol: Trading symbol for history tracking
            
        Returns:
            WyckoffAnalysis with phase and events
        """
        if not candles or len(candles) < self.config["phase_min_candles"]:
            return WyckoffAnalysis(
                phase=WyckoffPhase(
                    phase="UNKNOWN",
                    confidence=0.0,
                    events=[],
                    duration_candles=0,
                    volume_profile="STABLE"
                ),
                recent_events=[],
                phase_score=50.0,
                bias="NEUTRAL"
            )
        
        # Extract volume from candles if not provided separately
        if not volume:
            volume = [c.get('volume', 0) for c in candles]
        
        # Identify current phase
        phase = self.identify_phase(candles, volume)
        
        # Detect key events based on phase
        events = []
        
        # Find support and resistance levels
        support_level = self._find_support_level(candles)
        resistance_level = self._find_resistance_level(candles)
        
        # Detect Spring (in accumulation)
        if phase.phase == "ACCUMULATION":
            spring = self.detect_spring(candles, support_level)
            if spring:
                events.append(spring)
        
        # Detect Upthrust (in distribution)
        if phase.phase == "DISTRIBUTION":
            upthrust = self.detect_upthrust(candles, resistance_level)
            if upthrust:
                events.append(upthrust)
        
        # Detect SOS/SOW (in any phase)
        sos_sow = self.detect_sos_sow(candles)
        if sos_sow:
            events.append(sos_sow)
        
        # Detect LPS/LPSY (after SOS/SOW)
        lps_lpsy = self.detect_lps_lpsy(candles, phase.phase)
        if lps_lpsy:
            events.append(lps_lpsy)
        
        # Add events to phase
        phase.events = events
        
        # Store phase in history
        self.phase_history[symbol] = phase
        
        # Calculate aggregate score and bias
        phase_score = self.calculate_phase_score(phase)
        bias = self._determine_bias(phase, events)
        
        return WyckoffAnalysis(
            phase=phase,
            recent_events=events,
            phase_score=phase_score,
            bias=bias
        )
    
    def identify_phase(self, candles: List[Dict], volume: List[float]) -> WyckoffPhase:
        """
        Identify current Wyckoff phase.
        
        Phases:
        - ACCUMULATION: Sideways price action with decreasing volume
        - MARKUP: Strong uptrend with increasing volume
        - DISTRIBUTION: Sideways price action with increasing volume
        - MARKDOWN: Strong downtrend with increasing volume
        
        Args:
            candles: OHLCV candle data
            volume: Volume data
            
        Returns:
            WyckoffPhase with phase type and confidence
        """
        if len(candles) < self.config["phase_min_candles"]:
            return WyckoffPhase(
                phase="UNKNOWN",
                confidence=0.0,
                events=[],
                duration_candles=0,
                volume_profile="STABLE"
            )
        
        # Analyze price action (trending vs sideways)
        price_trend = self._analyze_price_trend(candles)
        
        # Analyze volume profile
        volume_profile = self._analyze_volume_profile(volume)
        
        # Determine phase based on price trend and volume
        phase = "UNKNOWN"
        confidence = 0.0
        
        if price_trend["type"] == "SIDEWAYS":
            if volume_profile == "DECREASING":
                phase = "ACCUMULATION"
                confidence = price_trend["confidence"] * 0.7 + 30
            elif volume_profile == "INCREASING":
                phase = "DISTRIBUTION"
                confidence = price_trend["confidence"] * 0.7 + 30
        elif price_trend["type"] == "UPTREND":
            phase = "MARKUP"
            confidence = price_trend["confidence"]
        elif price_trend["type"] == "DOWNTREND":
            phase = "MARKDOWN"
            confidence = price_trend["confidence"]
        
        return WyckoffPhase(
            phase=phase,
            confidence=min(100, confidence),
            events=[],
            duration_candles=len(candles),
            volume_profile=volume_profile
        )
    
    def detect_spring(self, candles: List[Dict], support_level: float) -> Optional[WyckoffEvent]:
        """
        Detect Spring (false breakdown in accumulation).
        
        A Spring is a false breakdown below support that quickly reverses,
        indicating smart money shaking out weak hands before markup.
        
        Args:
            candles: OHLCV candle data
            support_level: Support level to test
            
        Returns:
            WyckoffEvent if detected, None otherwise
        """
        if len(candles) < 3 or support_level == 0:
            return None
        
        # Check last few candles for spring pattern
        recent = candles[-5:]
        
        for idx, candle in enumerate(recent[:-1]):  # Exclude last candle
            low = candle.get('low', 0)
            close = candle.get('close', 0)
            
            # Check if price penetrated support
            penetration_pct = self.config["spring_penetration_pct"] / 100
            if low < support_level * (1 - penetration_pct):
                # Check if price reversed back above support
                next_candle = recent[idx + 1]
                next_close = next_candle.get('close', 0)
                
                reversal_pct = self.config["spring_reversal_pct"] / 100
                if next_close > support_level * (1 + reversal_pct):
                    # Spring detected!
                    penetration_depth = (support_level - low) / support_level * 100
                    reversal_strength = (next_close - support_level) / support_level * 100
                    
                    confidence = min(100, (
                        penetration_depth * 20 +  # Deeper penetration = more confidence
                        reversal_strength * 30 +  # Stronger reversal = more confidence
                        50  # Base confidence
                    ))
                    
                    return WyckoffEvent(
                        event_type="SPRING",
                        price=low,
                        confidence=max(60, confidence),
                        timestamp=datetime.utcnow(),
                        description=f"Spring detected: false breakdown at ${low:.2f}, reversed to ${next_close:.2f}",
                        candle_index=len(candles) - len(recent) + idx
                    )
        
        return None
    
    def detect_upthrust(self, candles: List[Dict], resistance_level: float) -> Optional[WyckoffEvent]:
        """
        Detect Upthrust (false breakout in distribution).
        
        An Upthrust is a false breakout above resistance that quickly reverses,
        indicating smart money distributing to late buyers before markdown.
        
        Args:
            candles: OHLCV candle data
            resistance_level: Resistance level to test
            
        Returns:
            WyckoffEvent if detected, None otherwise
        """
        if len(candles) < 3 or resistance_level == 0:
            return None
        
        # Check last few candles for upthrust pattern
        recent = candles[-5:]
        
        for idx, candle in enumerate(recent[:-1]):  # Exclude last candle
            high = candle.get('high', 0)
            close = candle.get('close', 0)
            
            # Check if price penetrated resistance
            penetration_pct = self.config["upthrust_penetration_pct"] / 100
            if high > resistance_level * (1 + penetration_pct):
                # Check if price reversed back below resistance
                next_candle = recent[idx + 1]
                next_close = next_candle.get('close', 0)
                
                reversal_pct = self.config["spring_reversal_pct"] / 100
                if next_close < resistance_level * (1 - reversal_pct):
                    # Upthrust detected!
                    penetration_depth = (high - resistance_level) / resistance_level * 100
                    reversal_strength = (resistance_level - next_close) / resistance_level * 100
                    
                    confidence = min(100, (
                        penetration_depth * 20 +  # Deeper penetration = more confidence
                        reversal_strength * 30 +  # Stronger reversal = more confidence
                        50  # Base confidence
                    ))
                    
                    return WyckoffEvent(
                        event_type="UPTHRUST",
                        price=high,
                        confidence=max(60, confidence),
                        timestamp=datetime.utcnow(),
                        description=f"Upthrust detected: false breakout at ${high:.2f}, reversed to ${next_close:.2f}",
                        candle_index=len(candles) - len(recent) + idx
                    )
        
        return None
    
    def detect_sos_sow(self, candles: List[Dict]) -> Optional[WyckoffEvent]:
        """
        Detect Sign of Strength (SOS) or Sign of Weakness (SOW).
        
        SOS: Strong upward move with high volume (bullish)
        SOW: Strong downward move with high volume (bearish)
        
        Args:
            candles: OHLCV candle data
            
        Returns:
            WyckoffEvent if detected, None otherwise
        """
        if len(candles) < 10:
            return None
        
        # Calculate average volume
        recent = candles[-10:]
        avg_volume = mean([c.get('volume', 0) for c in recent[:-1]])
        
        # Check last candle for SOS/SOW
        last_candle = candles[-1]
        volume = last_candle.get('volume', 0)
        open_price = last_candle.get('open', 0)
        close_price = last_candle.get('close', 0)
        high = last_candle.get('high', 0)
        low = last_candle.get('low', 0)
        
        # High volume requirement
        if volume < avg_volume * self.config["sos_volume_multiplier"]:
            return None
        
        # Calculate price move
        price_change_pct = abs(close_price - open_price) / open_price * 100
        spread = high - low
        
        # SOS: Strong upward move
        if close_price > open_price and price_change_pct > 1.0:
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
            
            confidence = min(100, (
                price_change_pct * 15 +  # Larger move = more confidence
                (volume_ratio - 1.0) * 20 +  # Higher volume = more confidence
                40  # Base confidence
            ))
            
            return WyckoffEvent(
                event_type="SOS",
                price=close_price,
                confidence=max(60, confidence),
                timestamp=datetime.utcnow(),
                description=f"Sign of Strength: {price_change_pct:.1f}% move with {volume_ratio:.1f}x volume",
                candle_index=len(candles) - 1
            )
        
        # SOW: Strong downward move
        elif close_price < open_price and price_change_pct > 1.0:
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
            
            confidence = min(100, (
                price_change_pct * 15 +  # Larger move = more confidence
                (volume_ratio - 1.0) * 20 +  # Higher volume = more confidence
                40  # Base confidence
            ))
            
            return WyckoffEvent(
                event_type="SOW",
                price=close_price,
                confidence=max(60, confidence),
                timestamp=datetime.utcnow(),
                description=f"Sign of Weakness: {price_change_pct:.1f}% move with {volume_ratio:.1f}x volume",
                candle_index=len(candles) - 1
            )
        
        return None
    
    def detect_lps_lpsy(self, candles: List[Dict], phase: str) -> Optional[WyckoffEvent]:
        """
        Detect Last Point of Support (LPS) or Last Point of Supply (LPSY).
        
        LPS: Final pullback to support before markup (after SOS)
        LPSY: Final rally to resistance before markdown (after SOW)
        
        Args:
            candles: OHLCV candle data
            phase: Current Wyckoff phase
            
        Returns:
            WyckoffEvent if detected, None otherwise
        """
        if len(candles) < 5:
            return None
        
        recent = candles[-5:]
        
        # LPS: Look for pullback after upward move (in accumulation/markup)
        if phase in ["ACCUMULATION", "MARKUP"]:
            # Check if we had an upward move followed by a pullback
            for idx in range(len(recent) - 2):
                candle1 = recent[idx]
                candle2 = recent[idx + 1]
                candle3 = recent[idx + 2]
                
                # Upward move
                if candle2.get('close', 0) > candle1.get('close', 0):
                    # Followed by pullback
                    if candle3.get('low', 0) < candle2.get('close', 0):
                        # Check if price is holding above a support level
                        support = min(c.get('low', 0) for c in recent[:idx+1])
                        
                        if candle3.get('low', 0) > support * 0.99:  # Within 1% of support
                            confidence = 70.0  # Moderate confidence for LPS
                            
                            return WyckoffEvent(
                                event_type="LPS",
                                price=candle3.get('low', 0),
                                confidence=confidence,
                                timestamp=datetime.utcnow(),
                                description=f"Last Point of Support at ${candle3.get('low', 0):.2f}",
                                candle_index=len(candles) - len(recent) + idx + 2
                            )
        
        # LPSY: Look for rally after downward move (in distribution/markdown)
        elif phase in ["DISTRIBUTION", "MARKDOWN"]:
            # Check if we had a downward move followed by a rally
            for idx in range(len(recent) - 2):
                candle1 = recent[idx]
                candle2 = recent[idx + 1]
                candle3 = recent[idx + 2]
                
                # Downward move
                if candle2.get('close', 0) < candle1.get('close', 0):
                    # Followed by rally
                    if candle3.get('high', 0) > candle2.get('close', 0):
                        # Check if price is capped below a resistance level
                        resistance = max(c.get('high', 0) for c in recent[:idx+1])
                        
                        if candle3.get('high', 0) < resistance * 1.01:  # Within 1% of resistance
                            confidence = 70.0  # Moderate confidence for LPSY
                            
                            return WyckoffEvent(
                                event_type="LPSY",
                                price=candle3.get('high', 0),
                                confidence=confidence,
                                timestamp=datetime.utcnow(),
                                description=f"Last Point of Supply at ${candle3.get('high', 0):.2f}",
                                candle_index=len(candles) - len(recent) + idx + 2
                            )
        
        return None
    
    def calculate_phase_score(self, phase: WyckoffPhase) -> float:
        """
        Calculate 0-100 confidence score for phase.
        
        Args:
            phase: WyckoffPhase to score
            
        Returns:
            Phase score (0-100)
        """
        if phase.phase == "UNKNOWN":
            return 50.0  # Neutral
        
        # Base score from phase confidence
        base_score = phase.confidence
        
        # Boost for high-confidence events
        event_boost = 0
        for event in phase.events:
            if event.confidence > 80:
                event_boost += 5
        
        final_score = min(100, base_score + event_boost)
        return round(final_score, 2)
    
    def _analyze_price_trend(self, candles: List[Dict]) -> Dict:
        """
        Analyze price trend (uptrend, downtrend, sideways).
        
        Args:
            candles: OHLCV candle data
            
        Returns:
            Dict with trend type and confidence
        """
        if len(candles) < 10:
            return {"type": "UNKNOWN", "confidence": 0.0}
        
        # Calculate price change over period
        first_close = candles[0].get('close', 0)
        last_close = candles[-1].get('close', 0)
        price_change_pct = (last_close - first_close) / first_close * 100
        
        # Calculate volatility (range)
        highs = [c.get('high', 0) for c in candles]
        lows = [c.get('low', 0) for c in candles]
        price_range = max(highs) - min(lows)
        avg_price = (max(highs) + min(lows)) / 2
        volatility_pct = (price_range / avg_price) * 100
        
        # Determine trend type
        if abs(price_change_pct) < 3.0 and volatility_pct < 10.0:
            # Sideways: small price change and low volatility
            trend_type = "SIDEWAYS"
            confidence = 70.0
        elif price_change_pct > 5.0:
            # Uptrend: significant upward move
            trend_type = "UPTREND"
            confidence = min(100, abs(price_change_pct) * 5 + 50)
        elif price_change_pct < -5.0:
            # Downtrend: significant downward move
            trend_type = "DOWNTREND"
            confidence = min(100, abs(price_change_pct) * 5 + 50)
        else:
            # Unclear
            trend_type = "SIDEWAYS"
            confidence = 50.0
        
        return {
            "type": trend_type,
            "confidence": confidence,
            "price_change_pct": price_change_pct,
            "volatility_pct": volatility_pct
        }
    
    def _analyze_volume_profile(self, volume: List[float]) -> str:
        """
        Analyze volume profile (increasing, decreasing, stable).
        
        Args:
            volume: Volume data
            
        Returns:
            Volume profile string
        """
        if len(volume) < 10:
            return "STABLE"
        
        # Split into two halves
        mid = len(volume) // 2
        first_half_avg = mean(volume[:mid])
        second_half_avg = mean(volume[mid:])
        
        # Compare halves
        if second_half_avg > first_half_avg * self.config["distribution_volume_increase"]:
            return "INCREASING"
        elif second_half_avg < first_half_avg * self.config["accumulation_volume_decrease"]:
            return "DECREASING"
        else:
            return "STABLE"
    
    def _find_support_level(self, candles: List[Dict]) -> float:
        """
        Find support level from recent lows.
        
        Args:
            candles: OHLCV candle data
            
        Returns:
            Support level price
        """
        if not candles:
            return 0.0
        
        # Find lowest low in recent candles
        recent = candles[-20:] if len(candles) > 20 else candles
        lows = [c.get('low', 0) for c in recent]
        
        return min(lows) if lows else 0.0
    
    def _find_resistance_level(self, candles: List[Dict]) -> float:
        """
        Find resistance level from recent highs.
        
        Args:
            candles: OHLCV candle data
            
        Returns:
            Resistance level price
        """
        if not candles:
            return 0.0
        
        # Find highest high in recent candles
        recent = candles[-20:] if len(candles) > 20 else candles
        highs = [c.get('high', 0) for c in recent]
        
        return max(highs) if highs else 0.0
    
    def _determine_bias(self, phase: WyckoffPhase, events: List[WyckoffEvent]) -> str:
        """
        Determine overall Wyckoff bias (BULLISH, BEARISH, NEUTRAL).
        
        Args:
            phase: Current Wyckoff phase
            events: Recent Wyckoff events
            
        Returns:
            Bias string
        """
        # Phase-based bias
        if phase.phase == "ACCUMULATION":
            phase_bias = "BULLISH"
        elif phase.phase == "MARKUP":
            phase_bias = "BULLISH"
        elif phase.phase == "DISTRIBUTION":
            phase_bias = "BEARISH"
        elif phase.phase == "MARKDOWN":
            phase_bias = "BEARISH"
        else:
            phase_bias = "NEUTRAL"
        
        # Event-based bias
        bullish_events = sum(1 for e in events if e.event_type in ["SPRING", "SOS", "LPS"])
        bearish_events = sum(1 for e in events if e.event_type in ["UPTHRUST", "SOW", "LPSY"])
        
        # Combine phase and event bias
        if phase_bias == "BULLISH" and bullish_events > bearish_events:
            return "BULLISH"
        elif phase_bias == "BEARISH" and bearish_events > bullish_events:
            return "BEARISH"
        elif phase_bias in ["BULLISH", "BEARISH"] and bullish_events == bearish_events:
            return phase_bias
        else:
            return "NEUTRAL"
