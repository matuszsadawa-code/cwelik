"""
ICT Killzones - Time-based trading windows.

Based on Inner Circle Trader methodology:
- 80% of significant moves occur during killzones
- Each killzone has specific characteristics
- Combine with market structure for highest probability

Killzones (EST/New York time):
- London Open: 02:00-05:00 EST (08:00-11:00 CET)
- NY AM: 07:00-10:00 EST (13:00-16:00 CET) - STRONGEST
- Lunch: 11:00-13:00 EST (17:00-19:00 CET) - AVOID
- NY PM: 13:00-16:00 EST (19:00-22:00 CET)
- Asian: 19:00-00:00 EST (01:00-06:00 CET next day)

Silver Bullet windows (highest probability):
- AM: 09:00-10:00 EST (15:00-16:00 CET)
- PM: 15:00-16:00 EST (21:00-22:00 CET)
"""

from datetime import datetime, timezone
from typing import Dict, Optional
from utils.logger import get_logger

try:
    from pytz import timezone as pytz_timezone
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False
    import logging
    logging.warning("pytz not available - install with: pip install pytz")

log = get_logger("analytics.ict.killzones")


class ICTKillzones:
    """
    ICT Killzone Analysis - Time-based trading windows.
    
    Identifies optimal trading windows based on institutional activity patterns.
    """
    
    def __init__(self):
        # Killzones in EST (New York time)
        self.killzones = {
            'LONDON_OPEN': {
                'start': 2,   # 02:00 EST (08:00 CET)
                'end': 5,     # 05:00 EST (11:00 CET)
                'characteristics': 'High volatility, liquidity sweeps',
                'confidence_boost': 15,
                'optimal_for': ['LONG', 'SHORT'],
                'description': 'London session open - high volatility window',
            },
            'NY_AM': {
                'start': 7,   # 07:00 EST (13:00 CET)
                'end': 10,    # 10:00 EST (16:00 CET)
                'characteristics': 'Strongest moves, institutional entry',
                'confidence_boost': 20,  # Highest boost
                'optimal_for': ['LONG', 'SHORT'],
                'description': 'New York AM session - strongest institutional activity',
            },
            'LUNCH': {
                'start': 11,  # 11:00 EST (17:00 CET)
                'end': 13,    # 13:00 EST (19:00 CET)
                'characteristics': 'Low volume, avoid trading',
                'confidence_boost': -10,  # Penalty
                'optimal_for': [],
                'description': 'Lunch hour - low liquidity, avoid trading',
            },
            'NY_PM': {
                'start': 13,  # 13:00 EST (19:00 CET)
                'end': 16,    # 16:00 EST (22:00 CET)
                'characteristics': 'Continuation or reversal',
                'confidence_boost': 12,
                'optimal_for': ['LONG', 'SHORT'],
                'description': 'New York PM session - continuation moves',
            },
            'ASIAN': {
                'start': 19,  # 19:00 EST (01:00 CET next day)
                'end': 24,    # 00:00 EST (06:00 CET)
                'characteristics': 'Range-bound, low volume',
                'confidence_boost': 5,
                'optimal_for': ['RANGE'],
                'description': 'Asian session - typically range-bound',
            },
        }
        
        # Silver Bullet windows (1-hour high-probability setups)
        self.silver_bullet_windows = {
            'AM': {
                'hour': 9,    # 09:00 EST (15:00 CET)
                'boost': 25,  # Highest boost
                'description': 'AM Silver Bullet - highest probability window',
            },
            'PM': {
                'hour': 15,   # 15:00 EST (21:00 CET)
                'boost': 20,
                'description': 'PM Silver Bullet - high probability window',
            },
        }
        
        log.info("ICT Killzones initialized")
    
    def get_current_killzone(self, timestamp: Optional[datetime] = None) -> Dict:
        """
        Get current killzone and its characteristics.
        
        Args:
            timestamp: Optional timestamp (defaults to now UTC)
        
        Returns:
            {
                'killzone': str,
                'active': bool,
                'confidence_boost': int,
                'characteristics': str,
                'optimal_for': List[str],
                'time_remaining_minutes': int,
                'hour_est': int,
                'is_optimal': bool,
            }
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        if not PYTZ_AVAILABLE:
            # Fallback: assume UTC-5 (EST) without DST handling
            hour = (timestamp.hour - 5) % 24
            log.warning("pytz not available - using simple UTC-5 conversion (no DST)")
        else:
            # Convert to EST with proper DST handling
            est_tz = pytz_timezone('US/Eastern')
            time_est = timestamp.astimezone(est_tz)
            hour = time_est.hour
        
        minute = timestamp.minute
        
        # Check each killzone
        for name, kz in self.killzones.items():
            if kz['start'] <= hour < kz['end']:
                # Calculate time remaining
                minutes_into_kz = (hour - kz['start']) * 60 + minute
                total_kz_minutes = (kz['end'] - kz['start']) * 60
                time_remaining = total_kz_minutes - minutes_into_kz
                
                return {
                    'killzone': name,
                    'active': True,
                    'confidence_boost': kz['confidence_boost'],
                    'characteristics': kz['characteristics'],
                    'optimal_for': kz['optimal_for'],
                    'description': kz['description'],
                    'time_remaining_minutes': time_remaining,
                    'hour_est': hour,
                    'is_optimal': kz['confidence_boost'] > 10,
                }
        
        # Outside killzone
        return {
            'killzone': 'OUTSIDE_KILLZONE',
            'active': False,
            'confidence_boost': -5,  # Small penalty for trading outside killzones
            'characteristics': 'Low probability window',
            'optimal_for': [],
            'description': 'Outside defined killzones - lower probability',
            'time_remaining_minutes': 0,
            'hour_est': hour,
            'is_optimal': False,
        }
    
    def is_silver_bullet_time(self, timestamp: Optional[datetime] = None) -> Dict:
        """
        Check if current time is Silver Bullet setup window.
        
        Silver Bullet: Specific 1-hour windows with highest probability:
        - 09:00-10:00 EST (15:00-16:00 CET) - AM Silver Bullet
        - 15:00-16:00 EST (21:00-22:00 CET) - PM Silver Bullet
        
        Args:
            timestamp: Optional timestamp (defaults to now UTC)
        
        Returns:
            {
                'is_silver_bullet': bool,
                'type': str,
                'confidence_boost': int,
                'description': str,
            }
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        if not PYTZ_AVAILABLE:
            hour = (timestamp.hour - 5) % 24
        else:
            est_tz = pytz_timezone('US/Eastern')
            time_est = timestamp.astimezone(est_tz)
            hour = time_est.hour
        
        # Check AM Silver Bullet
        if hour == self.silver_bullet_windows['AM']['hour']:
            return {
                'is_silver_bullet': True,
                'type': 'AM_SILVER_BULLET',
                'confidence_boost': self.silver_bullet_windows['AM']['boost'],
                'description': self.silver_bullet_windows['AM']['description'],
            }
        
        # Check PM Silver Bullet
        elif hour == self.silver_bullet_windows['PM']['hour']:
            return {
                'is_silver_bullet': True,
                'type': 'PM_SILVER_BULLET',
                'confidence_boost': self.silver_bullet_windows['PM']['boost'],
                'description': self.silver_bullet_windows['PM']['description'],
            }
        
        # Not a Silver Bullet window
        return {
            'is_silver_bullet': False,
            'type': 'NONE',
            'confidence_boost': 0,
            'description': 'Not a Silver Bullet window',
        }
    
    def get_next_killzone(self, timestamp: Optional[datetime] = None) -> Dict:
        """
        Get information about the next upcoming killzone.
        
        Args:
            timestamp: Optional timestamp (defaults to now UTC)
        
        Returns:
            {
                'next_killzone': str,
                'starts_in_hours': int,
                'confidence_boost': int,
            }
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        if not PYTZ_AVAILABLE:
            current_hour = (timestamp.hour - 5) % 24
        else:
            est_tz = pytz_timezone('US/Eastern')
            time_est = timestamp.astimezone(est_tz)
            current_hour = time_est.hour
        
        # Find next killzone
        for name, kz in sorted(self.killzones.items(), 
                              key=lambda x: x[1]['start']):
            if kz['start'] > current_hour:
                hours_until = kz['start'] - current_hour
                return {
                    'next_killzone': name,
                    'starts_in_hours': hours_until,
                    'confidence_boost': kz['confidence_boost'],
                    'description': kz['description'],
                }
        
        # If no killzone today, return tomorrow's first
        first_kz = min(self.killzones.items(), key=lambda x: x[1]['start'])
        hours_until = 24 - current_hour + first_kz[1]['start']
        
        return {
            'next_killzone': first_kz[0],
            'starts_in_hours': hours_until,
            'confidence_boost': first_kz[1]['confidence_boost'],
            'description': first_kz[1]['description'],
        }
