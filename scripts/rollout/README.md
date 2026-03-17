# Rollout Scripts

This directory contains scripts for managing the gradual rollout of advanced trading features.

## Quick Start

### Enable Phase 1
```bash
python scripts/rollout/enable_phase.py 1
python scripts/rollout/verify_features.py --phase 1
python scripts/rollout/restart_system.py
python scripts/rollout/monitor_realtime.py 1
```

### Validate Phase After 7 Days
```bash
python scripts/rollout/validate_phase.py 1 --days 7
```

### Emergency Rollback
```bash
python scripts/rollout/disable_all_phases.py --force
python scripts/rollout/restart_system.py --force
```

## Available Scripts

### enable_phase.py
Enable all features for a specific phase (1-4).

**Usage:**
```bash
python scripts/rollout/enable_phase.py <phase>
```

**Example:**
```bash
python scripts/rollout/enable_phase.py 1
```

### disable_phase.py
Disable all features for a specific phase.

**Usage:**
```bash
python scripts/rollout/disable_phase.py <phase>
```

**Example:**
```bash
python scripts/rollout/disable_phase.py 1
```

### disable_all_phases.py
Emergency rollback - disable all features and return to baseline.

**Usage:**
```bash
python scripts/rollout/disable_all_phases.py [--force]
```

**Example:**
```bash
# With confirmation prompt
python scripts/rollout/disable_all_phases.py

# Skip confirmation (for automation)
python scripts/rollout/disable_all_phases.py --force
```

### verify_features.py
Verify feature flags configuration and display current state.

**Usage:**
```bash
# Show enabled features
python scripts/rollout/verify_features.py

# Verify specific phase
python scripts/rollout/verify_features.py --phase 1

# Verify multiple phases
python scripts/rollout/verify_features.py --phase 1 --phase 2

# Show all features
python scripts/rollout/verify_features.py --all
```

### monitor_realtime.py
Real-time monitoring of phase deployment with anomaly detection.

**Usage:**
```bash
python scripts/rollout/monitor_realtime.py <phase> [--hours 48]
```

**Example:**
```bash
# Monitor Phase 1 for 48 hours (default)
python scripts/rollout/monitor_realtime.py 1

# Monitor Phase 2 for 24 hours
python scripts/rollout/monitor_realtime.py 2 --hours 24
```

**Monitoring Metrics:**
- Signal generation count
- Win rate
- Average confidence
- Latency
- Error rate

**Alerts:**
- Win rate drops >10%
- Latency increases >50%
- Error rate >5 per hour

### validate_phase.py
Validate phase performance against success criteria.

**Usage:**
```bash
python scripts/rollout/validate_phase.py <phase> [--days 7]
```

**Example:**
```bash
# Validate Phase 1 over last 7 days
python scripts/rollout/validate_phase.py 1

# Validate Phase 2 over last 14 days
python scripts/rollout/validate_phase.py 2 --days 14
```

**Success Criteria:**
- **Phase 1**: Win rate maintained (±5%), ≥50 signals
- **Phase 2**: Win rate improved ≥2%, ≥100 signals
- **Phase 3**: Avg R:R improved ≥10%, ≥150 signals
- **Phase 4**: Win rate +5%, R:R +15%, ≥200 signals

### restart_system.py
Safely restart the trading system with new configuration.

**Usage:**
```bash
python scripts/rollout/restart_system.py [--force]
```

**Example:**
```bash
# With confirmation prompt
python scripts/rollout/restart_system.py

# Skip confirmation
python scripts/rollout/restart_system.py --force
```

## Typical Workflow

### Phase 1 Deployment (Days 1-7)

```bash
# Day 1: Enable Phase 1
python scripts/rollout/enable_phase.py 1
python scripts/rollout/verify_features.py --phase 1
python scripts/rollout/restart_system.py

# Days 1-3: Monitor (48 hours)
python scripts/rollout/monitor_realtime.py 1 --hours 48

# Days 3-7: Continue monitoring and validate
python scripts/rollout/validate_phase.py 1 --days 7
```

### Phase 2 Deployment (Days 8-14)

```bash
# Day 8: Enable Phase 2
python scripts/rollout/enable_phase.py 2
python scripts/rollout/verify_features.py --phase 1 --phase 2
python scripts/rollout/restart_system.py

# Days 8-10: Monitor (48 hours)
python scripts/rollout/monitor_realtime.py 2 --hours 48

# Days 10-14: Validate
python scripts/rollout/validate_phase.py 2 --days 7
```

### Emergency Rollback

```bash
# If issues detected, rollback immediately
python scripts/rollout/disable_all_phases.py --force
python scripts/rollout/restart_system.py --force

# Verify rollback
python scripts/rollout/verify_features.py
```

## Monitoring Best Practices

1. **Always monitor for 48 hours** after enabling a new phase
2. **Check logs regularly**: `tail -f logs/trading_system.log`
3. **Validate before proceeding** to next phase
4. **Keep baseline metrics** for comparison
5. **Document any issues** encountered during rollout

## Troubleshooting

### Issue: Features not enabling
```bash
# Check feature flags file
cat config/feature_flags.py | grep "enabled"

# Verify features
python scripts/rollout/verify_features.py --all
```

### Issue: System not restarting
```bash
# Check if process is running
ps aux | grep python | grep main

# Force kill if needed
pkill -f "python main.py"

# Restart manually
python main.py
```

### Issue: Monitoring shows anomalies
```bash
# Check recent signals
python -c "from storage.database import Database; db = Database(); print(db.execute('SELECT * FROM signals ORDER BY created_at DESC LIMIT 10').fetchall())"

# Disable problematic phase
python scripts/rollout/disable_phase.py <phase>
python scripts/rollout/restart_system.py
```

## Support

For issues or questions:
1. Check logs: `logs/trading_system.log`
2. Review documentation: `docs/GRADUAL_ROLLOUT_STRATEGY.md`
3. Contact deployment team

## Safety Notes

- ⚠️ Always backup configuration before changes
- ⚠️ Never skip monitoring periods
- ⚠️ Validate each phase before proceeding
- ⚠️ Keep emergency rollback procedure ready
- ⚠️ Monitor active positions during restarts
