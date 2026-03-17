"""
Reversal Pattern Detection - Professional Candlestick Analysis

Implements classic and advanced reversal patterns with confidence scoring.
Based on Japanese candlestick theory and modern price action analysis.

Patterns Implemented:
- Pin Bar (Hammer/Shooting Star)
- Engulfing (Bullish/Bearish)
- Doji (Indecision)
- Morning Star / Evening Star
- Three White Soldiers / Three Black Crows
- Tweezer Top / Bottom
- Dark Cloud Cover / Piercing Pattern

Each pattern returns a confidence score (0-100) based on:
- Pattern quality (wick/body ratios)
- Volume confirmation
- Context (trend, support/resistance)
"""

from typing import List, Dict, Optional
from utils.logger import get_logger

log = get_logger("analytics.reversal_patterns")


class ReversalPatterns:
    """
    Professional candlestick reversal pattern detection.
    
    Returns confidence scores, not binary signals.
    """
    
    def __init__(self):
        log.info("ReversalPatterns initialized")
    
    def analyze(self, candles: List[Dict], context: Dict = None) -> Dict:
        """
        Analyze candles for all reversal patterns.
        
        Args:
            candles: List of candle dicts (need at least 3-5 for patterns)
            context: Optional context (trend, volume, support/resistance)
        
        Returns:
            {
                'pin_bar': {...},
                'engulfing': {...},
                'doji': {...},
                'morning_evening_star': {...},
                'three_soldiers_crows': {...},
                'tweezer': {...},
                'cloud_piercing': {...},
                'best_pattern': {...},  # Highest confidence pattern
            }
        """
        if not candles or len(candles) < 3:
            return {}
        
        results = {
            'pin_bar': self.detect_pin_bar(candles),
            'engulfing': self.detect_engulfing(candles),
            'doji': self.detect_doji(candles),
            'morning_evening_star': self.detect_star_patterns(candles),
            'three_soldiers_crows': self.detect_three_pattern(candles),
            'tweezer': self.detect_tweezer(candles),
            'cloud_piercing': self.detect_cloud_piercing(candles),
        }
        
        # Find best pattern
        best = None
        best_confidence = 0
        
        for pattern_name, pattern_data in results.items():
            if pattern_data and pattern_data.get('detected'):
                confidence = pattern_data.get('confidence', 0)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best = {
                        'name': pattern_name,
                        **pattern_data
                    }
        
        results['best_pattern'] = best
        
        return results
    
    def detect_pin_bar(self, candles: List[Dict]) -> Dict:
        """
        Detect Pin Bar (Hammer/Shooting Star).
        
        Characteristics:
        - Long wick (2-3x body size)
        - Small body
        - Little to no opposite wick
        - Bullish: long lower wick (rejection of lows)
        - Bearish: long upper wick (rejection of highs)
        
        Confidence factors:
        - Wick/body ratio (higher = better)
        - Body position (closer to opposite end = better)
        - Volume (higher = better)
        """
        if len(candles) < 1:
            return {'detected': False}
        
        candle = candles[-1]
        
        open_price = candle['open']
        close = candle['close']
        high = candle['high']
        low = candle['low']
        
        body = abs(close - open_price)
        total_range = high - low
        
        if total_range == 0:
            return {'detected': False}
        
        upper_wick = high - max(open_price, close)
        lower_wick = min(open_price, close) - low
        
        # Bullish Pin Bar (Hammer)
        if lower_wick > body * 2 and upper_wick < body * 0.3:
            confidence = min(100, 50 + (lower_wick / body) * 10)
            
            # Volume boost
            if len(candles) >= 5:
                avg_volume = sum(c['volume'] for c in candles[-5:-1]) / 4
                if candle['volume'] > avg_volume * 1.2:
                    confidence += 10
            
            return {
                'detected': True,
                'type': 'BULLISH_PIN_BAR',
                'direction': 'LONG',
                'confidence': round(min(100, confidence), 1),
                'wick_body_ratio': round(lower_wick / body, 2) if body > 0 else 0,
                'description': 'Bullish Pin Bar (Hammer) - rejection of lows',
            }
        
        # Bearish Pin Bar (Shooting Star)
        elif upper_wick > body * 2 and lower_wick < body * 0.3:
            confidence = min(100, 50 + (upper_wick / body) * 10)
            
            if len(candles) >= 5:
                avg_volume = sum(c['volume'] for c in candles[-5:-1]) / 4
                if candle['volume'] > avg_volume * 1.2:
                    confidence += 10
            
            return {
                'detected': True,
                'type': 'BEARISH_PIN_BAR',
                'direction': 'SHORT',
                'confidence': round(min(100, confidence), 1),
                'wick_body_ratio': round(upper_wick / body, 2) if body > 0 else 0,
                'description': 'Bearish Pin Bar (Shooting Star) - rejection of highs',
            }
        
        return {'detected': False}
    
    def detect_engulfing(self, candles: List[Dict]) -> Dict:
        """
        Detect Engulfing Pattern.
        
        Bullish Engulfing:
        - Previous candle bearish
        - Current candle bullish
        - Current body completely engulfs previous body
        
        Bearish Engulfing:
        - Previous candle bullish
        - Current candle bearish
        - Current body completely engulfs previous body
        """
        if len(candles) < 2:
            return {'detected': False}
        
        prev = candles[-2]
        curr = candles[-1]
        
        prev_body = abs(prev['close'] - prev['open'])
        curr_body = abs(curr['close'] - curr['open'])
        
        prev_is_bearish = prev['close'] < prev['open']
        curr_is_bullish = curr['close'] > curr['open']
        
        # Bullish Engulfing
        if prev_is_bearish and curr_is_bullish:
            if curr['open'] <= prev['close'] and curr['close'] >= prev['open']:
                confidence = 60
                
                # Size matters
                if curr_body > prev_body * 1.5:
                    confidence += 15
                
                # Volume confirmation
                if curr['volume'] > prev['volume'] * 1.2:
                    confidence += 15
                
                return {
                    'detected': True,
                    'type': 'BULLISH_ENGULFING',
                    'direction': 'LONG',
                    'confidence': round(min(100, confidence), 1),
                    'size_ratio': round(curr_body / prev_body, 2) if prev_body > 0 else 0,
                    'description': 'Bullish Engulfing - strong reversal signal',
                }
        
        # Bearish Engulfing
        elif not prev_is_bearish and not curr_is_bullish:
            if curr['open'] >= prev['close'] and curr['close'] <= prev['open']:
                confidence = 60
                
                if curr_body > prev_body * 1.5:
                    confidence += 15
                
                if curr['volume'] > prev['volume'] * 1.2:
                    confidence += 15
                
                return {
                    'detected': True,
                    'type': 'BEARISH_ENGULFING',
                    'direction': 'SHORT',
                    'confidence': round(min(100, confidence), 1),
                    'size_ratio': round(curr_body / prev_body, 2) if prev_body > 0 else 0,
                    'description': 'Bearish Engulfing - strong reversal signal',
                }
        
        return {'detected': False}
    
    def detect_doji(self, candles: List[Dict]) -> Dict:
        """
        Detect Doji Pattern.
        
        Characteristics:
        - Open ≈ Close (body < 10% of total range)
        - Indicates indecision
        - Potential reversal at extremes
        """
        if len(candles) < 1:
            return {'detected': False}
        
        candle = candles[-1]
        
        body = abs(candle['close'] - candle['open'])
        total_range = candle['high'] - candle['low']
        
        if total_range == 0:
            return {'detected': False}
        
        body_pct = body / total_range * 100
        
        if body_pct < 10:
            confidence = 50 + (10 - body_pct) * 3
            
            return {
                'detected': True,
                'type': 'DOJI',
                'direction': 'NEUTRAL',
                'confidence': round(min(100, confidence), 1),
                'body_pct': round(body_pct, 2),
                'description': 'Doji - indecision, potential reversal',
            }
        
        return {'detected': False}
    
    def detect_star_patterns(self, candles: List[Dict]) -> Dict:
        """
        Detect Morning Star / Evening Star.
        
        3-candle pattern:
        Morning Star (bullish):
        1. Large bearish candle
        2. Small body (star) - gap down
        3. Large bullish candle
        
        Evening Star (bearish):
        1. Large bullish candle
        2. Small body (star) - gap up
        3. Large bearish candle
        """
        if len(candles) < 3:
            return {'detected': False}
        
        c1 = candles[-3]
        c2 = candles[-2]  # Star
        c3 = candles[-1]
        
        c1_body = abs(c1['close'] - c1['open'])
        c2_body = abs(c2['close'] - c2['open'])
        c3_body = abs(c3['close'] - c3['open'])
        
        c1_range = c1['high'] - c1['low']
        c2_range = c2['high'] - c2['low']
        
        # Morning Star
        if (c1['close'] < c1['open'] and  # Bearish
            c2_body < c1_body * 0.3 and  # Small star
            c3['close'] > c3['open'] and  # Bullish
            c3_body > c1_body * 0.5):  # Large
            
            confidence = 65
            
            # Gap confirmation
            if c2['high'] < c1['close']:
                confidence += 10
            if c3['close'] > (c1['open'] + c1['close']) / 2:
                confidence += 10
            
            return {
                'detected': True,
                'type': 'MORNING_STAR',
                'direction': 'LONG',
                'confidence': round(min(100, confidence), 1),
                'description': 'Morning Star - strong bullish reversal',
            }
        
        # Evening Star
        elif (c1['close'] > c1['open'] and  # Bullish
              c2_body < c1_body * 0.3 and  # Small star
              c3['close'] < c3['open'] and  # Bearish
              c3_body > c1_body * 0.5):  # Large
            
            confidence = 65
            
            if c2['low'] > c1['close']:
                confidence += 10
            if c3['close'] < (c1['open'] + c1['close']) / 2:
                confidence += 10
            
            return {
                'detected': True,
                'type': 'EVENING_STAR',
                'direction': 'SHORT',
                'confidence': round(min(100, confidence), 1),
                'description': 'Evening Star - strong bearish reversal',
            }
        
        return {'detected': False}
    
    def detect_three_pattern(self, candles: List[Dict]) -> Dict:
        """
        Detect Three White Soldiers / Three Black Crows.
        
        3 consecutive candles in same direction with progressively higher/lower closes.
        """
        if len(candles) < 3:
            return {'detected': False}
        
        c1, c2, c3 = candles[-3], candles[-2], candles[-1]
        
        # Three White Soldiers (bullish)
        if (c1['close'] > c1['open'] and
            c2['close'] > c2['open'] and
            c3['close'] > c3['open'] and
            c2['close'] > c1['close'] and
            c3['close'] > c2['close']):
            
            return {
                'detected': True,
                'type': 'THREE_WHITE_SOLDIERS',
                'direction': 'LONG',
                'confidence': 70,
                'description': 'Three White Soldiers - strong bullish continuation',
            }
        
        # Three Black Crows (bearish)
        elif (c1['close'] < c1['open'] and
              c2['close'] < c2['open'] and
              c3['close'] < c3['open'] and
              c2['close'] < c1['close'] and
              c3['close'] < c2['close']):
            
            return {
                'detected': True,
                'type': 'THREE_BLACK_CROWS',
                'direction': 'SHORT',
                'confidence': 70,
                'description': 'Three Black Crows - strong bearish continuation',
            }
        
        return {'detected': False}
    
    def detect_tweezer(self, candles: List[Dict]) -> Dict:
        """Detect Tweezer Top/Bottom - same highs/lows."""
        if len(candles) < 2:
            return {'detected': False}
        
        c1, c2 = candles[-2], candles[-1]
        
        # Tweezer Bottom (bullish)
        if abs(c1['low'] - c2['low']) / c1['low'] < 0.001:
            return {
                'detected': True,
                'type': 'TWEEZER_BOTTOM',
                'direction': 'LONG',
                'confidence': 55,
                'description': 'Tweezer Bottom - support confirmation',
            }
        
        # Tweezer Top (bearish)
        elif abs(c1['high'] - c2['high']) / c1['high'] < 0.001:
            return {
                'detected': True,
                'type': 'TWEEZER_TOP',
                'direction': 'SHORT',
                'confidence': 55,
                'description': 'Tweezer Top - resistance confirmation',
            }
        
        return {'detected': False}
    
    def detect_cloud_piercing(self, candles: List[Dict]) -> Dict:
        """Detect Dark Cloud Cover / Piercing Pattern."""
        if len(candles) < 2:
            return {'detected': False}
        
        c1, c2 = candles[-2], candles[-1]
        
        c1_mid = (c1['open'] + c1['close']) / 2
        
        # Piercing Pattern (bullish)
        if (c1['close'] < c1['open'] and  # Bearish
            c2['close'] > c2['open'] and  # Bullish
            c2['open'] < c1['low'] and  # Gap down
            c2['close'] > c1_mid):  # Closes above midpoint
            
            return {
                'detected': True,
                'type': 'PIERCING_PATTERN',
                'direction': 'LONG',
                'confidence': 65,
                'description': 'Piercing Pattern - bullish reversal',
            }
        
        # Dark Cloud Cover (bearish)
        elif (c1['close'] > c1['open'] and  # Bullish
              c2['close'] < c2['open'] and  # Bearish
              c2['open'] > c1['high'] and  # Gap up
              c2['close'] < c1_mid):  # Closes below midpoint
            
            return {
                'detected': True,
                'type': 'DARK_CLOUD_COVER',
                'direction': 'SHORT',
                'confidence': 65,
                'description': 'Dark Cloud Cover - bearish reversal',
            }
        
        return {'detected': False}
