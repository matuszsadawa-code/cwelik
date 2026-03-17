---
name: adaptive-sl-tp-system
description: ATR-based adaptive stop loss and dynamic take profit system with structure-aware placement, trailing stops, and profit locking. Use when implementing position risk management, SL/TP calculation, or trailing stop logic.
---

# Adaptive SL/TP System

Intelligent stop loss and take profit system that adapts to volatility, market structure, and position progress.

## Core Components

### AdaptiveSLSystem
Calculates and manages adaptive stop losses using:
- ATR-based SL with volatility regime multipliers
- Structure-aware placement (beyond OBs, FVGs, round numbers)
- Stop hunt zone detection and avoidance
- Breakeven moves and profit locking logic

### DynamicTPOptimizer
Calculates optimal take profit levels using:
- ATR-based TP levels (TP1 at 1.5x, TP2 at 3.0x)
- Momentum detection for TP extensions
- Fibonacci extension zones

## Usage Examples

### Calculate Initial SL
```python
from execution.adaptive_sl import AdaptiveSLSystem

sl_system = AdaptiveSLSystem()
sl_calc = sl_system.calculate_initial_sl(
    signal=signal,
    candles=recent_candles,
    market_structure=structure_data,
    volatility_regime="HIGH"
)
final_sl = sl_calc.final_sl
```

### Dynamic TP Calculation
```python
from execution.dynamic_tp_optimizer import DynamicTPOptimizer

tp_optimizer = DynamicTPOptimizer()
dynamic_tp = tp_optimizer.calculate_dynamic_tp(
    signal=signal,
    candles=recent_candles
)
```

## Best Practices
- **Never use fixed percentage stops** in this system.
- **Always validate ATR** before calculation to avoid division by zero or invalid stops.
- **Only move SL in favorable directions** (up for longs, down for shorts).
- **Verify momentum** before extending TP2.

## Common Pitfalls
- Moving to breakeven too early can result in premature stop-outs. Use a small buffer (e.g., 0.1%).
- Excessive structure adjustments can widen the SL too much. Always cap the maximum SL distance.
