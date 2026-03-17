"""
Adaptive Stop Loss System

Intelligent stop loss system that adapts to volatility, market structure, and protects profits dynamically.

Features:
- ATR-based initial SL calculation with volatility regime multipliers
- Structure-aware SL placement (beyond Order Blocks, FVGs, round numbers)
- Stop hunt zone detection
- Breakeven move logic (at 50% to TP1)
- Profit lock logic (at TP1 hit, lock 50% profit)
- Chandelier Stop trailing (ATR-based trailing)
- Integration with Position_Manager for dynamic SL updates

**Validates: Requirements 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.7, 19.8**
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

log = logging.getLogger(__name__)


@dataclass
class AdaptiveStop:
    """Adaptive stop configuration for a position."""
    position_id: str
    initial_sl: float
    current_sl: float
    sl_type: str  # INITIAL, BREAKEVEN, PROFIT_LOCK, TRAILING
    atr_multiplier: float
    last_update: datetime
    updates_history: List[Tuple[datetime, float, str]]  # (time, price, reason)


@dataclass
class SLCalculation:
    """Stop loss calculation result."""
    atr_based_sl: float
    volatility_adjusted_sl: float
    structure_adjusted_sl: float
    final_sl: float
    adjustments_applied: List[str]
    stop_hunt_zones: List[float]


class AdaptiveSLSystem:
    """
    Adaptive Stop Loss System.
    
    Calculates and manages intelligent stop losses that adapt to:
    - Volatility regime (ATR-based with multipliers)
    - Market structure (Order Blocks, FVGs, round numbers)
    - Stop hunt zones
    - Position progress (breakeven, profit lock, trailing)
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Adaptive SL System.
        
        Args:
            config: Optional configuration dict
        """
        self.config = config or self._default_config()
        self.active_stops: Dict[str, AdaptiveStop] = {}
        log.info("AdaptiveSLSystem initialized")
    
    def _default_config(self) -> Dict:
        """Get default configuration."""
        return {
            "atr_multipliers": {
                "LOW": 1.5,
                "NORMAL": 2.0,
                "HIGH": 3.0,
                "EXTREME": 4.0,
            },
            "breakeven_trigger_pct": 50,  # Move to BE at 50% to TP1
            "profit_lock_trigger": "TP1_HIT",  # Lock profit when TP1 hits
            "profit_lock_pct": 50,  # Lock in 50% of profit
            "chandelier_atr_multiplier": 3.0,  # 3x ATR for trailing
            "structure_buffer_pct": 0.3,  # 0.3% buffer beyond structure
            "round_number_buffer_pct": 0.2,  # 0.2% buffer beyond round numbers
            "stop_hunt_detection_range_pct": 1.0,  # Check 1% range for stop hunts
            "atr_period": 14,  # 14-period ATR
        }
    
    def calculate_initial_sl(
        self,
        signal: Dict,
        candles: List[Dict],
        market_structure: Optional[Dict] = None,
        volatility_regime: str = "NORMAL"
    ) -> SLCalculation:
        """
        Calculate initial SL based on ATR and market structure.
        
        Process:
        1. Calculate ATR-based SL
        2. Adjust multiplier for volatility regime
        3. Place beyond key levels (OBs, FVGs, round numbers)
        4. Add buffer for stop hunts
        
        Args:
            signal: Trading signal with entry_price and direction
            candles: Recent candle data for ATR calculation
            market_structure: Optional market structure data (OBs, FVGs, etc.)
            volatility_regime: Volatility regime (LOW, NORMAL, HIGH, EXTREME)
            
        Returns:
            SLCalculation with final SL and adjustments applied
        """
        entry_price = signal.get("entry_price", 0)
        direction = signal.get("direction", "LONG")
        
        if entry_price <= 0:
            log.warning("Invalid entry price for SL calculation")
            return self._fallback_sl(signal)
        
        adjustments_applied = []
        
        # Step 1: Calculate ATR
        atr = self._calculate_atr(candles)
        if atr <= 0:
            log.warning("Invalid ATR, using fallback SL")
            return self._fallback_sl(signal)
        
        # Step 2: Get ATR multiplier for volatility regime
        atr_multiplier = self.get_atr_multiplier(volatility_regime)
        adjustments_applied.append(f"volatility_regime_{volatility_regime}_multiplier_{atr_multiplier}x")
        
        # Step 3: Calculate base SL
        if direction == "LONG":
            atr_based_sl = entry_price - (atr * atr_multiplier)
        else:  # SHORT
            atr_based_sl = entry_price + (atr * atr_multiplier)
        
        volatility_adjusted_sl = atr_based_sl
        
        # Step 4: Adjust for market structure
        structure_adjusted_sl = self.place_beyond_structure(
            volatility_adjusted_sl, direction, market_structure, entry_price
        )
        
        if structure_adjusted_sl != volatility_adjusted_sl:
            adjustments_applied.append("structure_adjustment")
        
        # Step 5: Detect stop hunt zones
        stop_hunt_zones = self.detect_stop_hunt_zones(
            candles, structure_adjusted_sl, direction
        )
        
        # Step 6: Adjust for stop hunt zones if needed
        final_sl = structure_adjusted_sl
        if stop_hunt_zones:
            final_sl = self._adjust_for_stop_hunts(
                structure_adjusted_sl, direction, stop_hunt_zones
            )
            if final_sl != structure_adjusted_sl:
                adjustments_applied.append("stop_hunt_buffer")
        
        log.info(
            f"Initial SL calculated: ${final_sl:.2f} "
            f"(ATR=${atr:.2f}, Multiplier={atr_multiplier}x, "
            f"Regime={volatility_regime}, Adjustments={len(adjustments_applied)})"
        )
        
        return SLCalculation(
            atr_based_sl=atr_based_sl,
            volatility_adjusted_sl=volatility_adjusted_sl,
            structure_adjusted_sl=structure_adjusted_sl,
            final_sl=final_sl,
            adjustments_applied=adjustments_applied,
            stop_hunt_zones=stop_hunt_zones
        )
    
    def get_atr_multiplier(self, volatility_regime: str) -> float:
        """
        Get ATR multiplier based on volatility regime.
        
        LOW: 1.5x ATR
        NORMAL: 2.0x ATR
        HIGH: 3.0x ATR
        EXTREME: 4.0x ATR
        
        Args:
            volatility_regime: Volatility regime
            
        Returns:
            ATR multiplier
        """
        return self.config["atr_multipliers"].get(
            volatility_regime.upper(),
            self.config["atr_multipliers"]["NORMAL"]
        )
    
    def place_beyond_structure(
        self,
        initial_sl: float,
        direction: str,
        market_structure: Optional[Dict],
        entry_price: float
    ) -> float:
        """
        Adjust SL to be beyond key market structure levels.
        
        Checks:
        - Order Blocks
        - Fair Value Gaps
        - Round numbers
        - Equal highs/lows
        
        Args:
            initial_sl: Initial SL price
            direction: LONG or SHORT
            market_structure: Market structure data
            entry_price: Entry price for reference
            
        Returns:
            Adjusted SL price
        """
        if not market_structure:
            return initial_sl
        
        adjusted_sl = initial_sl
        structure_buffer_pct = self.config["structure_buffer_pct"] / 100
        round_buffer_pct = self.config["round_number_buffer_pct"] / 100
        
        # Collect all structural levels that could interfere with SL
        structural_levels = []
        
        # 1. Order Blocks
        order_blocks = market_structure.get("order_blocks", [])
        for ob in order_blocks:
            if direction == "LONG":
                # For LONG, check bearish OBs below entry
                if ob.get("type") == "BEARISH" and ob.get("bottom", 0) < entry_price:
                    structural_levels.append(("order_block", ob.get("bottom")))
            else:  # SHORT
                # For SHORT, check bullish OBs above entry
                if ob.get("type") == "BULLISH" and ob.get("top", float("inf")) > entry_price:
                    structural_levels.append(("order_block", ob.get("top")))
        
        # 2. Fair Value Gaps
        fvgs = market_structure.get("fvg", [])
        for fvg in fvgs:
            if direction == "LONG":
                # For LONG, check FVGs below entry
                if fvg.get("bottom", 0) < entry_price:
                    structural_levels.append(("fvg", fvg.get("bottom")))
            else:  # SHORT
                # For SHORT, check FVGs above entry
                if fvg.get("top", float("inf")) > entry_price:
                    structural_levels.append(("fvg", fvg.get("top")))
        
        # 3. Liquidity Pools
        liquidity_pools = market_structure.get("liquidity_pools", [])
        for pool in liquidity_pools:
            price_level = pool.get("price_level")
            if price_level:
                if direction == "LONG" and price_level < entry_price:
                    structural_levels.append(("liquidity_pool", price_level))
                elif direction == "SHORT" and price_level > entry_price:
                    structural_levels.append(("liquidity_pool", price_level))
        
        # 4. Round numbers
        round_numbers = self._find_round_numbers_near_sl(initial_sl, direction)
        for rn in round_numbers:
            structural_levels.append(("round_number", rn))
        
        # Find the closest structural level that would interfere with SL
        if direction == "LONG":
            # For LONG, SL is below entry, check if any structure is between SL and entry
            interfering_levels = [
                (level_type, price) for level_type, price in structural_levels
                if price > initial_sl and price < entry_price
            ]
            
            if interfering_levels:
                # Place SL below the lowest interfering level
                lowest_level = min(interfering_levels, key=lambda x: x[1])
                level_type, level_price = lowest_level
                
                if level_type == "round_number":
                    adjusted_sl = level_price * (1 - round_buffer_pct)
                else:
                    adjusted_sl = level_price * (1 - structure_buffer_pct)
                
                log.info(
                    f"Adjusted SL for structure: ${initial_sl:.2f} -> ${adjusted_sl:.2f} "
                    f"(placed below {level_type} at ${level_price:.2f})"
                )
        
        else:  # SHORT
            # For SHORT, SL is above entry, check if any structure is between entry and SL
            interfering_levels = [
                (level_type, price) for level_type, price in structural_levels
                if price < initial_sl and price > entry_price
            ]
            
            if interfering_levels:
                # Place SL above the highest interfering level
                highest_level = max(interfering_levels, key=lambda x: x[1])
                level_type, level_price = highest_level
                
                if level_type == "round_number":
                    adjusted_sl = level_price * (1 + round_buffer_pct)
                else:
                    adjusted_sl = level_price * (1 + structure_buffer_pct)
                
                log.info(
                    f"Adjusted SL for structure: ${initial_sl:.2f} -> ${adjusted_sl:.2f} "
                    f"(placed above {level_type} at ${level_price:.2f})"
                )
        
        return adjusted_sl
    
    def _find_round_numbers_near_sl(self, sl_price: float, direction: str) -> List[float]:
        """
        Find round numbers near SL price.
        
        Round numbers: multiples of 100, 500, 1000, 5000, 10000
        
        Args:
            sl_price: Stop loss price
            direction: LONG or SHORT
            
        Returns:
            List of round numbers near SL
        """
        round_numbers = []
        
        # Determine appropriate round number intervals based on price
        if sl_price < 10:
            intervals = [1, 5]
        elif sl_price < 100:
            intervals = [10, 50]
        elif sl_price < 1000:
            intervals = [100, 500]
        elif sl_price < 10000:
            intervals = [1000, 5000]
        else:
            intervals = [10000, 50000]
        
        # Find round numbers within 2% of SL
        search_range = sl_price * 0.02
        
        for interval in intervals:
            # Find nearest round number
            nearest = round(sl_price / interval) * interval
            
            # Check if it's within range
            if abs(nearest - sl_price) <= search_range:
                # Check if it's on the correct side
                if direction == "LONG" and nearest < sl_price:
                    round_numbers.append(nearest)
                elif direction == "SHORT" and nearest > sl_price:
                    round_numbers.append(nearest)
        
        return round_numbers
    
    def detect_stop_hunt_zones(
        self, candles: List[Dict], sl_price: float, direction: str
    ) -> List[float]:
        """
        Identify stop hunt zones near SL.
        
        Stop hunt zones are areas where price has spiked briefly (wicks)
        but quickly reversed, indicating stop hunting behavior.
        
        Args:
            candles: Recent candle data
            sl_price: Stop loss price
            direction: LONG or SHORT
            
        Returns:
            List of prices where stops might be hunted
        """
        if len(candles) < 10:
            return []
        
        stop_hunt_zones = []
        detection_range_pct = self.config["stop_hunt_detection_range_pct"] / 100
        
        # Check recent candles for stop hunt patterns
        for candle in candles[-20:]:  # Check last 20 candles
            high = candle['high']
            low = candle['low']
            open_price = candle['open']
            close = candle['close']
            
            # Calculate wick sizes
            body_top = max(open_price, close)
            body_bottom = min(open_price, close)
            upper_wick = high - body_top
            lower_wick = body_bottom - low
            body_size = abs(close - open_price)
            
            # Stop hunt pattern: large wick (>2x body) with quick reversal
            if direction == "LONG":
                # Check for downward stop hunts (large lower wick)
                if lower_wick > body_size * 2 and body_size > 0:
                    # Check if low is near SL
                    if abs(low - sl_price) / sl_price <= detection_range_pct:
                        stop_hunt_zones.append(low)
            
            else:  # SHORT
                # Check for upward stop hunts (large upper wick)
                if upper_wick > body_size * 2 and body_size > 0:
                    # Check if high is near SL
                    if abs(high - sl_price) / sl_price <= detection_range_pct:
                        stop_hunt_zones.append(high)
        
        if stop_hunt_zones:
            log.info(f"Detected {len(stop_hunt_zones)} stop hunt zones near SL")
        
        return stop_hunt_zones
    
    def _adjust_for_stop_hunts(
        self, sl_price: float, direction: str, stop_hunt_zones: List[float]
    ) -> float:
        """
        Adjust SL to avoid stop hunt zones.
        
        Args:
            sl_price: Current SL price
            direction: LONG or SHORT
            stop_hunt_zones: List of stop hunt zone prices
            
        Returns:
            Adjusted SL price
        """
        if not stop_hunt_zones:
            return sl_price
        
        buffer_pct = self.config["structure_buffer_pct"] / 100
        
        if direction == "LONG":
            # For LONG, place SL below the lowest stop hunt zone
            lowest_hunt = min(stop_hunt_zones)
            if lowest_hunt < sl_price:
                adjusted_sl = lowest_hunt * (1 - buffer_pct)
                log.info(
                    f"Adjusted SL for stop hunt: ${sl_price:.2f} -> ${adjusted_sl:.2f} "
                    f"(below hunt zone at ${lowest_hunt:.2f})"
                )
                return adjusted_sl
        
        else:  # SHORT
            # For SHORT, place SL above the highest stop hunt zone
            highest_hunt = max(stop_hunt_zones)
            if highest_hunt > sl_price:
                adjusted_sl = highest_hunt * (1 + buffer_pct)
                log.info(
                    f"Adjusted SL for stop hunt: ${sl_price:.2f} -> ${adjusted_sl:.2f} "
                    f"(above hunt zone at ${highest_hunt:.2f})"
                )
                return adjusted_sl
        
        return sl_price
    
    def move_to_breakeven(
        self, position: Dict, current_price: float
    ) -> Optional[float]:
        """
        Move SL to breakeven when price reaches 50% to TP1.
        """
        entry_price = position.get("entry_price")
        # Support both tp1_price (direct) and tp_price (from Position.to_dict())
        tp1_price = position.get("tp1_price") or position.get("tp_price")
        direction = position.get("direction")
        
        if not all([entry_price, tp1_price, direction]):
            return None
        
        # Calculate 50% progress to TP1
        if direction == "LONG":
            tp1_distance = tp1_price - entry_price
            halfway_price = entry_price + (tp1_distance * 0.5)
            
            if current_price >= halfway_price:
                log.info(
                    f"Moving SL to breakeven: price ${current_price:.2f} "
                    f"reached 50% to TP1 (${halfway_price:.2f})"
                )
                return entry_price
        
        else:  # SHORT
            tp1_distance = entry_price - tp1_price
            halfway_price = entry_price - (tp1_distance * 0.5)
            
            if current_price <= halfway_price:
                log.info(
                    f"Moving SL to breakeven: price ${current_price:.2f} "
                    f"reached 50% to TP1 (${halfway_price:.2f})"
                )
                return entry_price
        
        return None
    
    def lock_in_profit(
        self, position: Dict, current_price: float
    ) -> Optional[float]:
        """
        Move SL to lock in 50% profit when TP1 is hit.
        
        Args:
            position: Position dict with entry_price, tp1_price, direction
            current_price: Current market price
            
        Returns:
            New SL price or None
        """
        entry_price = position.get("entry_price")
        # Support both tp1_price (direct) and tp_price (from Position.to_dict())
        tp1_price = position.get("tp1_price") or position.get("tp_price")
        direction = position.get("direction")
        tp1_hit = position.get("tp1_hit", False) or position.get("tp_hit", False)
        
        if not all([entry_price, tp1_price, direction]) or not tp1_hit:
            return None
        
        profit_lock_pct = self.config["profit_lock_pct"] / 100
        
        if direction == "LONG":
            profit = tp1_price - entry_price
            lock_price = entry_price + (profit * profit_lock_pct)
            
            log.info(
                f"Locking in profit: SL moved to ${lock_price:.2f} "
                f"(50% of profit from ${entry_price:.2f} to ${tp1_price:.2f})"
            )
            return lock_price
        
        else:  # SHORT
            profit = entry_price - tp1_price
            lock_price = entry_price - (profit * profit_lock_pct)
            
            log.info(
                f"Locking in profit: SL moved to ${lock_price:.2f} "
                f"(50% of profit from ${entry_price:.2f} to ${tp1_price:.2f})"
            )
            return lock_price
    
    def calculate_chandelier_stop(
        self,
        candles: List[Dict],
        direction: str,
        atr_multiplier: Optional[float] = None
    ) -> float:
        """
        Calculate Chandelier Stop (trailing stop based on ATR).
        
        LONG: Highest High - (ATR × multiplier)
        SHORT: Lowest Low + (ATR × multiplier)
        
        Args:
            candles: Recent candle data
            direction: LONG or SHORT
            atr_multiplier: Optional ATR multiplier (default from config)
            
        Returns:
            Chandelier stop price
        """
        if len(candles) < 14:
            return 0.0
        
        if atr_multiplier is None:
            atr_multiplier = self.config["chandelier_atr_multiplier"]
        
        # Calculate ATR
        atr = self._calculate_atr(candles)
        
        if atr <= 0:
            return 0.0
        
        # Find highest high / lowest low in recent period
        lookback = min(22, len(candles))  # 22-period lookback
        recent_candles = candles[-lookback:]
        
        if direction == "LONG":
            highest_high = max(c['high'] for c in recent_candles)
            chandelier_stop = highest_high - (atr * atr_multiplier)
        else:  # SHORT
            lowest_low = min(c['low'] for c in recent_candles)
            chandelier_stop = lowest_low + (atr * atr_multiplier)
        
        return chandelier_stop
    
    def update_trailing_stop(
        self,
        position: Dict,
        current_price: float,
        candles: List[Dict]
    ) -> Optional[float]:
        """
        Update trailing stop using Chandelier method.
        
        Only moves in favorable direction, never against position.
        
        Args:
            position: Position dict with current_sl, direction
            current_price: Current market price
            candles: Recent candle data
            
        Returns:
            New SL price or None if no update
        """
        # Support both current_sl (direct) and sl_price (from Position.to_dict())
        current_sl = position.get("current_sl") or position.get("sl_price")
        direction = position.get("direction")
        
        if not all([current_sl, direction]):
            return None
        
        # Calculate new Chandelier stop
        new_chandelier_stop = self.calculate_chandelier_stop(
            candles, direction
        )
        
        if new_chandelier_stop <= 0:
            return None
        
        # Only move SL in favorable direction
        if direction == "LONG":
            # For LONG, only move SL up
            if new_chandelier_stop > current_sl:
                log.info(
                    f"Trailing SL updated: ${current_sl:.2f} -> ${new_chandelier_stop:.2f} "
                    f"(Chandelier Stop)"
                )
                return new_chandelier_stop
        
        else:  # SHORT
            # For SHORT, only move SL down
            if new_chandelier_stop < current_sl:
                log.info(
                    f"Trailing SL updated: ${current_sl:.2f} -> ${new_chandelier_stop:.2f} "
                    f"(Chandelier Stop)"
                )
                return new_chandelier_stop
        
        return None
    
    def register_position(
        self, position_id: str, initial_sl: float, atr_multiplier: float
    ):
        """
        Register a position for adaptive SL tracking.
        
        Args:
            position_id: Position identifier
            initial_sl: Initial SL price
            atr_multiplier: ATR multiplier used
        """
        adaptive_stop = AdaptiveStop(
            position_id=position_id,
            initial_sl=initial_sl,
            current_sl=initial_sl,
            sl_type="INITIAL",
            atr_multiplier=atr_multiplier,
            last_update=datetime.now(),
            updates_history=[(datetime.now(), initial_sl, "INITIAL")]
        )
        
        self.active_stops[position_id] = adaptive_stop
        log.info(f"Registered position {position_id} for adaptive SL tracking")
    
    def update_position_sl(
        self, position_id: str, new_sl: float, sl_type: str, reason: str
    ):
        """
        Update SL for a tracked position.
        
        Args:
            position_id: Position identifier
            new_sl: New SL price
            sl_type: SL type (BREAKEVEN, PROFIT_LOCK, TRAILING)
            reason: Reason for update
        """
        if position_id not in self.active_stops:
            log.warning(f"Position {position_id} not found in active stops")
            return
        
        adaptive_stop = self.active_stops[position_id]
        adaptive_stop.current_sl = new_sl
        adaptive_stop.sl_type = sl_type
        adaptive_stop.last_update = datetime.now()
        adaptive_stop.updates_history.append(
            (datetime.now(), new_sl, reason)
        )
        
        log.info(
            f"Updated SL for {position_id}: ${new_sl:.2f} "
            f"(Type: {sl_type}, Reason: {reason})"
        )
    
    def unregister_position(self, position_id: str):
        """
        Unregister a closed position.
        
        Args:
            position_id: Position identifier
        """
        if position_id in self.active_stops:
            del self.active_stops[position_id]
            log.info(f"Unregistered position {position_id}")
    
    def _calculate_atr(self, candles: List[Dict]) -> float:
        """Calculate ATR using shared indicator utility."""
        from utils.indicators import calculate_atr
        return calculate_atr(candles, period=self.config["atr_period"])
    
    def _fallback_sl(self, signal: Dict) -> SLCalculation:
        """
        Generate fallback SL when calculation fails.
        
        Uses simple percentage-based SL.
        
        Args:
            signal: Trading signal
            
        Returns:
            Fallback SLCalculation
        """
        entry_price = signal.get("entry_price", 0)
        direction = signal.get("direction", "LONG")
        
        # Fallback: 2% SL
        if direction == "LONG":
            fallback_sl = entry_price * 0.98
        else:
            fallback_sl = entry_price * 1.02
        
        log.warning(f"Using fallback SL: ${fallback_sl:.2f} (2% from entry)")
        
        return SLCalculation(
            atr_based_sl=fallback_sl,
            volatility_adjusted_sl=fallback_sl,
            structure_adjusted_sl=fallback_sl,
            final_sl=fallback_sl,
            adjustments_applied=["fallback"],
            stop_hunt_zones=[]
        )
    
    def get_sl_summary(self, position_id: str) -> Optional[Dict]:
        """
        Get SL summary for a position.
        
        Args:
            position_id: Position identifier
            
        Returns:
            SL summary dict or None
        """
        if position_id not in self.active_stops:
            return None
        
        adaptive_stop = self.active_stops[position_id]
        
        return {
            "position_id": adaptive_stop.position_id,
            "initial_sl": adaptive_stop.initial_sl,
            "current_sl": adaptive_stop.current_sl,
            "sl_type": adaptive_stop.sl_type,
            "atr_multiplier": adaptive_stop.atr_multiplier,
            "last_update": adaptive_stop.last_update.isoformat(),
            "updates_count": len(adaptive_stop.updates_history),
            "updates_history": [
                {
                    "timestamp": ts.isoformat(),
                    "price": price,
                    "reason": reason
                }
                for ts, price, reason in adaptive_stop.updates_history
            ]
        }
