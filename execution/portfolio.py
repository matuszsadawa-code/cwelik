"""
OpenClaw Portfolio Manager — Portfolio-level risk management.

Controls:
- Position sizing via EnhancedRiskManager (Kelly Criterion + streak adjustment)
- Dynamic correlation-based position blocking via CorrelationOptimizer
- Maximum concurrent positions limit
- Daily drawdown protection (halt trading on excessive loss)
- Circuit breakers (rapid loss detection)
- Balance tracking and equity snapshots
"""

import time
from datetime import datetime, date
from typing import Dict, List, Optional

from execution.position_manager import PositionManager
from execution.order_executor import OrderExecutor
from execution.enhanced_risk_manager import EnhancedRiskManager
from execution.correlation_optimizer import CorrelationOptimizer
from execution.adaptive_sl import AdaptiveSLSystem
from utils.logger import get_logger

log = get_logger("execution.portfolio")


# ═══════════════════════════════════════════════════════════════════
# DEFAULT RISK PARAMETERS
# ═══════════════════════════════════════════════════════════════════

DEFAULT_RISK = {
    # DYNAMIC POSITION SIZING via EnhancedRiskManager (Kelly Criterion)
    # Base 1% per trade, adjusted by performance streaks
    # Fallback fixed allocation when ERM unavailable:
    "capital_allocation_pct": 2.0,

    # DYNAMIC LEVERAGE: Scaled by quality, capped at 25x
    "leverage_by_quality": {
        "A+": 25,    # 25x for highest quality
        "A": 20,     # 20x for A quality
        "B": 15,     # 15x for B quality
        "C": 10,     # 10x for C quality
    },
    "min_leverage": 10,      # Never go below 10x
    "max_leverage": 25,      # Hard cap at 25x (was 100x — too aggressive)

    # Portfolio limits
    "max_concurrent_positions": 20,     # Max 20 open positions
    "max_daily_drawdown_pct": 6.0,     # Halt all trades if -6% daily
    "max_single_loss_pct": 3.0,         # Max loss per single trade

    # Circuit breaker
    "circuit_breaker_losses_window": 3,   # Halt if N losses within...
    "circuit_breaker_minutes": 30,        # ...M minutes
    "circuit_breaker_hourly_drawdown": 5.0,  # Halt on 5% drawdown in 1 hour

    # Paper trading defaults
    "paper_initial_balance": 10000.0,
}


