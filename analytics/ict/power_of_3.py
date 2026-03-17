"""
Power of 3 - ICT Market Manipulation Model

ICT's Power of 3 describes how institutional traders manipulate markets in 3 phases:

1. ACCUMULATION: Consolidation phase where smart money builds positions
   - Low volatility
   - Tight range
   - Volume declining
   - Price coiling for move

2. MANIPULATION: False breakout (Judas Swing) to trap retail traders
   - Sudden spike/drop
   - Breaks key level
   - Triggers stops
   - Reverses quickly
   - "Stop hunt" or "liquidity grab"

3. DISTRIBUTION: True directional move after manipulation
   - Strong momentum
   - Volume expansion
   - Sustained move
   - Smart money exits into retail flow

"The market must first manipulate before it distributes."
"""

from typing import List, Dict, Optional
from utils.logger import get_logger

log = get_logger("analytics.ict.power_of_3")


class PowerOf3Analyzer:
    """
    Power of 3 - Market manipulation phase detection.
    
    Identifies the 3 phases of institutional market manipulation:
    1. Accumulation (consolidation)
    2. Manipulation (Judas swing / false breakout)
    3. Distribution (true move)
    """
    
    def __init__(self):
        self.phases = {
            'ACCUMULATION': {
                'description': 'Consolidation - smart money building positions',
                'confidence_boost': 5,
            },
            'MANIPULATION': {
                'description': 'False breakout - stop hunt in progress',
                'confidence_boost': 15,  # High boost for reversal after manipulation
            },
            'DISTRIBUTION': {
                'description': 'True move - smart money distributing',
                'confidence_boost': 10,
            },
        }
        
        log.info("Power of 3 Analyzer initialized")
    
    def detect_phase(self, candles: List[Dict], lookback: int = 20) -> Dict:
        """
        Detect current Power of 3 phase.
        
        Args:
            candles: List of candle dicts (oldest first)
            lookback: Number of candles to analyze
        
        Returns:
            Dict with phase detection and confidence boost
        """
        if not candles or len(candles) < lookback:
            return {'phase': 'UNKNOWN', 'confidence_boost': 0}
        
        recent = candles[-lookback:]
        
        # Calculate volatility (ATR-like)
        volatility = self._calculate_volatility(recent)
        
        # Calculate range tightness
        range_tightness = self._calculate_range_tightness(recent)
        
        # Detect false breakout (Judas swing)
        judas_swing = self._detect_judas_swing(recent)
        
        # Detect strong momentum (distribution)
        strong_momentum = self._detect_strong_momentum(recent)
        
        # Classify phase
        if judas_swing['detected']:
            phase = 'MANIPULATION'
            confidence_boost = self.phases['MANIPULATION']['confidence_boost']
            description = f"Judas swing detected - {judas_swing['direction']} trap"
            signal = 'LONG' if judas_swing['reversal_direction'] == 'BULLISH' else 'SHORT'
        
        elif strong_momentum['detected']:
            phase = 'DISTRIBUTION'
            confidence_boost = self.phases['DISTRIBUTION']['confidence_boost']
            description = f"Strong {strong_momentum['direction']} momentum - distribution phase"
            signal = strong_momentum['direction']
        
        elif range_tightness > 0.7:  # Tight range = accumulation
            phase = 'ACCUMULATION'
            confidence_boost = self.phases['ACCUMULATION']['confidence_boost']
            description = "Consolidation - accumulation phase"
            signal = 'NEUTRAL'
        
        else:
            phase = 'UNKNOWN'
            confidence_boost = 0
            description = "Phase unclear"
            signal = 'NEUTRAL'
        
        return {
            'phase': phase,
            'confidence_boost': confidence_boost,
            'description': description,
            'signal': signal,
            'volatility': round(volatility, 4),
            'range_tightness': round(range_tightness, 4),
            'judas_swing': judas_swing,
            'strong_momentum': strong_momentum,
        }
    
    def _calculate_volatility(self, candles: List[Dict]) -> float:
        """Calculate average true range (volatility)."""
        if len(candles) < 2:
            return 0
        
        atr_values = []
        for i in range(1, len(candles)):
            high = candles[i]['high']
            low = candles[i]['low']
            prev_close = candles[i-1]['close']
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            atr_values.append(tr)
        
        return sum(atr_values) / len(atr_values) if atr_values else 0
    
    def _calculate_range_tightness(self, candles: List[Dict]) -> float:
        """
        Calculate how tight the range is (0-1).
        
        1.0 = very tight (accumulation)
        0.0 = very wide (distribution)
        """
        if not candles:
            return 0
        
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        
        overall_high = max(highs)
        overall_low = min(lows)
        overall_range = overall_high - overall_low
        
        if overall_range == 0:
            return 1.0
        
        # Calculate average candle range
        avg_candle_range = sum(c['high'] - c['low'] for c in candles) / len(candles)
        
        # Tightness = avg candle range / overall range
        # Higher value = tighter (more consolidation)
        tightness = avg_candle_range / overall_range if overall_range > 0 else 0
        
        return min(1.0, tightness * 10)  # Scale up for better sensitivity
    
    def _detect_judas_swing(self, candles: List[Dict]) -> Dict:
        """
        Detect Judas Swing (false breakout).
        
        Characteristics:
        - Price breaks a key level (high/low)
        - Reverses quickly (within 1-3 candles)
        - Creates a wick/rejection
        - Traps breakout traders
        """
        if len(candles) < 5:
            return {'detected': False}
        
        # Look at last 5 candles
        recent_5 = candles[-5:]
        
        # Find recent high and low (excluding last candle)
        prev_4 = recent_5[:-1]
        recent_high = max(c['high'] for c in prev_4)
        recent_low = min(c['low'] for c in prev_4)
        
        last_candle = recent_5[-1]
        
        # Check for bullish Judas (false breakdown)
        if last_candle['low'] < recent_low:
            # Broke below recent low
            if last_candle['close'] > recent_low:
                # But closed back above = false breakdown
                wick_size = last_candle['close'] - last_candle['low']
                body_size = abs(last_candle['close'] - last_candle['open'])
                
                if wick_size > body_size * 1.5:  # Significant wick
                    return {
                        'detected': True,
                        'direction': 'BEARISH_TRAP',
                        'reversal_direction': 'BULLISH',
                        'level_broken': round(recent_low, 2),
                        'wick_size_pct': round(wick_size / last_candle['close'] * 100, 3),
                    }
        
        # Check for bearish Judas (false breakout)
        if last_candle['high'] > recent_high:
            # Broke above recent high
            if last_candle['close'] < recent_high:
                # But closed back below = false breakout
                wick_size = last_candle['high'] - last_candle['close']
                body_size = abs(last_candle['close'] - last_candle['open'])
                
                if wick_size > body_size * 1.5:
                    return {
                        'detected': True,
                        'direction': 'BULLISH_TRAP',
                        'reversal_direction': 'BEARISH',
                        'level_broken': round(recent_high, 2),
                        'wick_size_pct': round(wick_size / last_candle['close'] * 100, 3),
                    }
        
        return {'detected': False}
    
    def _detect_strong_momentum(self, candles: List[Dict]) -> Dict:
        """
        Detect strong directional momentum (distribution phase).
        
        Characteristics:
        - 3+ consecutive candles in same direction
        - Increasing range
        - Strong closes (near high/low)
        """
        if len(candles) < 3:
            return {'detected': False}
        
        last_3 = candles[-3:]
        
        # Check for 3 bullish candles
        all_bullish = all(c['close'] > c['open'] for c in last_3)
        if all_bullish:
            # Check if closes are strong (near highs)
            strong_closes = all(
                (c['close'] - c['low']) / (c['high'] - c['low']) > 0.7
                for c in last_3 if c['high'] != c['low']
            )
            
            if strong_closes:
                return {
                    'detected': True,
                    'direction': 'LONG',
                    'strength': 'STRONG',
                }
        
        # Check for 3 bearish candles
        all_bearish = all(c['close'] < c['open'] for c in last_3)
        if all_bearish:
            strong_closes = all(
                (c['high'] - c['close']) / (c['high'] - c['low']) > 0.7
                for c in last_3 if c['high'] != c['low']
            )
            
            if strong_closes:
                return {
                    'detected': True,
                    'direction': 'SHORT',
                    'strength': 'STRONG',
                }
        
        return {'detected': False}
