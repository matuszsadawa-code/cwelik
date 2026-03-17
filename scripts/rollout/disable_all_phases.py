#!/usr/bin/env python3
"""
Emergency rollback: Disable all features and return to baseline.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config.feature_flags import disable_all_features, get_enabled_features

if __name__ == "__main__":
    print("⚠️  EMERGENCY ROLLBACK: Disabling all advanced features...")
    print("This will return the system to baseline configuration.")
    
    # Confirm action
    if "--force" not in sys.argv:
        response = input("Are you sure? Type 'YES' to confirm: ")
        if response != "YES":
            print("Rollback cancelled.")
            sys.exit(0)
    
    # Show currently enabled features
    enabled_before = get_enabled_features()
    print(f"\nDisabling {len(enabled_before)} features:")
    for feature_name in enabled_before.keys():
        print(f"  - {feature_name}")
    
    # Disable all features
    disable_all_features()
    
    # Verify all disabled
    enabled_after = get_enabled_features()
    
    if len(enabled_after) == 0:
        print(f"\n✅ All features disabled successfully")
        print("System returned to baseline configuration.")
        print("\nNext steps:")
        print("  1. Restart the trading system")
        print("  2. Monitor for stability")
        print("  3. Investigate issues before re-enabling features")
    else:
        print(f"\n⚠️  Warning: {len(enabled_after)} features still enabled:")
        for feature_name in enabled_after.keys():
            print(f"  - {feature_name}")
        sys.exit(1)