class PortfolioManager:
    """
    Portfolio-level risk management and position sizing.
    
    Integrates:
    - EnhancedRiskManager: Kelly Criterion + streak-based dynamic sizing
    - CorrelationOptimizer: Dynamic correlation matrix for position blocking
    - AdaptiveSLSystem: SL validation before placement
    - Circuit breakers: Rapid loss detection
    """

    def __init__(self, executor: OrderExecutor, pos_manager: PositionManager,
                 db=None, candle_manager=None, risk_config: Dict = None):
        self.executor = executor
        self.positions = pos_manager
        self.db = db
        self.candle_manager = candle_manager
        self.risk = {**DEFAULT_RISK, **(risk_config or {})}

        # ─── Advanced Risk Management ───────────────────────────────
        self.enhanced_risk = None
        if db:
            try:
                self.enhanced_risk = EnhancedRiskManager(db)
                log.info("✅ EnhancedRiskManager integrated (Kelly Criterion + streak-based sizing)")
            except Exception as e:
                log.warning(f"EnhancedRiskManager init failed, using fallback sizing: {e}")

        # ─── Correlation Optimizer ──────────────────────────────────
        self.correlation_optimizer = None
        if candle_manager:
            try:
                self.correlation_optimizer = CorrelationOptimizer(candle_manager=candle_manager)
                log.info("✅ CorrelationOptimizer integrated (dynamic correlation matrix)")
            except Exception as e:
                log.warning(f"CorrelationOptimizer init failed, will use basic checks: {e}")

        # ─── Adaptive SL for initial SL validation ──────────────────
        self.adaptive_sl = AdaptiveSLSystem()

        # State
        self._paper_balance = self.risk["paper_initial_balance"]
        self._daily_pnl = 0.0
        self._daily_trades = 0
        self._daily_date = date.today()
        self._halted = False
        self._halt_reason = None
        self._recent_losses: List[float] = []  # timestamps of recent losses for circuit breaker

        self._equity_history: List[Dict] = []

        # Execution enabled flag
        self._auto_execute = True

        log.info(f"PortfolioManager initialized")
        log.info(f"  Max positions: {self.risk['max_concurrent_positions']}")
        log.info(f"  Max daily drawdown: {self.risk['max_daily_drawdown_pct']}%")
        log.info(f"  Leverage: {self.risk['min_leverage']}x-{self.risk['max_leverage']}x")
        log.info(f"  Risk engine: {'EnhancedRiskManager (Kelly)' if self.enhanced_risk else 'Flat 2% allocation'}")
        log.info(f"  Correlation: {'Dynamic matrix' if self.correlation_optimizer else 'Disabled'}")

    # ═══════════════════════════════════════════════════════════════════
    # SIGNAL PROCESSING
    # ═══════════════════════════════════════════════════════════════════

    async def process_signal(self, signal: Dict) -> Optional[Dict]:
        """
        Process a signal through risk checks and execute if approved.
        
        Returns execution result if executed, None if rejected.
        """
        self._check_daily_reset()

        symbol = signal["symbol"]
        quality = signal.get("quality", "B")
        direction = signal["signal_type"]

        log.info(f"[PROCESSING] Processing signal: {direction} {symbol} (Q:{quality})")

        # ─── Enhanced Risk Management (portfolio-level) ───────────
        if self.enhanced_risk:
            active_positions = [p.to_dict() for p in self.positions.get_all_open()]
            account_balance = await self._get_equity()

            # Check daily loss limit (blocks all trading)
            if self.enhanced_risk.should_block_trading(self._daily_pnl, account_balance):
                self._halted = True
                self._halt_reason = "Daily loss limit exceeded (EnhancedRiskManager)"
                log.error(f"[BLOCKED] {self._halt_reason}")
                return None

            # Check portfolio limits
            portfolio_risk = self.enhanced_risk.calculate_portfolio_risk(active_positions)
            risk_check = self.enhanced_risk.check_portfolio_limits(
                portfolio_risk=portfolio_risk,
                daily_loss=abs(self._daily_pnl),
                account_balance=account_balance
            )
            if not risk_check.approved:
                log.warning(f"[REJECTED] ERM: {risk_check.reason}")
                return None

        # ─── Correlation check (dynamic) ────────────────────────
        if self.correlation_optimizer:
            try:
                open_symbols = [p.symbol for p in self.positions.get_all_open()]
                if open_symbols:
                    # Get highly correlated pairs with currently open positions
                    all_symbols = list(set(open_symbols + [symbol]))
                    corr_pairs = self.correlation_optimizer.get_highly_correlated_pairs(all_symbols)
                    for pair_a, pair_b, corr_value in corr_pairs:
                        if symbol in (pair_a, pair_b):
                            other = pair_b if symbol == pair_a else pair_a
                            other_pos = self.positions.get_position_for_symbol(other)
                            if other_pos and other_pos.direction == direction:
                                log.warning(
                                    f"[REJECTED] Dynamic correlation block: {symbol} ↔ {other} "
                                    f"(corr={corr_value:.2f}, both {direction})"
                                )
                                return None
            except Exception as e:
                log.debug(f"Correlation check skipped: {e}")

        # ─── Standard risk checks ──────────────────────────────
        reject_reason = self._check_risk_limits(signal)
        if reject_reason:
            log.warning(f"[REJECTED] Signal rejected: {reject_reason}")
            return None

        if not self._auto_execute:
            log.info(f"[PAUSED] Auto-execution disabled — signal logged but not executed")
            return None

        # ─── Calculate dynamic leverage ─────────────────────────
        leverage = self._calculate_dynamic_leverage(signal)

        # ─── Calculate position size (Kelly or fallback) ──────────
        position_size = await self._calculate_position_size(signal)
        if position_size <= 0:
            log.warning(f"[REJECTED] Position size too small: {position_size}")
            return None

        log.info(f"[SIZE] Position size: {position_size:.6f} {symbol.replace('USDT', '')} @ {leverage}x leverage")

        # ─── Execute ─────────────────────────────────────────
        result = await self.executor.execute_signal(
            signal=signal,
            position_size_qty=position_size,
            leverage=leverage,
        )

        if result.get("status") == "FILLED":
            # Track position
            self.positions.add_position(result)
            self._daily_trades += 1

            # ─── Apply Dynamic TP ────────────────────────────────
            if self.positions.use_dynamic_tp and self.candle_manager:
                try:
                    # We need some candles for ATR/RSI, using 15m as default
                    candles = await self.candle_manager.get_candles(symbol, "15", limit=50)
                    if candles:
                        exec_id = result.get("execution_id")
                        tp_result = self.positions.apply_dynamic_tp(exec_id, signal, candles)
                        if tp_result:
                            log.info(f"[DYNAMIC TP] Updated TP levels for {exec_id}: {tp_result}")
                except Exception as e:
                    log.error(f"[DYNAMIC TP] Failed to apply for {symbol}: {e}")

            log.info(f"[OK] Position opened: {result['execution_id']}")
            await self._record_equity()
            return result
        else:
            log.error(f"[FAILED] Execution failed: {result.get('error', 'Unknown')}")
            return None

    # ═══════════════════════════════════════════════════════════════════
    # RISK CHECKS
    # ═══════════════════════════════════════════════════════════════════

    def _check_risk_limits(self, signal: Dict) -> Optional[str]:
        """Run all risk checks. Returns rejection reason or None if OK."""
        symbol = signal["symbol"]
        direction = signal["signal_type"]

        # Check if halted
        if self._halted:
            return f"Trading halted: {self._halt_reason}"

        # Check daily drawdown
        if abs(self._daily_pnl) >= self.risk["max_daily_drawdown_pct"]:
            self._halted = True
            self._halt_reason = f"Daily drawdown limit hit: {self._daily_pnl:.2f}%"
            return self._halt_reason

        # Circuit breaker: rapid losses
        if self._check_circuit_breaker():
            return f"Circuit breaker: too many losses in short period"

        # Check max concurrent positions
        open_count = self.positions.count_open()
        max_positions = self.risk["max_concurrent_positions"]
        
        log.info(f"[RISK CHECK] Position limit: {open_count}/{max_positions} positions open")
        
        if open_count >= max_positions:
            rejection_reason = f"Max positions ({max_positions}) reached (current: {open_count})"
            log.warning(f"[REJECTED] {rejection_reason}")
            return rejection_reason

        # Check if already have position for this symbol
        existing = self.positions.get_position_for_symbol(symbol)
        if existing:
            return f"Already have {existing.direction} position for {symbol}"

        log.debug(f"[RISK CHECK] All checks passed for {symbol} {direction}")
        return None

    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker should trigger due to rapid losses."""
        window = self.risk.get("circuit_breaker_losses_window", 3)
        minutes = self.risk.get("circuit_breaker_minutes", 30)

        now = time.time()
        cutoff = now - (minutes * 60)

        # Clean old entries
        self._recent_losses = [t for t in self._recent_losses if t > cutoff]

        if len(self._recent_losses) >= window:
            self._halted = True
            self._halt_reason = f"Circuit breaker: {len(self._recent_losses)} losses in {minutes} min"
            log.error(f"[CIRCUIT BREAKER] {self._halt_reason}")
            return True
        return False

    def record_loss(self):
        """Record a trade loss for circuit breaker tracking."""
        self._recent_losses.append(time.time())

    # ═══════════════════════════════════════════════════════════════════
    # POSITION SIZING
    # ═══════════════════════════════════════════════════════════════════

    def _calculate_dynamic_leverage(self, signal: Dict) -> int:
        """
        Calculate dynamic leverage based on signal quality.
        
        Returns leverage between min_leverage (10x) and max_leverage (25x),
        scaled by signal quality.
        """
        quality = signal.get("quality", "B")
        leverage = self.risk["leverage_by_quality"].get(quality, 15)
        
        # Enforce min/max bounds
        min_lev = self.risk["min_leverage"]
        max_lev = self.risk["max_leverage"]
        leverage = max(min_lev, min(max_lev, leverage))
        
        log.info(f"[LEVERAGE] Dynamic leverage for {quality}: {leverage}x (min: {min_lev}x, max: {max_lev}x)")
        return leverage

    async def _calculate_position_size(self, signal: Dict) -> float:
        """
        Calculate position size.
        
        Uses EnhancedRiskManager (Kelly Criterion + performance adjustment) if available,
        otherwise falls back to fixed 2% capital allocation.
        """
        entry_price = signal["entry_price"]
        symbol = signal["symbol"]

        # Get current available balance
        balance = await self._get_equity()
        if balance <= 0:
            log.warning(f"[SIZE] No available balance: {balance}")
            return 0

        # ─── Enhanced sizing (Kelly + streaks) ───────────────────
        if self.enhanced_risk:
            try:
                active_positions = [p.to_dict() for p in self.positions.get_all_open()]
                portfolio_risk = self.enhanced_risk.calculate_portfolio_risk(active_positions)
                recent_perf = self.enhanced_risk.get_recent_performance()

                size_calc = self.enhanced_risk.calculate_position_size(
                    signal=signal,
                    account_balance=balance,
                    portfolio_risk=portfolio_risk,
                    recent_performance=recent_perf
                )

                if size_calc.final_size > 0:
                    leverage = self._calculate_dynamic_leverage(signal)
                    position_notional = size_calc.final_size * leverage
                    position_qty = position_notional / entry_price

                    log.info(
                        f"[SIZE/ERM] Balance: ${balance:.2f}, "
                        f"Kelly size: ${size_calc.kelly_size:.2f}, "
                        f"Risk: {size_calc.risk_pct:.2f}%, "
                        f"Adj: {', '.join(size_calc.adjustments_applied) if size_calc.adjustments_applied else 'none'}"
                    )
                    return max(position_qty, 0)
                else:
                    log.warning(f"[SIZE/ERM] ERM returned zero size: {', '.join(size_calc.adjustments_applied)}")
                    return 0
            except Exception as e:
                log.warning(f"[SIZE/ERM] Enhanced sizing failed, falling back to flat: {e}")

        # ─── Fallback: flat 2% allocation ────────────────────────
        allocation_pct = self.risk["capital_allocation_pct"]
        buffer = 0.98
        effective_balance = balance * buffer
        allocated_capital = effective_balance * (allocation_pct / 100)

        leverage = self._calculate_dynamic_leverage(signal)
        position_notional = allocated_capital * leverage
        position_qty = position_notional / entry_price

        log.info(
            f"[SIZE] Balance: ${balance:.2f} (Effective: ${effective_balance:.2f}), "
            f"Allocation: {allocation_pct}% (${allocated_capital:.2f}), "
            f"Leverage: {leverage}x, "
            f"Notional: ${position_notional:.2f}, "
            f"Qty: {position_qty:.6f}"
        )

        return max(position_qty, 0)

    # ═══════════════════════════════════════════════════════════════════
    # EQUITY & BALANCE
    # ═══════════════════════════════════════════════════════════════════

    async def _get_equity(self) -> float:
        """Get current equity (paper or live)."""
        if self.executor.mode.value == "paper":
            # Paper equity = initial + realised P&L
            agg = self.positions.get_aggregate_pnl()
            return self._paper_balance + (agg["total_realised_pnl"] / 100 * self._paper_balance)
        else:
            wallet = await self.executor.get_wallet_balance()
            return wallet.get("total_equity", 0)

    async def _record_equity(self):
        """Record current equity snapshot for charting."""
        equity = await self._get_equity()
        self._equity_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "equity": round(equity, 2),
            "open_positions": self.positions.count_open(),
            "daily_pnl": round(self._daily_pnl, 4),
        })

        if len(self._equity_history) > 720:
            self._equity_history = self._equity_history[-720:]

    def _check_daily_reset(self):
        """Reset daily stats if new day."""
        today = date.today()
        if today != self._daily_date:
            self._daily_pnl = 0.0
            self._daily_trades = 0
            self._daily_date = today
            self._halted = False
            self._halt_reason = None
            log.info(f"[DATE] Daily reset: {today}")

    async def update_daily_pnl(self):
        """Update daily P&L from closed positions."""
        agg = self.positions.get_aggregate_pnl()
        self._daily_pnl = agg.get("total_realised_pnl", 0)
        await self._record_equity()

        if self._daily_pnl <= -self.risk["max_daily_drawdown_pct"]:
            self._halted = True
            self._halt_reason = f"Daily drawdown breached: {self._daily_pnl:.2f}%"
            log.warning(f"[STOPPED] {self._halt_reason}")

    # ═══════════════════════════════════════════════════════════════════
    # CONTROL
    # ═══════════════════════════════════════════════════════════════════

    def set_auto_execute(self, enabled: bool):
        """Enable or disable automatic execution."""
        self._auto_execute = enabled
        log.info(f"Auto-execution: {'ENABLED' if enabled else 'DISABLED'}")

    def is_auto_execute(self) -> bool:
        return self._auto_execute

    def is_halted(self) -> bool:
        return self._halted

    def reset_halt(self):
        """Manually reset halt status (use with caution)."""
        self._halted = False
        self._halt_reason = None
        log.info("Trading halt manually reset")

    # ═══════════════════════════════════════════════════════════════════
    # STATUS / SERIALIZATION
    # ═══════════════════════════════════════════════════════════════════

    async def get_status(self) -> Dict:
        """Get full portfolio status for API/dashboard."""
        agg = self.positions.get_aggregate_pnl()

        return {
            "mode": self.executor.mode.value,
            "auto_execute": self._auto_execute,
            "halted": self._halted,
            "halt_reason": self._halt_reason,
            "equity": round(await self._get_equity(), 2) if self.executor.mode.value == "paper" else 0.0,
            "open_positions": agg["open_positions"],
            "closed_today": self._daily_trades,
            "daily_pnl": round(self._daily_pnl, 4),
            "unrealised_pnl": agg["total_unrealised_pnl"],
            "realised_pnl": agg["total_realised_pnl"],
            "max_positions": self.risk["max_concurrent_positions"],
            "max_daily_drawdown": self.risk["max_daily_drawdown_pct"],
            "risk_per_trade": self.risk.get("capital_allocation_pct", 2.0),
        }

    def get_equity_history(self) -> List[Dict]:
        """Get equity curve data for charting."""
        return self._equity_history


# Fallback for leverage config
try:
    from config import STRATEGY
    STRATEGY_LEVERAGE = STRATEGY.get("default_leverage", 10)
except ImportError:
    STRATEGY_LEVERAGE = 10
