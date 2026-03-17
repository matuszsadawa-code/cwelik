# Enhanced Risk Manager Integration Guide

## Overview

The Enhanced Risk Manager provides advanced risk management capabilities including:
- Kelly Criterion position sizing
- Dynamic risk adjustment based on performance
- Portfolio-level risk limits
- Daily loss limits
- Trading block logic

## Integration with Portfolio Manager

### Step 1: Initialize Enhanced Risk Manager

```python
from execution.enhanced_risk_manager import EnhancedRiskManager
from storage.database import Database

# Initialize database and risk manager
db = Database()
risk_manager = EnhancedRiskManager(db)
```

### Step 2: Integrate into Portfolio Manager

Add the Enhanced Risk Manager to the Portfolio Manager's `process_signal()` method:

```python
async def process_signal(self, signal: Dict) -> Optional[Dict]:
    """Process a signal through risk checks and execute if approved."""
    self._check_daily_reset()

    symbol = signal["symbol"]
    quality = signal.get("quality", "B")
    direction = signal["signal_type"]

    log.info(f"[PROCESSING] Processing signal: {direction} {symbol} (Q:{quality})")

    # ─── Enhanced Risk Management Checks ──────────────────────
    # Get current portfolio state
    active_positions = self.positions.get_all_open()
    account_balance = await self._get_equity()
    
    # Calculate portfolio risk
    portfolio_risk = self.risk_manager.calculate_portfolio_risk(active_positions)
    
    # Check daily loss limit (Requirement 16.9)
    if self.risk_manager.should_block_trading(self._daily_pnl, account_balance):
        log.error("[BLOCKED] Trading blocked due to daily loss limit")
        self._halted = True
        self._halt_reason = "Daily loss limit exceeded"
        return None
    
    # Check portfolio limits (Requirement 16.3, 16.8)
    risk_check = self.risk_manager.check_portfolio_limits(
        portfolio_risk=portfolio_risk,
        daily_loss=abs(self._daily_pnl),
        account_balance=account_balance
    )
    
    if not risk_check.approved:
        log.warning(f"[REJECTED] {risk_check.reason}")
        return None

    # ─── Pre-execution checks ────────────────────────────
    reject_reason = self._check_risk_limits(signal)
    if reject_reason:
        log.warning(f"[REJECTED] Signal rejected: {reject_reason}")
        return None

    if not self._auto_execute:
        log.info(f"[PAUSED] Auto-execution disabled")
        return None

    # ─── Enhanced Position Sizing ──────────────────────────
    # Get recent performance
    recent_performance = self.risk_manager.get_recent_performance()
    
    # Calculate position size with all enhancements
    size_calc = self.risk_manager.calculate_position_size(
        signal=signal,
        account_balance=account_balance,
        portfolio_risk=portfolio_risk,
        recent_performance=recent_performance
    )
    
    if size_calc.final_size <= 0:
        log.warning(f"[REJECTED] Position size too small: {size_calc.final_size}")
        log.info(f"[ADJUSTMENTS] {', '.join(size_calc.adjustments_applied)}")
        return None
    
    log.info(
        f"[SIZE] Position size: {size_calc.final_size:.6f} "
        f"(Risk: {size_calc.risk_pct:.2f}%)"
    )
    if size_calc.adjustments_applied:
        log.info(f"[ADJUSTMENTS] {', '.join(size_calc.adjustments_applied)}")

    # ─── Calculate dynamic leverage ───────────────────────
    leverage = self._calculate_dynamic_leverage(signal)

    # ─── Execute ──────────────────────────────────────────
    result = await self.executor.execute_signal(
        signal=signal,
        position_size_qty=size_calc.final_size,
        leverage=leverage,
    )

    if result.get("status") == "FILLED":
        self.positions.add_position(result)
        self._daily_trades += 1
        log.info(f"[OK] Position opened: {result['execution_id']}")
        await self._record_equity()
        return result
    else:
        log.error(f"[FAILED] Execution failed: {result.get('error', 'Unknown')}")
        return None
```

### Step 3: Add Risk Manager to Portfolio Manager Constructor

```python
def __init__(self, executor: OrderExecutor, pos_manager: PositionManager, 
             db: Database, risk_config: Dict):
    self.executor = executor
    self.positions = pos_manager
    self.db = db
    self.risk = risk_config
    
    # Initialize Enhanced Risk Manager
    self.risk_manager = EnhancedRiskManager(db)
    
    # ... rest of initialization
```

## Configuration

The Enhanced Risk Manager uses the following default configuration:

```python
{
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
```

You can override these settings by passing a custom config:

```python
custom_config = {
    "base_risk_per_trade_pct": 0.5,  # More conservative
    "max_daily_loss_pct": 2.0,  # Stricter daily limit
}
risk_manager = EnhancedRiskManager(db, config=custom_config)
```

## Features

### 1. Portfolio Risk Calculation (Requirement 16.1)
Calculates total portfolio risk as sum of all position risks.

### 2. Kelly Criterion Position Sizing (Requirement 16.2)
Uses Kelly Criterion for optimal position sizing based on historical win rate and R:R.

### 3. Portfolio Risk Limits (Requirement 16.3)
Blocks new positions when portfolio risk exceeds 5% of total capital.

### 4. Position Size Calculation (Requirement 16.4)
Calculates position size based on account size, risk per trade, and distance to SL.

### 5. Performance-Based Adjustment (Requirement 16.5)
Dynamically adjusts risk based on recent performance.

### 6. Losing Streak Reduction (Requirement 16.6)
Reduces position size by 50% after 3 consecutive losses.

### 7. Winning Streak Increase (Requirement 16.7)
Increases position size by 25% after 5 consecutive wins (max 2x base).

### 8. Daily Loss Limit (Requirement 16.8)
Enforces maximum 3% daily loss limit.

### 9. Trading Block Logic (Requirement 16.9)
Blocks all trading when daily loss limit is reached.

### 10. Portfolio Manager Integration (Requirement 16.10)
Seamlessly integrates with existing Portfolio Manager workflow.

## Testing

Run the standalone tests:

```bash
python test_enhanced_risk_standalone.py
```

Or run the full test suite:

```bash
pytest tests/test_enhanced_risk_manager.py -v
```

## Logging

The Enhanced Risk Manager provides detailed logging:

```
[INFO] Enhanced Risk Manager initialized
[WARNING] Losing streak detected (3 losses). Reducing risk to 0.50%
[INFO] Winning streak detected (5 wins). Increasing risk to 1.25%
[ERROR] Trading blocked: Daily loss limit reached (3.50% >= 3.0%)
[INFO] Position size: 0.05 (Risk: 1.25%)
[INFO] Adjustments: Performance adjustment: 1.00% -> 1.25%, Kelly sizing applied
```

## Requirements Validation

This implementation validates all requirements from Requirement 16:

- ✅ 16.1: Portfolio risk calculation
- ✅ 16.2: Kelly Criterion position sizing
- ✅ 16.3: Portfolio risk limit (<5%)
- ✅ 16.4: Position size calculation
- ✅ 16.5: Dynamic risk adjustment
- ✅ 16.6: Losing streak reduction (3 losses → -50%)
- ✅ 16.7: Winning streak increase (5 wins → +25%)
- ✅ 16.8: Daily loss limit (<3%)
- ✅ 16.9: Trading block logic
- ✅ 16.10: Portfolio Manager integration
