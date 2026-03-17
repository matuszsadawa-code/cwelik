#!/usr/bin/env python3
"""
Disable features for a specific phase.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import feature_flags

PHASE_FEATURES = {
    1: ["vsa_analysis", "wyckoff_method", "market_profile", "enhanced_liquidity", "smart_money_divergence"],
    2: ["mtf_confluence", "orderbook_imbalance", "institutional_flow", "volatility_regime", "ml_confidence_calibration"],
    3: ["dynamic_tp", "correlation_optimizer", "news_sentiment", "backtesting_engine", "ab_testing"],
    4: ["enhanced_risk", "market_microstructure", "seasonality_detection", "adaptive_sl", "performance_dashboard"],
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python disable_phase.py <phase>")
        print("  phase: 1-4")
        sys.exit(1)
    
    try:
        phase = int(sys.argv[1])
    except ValueError:
        print(f"Error: Phase must be a number (1-4)")
        sys.exit(1)
    
    if phase not in [1, 2, 3, 4]:
        print(f"Error: Invalid phase {phase}. Must be 1-4.")
        sys.exit(1)
    
    print(f"Disabling Phase {phase} features...")
    
    # Get phase features
    features_to_disable = PHASE_FEATURES[phase]
    
    # Disable each feature
    all_features = feature_flags.get_all_features()
    disabled_count = 0
    
    for feature_name in features_to_disable:
        if feature_name in all_features:
            all_features[feature_name]["enabled"] = False
            print(f"  - Disabled {feature_name}")
            disabled_count += 1
    
    print(f"✅ Phase {phase} features disabled successfully ({disabled_count} features)")
    
    # Show remaining enabled features
    enabled = feature_flags.get_enabled_features()
    print(f"\nRemaining enabled features ({len(enabled)}):")
    if enabled:
        for feature_name, feature_config in enabled.items():
            print(f"  - {feature_name}: {feature_config['description']}")
    else:
        print("  (none - all features disabled)")
