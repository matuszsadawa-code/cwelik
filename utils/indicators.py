"""
Shared Technical Indicators — DRY utility for ATR, RSI, and other common TA calculations.

Used by: AdaptiveSLSystem, DynamicTPOptimizer, and any module needing TA indicators.
"""

from typing import List, Dict, Optional


def calculate_atr(candles: List[Dict], period: int = 14) -> float:
    """
    Calculate Average True Range (ATR).
    
    Args:
        candles: List of OHLCV candles with 'high', 'low', 'close' keys
        period: ATR period (default 14)
        
    Returns:
        ATR value, or 0.0 if insufficient data
    """
    if len(candles) < 2:
        return 0.0
    
    true_ranges = []
    for i in range(1, len(candles)):
        high = candles[i]['high']
        low = candles[i]['low']
        prev_close = candles[i-1]['close']
        
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        true_ranges.append(tr)
    
    if len(true_ranges) < period:
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0
    
    return sum(true_ranges[-period:]) / period


def calculate_rsi(candles: List[Dict], period: int = 14) -> Optional[float]:
    """
    Calculate RSI (Relative Strength Index) using Wilder's smoothing method.
    
    Args:
        candles: List of OHLCV candles with 'close' key
        period: RSI period (default 14)
        
    Returns:
        RSI value (0-100) or None if insufficient data
    """
    if len(candles) < period + 1:
        return None
    
    closes = [c['close'] for c in candles]
    
    # Calculate price changes
    changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    
    gains = [max(0, change) for change in changes]
    losses = [abs(min(0, change)) for change in changes]
    
    # Initial averages
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # Smoothed averages (Wilder's method)
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi
