---
name: dynamic-weights-optimization
description: Optimization of signal weights and strategy parameters. Use when adjusting dynamic weights, running backtests for parameter optimization, or tuning strategy sensitivity.
---

# Dynamic Weights Optimization

System for dynamically adjusting strategy influence based on historical performance and current market regime.

## Key Concepts
- **Regime-Aware Weighting**: Different strategies perform better in different market states (Trending vs. Ranging).
- **Performance Decay**: Recent performance has a higher impact on current weighting.
- **Auto-Tuning**: Periodic optimization routines that adjust multipliers based on walk-forward analysis.

## Implementation Example
```python
from engine.optimizer import WeightOptimizer

optimizer = WeightOptimizer()
optimized_weights = optimizer.calculate_weights(
    performance_data=historical_signals,
    current_regime="TRENDING_UP"
)
```

## Best Practices
- **Avoid Overfitting**: Use cross-validation and walk-forward testing to ensure weights remain robust.
- **Gradual Adjustments**: Implement damping factors to prevent extreme weight swings between updates.
- **Monitor Correlation**: Ensure that optimization doesn't lead to over-exposure in highly correlated strategies.
