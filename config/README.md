# Advanced Trading Optimization - Configuration System

## Overview

This directory contains configuration templates and validation logic for all 20 advanced trading optimization features.

## Files

- **`advanced_features_default.py`**: Balanced configuration suitable for most market conditions
- **`advanced_features_conservative.py`**: Higher thresholds, lower confidence boosts, stricter risk management
- **`advanced_features_aggressive.py`**: Lower thresholds, higher confidence boosts, more lenient risk management
- **`config_validator.py`**: Configuration validation logic with error checking
- **`README.md`**: This file

## Quick Start

### Load Configuration

```python
from config.config_validator import load_config

# Load default configuration
config = load_config("default")

# Load conservative configuration
config = load_config("conservative")

# Load aggressive configuration
config = load_config("aggressive")
```

### Access Feature Configuration

```python
# Access specific feature
vsa_config = config["vsa"]

# Check if feature is enabled
if vsa_config["enabled"]:
    threshold = vsa_config["high_volume_threshold"]
    print(f"VSA high volume threshold: {threshold}x")
```

### Validate Custom Configuration

```python
from config.config_validator import validate_config

# Your custom configuration
custom_config = {
    "vsa": {...},
    "wyckoff": {...},
    # ... other features
}

# Validate (raises ConfigValidationError if invalid)
validate_config(custom_config)
```

## Configuration Templates

### Default Configuration

Balanced settings suitable for most market conditions:
- Moderate detection thresholds
- Balanced confidence boosts
- Standard risk management (1% per trade, 5% max portfolio)
- Suitable for live trading in normal market conditions

### Conservative Configuration

More cautious approach for risk-averse traders:
- **Higher detection thresholds** (require stronger signals)
- **Lower confidence boosts** (more conservative adjustments)
- **Stricter risk management** (0.75% per trade, 3.5% max portfolio)
- **Wider stop losses** (better protection in volatile markets)
- **Fewer concurrent positions** (better risk control)

Use when:
- Market conditions are uncertain or volatile
- You're new to the system
- Capital preservation is priority
- Testing new features

### Aggressive Configuration

More aggressive approach for experienced traders:
- **Lower detection thresholds** (more signals generated)
- **Higher confidence boosts** (stronger adjustments)
- **More lenient risk management** (1.5% per trade, 7% max portfolio)
- **Tighter stop losses** (maximize profit potential)
- **More concurrent positions** (higher exposure)

Use when:
- Market conditions are favorable
- You have experience with the system
- You want to maximize returns
- You can tolerate higher drawdowns

## Feature List

All 20 features are configured in each template:

1. **VSA** - Volume Spread Analysis
2. **Wyckoff** - Wyckoff Method
3. **Market Profile** - TPO/Market Profile
4. **Liquidity Engineering** - Enhanced liquidity analysis
5. **Smart Money Divergence** - Divergence detection
6. **MTF Confluence** - Multi-timeframe confluence
7. **Order Book Imbalance** - Advanced order book analysis
8. **Institutional Flow** - Institutional pattern detection
9. **Volatility Regime** - Volatility regime adaptation
10. **ML Calibration** - Machine learning confidence calibration
11. **Dynamic TP** - Dynamic take profit optimization
12. **Correlation Optimizer** - Portfolio correlation optimization
13. **News Sentiment** - News sentiment integration
14. **Backtesting** - Backtesting engine
15. **A/B Testing** - A/B testing framework
16. **Enhanced Risk** - Enhanced risk management
17. **Microstructure** - Market microstructure analysis
18. **Seasonality** - Seasonality detection
19. **Adaptive SL** - Adaptive stop loss system
20. **Dashboard** - Performance analytics dashboard

## Configuration Validation

All configurations are automatically validated on load. Validation checks:

- **Range validation**: Parameters must be within acceptable ranges
- **Type validation**: Parameters must be correct type (int, float, bool, etc.)
- **Logical consistency**: Related parameters must be logically consistent
- **Required fields**: All required parameters must be present

### Common Validation Errors

**Invalid percentage:**
```
VSA.confidence_boost: 150 is outside valid range [0, 100]
```
Fix: Ensure percentage values are between 0 and 100

**TP2 must be greater than TP1:**
```
Dynamic TP: tp2_atr_multiplier (2.0) must be greater than tp1_atr_multiplier (3.0)
```
Fix: Ensure TP2 multiplier is larger than TP1 multiplier

**Missing required parameter:**
```
Adaptive SL: Missing ATR multiplier for regime 'HIGH'
```
Fix: Add all required volatility regime multipliers

## Customization

### Modify Existing Configuration

```python
from config.advanced_features_default import ADVANCED_FEATURES_CONFIG
from config.config_validator import validate_config
import copy

# Create a copy
custom_config = copy.deepcopy(ADVANCED_FEATURES_CONFIG)

# Customize parameters
custom_config["vsa"]["high_volume_threshold"] = 1.8
custom_config["enhanced_risk"]["base_risk_per_trade_pct"] = 0.8

# Validate
validate_config(custom_config)
```

### Disable Features

```python
# Disable specific features
config["news_sentiment"]["enabled"] = False
config["ml_calibration"]["enabled"] = False
```

### Create New Configuration

```python
# Start from scratch
my_config = {
    "vsa": {
        "enabled": True,
        "high_volume_threshold": 1.6,
        # ... all other VSA parameters
    },
    # ... all other 19 features
}

# Validate
validate_config(my_config)
```

## Testing

Run configuration validation tests:

```bash
python -m pytest tests/test_config_validation.py -v
```

Tests verify:
- All three templates are valid
- Validation catches common errors
- Configuration loading works correctly
- Conservative/aggressive configs have appropriate thresholds

## Best Practices

1. **Start with default**: Begin with default configuration
2. **Backtest changes**: Always backtest configuration changes
3. **Monitor performance**: Use dashboard to track feature effectiveness
4. **A/B test**: Use A/B testing framework to validate improvements
5. **Document changes**: Keep log of configuration changes and impact
6. **Gradual adjustments**: Make small incremental changes
7. **Validate always**: Always validate custom configurations

## Documentation

See `docs/CONFIGURATION_GUIDE.md` for detailed parameter documentation.

## Support

For configuration questions:
1. Review this README and configuration files
2. Check validation error messages
3. Consult design document for parameter meanings
4. Test changes in backtesting before live trading
