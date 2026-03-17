"""
Optimal Trade Entry (OTE) - Fibonacci retracement analysis.

ICT methodology for identifying optimal entry points:
- 0.62 (62%) = Optimal entry (sweet spot)
- 0.705 (70.5%) = Deep retracement (still valid)
- 0.79 (79%) = Extreme retracement (last chance)
- 0.618-0.65 = Golden Pocket (highest probability)
- 0.5 (50%) = Equilibrium (fair value)

Price tends to retrace to these levels before continuing trend.
Entry at OTE levels provides best risk:reward ratio.
"""

from typing import Dict, List, Optional
from utils.logger import get_logger

log = get_logger("analytics.ict.ote")


class OptimalTradeEntry:
    """
    Optimal Trade Entry (OTE) - Fibonacci retracement analysis.
    
    Identifies optimal entry points based on Fibonacci retracements
    of recent swing highs and lows.
    """
    
    def __init__(self):
        # Fibonacci retracement levels
        self.fib_levels = {
            'ote_optimal': 0.62,           # Primary OTE level
            'ote_deep': 0.705,             # Deep but valid
            'ote_extreme': 0.79,           # Extreme retracement
            'equilibrium': 0.5,            # 50% fair value
            'golden_pocket_low': 0.618,    # Golden pocket start
            'golden_pocket_high': 0.65,    # Golden pocket end
        }
        
        log.info("Optimal Trade Entry (OTE) initialized")
    
    def calculate_ote_levels(self, swing_high: float, swing_low: float,
                            direction: str) -> Dict:
        """
        Calculate OTE levels for a swing.
        
        Args:
            swing_high: Recent swing high
            swing_low: Recent swing low
            direction: 'LONG' or 'SHORT'
        
        Returns:
            Dict with all OTE levels and metadata
        """
        if swing_high <= swing_low:
            log.warning(f"Invalid swing: high {swing_high} <= low {swing_low}")
            return {}
        
        range_size = swing_high - swing_low
        
        if direction == "LONG":
            # For longs, we want retracement from swing high down to OTE
            levels = {
                'swing_high': round(swing_high, 2),
                'swing_low': round(swing_low, 2),
                'range_size': round(range_size, 2),
                'ote_optimal': round(swing_low + range_size * self.fib_levels['ote_optimal'], 2),
                'ote_deep': round(swing_low + range_size * self.fib_levels['ote_deep'], 2),
                'ote_extreme': round(swing_low + range_size * self.fib_levels['ote_extreme'], 2),
                'equilibrium': round(swing_low + range_size * self.fib_levels['equilibrium'], 2),
                'golden_pocket_low': round(swing_low + range_size * self.fib_levels['golden_pocket_low'], 2),
                'golden_pocket_high': round(swing_low + range_size * self.fib_levels['golden_pocket_high'], 2),
                'direction': 'LONG',
            }
        else:  # SHORT
            # For shorts, we want retracement from swing low up to OTE
            levels = {
                'swing_high': round(swing_high, 2),
                'swing_low': round(swing_low, 2),
                'range_size': round(range_size, 2),
                'ote_optimal': round(swing_high - range_size * self.fib_levels['ote_optimal'], 2),
                'ote_deep': round(swing_high - range_size * self.fib_levels['ote_deep'], 2),
                'ote_extreme': round(swing_high - range_size * self.fib_levels['ote_extreme'], 2),
                'equilibrium': round(swing_high - range_size * self.fib_levels['equilibrium'], 2),
                'golden_pocket_low': round(swing_high - range_size * self.fib_levels['golden_pocket_high'], 2),
                'golden_pocket_high': round(swing_high - range_size * self.fib_levels['golden_pocket_low'], 2),
                'direction': 'SHORT',
            }
        
        return levels
    
    def check_ote_entry(self, current_price: float, ote_levels: Dict,
                       tolerance_pct: float = 0.5) -> Dict:
        """
        Check if current price is at an OTE level.
        
        Args:
            current_price: Current market price
            ote_levels: OTE levels from calculate_ote_levels()
            tolerance_pct: Tolerance for "at level" (default 0.5%)
        
        Returns:
            Dict with entry analysis and confidence boost
        """
        if not ote_levels:
            return {'at_ote': False, 'confidence_boost': 0}
        
        at_level = None
        confidence_boost = 0
        
        # Calculate distance to optimal level
        optimal_price = ote_levels.get('ote_optimal', 0)
        if optimal_price > 0:
            distance_to_optimal = abs(current_price - optimal_price) / optimal_price * 100
        else:
            distance_to_optimal = 999
        
        # Check each level
        for level_name in ['ote_optimal', 'ote_deep', 'ote_extreme', 'equilibrium']:
            level_price = ote_levels.get(level_name, 0)
            if level_price == 0:
                continue
            
            distance_pct = abs(current_price - level_price) / level_price * 100
            
            if distance_pct < tolerance_pct:
                at_level = level_name
                
                # Assign confidence boost based on level quality
                if level_name == 'ote_optimal':
                    confidence_boost = 15  # Highest boost
                elif level_name == 'ote_deep':
                    confidence_boost = 12
                elif level_name == 'ote_extreme':
                    confidence_boost = 8
                elif level_name == 'equilibrium':
                    confidence_boost = 5
                
                break
        
        # Check if in golden pocket (0.618-0.65)
        gp_low = ote_levels.get('golden_pocket_low', 0)
        gp_high = ote_levels.get('golden_pocket_high', 0)
        
        in_golden_pocket = False
        if gp_low > 0 and gp_high > 0:
            if ote_levels['direction'] == 'LONG':
                in_golden_pocket = gp_low <= current_price <= gp_high
            else:
                in_golden_pocket = gp_high <= current_price <= gp_low
        
        if in_golden_pocket and not at_level:
            at_level = 'golden_pocket'
            confidence_boost = 18  # Very high boost for golden pocket
        
        return {
            'at_ote': at_level is not None,
            'ote_level': at_level,
            'confidence_boost': confidence_boost,
            'distance_to_optimal_pct': round(distance_to_optimal, 3),
            'in_golden_pocket': in_golden_pocket,
            'current_price': round(current_price, 2),
            'ote_optimal_price': optimal_price,
            'direction': ote_levels.get('direction', 'UNKNOWN'),
        }
    
    def find_swing_points(self, candles: List[Dict], 
                         lookback: int = 50) -> Optional[Dict]:
        """
        Find recent swing high and swing low for OTE calculation.
        
        Uses simple peak/trough detection over lookback period.
        
        Args:
            candles: List of candle dicts (oldest first)
            lookback: Number of candles to analyze
        
        Returns:
            Dict with swing high, swing low, and direction
        """
        if not candles or len(candles) < lookback:
            return None
        
        recent = candles[-lookback:]
        
        # Find swing high (highest high in period)
        swing_high = max(c['high'] for c in recent)
        swing_high_idx = next(i for i, c in enumerate(recent) if c['high'] == swing_high)
        
        # Find swing low (lowest low in period)
        swing_low = min(c['low'] for c in recent)
        swing_low_idx = next(i for i, c in enumerate(recent) if c['low'] == swing_low)
        
        # Determine trend direction based on which came first
        if swing_low_idx < swing_high_idx:
            # Low came first, then high = uptrend
            direction = "LONG"
        else:
            # High came first, then low = downtrend
            direction = "SHORT"
        
        # Calculate range percentage
        range_pct = (swing_high - swing_low) / swing_low * 100 if swing_low > 0 else 0
        
        return {
            'swing_high': round(swing_high, 2),
            'swing_low': round(swing_low, 2),
            'direction': direction,
            'swing_high_idx': swing_high_idx,
            'swing_low_idx': swing_low_idx,
            'range_pct': round(range_pct, 3),
            'lookback': lookback,
        }
