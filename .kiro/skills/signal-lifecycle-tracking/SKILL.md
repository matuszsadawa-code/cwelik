---
name: signal-lifecycle-tracking
description: Tracking and logging signal transitions from detection to execution and closure. Use when debugging signal flow, monitoring trade states, or analyzing performance attribution.
---

# Signal Lifecycle Tracking

Comprehensive monitoring of every trade signal as it moves through the system.

## Lifecycle States
1. **DETECTED**: Strategy identifies a potential setup.
2. **VALIDATED**: Signal passes filters, risk checks, and regime alignment.
3. **EXECUTING**: Order is sent to the exchange and tracked during fulfillment.
4. **ACTIVE**: Position is open and monitored by adaptive risk management.
5. **CLOSED**: Position is exited due to SL, TP, or manual intervention.

## Key Features
- **State Persistence**: Current state is always saved to the database.
- **Attribution Logic**: Track which strategy generated the signal and which regime it occurred in.
- **Latency Monitoring**: Record timing for each state transition to identify execution bottlenecks.

## Best Practices
- **Log every transition** with full context (price, time, reason).
- **Ensure atomicity** when updating signal states in the database.
- **Use unique IDs** (`SIGNAL-YYYYMMDD-XXXX`) for all tracking.
- **Clean up history** periodically for closed signals that are no longer needed for analysis.
