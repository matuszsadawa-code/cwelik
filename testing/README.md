# A/B Testing Framework

Comprehensive A/B testing framework for objectively measuring the impact of new trading features before full deployment.

## Features

- **Experiment Management**: Create and manage A/B test experiments
- **Random Assignment**: 50/50 split for control and treatment groups
- **Signal Tracking**: Track signal assignments and outcomes
- **Metrics Calculation**: Win Rate, Average Profit, Confidence Accuracy per variant
- **Statistical Testing**: T-test and Chi-square for significance (p<0.05)
- **Deployment Recommendations**: Automated recommendations based on performance
- **Comparison Reports**: Detailed reports with visualizations

## Requirements

Implements Requirements 15.1-15.8:
- 15.1: Experiment creation and management
- 15.2: Random variant assignment (50/50 split)
- 15.3: Signal tracking (assignment and outcomes)
- 15.4: Metrics calculation per variant
- 15.5: Statistical significance testing
- 15.6: Deployment recommendation logic
- 15.7: Comparison report generation
- 15.8: Integration with Signal_Engine

## Installation

The framework is already integrated into the trading system. No additional installation required.

## CLI Usage

### Create Experiment

```bash
python -m testing create \
  --name "VSA Integration" \
  --description "Test VSA feature impact on win rate" \
  --variants control treatment
```

### List Experiments

```bash
# List all experiments
python -m testing list

# List only active experiments
python -m testing list --status ACTIVE
```

### Show Metrics

```bash
python -m testing metrics --name "VSA Integration"
```


### Generate Report

```bash
# Print to console
python -m testing report --name "VSA Integration"

# Save to file
python -m testing report --name "VSA Integration" --output report.txt
```

### End Experiment

```bash
python -m testing end --name "VSA Integration"
```

## Python API Usage

### Basic Example

```python
from testing.ab_framework import ABTestingFramework

# Initialize framework
framework = ABTestingFramework()

# Create experiment
experiment = framework.create_experiment(
    name="VSA Integration",
    description="Test VSA feature impact",
    variants=["control", "treatment"]
)

# Assign signal to variant
variant = framework.assign_variant("signal_001", "VSA Integration")

# Track signal
framework.track_signal(
    signal_id="signal_001",
    experiment_name="VSA Integration",
    variant=variant,
    signal_data={"symbol": "BTCUSDT", "confidence": 75}
)

# Track outcome
framework.track_outcome("signal_001", "WIN", 150.0)

# Calculate metrics (after collecting data)
metrics = framework.calculate_metrics("VSA Integration")

# Get deployment recommendation
recommendation = framework.should_deploy_treatment("VSA Integration")
print(f"Should deploy: {recommendation.should_deploy}")
print(f"Reason: {recommendation.reason}")
```

### Integration with Signal Engine

```python
from testing.integration_example import ABTestingIntegration

integration = ABTestingIntegration()

# Setup feature test
integration.setup_feature_test(
    feature_name="VSA Integration",
    feature_description="Test VSA signals"
)

# Process signal with A/B testing
def apply_vsa_feature(signal):
    # Apply VSA feature logic
    return signal

processed_signal = integration.process_signal_with_ab_test(
    signal=my_signal,
    experiment_name="VSA Integration",
    apply_feature_fn=apply_vsa_feature
)

# Track outcome later
integration.track_signal_outcome(
    signal_id=processed_signal['signal_id'],
    hit_tp=True,
    pnl=150.0
)

# Evaluate feature
evaluation = integration.evaluate_feature("VSA Integration")
```

## Deployment Criteria

The framework recommends deployment when ALL criteria are met:

1. **Statistical Significance**: p-value < 0.05
2. **Performance Improvement**: Treatment >10% better than control
3. **Minimum Sample Size**: 100+ samples per variant

## Metrics Explained

### Win Rate
Percentage of signals that hit TP (vs SL).

### Average Profit
Average PnL per signal.

### Confidence Accuracy
How well predicted confidence matches actual win rate (using Brier score).

### Total PnL
Cumulative profit/loss for the variant.

## Statistical Tests

### T-Test (2 variants)
Compares mean PnL between control and treatment groups.

### Chi-Square (3+ variants)
Tests independence of win rates across multiple variants.

## Database Schema

The framework uses three tables:

- `experiments`: Experiment metadata
- `experiment_assignments`: Signal-to-variant assignments
- `experiment_outcomes`: Signal outcomes (WIN/LOSS, PnL)

## Best Practices

1. **Run experiments for sufficient time**: Collect 100+ samples per variant
2. **Test one feature at a time**: Avoid confounding effects
3. **Monitor metrics regularly**: Check for early signals
4. **Document experiments**: Clear names and descriptions
5. **End completed experiments**: Keep database clean

## Example Workflow

1. **Create experiment** for new feature
2. **Integrate** A/B testing into signal processing
3. **Collect data** (100+ samples per variant)
4. **Review metrics** regularly
5. **Check recommendation** when sufficient data collected
6. **Deploy or iterate** based on results
7. **End experiment** when complete

## Troubleshooting

### "Experiment not found"
Ensure experiment name matches exactly (case-sensitive).

### "Insufficient samples"
Need 100+ samples per variant for deployment recommendation.

### "Not statistically significant"
Difference between variants may not be meaningful. Consider:
- Collecting more data
- Increasing feature impact
- Re-evaluating feature design

## Testing

Run unit tests:

```bash
python -m pytest tests/test_ab_framework.py -v
```

All tests should pass.
