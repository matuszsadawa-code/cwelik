#!/usr/bin/env python3
"""
Verify feature flags configuration and display current state.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config.feature_flags import (
    get_all_features,
    get_enabled_features,
    PHASE_1_FEATURES,
    PHASE_2_FEATURES,
    PHASE_3_FEATURES,
    PHASE_4_FEATURES,
)

def verify_phase(phase: int) -> bool:
    """Verify all features in a phase are enabled."""
    phase_map = {
        1: PHASE_1_FEATURES,
        2: PHASE_2_FEATURES,
        3: PHASE_3_FEATURES,
        4: PHASE_4_FEATURES,
    }
    
    phase_features = phase_map[phase]
    all_enabled = True
    
    print(f"\nPhase {phase} Features:")
    for feature_name, feature_config in phase_features.items():
        status = "✅ ENABLED" if feature_config["enabled"] else "❌ DISABLED"
        print(f"  {status} - {feature_name}: {feature_config['description']}")
        if not feature_config["enabled"]:
            all_enabled = False
    
    return all_enabled

if __name__ == "__main__":
    print("="*70)
    print("FEATURE FLAGS VERIFICATION")
    print("="*70)
    
    # Get all features
    all_features = get_all_features()
    enabled_features = get_enabled_features()
    
    print(f"\nTotal Features: {len(all_features)}")
    print(f"Enabled Features: {len(enabled_features)}")
    print(f"Disabled Features: {len(all_features) - len(enabled_features)}")
    
    # Check specific phases if requested
    if "--phase" in sys.argv:
        phase_indices = [i for i, arg in enumerate(sys.argv) if arg == "--phase"]
        phases_to_check = []
        
        for idx in phase_indices:
            if idx + 1 < len(sys.argv):
                try:
                    phase = int(sys.argv[idx + 1])
                    if phase in [1, 2, 3, 4]:
                        phases_to_check.append(phase)
                except ValueError:
                    pass
        
        if phases_to_check:
            print("\n" + "="*70)
            print("PHASE VERIFICATION")
            print("="*70)
            
            all_phases_ok = True
            for phase in sorted(phases_to_check):
                phase_ok = verify_phase(phase)
                if not phase_ok:
                    all_phases_ok = False
            
            print("\n" + "="*70)
            if all_phases_ok:
                print("✅ All requested phases are fully enabled")
            else:
                print("⚠️  Some features in requested phases are not enabled")
            print("="*70)
    
    # Show all enabled features
    elif "--all" in sys.argv:
        print("\n" + "="*70)
        print("ALL FEATURES STATUS")
        print("="*70)
        
        for phase_num, phase_features in [
            (1, PHASE_1_FEATURES),
            (2, PHASE_2_FEATURES),
            (3, PHASE_3_FEATURES),
            (4, PHASE_4_FEATURES),
        ]:
            verify_phase(phase_num)
        
        print("\n" + "="*70)
    
    else:
        # Just show enabled features
        print("\n" + "="*70)
        print("CURRENTLY ENABLED FEATURES")
        print("="*70)
        
        if enabled_features:
            for feature_name, feature_config in enabled_features.items():
                boost = feature_config.get("confidence_boost", 0)
                boost_str = f" (boost: +{boost}%)" if boost > 0 else ""
                print(f"  ✅ {feature_name}: {feature_config['description']}{boost_str}")
        else:
            print("  (none - all features disabled)")
        
        print("\n" + "="*70)
        print("Use --phase <N> to verify specific phase")
        print("Use --all to show all features")
        print("="*70)
