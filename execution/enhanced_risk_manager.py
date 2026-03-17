"""
Enhanced Risk Management System

Provides advanced risk management with:
- Kelly Criterion position sizing
- Dynamic risk adjustment based on performance
- Portfolio-level risk limits
- Daily loss limits

**Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7, 16.8, 16.9, 16.10**
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from utils.logger import get_logger

log = get_logger("execution.enhanced_risk_manager")


@dataclass
class PerformanceStats:
    """Recent performance statistics for risk adjustment."""
    consecutive_wins: int
    consecutive_losses: int
    recent_win_rate: float  # Last 20 trades
    recent_avg_rr: float
    recent_pnl: float


@dataclass
class RiskCheckResult:
    """Result of portfolio risk limit checks."""
    approved: bool
    reason: str
    current_portfolio_risk: float
    max_portfolio_risk: float
    current_daily_loss: float
    max_daily_loss: float


@dataclass
class PositionSizeCalculation:
    """Detailed position size calculation breakdown."""
    base_size: float
    kelly_size: float
    adjusted_size: float  # After performance adjustment
    final_size: float  # After portfolio limits
    risk_pct: float
    adjustments_applied: List[str]


class EnhancedRiskManager:
    """
    Enhanced Risk Management System with Kelly Criterion and dynamic adjustments.
    
    **Validates: Requirements 16.1-16.10**
    """
    
    def __init__(self, db, config: Optional[Dict] = None):
        """
        Initialize Enhanced Risk Manager.
        
        Args:
            db: Database instance for tracking performance
            config: Optional configuration overrides
        """
        self.db = db
        self.config = config or self._default_config()
        log.info("Enhanced Risk Manager initialized")
    
    def _default_config(self) -> Dict:
        """Default risk management configuration."""
        return {
            "base_risk_per_trade_pct": 1.0,  # 1% risk per trade
            "max_portfolio_risk_pct": 5.0,  # Max 5% portfolio risk
            "max_daily_loss_pct": 3.0,  # Max 3% daily loss
            "consecutive_loss_threshold": 3,  # Reduce after 3 losses
            "consecutive_win_threshold": 5,  # Increase after 5 wins
            "loss_reduction_multiplier": 0.5,  # Reduce to 50%
            "win_increase_multiplier": 1.25,  # Increase to 125%
            "max_position_size_multiplier": 2.0,  # Max 2x base size
            "kelly_fraction": 0.25,  # Use 25% of Kelly (conservative)
        }
    
    def calculate_portfolio_risk(self, active_positions: List[Dict]) -> float:
        """
        Calculate current portfolio risk as % of total capital.
        
        **Validates: Requirement 16.1**
        
        Args:
            active_positions: List of active position dictionaries
            
        Returns:
            Portfolio risk percentage
        """
        if not active_positions:
            return 0.0
        
        total_risk = 0.0
        for position in active_positions:
            # Calculate risk per position (distance to SL)
            entry_price = position.get("entry_price", 0)
            sl_price = position.get("sl_price", 0)
            qty = position.get("qty", 0)
            
            if entry_price > 0 and sl_price > 0:
                risk_per_unit = abs(entry_price - sl_price)
                position_risk = risk_per_unit * qty
                total_risk += position_risk
        
        # Get account balance to calculate percentage
        # Note: This would need to be passed in or retrieved from portfolio manager
        # For now, return absolute risk
        return total_risk
    
    def calculate_kelly_position_size(
        self, 
        win_rate: float, 
        avg_win: float, 
        avg_loss: float, 
        capital: float
    ) -> float:
        """
        Calculate optimal position size using Kelly Criterion.
        
        **Validates: Requirement 16.2**
        
        Kelly % = (Win Rate * Avg Win - (1 - Win Rate) * Avg Loss) / Avg Win
        
        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average win amount
            avg_loss: Average loss amount (positive value)
            capital: Available capital
            
        Returns:
            Position size in $
        """
        if avg_win <= 0 or win_rate <= 0:
            return 0.0
        
        # Kelly formula
        kelly_pct = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        
        # Apply conservative fraction (default 25% of Kelly)
        kelly_fraction = self.config["kelly_fraction"]
        adjusted_kelly = kelly_pct * kelly_fraction
        
        # Ensure non-negative
        adjusted_kelly = max(0, adjusted_kelly)
        
        # Calculate position size
        position_size = capital * adjusted_kelly
        
        log.debug(
            f"Kelly calculation: WR={win_rate:.2%}, AvgWin={avg_win:.2f}, "
            f"AvgLoss={avg_loss:.2f}, Kelly%={kelly_pct:.2%}, "
            f"Adjusted={adjusted_kelly:.2%}, Size=${position_size:.2f}"
        )
        
        return position_size
    
    def adjust_risk_per_trade(self, recent_performance: PerformanceStats) -> float:
        """
        Adjust risk per trade based on recent performance.
        
        **Validates: Requirements 16.5, 16.6, 16.7**
        
        - 3 consecutive losses: reduce by 50%
        - 5 consecutive wins: increase by 25% (max 2x base)
        
        Args:
            recent_performance: Recent performance statistics
            
        Returns:
            Adjusted risk per trade (%)
        """
        base_risk = self.config["base_risk_per_trade_pct"]
        adjusted_risk = base_risk
        
        # Check for losing streak (Requirement 16.6)
        if recent_performance.consecutive_losses >= self.config["consecutive_loss_threshold"]:
            multiplier = self.config["loss_reduction_multiplier"]
            adjusted_risk = base_risk * multiplier
            log.warning(
                f"Losing streak detected ({recent_performance.consecutive_losses} losses). "
                f"Reducing risk to {adjusted_risk:.2f}%"
            )
        
        # Check for winning streak (Requirement 16.7)
        elif recent_performance.consecutive_wins >= self.config["consecutive_win_threshold"]:
            multiplier = self.config["win_increase_multiplier"]
            max_multiplier = self.config["max_position_size_multiplier"]
            adjusted_risk = min(base_risk * multiplier, base_risk * max_multiplier)
            log.info(
                f"Winning streak detected ({recent_performance.consecutive_wins} wins). "
                f"Increasing risk to {adjusted_risk:.2f}%"
            )
        
        return adjusted_risk
    
    def check_portfolio_limits(
        self, 
        portfolio_risk: float, 
        daily_loss: float,
        account_balance: float
    ) -> RiskCheckResult:
        """
        Check portfolio-level risk limits.
        
        **Validates: Requirements 16.3, 16.8, 16.9**
        
        Limits:
        - Portfolio risk <5% total capital (Requirement 16.3)
        - Daily loss <3% account (Requirement 16.8)
        
        Args:
            portfolio_risk: Current portfolio risk in $
            daily_loss: Current daily loss in $
            account_balance: Current account balance
            
        Returns:
            RiskCheckResult with approval/rejection
        """
        max_portfolio_risk_pct = self.config["max_portfolio_risk_pct"]
        max_daily_loss_pct = self.config["max_daily_loss_pct"]
        
        # Calculate percentages
        portfolio_risk_pct = (portfolio_risk / account_balance * 100) if account_balance > 0 else 0
        daily_loss_pct = (abs(daily_loss) / account_balance * 100) if account_balance > 0 else 0
        
        # Check portfolio risk limit (Requirement 16.3)
        if portfolio_risk_pct >= max_portfolio_risk_pct:
            return RiskCheckResult(
                approved=False,
                reason=f"Portfolio risk limit exceeded: {portfolio_risk_pct:.2f}% >= {max_portfolio_risk_pct}%",
                current_portfolio_risk=portfolio_risk_pct,
                max_portfolio_risk=max_portfolio_risk_pct,
                current_daily_loss=daily_loss_pct,
                max_daily_loss=max_daily_loss_pct
            )
        
        # Check daily loss limit (Requirement 16.8)
        if daily_loss_pct >= max_daily_loss_pct:
            return RiskCheckResult(
                approved=False,
                reason=f"Daily loss limit exceeded: {daily_loss_pct:.2f}% >= {max_daily_loss_pct}%",
                current_portfolio_risk=portfolio_risk_pct,
                max_portfolio_risk=max_portfolio_risk_pct,
                current_daily_loss=daily_loss_pct,
                max_daily_loss=max_daily_loss_pct
            )
        
        # All checks passed
        return RiskCheckResult(
            approved=True,
            reason="All risk limits satisfied",
            current_portfolio_risk=portfolio_risk_pct,
            max_portfolio_risk=max_portfolio_risk_pct,
            current_daily_loss=daily_loss_pct,
            max_daily_loss=max_daily_loss_pct
        )
    
    def should_block_trading(self, daily_loss: float, account_balance: float) -> bool:
        """
        Check if trading should be blocked due to daily loss limit.
        
        **Validates: Requirement 16.9**
        
        Args:
            daily_loss: Current daily loss in $
            account_balance: Current account balance
            
        Returns:
            True if daily loss limit reached
        """
        max_daily_loss_pct = self.config["max_daily_loss_pct"]
        daily_loss_pct = (abs(daily_loss) / account_balance * 100) if account_balance > 0 else 0
        
        if daily_loss_pct >= max_daily_loss_pct:
            log.error(
                f"Trading blocked: Daily loss limit reached "
                f"({daily_loss_pct:.2f}% >= {max_daily_loss_pct}%)"
            )
            return True
        
        return False
    
    def calculate_position_size(
        self,
        signal: Dict,
        account_balance: float,
        portfolio_risk: float,
        recent_performance: PerformanceStats
    ) -> PositionSizeCalculation:
        """
        Calculate position size with all adjustments applied.
        
        **Validates: Requirements 16.4, 16.5, 16.10**
        
        Args:
            signal: Trading signal dictionary
            account_balance: Current account balance
            portfolio_risk: Current portfolio risk in $
            recent_performance: Recent performance statistics
            
        Returns:
            PositionSizeCalculation with detailed breakdown
        """
        adjustments = []
        
        # Base calculation (Requirement 16.4)
        entry_price = signal.get("entry_price", 0)
        sl_price = signal.get("sl_price", 0)
        
        if entry_price <= 0 or sl_price <= 0:
            return PositionSizeCalculation(
                base_size=0,
                kelly_size=0,
                adjusted_size=0,
                final_size=0,
                risk_pct=0,
                adjustments_applied=["Invalid entry or SL price"]
            )
        
        # Calculate base risk per trade
        base_risk_pct = self.config["base_risk_per_trade_pct"]
        
        # Adjust for recent performance (Requirement 16.5)
        adjusted_risk_pct = self.adjust_risk_per_trade(recent_performance)
        if adjusted_risk_pct != base_risk_pct:
            adjustments.append(
                f"Performance adjustment: {base_risk_pct:.2f}% -> {adjusted_risk_pct:.2f}%"
            )
        
        # Calculate base position size
        risk_amount = account_balance * (adjusted_risk_pct / 100)
        sl_distance = abs(entry_price - sl_price)
        base_size = risk_amount / sl_distance if sl_distance > 0 else 0
        
        # Calculate Kelly size (Requirement 16.2)
        kelly_size = 0
        if recent_performance.recent_win_rate > 0:
            # Estimate avg win/loss from recent R:R
            avg_rr = recent_performance.recent_avg_rr
            avg_win = sl_distance * avg_rr if avg_rr > 0 else sl_distance
            avg_loss = sl_distance
            
            kelly_size = self.calculate_kelly_position_size(
                win_rate=recent_performance.recent_win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss,
                capital=account_balance
            )
            
            # Convert Kelly $ to quantity
            kelly_size = kelly_size / entry_price if entry_price > 0 else 0
            adjustments.append(f"Kelly sizing applied")
        
        # Use the more conservative of base and Kelly
        adjusted_size = min(base_size, kelly_size) if kelly_size > 0 else base_size
        
        # Check portfolio limits (Requirement 16.3)
        final_size = adjusted_size
        max_portfolio_risk_pct = self.config["max_portfolio_risk_pct"]
        portfolio_risk_pct = (portfolio_risk / account_balance * 100) if account_balance > 0 else 0
        
        # If adding this position would exceed portfolio limit, reduce size
        new_position_risk = final_size * sl_distance
        total_risk_pct = ((portfolio_risk + new_position_risk) / account_balance * 100) if account_balance > 0 else 0
        
        if total_risk_pct > max_portfolio_risk_pct:
            # Reduce size to fit within limit
            available_risk = account_balance * (max_portfolio_risk_pct / 100) - portfolio_risk
            if available_risk > 0:
                final_size = available_risk / sl_distance if sl_distance > 0 else 0
                adjustments.append(
                    f"Portfolio limit: reduced to fit within {max_portfolio_risk_pct}% total risk"
                )
            else:
                final_size = 0
                adjustments.append("Portfolio limit: no risk capacity available")
        
        return PositionSizeCalculation(
            base_size=base_size,
            kelly_size=kelly_size,
            adjusted_size=adjusted_size,
            final_size=final_size,
            risk_pct=adjusted_risk_pct,
            adjustments_applied=adjustments
        )
    
    def get_recent_performance(self, lookback_trades: int = 20) -> PerformanceStats:
        """
        Get recent performance statistics from database.
        
        Args:
            lookback_trades: Number of recent trades to analyze
            
        Returns:
            PerformanceStats with recent performance data
        """
        try:
            # Get recent executions
            executions = self.db.get_executions(status="CLOSED", limit=lookback_trades)
            
            if not executions:
                # No history, return neutral stats
                return PerformanceStats(
                    consecutive_wins=0,
                    consecutive_losses=0,
                    recent_win_rate=0.5,  # Assume 50% for new accounts
                    recent_avg_rr=1.5,  # Assume 1.5 R:R
                    recent_pnl=0
                )
            
            # Calculate consecutive wins/losses
            consecutive_wins = 0
            consecutive_losses = 0
            for execution in executions:
                pnl = execution.get("realised_pnl", 0)
                if pnl > 0:
                    consecutive_wins += 1
                    consecutive_losses = 0
                elif pnl < 0:
                    consecutive_losses += 1
                    consecutive_wins = 0
                else:
                    break  # Stop at breakeven
            
            # Calculate win rate
            wins = sum(1 for e in executions if e.get("realised_pnl", 0) > 0)
            total = len(executions)
            win_rate = wins / total if total > 0 else 0.5
            
            # Calculate average R:R (for winners)
            rr_values = []
            for execution in executions:
                entry = execution.get("entry_price", 0)
                exit_price = execution.get("exit_price", 0)
                sl = execution.get("sl_price", 0)
                
                if entry > 0 and exit_price > 0 and sl > 0:
                    direction = execution.get("direction", "LONG")
                    if direction == "LONG":
                        profit = exit_price - entry
                        risk = entry - sl
                    else:
                        profit = entry - exit_price
                        risk = sl - entry
                    
                    if risk > 0 and profit > 0:
                        rr = profit / risk
                        rr_values.append(rr)
            
            avg_rr = sum(rr_values) / len(rr_values) if rr_values else 1.5
            
            # Calculate recent PnL
            recent_pnl = sum(e.get("realised_pnl", 0) for e in executions)
            
            return PerformanceStats(
                consecutive_wins=consecutive_wins,
                consecutive_losses=consecutive_losses,
                recent_win_rate=win_rate,
                recent_avg_rr=avg_rr,
                recent_pnl=recent_pnl
            )
            
        except Exception as e:
            log.error(f"Error getting recent performance: {e}")
            # Return neutral stats on error
            return PerformanceStats(
                consecutive_wins=0,
                consecutive_losses=0,
                recent_win_rate=0.5,
                recent_avg_rr=1.5,
                recent_pnl=0
            )
