"""
Signal Tracker — Monitors open signals and resolves outcomes.

Tracks price movement after signal generation to determine:
- TP1/TP2/TP3 hits
- SL hit
- Maximum favorable/adverse excursion
- Time in trade
"""

import time
from datetime import datetime
from typing import List, Dict, Optional

from data.candle_manager import CandleManager
from storage.database import Database
from utils.logger import get_logger

log = get_logger("analytics.tracker")


class SignalTracker:
    """Tracks open signals and resolves outcomes."""

    def __init__(self, candle_mgr: CandleManager, db: Database):
        self.candles = candle_mgr
        self.db = db
        # In-memory tracking of active signals
        self._active: Dict[str, Dict] = {}
        # Price snapshots for each signal
        self._snapshots: Dict[str, Dict[str, float]] = {}
        log.info("SignalTracker initialized")

    def track_signal(self, signal: Dict):
        """Start tracking a new signal."""
        signal_id = signal["signal_id"]
        self._active[signal_id] = {
            **signal,
            "tracked_at": time.time(),
            "max_favorable": 0,
            "max_adverse": 0,
            "tp1_hit": False,  # TP1 (risk-off at 1:1 R:R)
            "tp2_hit": False,  # TP2 (primary target at 2:1 R:R)
            "sl_hit": False,
        }
        self._snapshots[signal_id] = {}
        log.info(f"Tracking signal {signal_id} ({signal['signal_type']} {signal['symbol']})")

    def update_all(self):
        """Update price for all active signals and check exits."""
        for signal_id in list(self._active.keys()):
            signal = self._active[signal_id]
            try:
                current_price = self.candles.get_current_price(signal["symbol"])
                if current_price > 0:
                    self._check_price(signal_id, signal, current_price)
            except Exception as e:
                log.error(f"Error updating signal {signal_id}: {e}")

    def update_price(self, symbol: str, price: float):
        """Update price for all active signals of a given symbol (called from WebSocket)."""
        for signal_id, signal in list(self._active.items()):
            if signal["symbol"] == symbol:
                self._check_price(signal_id, signal, price)

    def _check_price(self, signal_id: str, signal: Dict, current_price: float):
        """Check price against signal levels."""
        entry = signal["entry_price"]
        sl = signal["sl_price"]
        tp1 = signal.get("tp1_price", signal.get("tp_price"))  # Backward compatibility
        tp2 = signal.get("tp2_price")
        direction = signal["signal_type"]

        # Calculate P&L
        if direction == "LONG":
            pnl_pct = (current_price - entry) / entry * 100
            favorable = max(0, pnl_pct)
            adverse = max(0, -pnl_pct)
        else:
            pnl_pct = (entry - current_price) / entry * 100
            favorable = max(0, pnl_pct)
            adverse = max(0, -pnl_pct)

        # Update max excursion
        signal["max_favorable"] = max(signal["max_favorable"], favorable)
        signal["max_adverse"] = max(signal["max_adverse"], adverse)

        # Track time-based snapshots (5m, 15m, 30m, 1h, 4h after signal)
        elapsed_min = (time.time() - signal["tracked_at"]) / 60
        snapshots = self._snapshots.get(signal_id, {})
        for mins, key in [(5, "5m"), (15, "15m"), (30, "30m"), (60, "1h"), (240, "4h")]:
            if key not in snapshots and elapsed_min >= mins:
                snapshots[key] = current_price
                self._snapshots[signal_id] = snapshots

        # Check target hits (priority: SL > TP1 > TP2)
        if direction == "LONG":
            # Check SL first
            if current_price <= sl and not signal["sl_hit"]:
                signal["sl_hit"] = True
                self._close_signal(signal_id, "LOSS", current_price, "SL_HIT")
                return
            # Check TP1 (risk-off)
            if tp1 and current_price >= tp1 and not signal["tp1_hit"]:
                signal["tp1_hit"] = True
                # If TP2 exists, partial close; otherwise full close
                if tp2:
                    log.info(f"Signal {signal_id} TP1 HIT @ ${current_price:.2f} (continuing to TP2)")
                else:
                    self._close_signal(signal_id, "WIN", current_price, "TP1_HIT")
                    return
            # Check TP2 (primary target)
            if tp2 and current_price >= tp2 and not signal["tp2_hit"]:
                signal["tp2_hit"] = True
                self._close_signal(signal_id, "WIN", current_price, "TP2_HIT")
                return
        else:  # SHORT
            # Check SL first
            if current_price >= sl and not signal["sl_hit"]:
                signal["sl_hit"] = True
                self._close_signal(signal_id, "LOSS", current_price, "SL_HIT")
                return
            # Check TP1 (risk-off)
            if tp1 and current_price <= tp1 and not signal["tp1_hit"]:
                signal["tp1_hit"] = True
                # If TP2 exists, partial close; otherwise full close
                if tp2:
                    log.info(f"Signal {signal_id} TP1 HIT @ ${current_price:.2f} (continuing to TP2)")
                else:
                    self._close_signal(signal_id, "WIN", current_price, "TP1_HIT")
                    return
            # Check TP2 (primary target)
            if tp2 and current_price <= tp2 and not signal["tp2_hit"]:
                signal["tp2_hit"] = True
                self._close_signal(signal_id, "WIN", current_price, "TP2_HIT")
                return

    def _close_signal(self, signal_id: str, outcome: str,
                      exit_price: float, reason: str):
        """Close a signal and save outcome."""
        signal = self._active.get(signal_id)
        if not signal:
            return

        entry = signal["entry_price"]
        direction = signal["signal_type"]
        sl = signal["sl_price"]

        if direction == "LONG":
            pnl_pct = (exit_price - entry) / entry * 100
        else:
            pnl_pct = (entry - exit_price) / entry * 100

        sl_distance = abs(entry - sl)
        rr_achieved = abs(exit_price - entry) / sl_distance if sl_distance > 0 else 0
        if pnl_pct < 0:
            rr_achieved = -rr_achieved

        elapsed_min = (time.time() - signal["tracked_at"]) / 60
        snapshots = self._snapshots.get(signal_id, {})

        outcome_data = {
            "signal_id": signal_id,
            "outcome": outcome,
            "exit_price": exit_price,
            "exit_reason": reason,
            "pnl_pct": round(pnl_pct, 4),
            "rr_achieved": round(rr_achieved, 4),
            "tp1_hit": 1 if signal.get("tp1_hit", False) else 0,
            "tp2_hit": 1 if signal.get("tp2_hit", False) else 0,
            "sl_hit": 1 if signal["sl_hit"] else 0,
            "max_favorable": round(signal["max_favorable"], 4),
            "max_adverse": round(signal["max_adverse"], 4),
            "duration_minutes": int(elapsed_min),
            "price_at_5m": snapshots.get("5m"),
            "price_at_15m": snapshots.get("15m"),
            "price_at_30m": snapshots.get("30m"),
            "price_at_1h": snapshots.get("1h"),
            "price_at_4h": snapshots.get("4h"),
            "closed_at": datetime.utcnow().isoformat(),
        }

        try:
            self.db.save_outcome(outcome_data)
            log.info(
                f"Signal {signal_id} CLOSED: {outcome} | "
                f"PnL: {pnl_pct:+.2f}% | R:R: {rr_achieved:.2f}:1 | "
                f"Duration: {int(elapsed_min)}min | Reason: {reason}"
            )
        except Exception as e:
            log.error(f"Error saving outcome for {signal_id}: {e}")

        # Remove from active tracking
        del self._active[signal_id]
        self._snapshots.pop(signal_id, None)

    def get_active_signals(self) -> List[Dict]:
        """Get all actively tracked signals."""
        return list(self._active.values())

    def get_active_count(self) -> int:
        """Get number of active signals."""
        return len(self._active)
