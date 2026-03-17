"""
Dynamic Take Profit Optimizer

Intelligently adjusts TP levels based on ATR, momentum, and market conditions.
Implements partial profit taking and trailing stop activation.

Features:
- ATR-based TP calculation (TP1 at 1.5x ATR, TP2 at 3.0x ATR)
- Strong momentum detection (RSI >70 or <30)
- Fibonacci extension zones (1.618, 2.0, 2.618)
- Trailing stop activation after TP1
- Dynamic TP2 extension when momentum remains strong
- Partial profit taking (50% at TP1, 50% at TP2)
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

log = logging.getLogger(__name__)


@dataclass
class DynamicTP:
    """Dynamic TP configuration for a position."""
    tp1_price: float  # First TP at 1.5x ATR (50% position)
    tp2_price: float  # Second TP at 3.0x ATR (50% position)
    tp1_atr_multiplier: float
    tp2_atr_multiplier: float
    extension_zones: List[float]  # Fibonacci extensions
    trailing_stop_enabled: bool
    trailing_stop_distance_pct: float
    partial_profit_pct: float  # % to close at TP1


class DynamicTPOptimizer:
    """
    Dynamic Take Profit Optimizer.
    
    Calculates optimal TP levels based on:
    - ATR (Average True Range)
    - Momentum (RSI)
    - Fibonacci extensions
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Dynamic TP Optimizer.
        
        Args:
            config: Optional configuration dict
        """
        self.config = config or self._default_config()
        self.active_tps: Dict[str, DynamicTP] = {}
        log.info("DynamicTPOptimizer initialized")
    
    def _default_config(self) -> Dict:
        """Get default configuration."""
        return {
            "tp1_atr_multiplier": 1.5,  # TP1 at 1.5x ATR
            "tp2_atr_multiplier": 3.0,  # TP2 at 3.0x ATR
            "momentum_rsi_threshold": 70,  # RSI >70 or <30 = strong momentum
            "momentum_tp2_extension_pct": 50,  # Extend TP2 by 50% if momentum strong
            "trailing_stop_distance_pct": 1.0,  # Trail by 1% after TP1
            "partial_profit_pct": 50,  # Take 50% profit at TP1
            "fibonacci_extensions": [1.618, 2.0, 2.618],
            "atr_period": 14,  # 14-period ATR
            "rsi_period": 14,  # 14-period RSI
        }
    
    def calculate_dynamic_tp(self, signal: Dict, candles: List[Dict]) -> DynamicTP:
        """
        Calculate dynamic TP levels based on ATR and momentum.
        
        Args:
            signal: Trading signal with entry_price and direction
            candles: Recent candle data for ATR/RSI calculation
            
        Returns:
            DynamicTP with TP1, TP2, and trailing stop parameters
        """
        if not candles or len(candles) < 20:
            log.warning("Insufficient candles for dynamic TP calculation")
            return self._fallback_tp(signal)
        
        entry_price = signal.get("entry_price", 0)
        direction = signal.get("direction", "LONG")
        
        if entry_price <= 0:
            log.warning("Invalid entry price for dynamic TP")
            return self._fallback_tp(signal)
        
        # Calculate ATR
        atr = self._calculate_atr(candles)
        if atr <= 0:
            log.warning("Invalid ATR, using fallback TP")
            return self._fallback_tp(signal)
        
        # Detect strong momentum
        strong_momentum = self._detect_strong_momentum(candles)
        
        # Calculate base TP levels
        tp1_multiplier = self.config["tp1_atr_multiplier"]
        tp2_multiplier = self.config["tp2_atr_multiplier"]
        
        # Extend TP2 if momentum is strong
        if strong_momentum:
            extension_pct = self.config["momentum_tp2_extension_pct"]
            tp2_multiplier *= (1 + extension_pct / 100)
            log.info(f"Strong momentum detected, extending TP2 to {tp2_multiplier:.2f}x ATR")
        
        # Calculate TP prices
        if direction == "LONG":
            tp1_price = entry_price + (atr * tp1_multiplier)
            tp2_price = entry_price + (atr * tp2_multiplier)
        else:  # SHORT
            tp1_price = entry_price - (atr * tp1_multiplier)
            tp2_price = entry_price - (atr * tp2_multiplier)
        
        # Calculate Fibonacci extension zones
        extension_zones = self._calculate_extension_zones(
            entry_price, direction, atr
        )
        
        dynamic_tp = DynamicTP(
            tp1_price=tp1_price,
            tp2_price=tp2_price,
            tp1_atr_multiplier=tp1_multiplier,
            tp2_atr_multiplier=tp2_multiplier,
            extension_zones=extension_zones,
            trailing_stop_enabled=True,
            trailing_stop_distance_pct=self.config["trailing_stop_distance_pct"],
            partial_profit_pct=self.config["partial_profit_pct"]
        )
        
        log.info(
            f"Dynamic TP calculated: TP1=${tp1_price:.2f} ({tp1_multiplier:.1f}x ATR), "
            f"TP2=${tp2_price:.2f} ({tp2_multiplier:.1f}x ATR), "
            f"ATR=${atr:.2f}, Momentum={strong_momentum}"
        )
        
        return dynamic_tp
    
    def _calculate_atr(self, candles: List[Dict]) -> float:
        """Calculate ATR using shared indicator utility."""
        from utils.indicators import calculate_atr
        return calculate_atr(candles, period=self.config["atr_period"])
    
    def _detect_strong_momentum(self, candles: List[Dict]) -> bool:
        """
        Detect strong momentum using RSI.
        
        Strong momentum = RSI >70 (overbought) or RSI <30 (oversold)
        
        Args:
            candles: List of OHLCV candles
            
        Returns:
            True if momentum is strong
        """
        period = self.config["rsi_period"]
        threshold = self.config["momentum_rsi_threshold"]
        
        if len(candles) < period + 1:
            return False
        
        rsi = self._calculate_rsi(candles, period)
        
        if rsi is None:
            return False
        
        # Strong momentum = RSI >70 or <30
        is_strong = rsi > threshold or rsi < (100 - threshold)
        
        if is_strong:
            log.info(f"Strong momentum detected: RSI={rsi:.1f}")
        
        return is_strong
    
    def _calculate_rsi(self, candles: List[Dict], period: int = 14) -> Optional[float]:
        """Calculate RSI using shared indicator utility."""
        from utils.indicators import calculate_rsi
        return calculate_rsi(candles, period=period)
    
    def _calculate_extension_zones(
        self, entry: float, direction: str, atr: float
    ) -> List[float]:
        """
        Calculate Fibonacci extension zones as additional TP levels.
        
        Extension zones: 1.618, 2.0, 2.618 times ATR from entry
        
        Args:
            entry: Entry price
            direction: LONG or SHORT
            atr: Average True Range
            
        Returns:
            List of extension prices
        """
        extensions = self.config["fibonacci_extensions"]
        zones = []
        
        for ext in extensions:
            if direction == "LONG":
                zone_price = entry + (atr * ext)
            else:  # SHORT
                zone_price = entry - (atr * ext)
            zones.append(zone_price)
        
        return zones
    
    def should_activate_trailing_stop(
        self, position: Dict, current_price: float
    ) -> bool:
        """
        Check if trailing stop should be activated.
        
        Trailing stop activates after TP1 is hit.
        
        Args:
            position: Position dict with tp1_price and direction
            current_price: Current market price
            
        Returns:
            True if trailing stop should be activated
        """
        tp1_price = position.get("tp1_price")
        direction = position.get("direction")
        
        if not tp1_price or not direction:
            return False
        
        if direction == "LONG":
            return current_price >= tp1_price
        else:  # SHORT
            return current_price <= tp1_price
    
    def update_tp_levels(
        self, position_id: str, current_price: float, candles: List[Dict]
    ) -> Optional[Dict]:
        """
        Update TP2 if momentum remains strong after TP1.
        
        If price hits TP1 and momentum is still strong, extend TP2 to next extension zone.
        
        Args:
            position_id: Position identifier
            current_price: Current market price
            candles: Recent candle data for momentum check
            
        Returns:
            Updated TP levels dict or None if no update
        """
        if position_id not in self.active_tps:
            return None
        
        dynamic_tp = self.active_tps[position_id]
        
        # Check if momentum is still strong
        strong_momentum = self._detect_strong_momentum(candles)
        
        if not strong_momentum:
            return None
        
        # Find next extension zone beyond current TP2
        next_zone = None
        for zone in dynamic_tp.extension_zones:
            if zone > dynamic_tp.tp2_price:
                next_zone = zone
                break
        
        if next_zone:
            old_tp2 = dynamic_tp.tp2_price
            dynamic_tp.tp2_price = next_zone
            
            log.info(
                f"Extended TP2 due to strong momentum: "
                f"${old_tp2:.2f} -> ${next_zone:.2f}"
            )
            
            return {
                "tp2_price": next_zone,
                "reason": "momentum_extension"
            }
        
        return None
    
    def register_position(self, position_id: str, dynamic_tp: DynamicTP):
        """
        Register a position for tracking.
        
        Args:
            position_id: Position identifier
            dynamic_tp: DynamicTP configuration
        """
        self.active_tps[position_id] = dynamic_tp
        log.info(f"Registered position {position_id} for dynamic TP tracking")
    
    def unregister_position(self, position_id: str):
        """
        Unregister a closed position.
        
        Args:
            position_id: Position identifier
        """
        if position_id in self.active_tps:
            del self.active_tps[position_id]
            log.info(f"Unregistered position {position_id}")
    
    def _fallback_tp(self, signal: Dict) -> DynamicTP:
        """
        Generate fallback TP when calculation fails.
        
        Uses simple percentage-based TP levels.
        
        Args:
            signal: Trading signal
            
        Returns:
            Fallback DynamicTP
        """
        entry_price = signal.get("entry_price", 0)
        direction = signal.get("direction", "LONG")
        
        # Fallback: 1% for TP1, 2% for TP2
        if direction == "LONG":
            tp1_price = entry_price * 1.01
            tp2_price = entry_price * 1.02
        else:
            tp1_price = entry_price * 0.99
            tp2_price = entry_price * 0.98
        
        log.warning(f"Using fallback TP: TP1=${tp1_price:.2f}, TP2=${tp2_price:.2f}")
        
        return DynamicTP(
            tp1_price=tp1_price,
            tp2_price=tp2_price,
            tp1_atr_multiplier=1.5,
            tp2_atr_multiplier=3.0,
            extension_zones=[],
            trailing_stop_enabled=True,
            trailing_stop_distance_pct=1.0,
            partial_profit_pct=50
        )
    
    def get_tp_summary(self, position_id: str) -> Optional[Dict]:
        """
        Get TP summary for a position.
        
        Args:
            position_id: Position identifier
            
        Returns:
            TP summary dict or None
        """
        if position_id not in self.active_tps:
            return None
        
        dynamic_tp = self.active_tps[position_id]
        
        return {
            "tp1_price": dynamic_tp.tp1_price,
            "tp2_price": dynamic_tp.tp2_price,
            "tp1_atr_multiplier": dynamic_tp.tp1_atr_multiplier,
            "tp2_atr_multiplier": dynamic_tp.tp2_atr_multiplier,
            "extension_zones": dynamic_tp.extension_zones,
            "trailing_stop_enabled": dynamic_tp.trailing_stop_enabled,
            "trailing_stop_distance_pct": dynamic_tp.trailing_stop_distance_pct,
            "partial_profit_pct": dynamic_tp.partial_profit_pct
        }
