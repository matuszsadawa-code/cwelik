"""
ICT (Inner Circle Trader) Configuration

Configuration for ICT analytics components:
- Killzones (time-based trading windows)
- OTE (Optimal Trade Entry - Fibonacci levels)
- Premium/Discount zones
"""

# ─── ICT Killzones Configuration ─────────────────────────────────────────────
ICT_KILLZONES_CONFIG = {
    'enabled': True,
    
    # Timezone for killzone calculations (ICT uses EST/New York time)
    'timezone': 'US/Eastern',
    
    # Boost multiplier (adjust all confidence boosts by this factor)
    'boost_multiplier': 1.0,
    
    # Require killzone (if True, only trade during killzones)
    'require_killzone': False,
    
    # Minimum killzone boost to consider (ignore killzones with lower boost)
    'min_boost': 5,
}

# ─── Silver Bullet Configuration ─────────────────────────────────────────────
ICT_SILVER_BULLET_CONFIG = {
    'enabled': True,
    
    # AM window (EST)
    'am_window': (9, 10),  # 09:00-10:00 EST (15:00-16:00 CET)
    
    # PM window (EST)
    'pm_window': (15, 16),  # 15:00-16:00 EST (21:00-22:00 CET)
    
    # Boost multiplier for Silver Bullet windows
    'boost_multiplier': 1.2,
}

# ─── OTE (Optimal Trade Entry) Configuration ─────────────────────────────────
ICT_OTE_CONFIG = {
    'enabled': True,
    
    # Tolerance for "at level" detection (%)
    'tolerance_pct': 0.5,
    
    # Lookback period for swing detection (candles)
    'swing_lookback': 50,
    
    # Minimum swing range to consider (%)
    'min_swing_range_pct': 1.0,
    
    # Boost multiplier
    'boost_multiplier': 1.0,
}

# ─── Premium/Discount Configuration ──────────────────────────────────────────
ICT_PREMIUM_DISCOUNT_CONFIG = {
    'enabled': True,
    
    # Use same swing points as OTE
    'use_ote_swings': True,
    
    # Boost multiplier
    'boost_multiplier': 1.0,
}

# ─── Master ICT Configuration ────────────────────────────────────────────────
ICT_CONFIG = {
    'killzones': ICT_KILLZONES_CONFIG,
    'silver_bullet': ICT_SILVER_BULLET_CONFIG,
    'ote': ICT_OTE_CONFIG,
    'premium_discount': ICT_PREMIUM_DISCOUNT_CONFIG,
    
    # Global ICT settings
    'global': {
        'enabled': True,
        'log_level': 'INFO',
    },
}
