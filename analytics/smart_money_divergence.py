"""
Smart Money Divergence Detector Module

Detects divergences between price and smart money indicators:
- CVD (Cumulative Volume Delta) divergence
- Open Interest divergence
- Funding Rate divergence

Divergences indicate potential trend reversals when price and smart money
indicators move in opposite directions.

Types:
- REGULAR divergence: Counter-trend (price makes new high/low, indicator doesn't)
- HIDDEN divergence: With-trend (indicator makes new high/low, price doesn't)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from statistics import mean


@dataclass
class Divergence:
    """Individual divergence detection"""
    divergence_type: str  # BULLISH, BEARISH
    divergence_class: str  # REGULAR, HIDDEN
    indicator: str  # CVD, OPEN_INTEREST, FUNDING_RATE
    strength: float  # 0-100
    price_swing: Tuple[float, float]  # (start, end)
    indicator_swing: Tuple[float, float]  # (start, end)
    confidence_boost: float  # Confidence adjustment
    timestamp: datetime
    candle_index: int  # Position in candle array


@dataclass
class DivergenceAnalysis:
    """Complete divergence analysis result"""
    divergences: List[Divergence]
    dominant_divergence: Optional[Divergence]
    aggregate_score: float  # 0-100
    bias: str  # BULLISH, BEARISH, NEUTRAL


class SmartMoneyDivergenceDetector:
    """
    Smart Money Divergence Detection implementation.
    
    Detects divergences between price action and smart money indicators
    (CVD, Open Interest, Funding Rate) to identify potential reversals.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Smart Money Divergence Detector.
        
        Args:
            config: Optional configuration overrides
        """
        self.config = config or {
            "min_swing_size_pct": 2.0,  # Min 2% price swing for divergence
            "lookback_candles": 50,  # Candles to search for swings
            "regular_divergence_boost": 20,  # Confidence boost for regular
            "hidden_divergence_boost": 10,  # Confidence boost for hidden
            "high_strength_threshold": 75,  # >75% = high strength
        }
        self.divergence_history: Dict[str, List[Divergence]] = {}
    
    def analyze(self, candles: List[Dict], crypto_data: Optional[Dict] = None,
                symbol: str = "UNKNOWN") -> DivergenceAnalysis:
        """
        Perform complete divergence analysis.
        
        Args:
            candles: OHLCV candle data
            crypto_data: Crypto analytics data (from CryptoAnalytics.get_full_analysis)
            symbol: Trading symbol for history tracking
            
        Returns:
            DivergenceAnalysis with detected divergences
        """
        if not candles or len(candles) < self.config["lookback_candles"]:
            return DivergenceAnalysis(
                divergences=[],
                dominant_divergence=None,
                aggregate_score=50.0,  # Neutral when insufficient data
                bias="NEUTRAL"
            )
        
        divergences = []
        
        # Extract CVD data if available
        cvd_data = None
        if crypto_data and crypto_data.get("advanced_orderflow"):
            cvd_info = crypto_data["advanced_orderflow"].get("cvd", {})
            if cvd_info and cvd_info.get("history"):
                cvd_data = [h["cumulative_delta"] for h in cvd_info["history"]]
        
        # Detect CVD divergence
        if cvd_data and len(cvd_data) >= len(candles):
            cvd_div = self.detect_cvd_divergence(candles, cvd_data[-len(candles):])
            if cvd_div:
                divergences.append(cvd_div)
        
        # Extract Open Interest data if available
        oi_data = None
        if crypto_data and crypto_data.get("open_interest"):
            # OI data is stored in crypto analytics history
            # For now, we'll skip OI divergence if not available in the expected format
            pass
        
        # Extract Funding Rate data if available
        funding_data = None
        if crypto_data and crypto_data.get("funding"):
            # Funding data is stored in crypto analytics history
            # For now, we'll skip funding divergence if not available in the expected format
            pass
        
        # Store divergences in history
        if symbol not in self.divergence_history:
            self.divergence_history[symbol] = []
        self.divergence_history[symbol].extend(divergences)
        
        # Keep only recent history (last 100 divergences)
        self.divergence_history[symbol] = self.divergence_history[symbol][-100:]
        
        # Determine dominant divergence and calculate aggregate score
        dominant_divergence = self._get_dominant_divergence(divergences)
        aggregate_score = self._calculate_aggregate_score(divergences, dominant_divergence)
        bias = self._determine_bias(divergences, dominant_divergence)
        
        return DivergenceAnalysis(
            divergences=divergences,
            dominant_divergence=dominant_divergence,
            aggregate_score=aggregate_score,
            bias=bias
        )
    
    def detect_cvd_divergence(self, candles: List[Dict], cvd_data: List[float]) -> Optional[Divergence]:
        """
        Detect divergence between price and CVD.
        
        Bullish Regular: Price makes lower low, CVD makes higher low
        Bearish Regular: Price makes higher high, CVD makes lower high
        Bullish Hidden: Price makes higher low, CVD makes lower low
        Bearish Hidden: Price makes lower high, CVD makes higher high
        
        Args:
            candles: OHLCV candle data
            cvd_data: CVD values aligned with candles
            
        Returns:
            Divergence if detected, None otherwise
        """
        if len(candles) < 10 or len(cvd_data) < 10:
            return None
        
        # Find price swings
        price_swings = self._find_swings(candles)
        if not price_swings:
            return None
        
        # Find CVD swings
        cvd_swings = self._find_indicator_swings(cvd_data)
        if not cvd_swings:
            return None
        
        # Check for divergences
        for price_swing in price_swings[-3:]:  # Check last 3 swings
            for cvd_swing in cvd_swings[-3:]:
                # Check if swings are roughly aligned in time
                if abs(price_swing["index"] - cvd_swing["index"]) > 5:
                    continue
                
                # Bullish Regular Divergence: Price LL, CVD HL
                if (price_swing["type"] == "LOW" and cvd_swing["type"] == "LOW" and
                    price_swing["is_lower"] and not cvd_swing["is_lower"]):
                    
                    strength = self.calculate_divergence_strength(
                        price_swing["change_pct"],
                        cvd_swing["change_pct"]
                    )
                    
                    confidence_boost = self._calculate_confidence_boost(strength, "REGULAR")
                    
                    return Divergence(
                        divergence_type="BULLISH",
                        divergence_class="REGULAR",
                        indicator="CVD",
                        strength=strength,
                        price_swing=(price_swing["prev_value"], price_swing["value"]),
                        indicator_swing=(cvd_swing["prev_value"], cvd_swing["value"]),
                        confidence_boost=confidence_boost,
                        timestamp=datetime.utcnow(),
                        candle_index=price_swing["index"]
                    )
                
                # Bearish Regular Divergence: Price HH, CVD LH
                elif (price_swing["type"] == "HIGH" and cvd_swing["type"] == "HIGH" and
                      not price_swing["is_lower"] and cvd_swing["is_lower"]):
                    
                    strength = self.calculate_divergence_strength(
                        price_swing["change_pct"],
                        cvd_swing["change_pct"]
                    )
                    
                    confidence_boost = self._calculate_confidence_boost(strength, "REGULAR")
                    
                    return Divergence(
                        divergence_type="BEARISH",
                        divergence_class="REGULAR",
                        indicator="CVD",
                        strength=strength,
                        price_swing=(price_swing["prev_value"], price_swing["value"]),
                        indicator_swing=(cvd_swing["prev_value"], cvd_swing["value"]),
                        confidence_boost=confidence_boost,
                        timestamp=datetime.utcnow(),
                        candle_index=price_swing["index"]
                    )
                
                # Bullish Hidden Divergence: Price HL, CVD LL
                elif (price_swing["type"] == "LOW" and cvd_swing["type"] == "LOW" and
                      not price_swing["is_lower"] and cvd_swing["is_lower"]):
                    
                    strength = self.calculate_divergence_strength(
                        price_swing["change_pct"],
                        cvd_swing["change_pct"]
                    )
                    
                    confidence_boost = self._calculate_confidence_boost(strength, "HIDDEN")
                    
                    return Divergence(
                        divergence_type="BULLISH",
                        divergence_class="HIDDEN",
                        indicator="CVD",
                        strength=strength,
                        price_swing=(price_swing["prev_value"], price_swing["value"]),
                        indicator_swing=(cvd_swing["prev_value"], cvd_swing["value"]),
                        confidence_boost=confidence_boost,
                        timestamp=datetime.utcnow(),
                        candle_index=price_swing["index"]
                    )
                
                # Bearish Hidden Divergence: Price LH, CVD HH
                elif (price_swing["type"] == "HIGH" and cvd_swing["type"] == "HIGH" and
                      price_swing["is_lower"] and not cvd_swing["is_lower"]):
                    
                    strength = self.calculate_divergence_strength(
                        price_swing["change_pct"],
                        cvd_swing["change_pct"]
                    )
                    
                    confidence_boost = self._calculate_confidence_boost(strength, "HIDDEN")
                    
                    return Divergence(
                        divergence_type="BEARISH",
                        divergence_class="HIDDEN",
                        indicator="CVD",
                        strength=strength,
                        price_swing=(price_swing["prev_value"], price_swing["value"]),
                        indicator_swing=(cvd_swing["prev_value"], cvd_swing["value"]),
                        confidence_boost=confidence_boost,
                        timestamp=datetime.utcnow(),
                        candle_index=price_swing["index"]
                    )
        
        return None
    
    def detect_oi_divergence(self, candles: List[Dict], oi_data: List[float]) -> Optional[Divergence]:
        """
        Detect divergence between price and Open Interest.
        
        Args:
            candles: OHLCV candle data
            oi_data: Open Interest values aligned with candles
            
        Returns:
            Divergence if detected, None otherwise
        """
        # Similar logic to CVD divergence
        # Implementation follows same pattern as detect_cvd_divergence
        # For brevity, returning None for now (can be implemented if OI data is available)
        return None
    
    def detect_funding_divergence(self, candles: List[Dict], funding_data: List[float]) -> Optional[Divergence]:
        """
        Detect divergence between price and Funding Rate.
        
        Args:
            candles: OHLCV candle data
            funding_data: Funding Rate values aligned with candles
            
        Returns:
            Divergence if detected, None otherwise
        """
        # Similar logic to CVD divergence
        # Implementation follows same pattern as detect_cvd_divergence
        # For brevity, returning None for now (can be implemented if funding data is available)
        return None
    
    def calculate_divergence_strength(self, price_swing_pct: float, indicator_swing_pct: float) -> float:
        """
        Calculate 0-100 strength score based on magnitude of divergence.
        
        Stronger divergence = larger difference between price and indicator swings.
        
        Args:
            price_swing_pct: Price swing percentage
            indicator_swing_pct: Indicator swing percentage
            
        Returns:
            Strength score (0-100)
        """
        # Calculate the difference in swing magnitudes
        divergence_magnitude = abs(abs(price_swing_pct) - abs(indicator_swing_pct))
        
        # Normalize to 0-100 scale
        # Assume 10% divergence = 100 strength
        strength = min(100, (divergence_magnitude / 10.0) * 100)
        
        return round(strength, 2)
    
    def classify_divergence_type(self, divergence: Divergence) -> str:
        """
        Classify as REGULAR (counter-trend) or HIDDEN (with-trend).
        
        Args:
            divergence: Divergence to classify
            
        Returns:
            Classification string
        """
        return divergence.divergence_class
    
    def _find_swings(self, candles: List[Dict]) -> List[Dict]:
        """
        Find price swing highs and lows.
        
        Args:
            candles: OHLCV candle data
            
        Returns:
            List of swing points with metadata
        """
        if len(candles) < 5:
            return []
        
        swings = []
        min_swing_pct = self.config["min_swing_size_pct"]
        
        # Find local highs and lows
        for i in range(2, len(candles) - 2):
            current_high = candles[i]["high"]
            current_low = candles[i]["low"]
            
            # Check if it's a local high
            is_high = (current_high > candles[i-1]["high"] and 
                      current_high > candles[i-2]["high"] and
                      current_high > candles[i+1]["high"] and
                      current_high > candles[i+2]["high"])
            
            # Check if it's a local low
            is_low = (current_low < candles[i-1]["low"] and 
                     current_low < candles[i-2]["low"] and
                     current_low < candles[i+1]["low"] and
                     current_low < candles[i+2]["low"])
            
            if is_high:
                # Find previous high to compare
                prev_high = None
                for swing in reversed(swings):
                    if swing["type"] == "HIGH":
                        prev_high = swing
                        break
                
                if prev_high:
                    change_pct = (current_high - prev_high["value"]) / prev_high["value"] * 100
                    
                    # Only record if swing is significant
                    if abs(change_pct) >= min_swing_pct:
                        swings.append({
                            "type": "HIGH",
                            "value": current_high,
                            "prev_value": prev_high["value"],
                            "change_pct": change_pct,
                            "is_lower": change_pct < 0,  # Lower high
                            "index": i
                        })
                else:
                    # First high
                    swings.append({
                        "type": "HIGH",
                        "value": current_high,
                        "prev_value": current_high,
                        "change_pct": 0,
                        "is_lower": False,
                        "index": i
                    })
            
            elif is_low:
                # Find previous low to compare
                prev_low = None
                for swing in reversed(swings):
                    if swing["type"] == "LOW":
                        prev_low = swing
                        break
                
                if prev_low:
                    change_pct = (current_low - prev_low["value"]) / prev_low["value"] * 100
                    
                    # Only record if swing is significant
                    if abs(change_pct) >= min_swing_pct:
                        swings.append({
                            "type": "LOW",
                            "value": current_low,
                            "prev_value": prev_low["value"],
                            "change_pct": change_pct,
                            "is_lower": change_pct < 0,  # Lower low
                            "index": i
                        })
                else:
                    # First low
                    swings.append({
                        "type": "LOW",
                        "value": current_low,
                        "prev_value": current_low,
                        "change_pct": 0,
                        "is_lower": False,
                        "index": i
                    })
        
        return swings
    
    def _find_indicator_swings(self, indicator_data: List[float]) -> List[Dict]:
        """
        Find indicator swing highs and lows.
        
        Args:
            indicator_data: Indicator values
            
        Returns:
            List of swing points with metadata
        """
        if len(indicator_data) < 5:
            return []
        
        swings = []
        min_swing_pct = self.config["min_swing_size_pct"]
        
        # Find local highs and lows
        for i in range(2, len(indicator_data) - 2):
            current = indicator_data[i]
            
            # Check if it's a local high
            is_high = (current > indicator_data[i-1] and 
                      current > indicator_data[i-2] and
                      current > indicator_data[i+1] and
                      current > indicator_data[i+2])
            
            # Check if it's a local low
            is_low = (current < indicator_data[i-1] and 
                     current < indicator_data[i-2] and
                     current < indicator_data[i+1] and
                     current < indicator_data[i+2])
            
            if is_high:
                # Find previous high to compare
                prev_high = None
                for swing in reversed(swings):
                    if swing["type"] == "HIGH":
                        prev_high = swing
                        break
                
                if prev_high:
                    change_pct = (current - prev_high["value"]) / abs(prev_high["value"]) * 100 if prev_high["value"] != 0 else 0
                    
                    # Only record if swing is significant
                    if abs(change_pct) >= min_swing_pct:
                        swings.append({
                            "type": "HIGH",
                            "value": current,
                            "prev_value": prev_high["value"],
                            "change_pct": change_pct,
                            "is_lower": change_pct < 0,  # Lower high
                            "index": i
                        })
                else:
                    # First high
                    swings.append({
                        "type": "HIGH",
                        "value": current,
                        "prev_value": current,
                        "change_pct": 0,
                        "is_lower": False,
                        "index": i
                    })
            
            elif is_low:
                # Find previous low to compare
                prev_low = None
                for swing in reversed(swings):
                    if swing["type"] == "LOW":
                        prev_low = swing
                        break
                
                if prev_low:
                    change_pct = (current - prev_low["value"]) / abs(prev_low["value"]) * 100 if prev_low["value"] != 0 else 0
                    
                    # Only record if swing is significant
                    if abs(change_pct) >= min_swing_pct:
                        swings.append({
                            "type": "LOW",
                            "value": current,
                            "prev_value": prev_low["value"],
                            "change_pct": change_pct,
                            "is_lower": change_pct < 0,  # Lower low
                            "index": i
                        })
                else:
                    # First low
                    swings.append({
                        "type": "LOW",
                        "value": current,
                        "prev_value": current,
                        "change_pct": 0,
                        "is_lower": False,
                        "index": i
                    })
        
        return swings
    
    def _calculate_confidence_boost(self, strength: float, divergence_class: str) -> float:
        """
        Calculate confidence boost based on divergence strength and class.
        
        Args:
            strength: Divergence strength (0-100)
            divergence_class: REGULAR or HIDDEN
            
        Returns:
            Confidence boost value
        """
        if divergence_class == "REGULAR":
            # Regular divergence with strength >75% adds +20% confidence
            if strength > self.config["high_strength_threshold"]:
                return self.config["regular_divergence_boost"]
            else:
                # Scale boost based on strength
                return (strength / self.config["high_strength_threshold"]) * self.config["regular_divergence_boost"]
        
        elif divergence_class == "HIDDEN":
            # Hidden divergence adds +10% confidence
            return self.config["hidden_divergence_boost"]
        
        return 0.0
    
    def _get_dominant_divergence(self, divergences: List[Divergence]) -> Optional[Divergence]:
        """
        Get the most significant divergence from the list.
        
        Args:
            divergences: List of detected divergences
            
        Returns:
            Dominant divergence or None
        """
        if not divergences:
            return None
        
        # Sort by strength and confidence boost (prefer high-strength regular divergences)
        sorted_divergences = sorted(
            divergences,
            key=lambda d: (d.strength, d.confidence_boost),
            reverse=True
        )
        
        return sorted_divergences[0]
    
    def _calculate_aggregate_score(self, divergences: List[Divergence], 
                                   dominant_divergence: Optional[Divergence]) -> float:
        """
        Calculate aggregate divergence score (0-100).
        
        Higher score = stronger divergence signal quality.
        
        Args:
            divergences: All detected divergences
            dominant_divergence: Most significant divergence
            
        Returns:
            Aggregate score (0-100)
        """
        if not divergences:
            return 50.0  # Neutral
        
        if not dominant_divergence:
            return 50.0
        
        # Base score from dominant divergence strength
        base_score = dominant_divergence.strength
        
        # Boost if multiple divergences agree
        bullish_count = sum(1 for d in divergences if d.divergence_type == "BULLISH")
        bearish_count = sum(1 for d in divergences if d.divergence_type == "BEARISH")
        
        # Agreement boost (max +15)
        if bullish_count > bearish_count:
            agreement_boost = min(15, bullish_count * 5)
        elif bearish_count > bullish_count:
            agreement_boost = min(15, bearish_count * 5)
        else:
            agreement_boost = 0
        
        final_score = min(100, base_score + agreement_boost)
        return round(final_score, 2)
    
    def _determine_bias(self, divergences: List[Divergence], 
                       dominant_divergence: Optional[Divergence]) -> str:
        """
        Determine overall divergence bias (BULLISH, BEARISH, NEUTRAL).
        
        Args:
            divergences: All detected divergences
            dominant_divergence: Most significant divergence
            
        Returns:
            Bias string
        """
        if not divergences or not dominant_divergence:
            return "NEUTRAL"
        
        # Count bullish vs bearish divergences
        bullish_count = sum(1 for d in divergences if d.divergence_type == "BULLISH")
        bearish_count = sum(1 for d in divergences if d.divergence_type == "BEARISH")
        
        # Weight by strength
        bullish_weight = sum(d.strength for d in divergences if d.divergence_type == "BULLISH")
        bearish_weight = sum(d.strength for d in divergences if d.divergence_type == "BEARISH")
        
        # Determine bias
        if bullish_weight > bearish_weight * 1.2:  # 20% threshold
            return "BULLISH"
        elif bearish_weight > bullish_weight * 1.2:
            return "BEARISH"
        else:
            return "NEUTRAL"
