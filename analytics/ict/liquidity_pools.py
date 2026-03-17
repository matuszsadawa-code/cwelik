"""
Liquidity Pools & Round Numbers Analysis

Round numbers act as psychological levels where liquidity clusters:
- Retail traders place stops at round numbers
- Smart money targets these levels for fills
- Price is "magnetically" attracted to round numbers

Key Concepts:
1. Major Round Numbers: 10000, 20000, 50000, 100000 (BTC)
2. Minor Round Numbers: 25000, 75000, 15000, 35000
3. Psychological Levels: 99000, 101000 (just below/above major)
4. Liquidity Pools: Clusters of stop losses at these levels

"Price delivers to liquidity. Round numbers are liquidity magnets."
"""

from typing import List, Dict
from utils.logger import get_logger

log = get_logger("analytics.ict.liquidity_pools")


class LiquidityPoolsAnalyzer:
    """
    Liquidity Pools & Round Numbers Analysis.
    
    Identifies round number levels and liquidity pools where
    stop losses cluster.
    """
    
    def __init__(self):
        # Round number patterns for different price ranges
        self.round_patterns = {
            'btc': {
                'major': [10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000],
                'minor': [5000, 15000, 25000, 35000, 45000, 55000, 65000, 75000, 85000, 95000],
                'psychological': [9900, 10100, 19900, 20100, 49900, 50100, 99900, 100100],
            },
            'eth': {
                'major': [1000, 2000, 3000, 4000, 5000],
                'minor': [500, 1500, 2500, 3500, 4500],
                'psychological': [990, 1010, 1990, 2010, 4990, 5010],
            },
            'default': {
                'major_divisor': 1000,   # Every 1000
                'minor_divisor': 500,    # Every 500
                'psych_offset': 10,      # ±10 from major
            },
        }
        
        log.info("Liquidity Pools Analyzer initialized")
    
    def find_nearby_levels(self, current_price: float, symbol: str = 'BTC',
                          distance_pct: float = 2.0) -> Dict:
        """
        Find round number levels near current price.
        
        Args:
            current_price: Current market price
            symbol: Symbol (BTC, ETH, etc.)
            distance_pct: Max distance to consider (%)
        
        Returns:
            Dict with nearby levels and analysis
        """
        # Determine which pattern to use
        if 'BTC' in symbol.upper():
            pattern = self.round_patterns['btc']
        elif 'ETH' in symbol.upper():
            pattern = self.round_patterns['eth']
        else:
            # Generate dynamic levels
            pattern = self._generate_dynamic_levels(current_price)
        
        # Find nearby levels
        nearby_major = self._find_nearby(current_price, pattern.get('major', []), distance_pct)
        nearby_minor = self._find_nearby(current_price, pattern.get('minor', []), distance_pct)
        nearby_psych = self._find_nearby(current_price, pattern.get('psychological', []), distance_pct)
        
        # Combine all levels
        all_levels = nearby_major + nearby_minor + nearby_psych
        
        # Find closest level
        if all_levels:
            closest = min(all_levels, key=lambda x: abs(x['distance_pct']))
        else:
            closest = None
        
        # Determine if at a level
        at_level = closest and abs(closest['distance_pct']) < 0.5  # Within 0.5%
        
        return {
            'current_price': round(current_price, 2),
            'nearby_major': nearby_major,
            'nearby_minor': nearby_minor,
            'nearby_psychological': nearby_psych,
            'closest_level': closest,
            'at_level': at_level,
            'confidence_boost': self._calculate_boost(closest) if at_level else 0,
        }
    
    def _find_nearby(self, price: float, levels: List[float], 
                    distance_pct: float) -> List[Dict]:
        """Find levels within distance_pct of price."""
        nearby = []
        
        for level in levels:
            distance = level - price
            distance_pct_calc = (distance / price) * 100
            
            if abs(distance_pct_calc) <= distance_pct:
                nearby.append({
                    'level': round(level, 2),
                    'distance': round(distance, 2),
                    'distance_pct': round(distance_pct_calc, 3),
                    'above': distance > 0,
                })
        
        return sorted(nearby, key=lambda x: abs(x['distance_pct']))
    
    def _generate_dynamic_levels(self, price: float) -> Dict:
        """Generate round number levels dynamically based on price."""
        # Determine appropriate divisor based on price magnitude
        if price >= 10000:
            major_div = 1000
            minor_div = 500
        elif price >= 1000:
            major_div = 100
            minor_div = 50
        elif price >= 100:
            major_div = 10
            minor_div = 5
        else:
            major_div = 1
            minor_div = 0.5
        
        # Generate levels around current price
        major_levels = []
        minor_levels = []
        psych_levels = []
        
        # Generate ±5 major levels
        base_major = int(price / major_div) * major_div
        for i in range(-5, 6):
            level = base_major + (i * major_div)
            if level > 0:
                major_levels.append(level)
                # Add psychological levels (±1% of major)
                psych_levels.append(level * 0.99)
                psych_levels.append(level * 1.01)
        
        # Generate minor levels
        base_minor = int(price / minor_div) * minor_div
        for i in range(-10, 11):
            level = base_minor + (i * minor_div)
            if level > 0 and level not in major_levels:
                minor_levels.append(level)
        
        return {
            'major': major_levels,
            'minor': minor_levels,
            'psychological': psych_levels,
        }
    
    def _calculate_boost(self, level_info: Dict) -> int:
        """
        Calculate confidence boost based on level proximity.
        
        Closer to level = higher boost
        Major levels = higher boost than minor
        """
        if not level_info:
            return 0
        
        distance_pct = abs(level_info['distance_pct'])
        
        # Determine level type (major levels are typically larger numbers)
        level = level_info['level']
        is_major = level % 10000 == 0 or level % 5000 == 0
        
        # Calculate boost
        if distance_pct < 0.2:  # Very close
            boost = 8 if is_major else 5
        elif distance_pct < 0.5:  # Close
            boost = 6 if is_major else 4
        else:
            boost = 0
        
        return boost
