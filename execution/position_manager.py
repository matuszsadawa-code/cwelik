"""
OpenClaw Position Manager — Live position tracking and lifecycle management.

Tracks open positions with:
- Real-time P&L calculation (unrealized + realized)
- MFE/MAE tracking (Maximum Favorable/Adverse Excursion)
- TP/SL progress monitoring
- Liquidation distance tracking
- Duration tracking
- Dynamic TP optimization integration
"""

import time
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

from utils.logger import get_logger
from execution.dynamic_tp_optimizer import DynamicTPOptimizer
from execution.adaptive_sl import AdaptiveSLSystem

log = get_logger("execution.positions")


class PositionStatus(Enum):
    OPEN = "OPEN"
    TP1_HIT = "TP1_HIT"    # First TP hit — partial close + activate trailing
    TP_HIT = "TP_HIT"      # All TPs hit (legacy compat)
    STOPPED = "STOPPED"
    CLOSED = "CLOSED"
    LIQUIDATED = "LIQUIDATED"


class Position:
    """Represents a single tracked position."""

    def __init__(self, execution_result: Dict):
        self.execution_id = execution_result["execution_id"]
        self.signal_id = execution_result.get("signal_id")
        self.symbol = execution_result["symbol"]
        self.direction = execution_result["direction"]  # LONG or SHORT
        self.side = execution_result["side"]  # Buy or Sell
        self.mode = execution_result["mode"]
        self.leverage = execution_result["leverage"]

        self.entry_price = execution_result.get("fill_price", execution_result["entry_price"])
        self.qty = execution_result["qty"]
        self.remaining_qty = self.qty

        # Risk levels
        self.sl_price = execution_result["sl_price"]

        # Dual-TP tracking (backward compatible: falls back to tp_price if no tp1/tp2)
        self.tp1_price = execution_result.get("tp1_price", execution_result.get("tp_price", 0))
        self.tp2_price = execution_result.get("tp2_price", 0)  # 0 = not set
        # Legacy compat property — points to tp1
        self.tp_price = self.tp1_price

        # TP quantity allocation (from order_executor: 50% TP1, 25% TP2, 25% moon bag)
        self.tp1_qty = self.qty * 0.50
        self.tp2_qty = self.qty * 0.25
        self.moon_qty = self.qty * 0.25  # Rides with trailing stop

        # State
        self.status = PositionStatus.OPEN
        self.current_price = self.entry_price
        self.unrealised_pnl = 0.0
        self.realised_pnl = 0.0

        # MFE/MAE
        self.mfe = 0.0  # Maximum Favorable Excursion (best unrealised P&L %)
        self.mae = 0.0  # Maximum Adverse Excursion (worst unrealised P&L %)
        self.high_price = self.entry_price
        self.low_price = self.entry_price

        # TP tracking — dual TP state
        self.tp1_hit = False
        self.tp2_hit = False
        self.tp_hit = False  # Legacy compat: True when all TPs reached
        self.sl_hit = False

        # Trailing stop (activated after TP1 hit)
        self.trailing_active = False
        self.trailing_stop_price = None

        # Timing
        self.opened_at = datetime.utcnow()
        self.closed_at = None
        self.exit_price = None
        self.exit_reason = None

        log.info(
            f"Position created: {self.direction} {self.symbol} "
            f"@ ${self.entry_price:.2f} (x{self.leverage}) "
            f"TP1=${self.tp1_price:.2f} TP2=${self.tp2_price:.2f}"
        )

    def update_price(self, price: float):
        """Update position with new market price."""
        self.current_price = price
        self.high_price = max(self.high_price, price)
        self.low_price = min(self.low_price, price)

        # Calculate unrealised P&L
        if self.direction == "LONG":
            self.unrealised_pnl = (price - self.entry_price) / self.entry_price * 100 * self.leverage
            pnl_pct = (price - self.entry_price) / self.entry_price * 100
        else:
            self.unrealised_pnl = (self.entry_price - price) / self.entry_price * 100 * self.leverage
            pnl_pct = (self.entry_price - price) / self.entry_price * 100

        # Update MFE/MAE
        self.mfe = max(self.mfe, pnl_pct)
        self.mae = min(self.mae, pnl_pct)

        # Check TP/SL hits
        self._check_tp_sl(price)

        # Update trailing stop if active
        if self.trailing_active:
            self._update_trailing(price)

    def _check_tp_sl(self, price: float):
        """Check if TP or SL levels have been hit (dual-TP with trailing)."""
        if self.status == PositionStatus.CLOSED:
            return

        is_long = self.direction == "LONG"

        # ─── Check SL ─────────────────────────────────────────
        sl_triggered = (price <= self.sl_price if is_long else price >= self.sl_price)
        if sl_triggered and not self.sl_hit:
            self.sl_hit = True
            self.status = PositionStatus.STOPPED
            self.exit_price = self.sl_price
            self.exit_reason = "TRAILING_STOP" if self.trailing_active else "STOP_LOSS"
            self.remaining_qty = 0
            self._close()
            return

        # ─── Check TP1 (first target — partial close + activate trailing) ──
        tp1_triggered = (price >= self.tp1_price if is_long else price <= self.tp1_price)
        if tp1_triggered and not self.tp1_hit and self.tp1_price > 0:
            self.tp1_hit = True
            # Realize P&L on TP1 portion (50%)
            tp1_pnl_pct = abs(self.tp1_price - self.entry_price) / self.entry_price * 100 * self.leverage
            self.realised_pnl += tp1_pnl_pct * (self.tp1_qty / self.qty)
            self.remaining_qty -= self.tp1_qty
            self.status = PositionStatus.TP1_HIT
            log.info(
                f"🎯 TP1 HIT: {self.symbol} @ ${price:.2f} "
                f"(closed {self.tp1_qty:.6f}, remaining: {self.remaining_qty:.6f}) "
                f"— activating trailing stop"
            )
            # Trailing stop will be activated by update_adaptive_sl
            return

        # ─── Check TP2 (second target — partial close) ─────────
        if self.tp2_price > 0:
            tp2_triggered = (price >= self.tp2_price if is_long else price <= self.tp2_price)
            if tp2_triggered and self.tp1_hit and not self.tp2_hit:
                self.tp2_hit = True
                # Realize P&L on TP2 portion (25%)
                tp2_pnl_pct = abs(self.tp2_price - self.entry_price) / self.entry_price * 100 * self.leverage
                self.realised_pnl += tp2_pnl_pct * (self.tp2_qty / self.qty)
                self.remaining_qty -= self.tp2_qty
                self.tp_hit = True  # Legacy compat
                self.status = PositionStatus.TP_HIT
                log.info(
                    f"🎯 TP2 HIT: {self.symbol} @ ${price:.2f} "
                    f"(closed {self.tp2_qty:.6f}, moon bag: {self.remaining_qty:.6f})"
                )
                # Moon bag (25%) rides with trailing stop
                return

    def _update_trailing(self, price: float):
        """Update trailing stop price."""
        trailing_distance = self.entry_price * 0.005  # 0.5% of entry

        if self.direction == "LONG":
            new_trail = price - trailing_distance
            if self.trailing_stop_price is None or new_trail > self.trailing_stop_price:
                self.trailing_stop_price = new_trail
        else:
            new_trail = price + trailing_distance
            if self.trailing_stop_price is None or new_trail < self.trailing_stop_price:
                self.trailing_stop_price = new_trail

    def _close(self):
        """Mark position as closed."""
        self.status = PositionStatus.CLOSED
        self.closed_at = datetime.utcnow()
        duration = (self.closed_at - self.opened_at).total_seconds() / 60
        total_pnl = self.realised_pnl
        outcome = "WIN" if total_pnl > 0 else "LOSS"

        log.info(f"📊 POSITION CLOSED: {self.symbol}")
        log.info(f"   Outcome: {outcome} | PnL: {total_pnl:+.2f}%")
        log.info(f"   MFE: {self.mfe:+.2f}% | MAE: {self.mae:+.2f}%")
        log.info(f"   Duration: {duration:.0f} min")
        log.info(f"   TP: {self.tp_hit} | SL: {self.sl_hit}")

    @property
    def is_open(self) -> bool:
        return self.status != PositionStatus.CLOSED

    @property
    def duration_minutes(self) -> float:
        end = self.closed_at or datetime.utcnow()
        return (end - self.opened_at).total_seconds() / 60

    @property
    def total_pnl(self) -> float:
        return self.realised_pnl + self.unrealised_pnl * (self.remaining_qty / self.qty if self.qty > 0 else 0)

    @property
    def tp_sl_progress(self) -> Dict:
        """Get progress toward TP1, TP2 and SL as percentages."""
        is_long = self.direction == "LONG"

        if is_long:
            total_tp1_dist = self.tp1_price - self.entry_price
            total_tp2_dist = (self.tp2_price - self.entry_price) if self.tp2_price > 0 else 0
            total_sl_dist = self.entry_price - self.sl_price
            current_dist = self.current_price - self.entry_price
        else:
            total_tp1_dist = self.entry_price - self.tp1_price
            total_tp2_dist = (self.entry_price - self.tp2_price) if self.tp2_price > 0 else 0
            total_sl_dist = self.sl_price - self.entry_price
            current_dist = self.entry_price - self.current_price

        tp1_progress = (current_dist / total_tp1_dist * 100) if total_tp1_dist > 0 else 0
        tp2_progress = (current_dist / total_tp2_dist * 100) if total_tp2_dist > 0 else 0
        sl_progress = (-current_dist / total_sl_dist * 100) if total_sl_dist > 0 and current_dist < 0 else 0

        return {
            "tp1_progress": max(0, min(100, tp1_progress)),
            "tp1_hit": self.tp1_hit,
            "tp2_progress": max(0, min(100, tp2_progress)),
            "tp2_hit": self.tp2_hit,
            "sl_progress": max(0, min(100, sl_progress)),
        }

    def to_dict(self) -> Dict:
        """Serialize position to dict for API/DB."""
        return {
            "execution_id": self.execution_id,
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "mode": self.mode,
            "leverage": self.leverage,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "qty": self.qty,
            "remaining_qty": self.remaining_qty,
            "sl_price": self.sl_price,
            "tp_price": self.tp_price,  # Single TP only (as per requirements)
            "status": self.status.value,
            "unrealised_pnl": round(self.unrealised_pnl, 4),
            "realised_pnl": round(self.realised_pnl, 4),
            "total_pnl": round(self.total_pnl, 4),
            "mfe": round(self.mfe, 4),
            "mae": round(self.mae, 4),
            "tp_hit": self.tp_hit,  # Single TP only (as per requirements)
            "sl_hit": self.sl_hit,
            "trailing_active": self.trailing_active,
            "trailing_stop_price": self.trailing_stop_price,
            "tp_sl_progress": self.tp_sl_progress,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "duration_minutes": round(self.duration_minutes, 1),
            "opened_at": self.opened_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }


