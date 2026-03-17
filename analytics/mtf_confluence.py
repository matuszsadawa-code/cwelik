"""
Multi-Timeframe Confluence System

Analyzes confluence across multiple timeframes (1M, 5M, 15M, 1H, 4H) to increase
signal accuracy through cross-timeframe validation.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TrendAlignment:
    """Trend alignment across timeframes"""
    trends: Dict[str, str]  # timeframe -> BULLISH/BEARISH/NEUTRAL
    alignment_pct: float  # % of timeframes agreeing
    dominant_trend: str  # BULLISH, BEARISH, NEUTRAL


@dataclass
class ConfluenceZone:
    """High confluence zone where 3+ timeframes show same level"""
    price_level: float
    timeframes: List[str]  # Which timeframes show this level
    zone_type: str  # SUPPORT, RESISTANCE
    strength: float  # 0-100


@dataclass
class TimeframeDivergence:
    """Conflicting trends between timeframes"""
    lower_tf_trend: str
    higher_tf_trend: str
    severity: float  # 0-100
    recommendation: str  # AVOID, REDUCE_SIZE, PROCEED_WITH_CAUTION


@dataclass
class MTFAnalysis:
    """Complete multi-timeframe analysis"""
    timeframe_alignment_score: float  # 0-100
    trend_alignment: TrendAlignment
    confluence_zones: List[ConfluenceZone]
    timeframe_divergence: Optional[TimeframeDivergence]
    confidence_adjustment: float  # +/- confidence based on MTF


class MultiTimeframeAnalyzer:
    """
    Analyzes confluence across multiple timeframes to validate signals.
    
    Integrates with Signal_Engine after all single-timeframe analysis.
    """
    
    def __init__(self, candle_manager):
        """
        Initialize Multi-Timeframe Analyzer.
        
        Args:
            candle_manager: CandleManager instance for fetching multi-timeframe data
        """
        self.candle_mgr = candle_manager
        self.timeframes = ["1", "5", "15", "60", "240"]  # 1M, 5M, 15M, 1H, 4H
        self.level_tolerance_pct = 0.5  # 0.5% tolerance for level alignment
        self.min_confluence_timeframes = 3  # Min 3 TFs for high confluence
    
    def analyze_confluence(self, symbol: str, current_price: float) -> MTFAnalysis:
        """
        Analyze confluence across all timeframes.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            MTFAnalysis with alignment scores and confluence zones
        """
        try:
            # Calculate trend alignment
            trend_alignment = self.calculate_trend_alignment(symbol)
            
            # Detect level alignment (support/resistance)
            confluence_zones = self.identify_high_confluence_zones(symbol, current_price)
            
            # Detect timeframe divergence
            timeframe_divergence = self.detect_timeframe_divergence(symbol)
            
            # Calculate overall alignment score
            alignment_score = self._calculate_alignment_score(
                trend_alignment, confluence_zones, timeframe_divergence
            )
            
            # Calculate confidence adjustment
            confidence_adjustment = self._calculate_confidence_adjustment(
                trend_alignment, timeframe_divergence
            )
            
            return MTFAnalysis(
                timeframe_alignment_score=alignment_score,
                trend_alignment=trend_alignment,
                confluence_zones=confluence_zones,
                timeframe_divergence=timeframe_divergence,
                confidence_adjustment=confidence_adjustment
            )
            
        except Exception as e:
            # Return neutral analysis on error
            return self._get_neutral_analysis()
    
    def calculate_trend_alignment(self, symbol: str) -> TrendAlignment:
        """
        Check if all timeframes show same trend direction.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            TrendAlignment with per-timeframe trends and alignment score
        """
        trends = {}
        
        for tf in self.timeframes:
            try:
                candles = self.candle_mgr.get_candles(symbol, tf, limit=50)
                if not candles or len(candles) < 20:
                    trends[tf] = "NEUTRAL"
                    continue
                
                # Simple trend detection: compare recent price to moving average
                trend = self._detect_trend(candles)
                trends[tf] = trend
                
            except Exception as e:
                trends[tf] = "NEUTRAL"
        
        # Calculate alignment
        if not trends:
            return TrendAlignment(
                trends={},
                alignment_pct=0.0,
                dominant_trend="NEUTRAL"
            )
        
        # Count trend occurrences
        bullish_count = sum(1 for t in trends.values() if t == "BULLISH")
        bearish_count = sum(1 for t in trends.values() if t == "BEARISH")
        total_count = len(trends)
        
        # Determine dominant trend
        if bullish_count > bearish_count:
            dominant_trend = "BULLISH"
            alignment_pct = (bullish_count / total_count) * 100
        elif bearish_count > bullish_count:
            dominant_trend = "BEARISH"
            alignment_pct = (bearish_count / total_count) * 100
        else:
            dominant_trend = "NEUTRAL"
            alignment_pct = 0.0
        
        return TrendAlignment(
            trends=trends,
            alignment_pct=alignment_pct,
            dominant_trend=dominant_trend
        )
    
    def detect_level_alignment(self, symbol: str, price_level: float) -> int:
        """
        Count how many timeframes show support/resistance at this level.
        
        Args:
            symbol: Trading symbol
            price_level: Price level to check
            
        Returns:
            Number of timeframes (0-5) showing this level
        """
        count = 0
        tolerance = price_level * (self.level_tolerance_pct / 100)
        
        for tf in self.timeframes:
            try:
                candles = self.candle_mgr.get_candles(symbol, tf, limit=100)
                if not candles:
                    continue
                
                # Check if this level appears as support or resistance
                if self._is_level_significant(candles, price_level, tolerance):
                    count += 1
                    
            except Exception as e:
                pass
        
        return count
    
    def identify_high_confluence_zones(self, symbol: str, current_price: float) -> List[ConfluenceZone]:
        """
        Identify zones where 3+ timeframes show same level.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            List of high confluence zones
        """
        confluence_zones = []
        
        # Collect all significant levels from all timeframes
        all_levels = []
        
        for tf in self.timeframes:
            try:
                candles = self.candle_mgr.get_candles(symbol, tf, limit=100)
                if not candles:
                    continue
                
                # Find support and resistance levels
                levels = self._find_support_resistance_levels(candles)
                for level, zone_type in levels:
                    all_levels.append({
                        'price': level,
                        'timeframe': tf,
                        'zone_type': zone_type
                    })
                    
            except Exception as e:
                pass
        
        if not all_levels:
            return []
        
        # Group levels by price (with tolerance)
        grouped_levels = self._group_levels_by_price(all_levels)
        
        # Identify high confluence zones (3+ timeframes)
        for price, level_group in grouped_levels.items():
            if len(level_group) >= self.min_confluence_timeframes:
                # Determine zone type (majority vote)
                support_count = sum(1 for l in level_group if l['zone_type'] == 'SUPPORT')
                zone_type = 'SUPPORT' if support_count > len(level_group) / 2 else 'RESISTANCE'
                
                # Calculate strength based on number of timeframes
                strength = min(100, (len(level_group) / len(self.timeframes)) * 100)
                
                confluence_zones.append(ConfluenceZone(
                    price_level=price,
                    timeframes=[l['timeframe'] for l in level_group],
                    zone_type=zone_type,
                    strength=strength
                ))
        
        # Sort by strength (highest first)
        confluence_zones.sort(key=lambda z: z.strength, reverse=True)
        
        return confluence_zones
    
    def detect_timeframe_divergence(self, symbol: str) -> Optional[TimeframeDivergence]:
        """
        Detect when lower and higher timeframes show conflicting trends.
        
        Example: 5M bullish but 1H bearish
        
        Args:
            symbol: Trading symbol
            
        Returns:
            TimeframeDivergence if detected, None otherwise
        """
        try:
            # Get trends for lower timeframes (1M, 5M)
            lower_tf_trends = []
            for tf in ["1", "5"]:
                candles = self.candle_mgr.get_candles(symbol, tf, limit=50)
                if candles and len(candles) >= 20:
                    trend = self._detect_trend(candles)
                    if trend != "NEUTRAL":
                        lower_tf_trends.append(trend)
            
            # Get trends for higher timeframes (1H, 4H)
            higher_tf_trends = []
            for tf in ["60", "240"]:
                candles = self.candle_mgr.get_candles(symbol, tf, limit=50)
                if candles and len(candles) >= 20:
                    trend = self._detect_trend(candles)
                    if trend != "NEUTRAL":
                        higher_tf_trends.append(trend)
            
            if not lower_tf_trends or not higher_tf_trends:
                return None
            
            # Determine dominant trends
            lower_bullish = sum(1 for t in lower_tf_trends if t == "BULLISH")
            lower_bearish = sum(1 for t in lower_tf_trends if t == "BEARISH")
            
            higher_bullish = sum(1 for t in higher_tf_trends if t == "BULLISH")
            higher_bearish = sum(1 for t in higher_tf_trends if t == "BEARISH")
            
            lower_trend = "BULLISH" if lower_bullish > lower_bearish else "BEARISH" if lower_bearish > lower_bullish else "NEUTRAL"
            higher_trend = "BULLISH" if higher_bullish > higher_bearish else "BEARISH" if higher_bearish > higher_bullish else "NEUTRAL"
            
            # Check for divergence
            if lower_trend != "NEUTRAL" and higher_trend != "NEUTRAL" and lower_trend != higher_trend:
                # Calculate severity based on how strong the divergence is
                severity = 50.0  # Base severity
                
                # Increase severity if all lower TFs agree and all higher TFs agree
                if lower_bullish == len(lower_tf_trends) or lower_bearish == len(lower_tf_trends):
                    severity += 25.0
                if higher_bullish == len(higher_tf_trends) or higher_bearish == len(higher_tf_trends):
                    severity += 25.0
                
                severity = min(100.0, severity)
                
                # Determine recommendation
                if severity >= 75:
                    recommendation = "AVOID"
                elif severity >= 50:
                    recommendation = "REDUCE_SIZE"
                else:
                    recommendation = "PROCEED_WITH_CAUTION"
                
                return TimeframeDivergence(
                    lower_tf_trend=lower_trend,
                    higher_tf_trend=higher_trend,
                    severity=severity,
                    recommendation=recommendation
                )
            
            return None
            
        except Exception as e:
            return None
    
    def _detect_trend(self, candles: List[Dict]) -> str:
        """
        Simple trend detection using price vs moving average.
        
        Args:
            candles: List of candle data
            
        Returns:
            BULLISH, BEARISH, or NEUTRAL
        """
        if not candles or len(candles) < 20:
            return "NEUTRAL"
        
        # Calculate 20-period moving average
        closes = [c['close'] for c in candles[-20:]]
        ma = sum(closes) / len(closes)
        
        current_price = candles[-1]['close']
        
        # Calculate trend strength
        deviation_pct = ((current_price - ma) / ma) * 100
        
        # Classify trend
        if deviation_pct > 1.0:  # Price > 1% above MA
            return "BULLISH"
        elif deviation_pct < -1.0:  # Price > 1% below MA
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    def _is_level_significant(self, candles: List[Dict], level: float, tolerance: float) -> bool:
        """
        Check if a price level is significant (support/resistance).
        
        Args:
            candles: List of candle data
            level: Price level to check
            tolerance: Price tolerance
            
        Returns:
            True if level is significant
        """
        touches = 0
        
        for candle in candles:
            # Check if candle touched this level
            if (candle['low'] - tolerance <= level <= candle['high'] + tolerance):
                touches += 1
        
        # Level is significant if touched 2+ times
        return touches >= 2
    
    def _find_support_resistance_levels(self, candles: List[Dict]) -> List[Tuple[float, str]]:
        """
        Find support and resistance levels in candle data.
        
        Args:
            candles: List of candle data
            
        Returns:
            List of (price, zone_type) tuples
        """
        if not candles or len(candles) < 10:
            return []
        
        levels = []
        
        # Find swing highs and lows
        for i in range(2, len(candles) - 2):
            # Swing high (resistance)
            if (candles[i]['high'] > candles[i-1]['high'] and 
                candles[i]['high'] > candles[i-2]['high'] and
                candles[i]['high'] > candles[i+1]['high'] and 
                candles[i]['high'] > candles[i+2]['high']):
                levels.append((candles[i]['high'], 'RESISTANCE'))
            
            # Swing low (support)
            if (candles[i]['low'] < candles[i-1]['low'] and 
                candles[i]['low'] < candles[i-2]['low'] and
                candles[i]['low'] < candles[i+1]['low'] and 
                candles[i]['low'] < candles[i+2]['low']):
                levels.append((candles[i]['low'], 'SUPPORT'))
        
        return levels
    
    def _group_levels_by_price(self, all_levels: List[Dict]) -> Dict[float, List[Dict]]:
        """
        Group levels by price with tolerance.
        
        Args:
            all_levels: List of level dictionaries
            
        Returns:
            Dictionary mapping price to list of levels
        """
        grouped = {}
        
        for level in all_levels:
            price = level['price']
            tolerance = price * (self.level_tolerance_pct / 100)
            
            # Find existing group within tolerance
            found_group = False
            for group_price in list(grouped.keys()):
                if abs(price - group_price) <= tolerance:
                    grouped[group_price].append(level)
                    found_group = True
                    break
            
            # Create new group if not found
            if not found_group:
                grouped[price] = [level]
        
        return grouped
    
    def _calculate_alignment_score(self, trend_alignment: TrendAlignment, 
                                   confluence_zones: List[ConfluenceZone],
                                   timeframe_divergence: Optional[TimeframeDivergence]) -> float:
        """
        Calculate overall alignment score (0-100).
        
        Args:
            trend_alignment: Trend alignment data
            confluence_zones: List of confluence zones
            timeframe_divergence: Timeframe divergence if detected
            
        Returns:
            Alignment score (0-100)
        """
        score = 0.0
        
        # Trend alignment contributes 60% of score
        score += trend_alignment.alignment_pct * 0.6
        
        # Confluence zones contribute 30% of score
        if confluence_zones:
            max_confluence_strength = max(z.strength for z in confluence_zones)
            score += max_confluence_strength * 0.3
        
        # Timeframe divergence reduces score by 10%
        if timeframe_divergence:
            divergence_penalty = timeframe_divergence.severity * 0.1
            score -= divergence_penalty
        
        return max(0.0, min(100.0, score))
    
    def _calculate_confidence_adjustment(self, trend_alignment: TrendAlignment,
                                        timeframe_divergence: Optional[TimeframeDivergence]) -> float:
        """
        Calculate confidence adjustment based on MTF analysis.
        
        Requirements:
        - All timeframes aligned: +25% confidence
        - Timeframe divergence: -15% confidence
        
        Args:
            trend_alignment: Trend alignment data
            timeframe_divergence: Timeframe divergence if detected
            
        Returns:
            Confidence adjustment (+/- percentage)
        """
        adjustment = 0.0
        
        # All timeframes aligned: +25% boost
        if trend_alignment.alignment_pct == 100.0:
            adjustment += 25.0
        
        # Timeframe divergence: -15% penalty
        if timeframe_divergence:
            adjustment -= 15.0
        
        return adjustment
    
    def _get_neutral_analysis(self) -> MTFAnalysis:
        """
        Return neutral analysis (used on errors).
        
        Returns:
            Neutral MTFAnalysis
        """
        return MTFAnalysis(
            timeframe_alignment_score=50.0,
            trend_alignment=TrendAlignment(
                trends={},
                alignment_pct=0.0,
                dominant_trend="NEUTRAL"
            ),
            confluence_zones=[],
            timeframe_divergence=None,
            confidence_adjustment=0.0
        )
