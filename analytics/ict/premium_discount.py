"""
Premium/Discount Zone Analysis.

ICT concept:
- Equilibrium (50%) = Fair value
- Premium (>50%) = Price is expensive -> favor shorts
- Discount (<50%) = Price is cheap -> favor longs

"Buy in discount, sell in premium"

Zones:
- Extreme Premium (70-100%): Strong short bias
- Premium (50-70%): Favor shorts
- Equilibrium (45-55%): Neutral
- Discount (30-50%): Favor longs
- Extreme Discount (0-30%): Strong long bias
"""

from typing import Dict
from utils.logger import get_logger

log = get_logger("analytics.ict.premium_discount")


class PremiumDiscountAnalysis:
    """
    Premium/Discount Zone Analysis.
    
    Classifies current price position within swing range to determine
    if price is at premium (expensive) or discount (cheap).
    """
    
    def __init__(self):
        # Zone definitions (position % within range)
        self.zones = {
            'extreme_premium': (70, 100),
            'premium': (50, 70),
            'equilibrium': (45, 55),
            'discount': (30, 50),
            'extreme_discount': (0, 30),
        }
        
        log.info("Premium/Discount Analysis initialized")
    
    def classify_zone(self, current_price: float,
                     swing_high: float, swing_low: float) -> Dict:
        """
        Classify current price position within swing range.
        
        Args:
            current_price: Current market price
            swing_high: Recent swing high
            swing_low: Recent swing low
        
        Returns:
            Dict with zone classification and trading bias
        """
        if swing_high <= swing_low:
            log.warning(f"Invalid swing: high {swing_high} <= low {swing_low}")
            return {
                'zone': 'INVALID',
                'position_pct': 0,
                'signal': 'NEUTRAL',
                'confidence_boost': 0,
            }
        
        # Calculate position within range (0-100%)
        range_size = swing_high - swing_low
        position_pct = (current_price - swing_low) / range_size * 100
        
        # Clamp to 0-100
        position_pct = max(0, min(100, position_pct))
        
        # Classify zone
        if position_pct >= 70:
            zone = "EXTREME_PREMIUM"
            signal = "STRONG_FAVOR_SHORTS"
            confidence_boost = 12
            description = "Price at extreme premium - strong short bias"
        elif position_pct >= 50:
            zone = "PREMIUM"
            signal = "FAVOR_SHORTS"
            confidence_boost = 6
            description = "Price in premium - favor shorts"
        elif position_pct >= 45:
            zone = "EQUILIBRIUM"
            signal = "NEUTRAL"
            confidence_boost = 0
            description = "Price at fair value - no bias"
        elif position_pct >= 30:
            zone = "DISCOUNT"
            signal = "FAVOR_LONGS"
            confidence_boost = 6
            description = "Price in discount - favor longs"
        else:
            zone = "EXTREME_DISCOUNT"
            signal = "STRONG_FAVOR_LONGS"
            confidence_boost = 12
            description = "Price at extreme discount - strong long bias"
        
        # Calculate equilibrium price and distance
        equilibrium_price = swing_low + range_size * 0.5
        distance_from_eq = current_price - equilibrium_price
        distance_from_eq_pct = (distance_from_eq / equilibrium_price) * 100 if equilibrium_price > 0 else 0
        
        return {
            'zone': zone,
            'position_pct': round(position_pct, 2),
            'signal': signal,
            'confidence_boost': confidence_boost,
            'description': description,
            'equilibrium_price': round(equilibrium_price, 2),
            'distance_from_equilibrium_pct': round(distance_from_eq_pct, 3),
            'swing_high': round(swing_high, 2),
            'swing_low': round(swing_low, 2),
            'current_price': round(current_price, 2),
        }
    
    def get_equilibrium(self, swing_high: float, swing_low: float) -> float:
        """
        Calculate equilibrium (50% level) between swing high and low.
        
        Args:
            swing_high: Recent swing high
            swing_low: Recent swing low
        
        Returns:
            Equilibrium price
        """
        if swing_high <= swing_low:
            return 0
        
        return round((swing_high + swing_low) / 2, 2)