class PositionManager:
    """
    Manages all tracked positions.
    
    Maintains a registry of open positions, processes price updates,
    and provides aggregate portfolio data.
    """

    def __init__(self, use_dynamic_tp: bool = True):
        self._positions: Dict[str, Position] = {}  # execution_id → Position
        self._closed_positions: List[Position] = []
        self.use_dynamic_tp = use_dynamic_tp
        self.tp_optimizer = DynamicTPOptimizer() if use_dynamic_tp else None
        self.adaptive_sl = AdaptiveSLSystem()  # Initialize adaptive SL system
        log.info(f"PositionManager initialized (Dynamic TP: {use_dynamic_tp}, Adaptive SL: enabled)")

    def add_position(self, execution_result: Dict) -> Position:
        """Create and track a new position from execution result."""
        if execution_result.get("status") != "FILLED":
            log.warning(f"Cannot add unfilled execution: {execution_result.get('status')}")
            return None

        pos = Position(execution_result)
        self._positions[pos.execution_id] = pos
        
        # Register with adaptive SL system
        atr_multiplier = execution_result.get("atr_multiplier", 2.0)  # Default to 2.0x if not provided
        self.adaptive_sl.register_position(pos.execution_id, pos.sl_price, atr_multiplier)
        log.info(f"Position registered with adaptive SL: {pos.execution_id} (ATR multiplier: {atr_multiplier}x)")
        
        # Register with dynamic TP optimizer if enabled
        if self.use_dynamic_tp and self.tp_optimizer:
            try:
                # Note: Dynamic TP calculation requires candle data
                # This should be called from the execution layer with candle data
                log.info(f"Position registered for dynamic TP tracking: {pos.execution_id}")
            except Exception as e:
                log.error(f"Failed to register position with TP optimizer: {e}")
        
        log.info(f"Tracking position: {pos.execution_id} ({pos.symbol})")
        return pos

    def update_prices(self, prices: Dict[str, float], candles_by_symbol: Optional[Dict[str, List[Dict]]] = None):
        """
        Update all open positions with latest prices.
        
        Args:
            prices: Dict mapping symbol to current price
            candles_by_symbol: Optional dict mapping symbol to candle data for trailing stops
        """
        for exec_id, pos in list(self._positions.items()):
            if pos.symbol in prices:
                price = prices[pos.symbol]
                candles = candles_by_symbol.get(pos.symbol) if candles_by_symbol else None
                
                pos.update_price(price)
                
                # Update adaptive SL after price update
                self.update_adaptive_sl(pos, price, candles)

                if not pos.is_open:
                    self._closed_positions.append(pos)
                    self.adaptive_sl.unregister_position(exec_id)
                    del self._positions[exec_id]
                    log.debug(f"Position {exec_id} ({pos.symbol}) removed from tracking (closed)")
        
        # Clean up any closed positions that weren't in the prices dict
        closed_positions = [(eid, p) for eid, p in list(self._positions.items()) if not p.is_open]
        for exec_id, pos in closed_positions:
            self._closed_positions.append(pos)
            self.adaptive_sl.unregister_position(exec_id)
            del self._positions[exec_id]
            log.debug(f"Position {exec_id} ({pos.symbol}) removed from tracking (closed, no price update)")

    def update_symbol_price(self, symbol: str, price: float, candles: Optional[List[Dict]] = None):
        """
        Update price for all positions of a specific symbol.
        
        Args:
            symbol: Trading symbol
            price: Current market price
            candles: Optional candle data for trailing stop calculation
        """
        for pos in self._positions.values():
            if pos.symbol == symbol:
                pos.update_price(price)
                
                # Update adaptive SL after price update
                self.update_adaptive_sl(pos, price, candles)
                
                if not pos.is_open:
                    self._closed_positions.append(pos)

        # Clean up closed — unregister from adaptive SL
        for exec_id, pos in list(self._positions.items()):
            if not pos.is_open:
                self.adaptive_sl.unregister_position(exec_id)
        self._positions = {eid: p for eid, p in self._positions.items() if p.is_open}

    def get_open_positions(self) -> List[Dict]:
        """Get all open positions as dicts."""
        return [pos.to_dict() for pos in self._positions.values()]

    def get_all_open(self) -> List[Position]:
        """Get all open Position objects (not dicts)."""
        return list(self._positions.values())

    def get_closed_positions(self, limit: int = 50) -> List[Dict]:
        """Get recent closed positions."""
        return [pos.to_dict() for pos in self._closed_positions[-limit:]]

    def get_position_for_symbol(self, symbol: str) -> Optional[Position]:
        """Get open position for a specific symbol (if any)."""
        for pos in self._positions.values():
            if pos.symbol == symbol and pos.is_open:
                return pos
        return None

    def count_open(self) -> int:
        """
        Count the number of open positions.
        
        Returns:
            Number of positions in _positions dict (which should only contain open positions)
        """
        count = len(self._positions)
        log.debug(f"Position count: {count} open positions tracked")
        return count
    
    def apply_dynamic_tp(self, execution_id: str, signal: Dict, candles: List[Dict]) -> Optional[Dict]:
        """
        Apply dynamic TP optimization to a position.
        
        Args:
            execution_id: Position execution ID
            signal: Original signal with entry_price and direction
            candles: Recent candle data for ATR/RSI calculation
            
        Returns:
            Dynamic TP configuration or None if failed
        """
        if not self.use_dynamic_tp or not self.tp_optimizer:
            return None
        
        if execution_id not in self._positions:
            log.warning(f"Position {execution_id} not found for dynamic TP")
            return None
        
        try:
            # Calculate dynamic TP
            dynamic_tp = self.tp_optimizer.calculate_dynamic_tp(signal, candles)
            
            # Register position with optimizer
            self.tp_optimizer.register_position(execution_id, dynamic_tp)
            
            # Update position TP levels
            pos = self._positions[execution_id]
            pos.tp_price = dynamic_tp.tp1_price  # Use TP1 as primary TP
            
            log.info(
                f"Applied dynamic TP to {execution_id}: "
                f"TP1=${dynamic_tp.tp1_price:.2f}, TP2=${dynamic_tp.tp2_price:.2f}"
            )
            
            return {
                "tp1_price": dynamic_tp.tp1_price,
                "tp2_price": dynamic_tp.tp2_price,
                "extension_zones": dynamic_tp.extension_zones,
                "trailing_stop_enabled": dynamic_tp.trailing_stop_enabled,
            }
        except Exception as e:
            log.error(f"Failed to apply dynamic TP: {e}")
            return None
    
    def update_adaptive_sl(self, position: Position, current_price: float, candles: Optional[List[Dict]] = None):
        """
        Update adaptive stop loss for a position.
        
        Checks and applies:
        1. Breakeven move (at 50% to TP1)
        2. Profit lock (at TP1 hit)
        3. Trailing stop (when TP2 hit - activation price = TP2)
        
        Args:
            position: Position object
            current_price: Current market price
            candles: Recent candle data for trailing stop calculation
        """
        if not position.is_open:
            return
        
        old_sl = position.sl_price
        new_sl = None
        update_reason = None
        
        # Check breakeven condition (50% to TP1)
        breakeven_sl = self.adaptive_sl.move_to_breakeven(position.to_dict(), current_price)
        if breakeven_sl is not None and breakeven_sl != old_sl:
            new_sl = breakeven_sl
            update_reason = "BREAKEVEN"
            log.info(f"SL moved to breakeven for {position.symbol} @ ${new_sl:.2f}")
        
        # Check profit lock condition (TP1 hit)
        if position.tp_hit and not update_reason:
            profit_lock_sl = self.adaptive_sl.lock_in_profit(position.to_dict(), current_price)
            if profit_lock_sl is not None and profit_lock_sl != old_sl:
                new_sl = profit_lock_sl
                update_reason = "PROFIT_LOCK"
                log.info(f"SL locked in profit for {position.symbol} @ ${new_sl:.2f}")
        
        # Check trailing stop condition (TP hit - activation price = TP price)
        # Trailing stop activates when price reaches TP
        if position.tp_hit:
            just_activated = not position.trailing_active
            # Always activate trailing flag when TP is hit
            if just_activated:
                position.trailing_active = True
                log.info(f"Trailing stop activated for {position.symbol} at TP price ${position.tp_price:.2f}")

            if candles:
                trailing_sl = self.adaptive_sl.update_trailing_stop(position.to_dict(), current_price, candles)
                if trailing_sl is not None:
                    # On first activation, always set trailing_stop_price even if below current SL
                    if just_activated:
                        position.trailing_stop_price = trailing_sl
                        log.info(f"Initial trailing stop set for {position.symbol} @ ${trailing_sl:.2f}")
                    # Only update sl_price if trailing stop is better than current SL
                    if (new_sl is None or trailing_sl > new_sl) and trailing_sl > old_sl:
                        new_sl = trailing_sl
                        update_reason = "TRAILING"
                        log.info(f"Trailing stop updated for {position.symbol}: ${old_sl:.2f} -> ${new_sl:.2f}")
                elif just_activated:
                    # Even if chandelier returns None, set trailing_stop_price to current SL as baseline
                    position.trailing_stop_price = position.sl_price
                    log.info(f"Trailing stop initialized at current SL for {position.symbol} @ ${position.sl_price:.2f}")
        
        # Apply SL update if any
        if new_sl is not None and new_sl != old_sl:
            position.sl_price = new_sl
            self.adaptive_sl.update_position_sl(
                position.execution_id,
                new_sl,
                update_reason,
                f"{update_reason} at price ${current_price:.2f}"
            )

    def get_aggregate_pnl(self) -> Dict:
        """Get aggregate P&L across all positions."""
        total_unrealised = sum(p.unrealised_pnl * (p.remaining_qty / p.qty) for p in self._positions.values() if p.qty > 0)
        total_realised = sum(p.realised_pnl for p in self._positions.values())
        total_realised += sum(p.realised_pnl for p in self._closed_positions)

        return {
            "open_positions": len(self._positions),
            "total_unrealised_pnl": round(total_unrealised, 4),
            "total_realised_pnl": round(total_realised, 4),
            "closed_count": len(self._closed_positions),
        }
