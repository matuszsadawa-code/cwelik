#!/usr/bin/env python3
"""
Enable features for a specific phase.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config.feature_flags import enable_phase

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python enable_phase.py <phase>")
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
    
    print(f"Enabling Phase {phase} features...")
    enable_phase(phase)
    print(f"✅ Phase {phase} features enabled successfully")
    
    # Show enabled features
    from config.feature_flags import get_enabled_features
    enabled = get_enabled_features()
    print(f"\nCurrently enabled features ({len(enabled)}):")
    for feature_name, feature_config in enabled.items():
        print(f"  - {feature_name}: {feature_config['description']}")
