---
name: configuration-feature-flags
description: Management of system configuration and feature flags. Use when adding new settings, toggling experimental features, or modifying environment variables.
---

# Configuration & Feature Flags

Standardized approach to system-wide settings and experimental feature management.

## Configuration Structure
Settings are organized by domain (exchange, strategy, execution, risk) to ensure clarity and avoid conflicts.

## Key Features
- **Environment Overrides**: All settings can be overridden via `.env` files.
- **Hot Reloading**: Support for dynamic configuration updates without system restart.
- **Feature Toggles**: Safely enable or disable experimental logic in production.

## Implementation Example
```python
from core.config import settings

# Accessing a configuration value
max_risk = settings.RISK_PER_TRADE

# Checking a feature flag
if settings.FEAT_ADAPTIVE_TP_ENABLED:
    optimizer.apply_dynamic_levels()
```

## Best Practices
- **Define defaults** for all configuration keys.
- **Use type hints** and validation (e.g., Pydantic) for configuration schemas.
- **Document every flag** explaining its purpose and impact.
- **Clean up old flags** once a feature is fully integrated and stable.
