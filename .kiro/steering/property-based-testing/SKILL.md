---
name: property-based-testing
description: Implementation of robust tests using property-based testing principles. Use when writing Hypothesis tests, validating edge cases in mathematical formulas, or ensuring logic consistency across large ranges of inputs.
---

# Property-Based Testing

Using the `Hypothesis` library to discover edge cases and ensure mathematical correctness across the codebase.

## Methodology
Instead of testing specific examples, we define "properties" that our code should always satisfy regardless of input.

## Features
- **Automatic Fuzzing**: Generates thousands of input variations to find failures.
- **Shrinking**: Automatically finds the simplest input that causes a test to fail.
- **Stateful Testing**: Models the system as a state machine to find complex sequence-based bugs.

## Example Test
```python
from hypothesis import given, strategies as st
from execution.risk import calculate_position_size

@given(equity=st.floats(min_value=100, max_value=1000000), 
       risk_pct=st.floats(min_value=0.1, max_value=5.0))
def test_position_size_never_exceeds_equity(equity, risk_pct):
    pos_size = calculate_position_size(equity, risk_pct)
    assert pos_size <= equity
```

## Best Practices
- **Define Tight Bounds**: Use appropriate min/max values in strategies to keep tests realistic.
- **Use for Core Logic**: Prioritize property-based tests for risk calculations, signal parsing, and data transformations.
- **Monitor Test Duration**: Property-based tests are slower; use them strategically rather than for every function.
