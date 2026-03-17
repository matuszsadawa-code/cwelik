"""
Simplified Final System Validation Script

Runs comprehensive validation without complex logging to avoid encoding issues.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import subprocess
import json
from datetime import datetime

def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80 + "\n")

def print_section(text):
    """Print formatted section."""
    print(f"\n[{text}]")
    print("-" * 80)

def run_tests():
    """Run all test suites."""
    print_header("STEP 1: Running All Test Suites")
    
    results = {}
    
    # Unit tests
    print_section("1/3 Running unit tests")
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "-x"],
            capture_output=True,
            text=True,
            timeout=300
        )
        results["unit_tests"] = result.returncode == 0
        if result.returncode == 0:
            print("PASS: Unit tests passed")
        else:
            print(f"FAIL: Unit tests failed")
            print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
    except Exception as e:
        print(f"ERROR: {e}")
        results["unit_tests"] = False
    
    # Integration tests
    print_section("2/3 Running integration tests")
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/test_integration_complete.py", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=300
        )
        results["integration_tests"] = result.returncode == 0
        if result.returncode == 0:
            print("PASS: Integration tests passed")
        else:
            print(f"FAIL: Integration tests failed")
            print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
    except Exception as e:
        print(f"ERROR: {e}")
        results["integration_tests"] = False
    
    # Property tests (optional)
    print_section("3/3 Running property tests (optional)")
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-v", "-m", "property", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=300
        )
        results["property_tests"] = result.returncode == 0
        if result.returncode == 0:
            print("PASS: Property tests passed")
        else:
            print("WARN: Property tests failed (optional)")
    except Exception as e:
        print(f"WARN: Property tests error (optional): {e}")
        results["property_tests"] = False
    
    return results

def check_feature_implementation():
    """Check that all 20 features are implemented."""
    print_header("STEP 2: Checking Feature Implementation")
    
    features = {
        "VSA": "analytics/vsa_analyzer.py",
        "Wyckoff": "analytics/wyckoff_analyzer.py",
        "Market Profile": "analytics/market_profile.py",
        "Liquidity Engineering": "analytics/liquidity_engineer.py",
        "Smart Money Divergence": "analytics/smart_money_divergence.py",
        "MTF Confluence": "analytics/mtf_confluence.py",
        "Order Book Imbalance": "analytics/orderbook_imbalance.py",
        "Institutional Flow": "analytics/institutional_flow.py",
        "Volatility Regime": "strategy/volatility_regime.py",
        "Seasonality": "analytics/seasonality.py",
        "ML Calibration": "ml/confidence_calibrator.py",
        "Dynamic TP": "execution/dynamic_tp_optimizer.py",
        "Adaptive SL": "execution/adaptive_sl.py",
        "Correlation Optimizer": "execution/correlation_optimizer.py",
        "Enhanced Risk": "execution/enhanced_risk_manager.py",
        "News Sentiment": "analytics/news_sentiment.py",
        "Microstructure": "analytics/microstructure.py",
        "Backtesting": "backtesting/backtest_engine.py",
        "A/B Testing": "testing/ab_framework.py",
        "Dashboard": "dashboard/performance_dashboard.py",
    }
    
    implemented = 0
    for name, path in features.items():
        if Path(path).exists():
            print(f"PASS: {name:25s} - {path}")
            implemented += 1
        else:
            print(f"FAIL: {name:25s} - {path} NOT FOUND")
    
    print(f"\nImplemented: {implemented}/20 features")
    return implemented == 20

def check_documentation():
    """Check that documentation is complete."""
    print_header("STEP 3: Checking Documentation")
    
    docs = {
        "README": "README.md",
        "Features Overview": "docs/FEATURES_OVERVIEW.md",
        "Integration Guide": "docs/INTEGRATION_GUIDE.md",
        "Deployment Checklist": "docs/DEPLOYMENT_CHECKLIST.md",
        "Rollback Procedure": "docs/ROLLBACK_PROCEDURE.md",
        "Monitoring": "docs/MONITORING_AND_ALERTING.md",
        "Dependencies": "docs/DEPENDENCIES.md",
        "Quick Reference": "docs/QUICK_REFERENCE.md",
        "Rollout Strategy": "docs/GRADUAL_ROLLOUT_STRATEGY.md",
    }
    
    complete = 0
    for name, path in docs.items():
        if Path(path).exists():
            print(f"PASS: {name:25s} - {path}")
            complete += 1
        else:
            print(f"FAIL: {name:25s} - {path} NOT FOUND")
    
    print(f"\nDocumentation: {complete}/{len(docs)} files")
    return complete == len(docs)

def check_configuration():
    """Check configuration templates."""
    print_header("STEP 4: Checking Configuration")
    
    configs = {
        "Default": "config/advanced_features_default.py",
        "Conservative": "config/advanced_features_conservative.py",
        "Aggressive": "config/advanced_features_aggressive.py",
        "Feature Flags": "config/feature_flags.py",
        "Config Validator": "config/config_validator.py",
    }
    
    complete = 0
    for name, path in configs.items():
        if Path(path).exists():
            print(f"PASS: {name:25s} - {path}")
            complete += 1
        else:
            print(f"FAIL: {name:25s} - {path} NOT FOUND")
    
    print(f"\nConfiguration: {complete}/{len(configs)} files")
    return complete == len(configs)

def generate_report(test_results, features_ok, docs_ok, config_ok):
    """Generate final validation report."""
    print_header("FINAL VALIDATION REPORT")
    
    print("TEST RESULTS:")
    print("-" * 80)
    for test_name, passed in test_results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name:30s}: {status}")
    
    print("\nFEATURE IMPLEMENTATION:")
    print("-" * 80)
    print(f"  All 20 features implemented: {'PASS' if features_ok else 'FAIL'}")
    
    print("\nDOCUMENTATION:")
    print("-" * 80)
    print(f"  All documentation complete: {'PASS' if docs_ok else 'FAIL'}")
    
    print("\nCONFIGURATION:")
    print("-" * 80)
    print(f"  All configuration files present: {'PASS' if config_ok else 'FAIL'}")
    
    # Overall assessment
    critical_tests = test_results.get("unit_tests", False) and test_results.get("integration_tests", False)
    overall_passed = critical_tests and features_ok and docs_ok and config_ok
    
    print("\n" + "=" * 80)
    if overall_passed:
        print("OVERALL: PASS")
        print("=" * 80)
        print("\nRECOMMENDATION: GO FOR PRODUCTION DEPLOYMENT")
        print("\nAll validation checks passed:")
        print("- All critical tests passing")
        print("- All 20 features implemented")
        print("- Documentation complete")
        print("- Configuration templates ready")
        print("\nNext steps:")
        print("1. Review deployment checklist (docs/DEPLOYMENT_CHECKLIST.md)")
        print("2. Execute gradual rollout strategy (4 phases over 4 weeks)")
        print("3. Monitor intensively during Phase 1 (first 48 hours)")
        print("4. Keep rollback team on standby")
        print("5. Follow rollout checklist (docs/ROLLOUT_CHECKLIST.md)")
    else:
        print("OVERALL: FAIL")
        print("=" * 80)
        print("\nRECOMMENDATION: NO-GO - Issues Found")
        print("\nIssues:")
        if not test_results.get("unit_tests", False):
            print("- Unit tests failing")
        if not test_results.get("integration_tests", False):
            print("- Integration tests failing")
        if not features_ok:
            print("- Not all features implemented")
        if not docs_ok:
            print("- Documentation incomplete")
        if not config_ok:
            print("- Configuration files missing")
        print("\nRecommended actions:")
        print("1. Fix failing tests")
        print("2. Complete missing implementations")
        print("3. Re-run validation after fixes")
        print("4. Do NOT deploy to production until all checks pass")
    
    # Save report
    report_path = Path("reports/final_validation_report.txt")
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("FINAL SYSTEM VALIDATION REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Timestamp: {datetime.now()}\n\n")
        
        f.write("TEST RESULTS:\n")
        f.write("-" * 80 + "\n")
        for test_name, passed in test_results.items():
            status = "PASS" if passed else "FAIL"
            f.write(f"  {test_name}: {status}\n")
        
        f.write("\n\nFEATURE IMPLEMENTATION:\n")
        f.write("-" * 80 + "\n")
        f.write(f"  All 20 features implemented: {'PASS' if features_ok else 'FAIL'}\n")
        
        f.write("\n\nDOCUMENTATION:\n")
        f.write("-" * 80 + "\n")
        f.write(f"  All documentation complete: {'PASS' if docs_ok else 'FAIL'}\n")
        
        f.write("\n\nCONFIGURATION:\n")
        f.write("-" * 80 + "\n")
        f.write(f"  All configuration files present: {'PASS' if config_ok else 'FAIL'}\n")
        
        f.write("\n\n" + "=" * 80 + "\n")
        f.write(f"OVERALL: {'PASS' if overall_passed else 'FAIL'}\n")
        f.write("=" * 80 + "\n")
    
    print(f"\nReport saved to: {report_path}")
    
    return overall_passed

def main():
    """Main entry point."""
    print_header("FINAL SYSTEM VALIDATION - TASK 11")
    print(f"Started at: {datetime.now()}")
    
    # Run validation steps
    test_results = run_tests()
    features_ok = check_feature_implementation()
    docs_ok = check_documentation()
    config_ok = check_configuration()
    
    # Generate report
    overall_passed = generate_report(test_results, features_ok, docs_ok, config_ok)
    
    print_header("VALIDATION COMPLETE")
    
    # Exit with appropriate code
    sys.exit(0 if overall_passed else 1)

if __name__ == "__main__":
    main()
