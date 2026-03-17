"""
Final System Validation Script

Comprehensive validation for Task 11: Final Checkpoint - System Validation

This script:
1. Runs all tests (unit, property, integration)
2. Runs comprehensive backtests with all features enabled
3. Compares baseline vs full system performance
4. Validates success criteria (win rate +5%, R:R +15%, drawdown -10%, Sharpe +0.2)
5. Generates final validation report
6. Provides go/no-go recommendation
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import subprocess
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict

from storage.database import Database
from backtesting.backtest_engine import BacktestingEngine
from utils.logger import get_logger

log = get_logger("final_validation")


@dataclass
class ValidationResult:
    """Validation result for a specific check."""
    check_name: str
    passed: bool
    expected: str
    actual: str
    details: str


@dataclass
class SystemValidationReport:
    """Complete system validation report."""
    timestamp: datetime
    test_results: Dict[str, bool]
    backtest_baseline: Dict
    backtest_full_system: Dict
    success_criteria_results: List[ValidationResult]
    overall_passed: bool
    recommendation: str
    details: str


class FinalSystemValidator:
    """Comprehensive system validator for final checkpoint."""
    
    def __init__(self):
        self.db = Database("db/trading_system.db")
        self.backtest_engine = BacktestingEngine(self.db)
        self.results: List[ValidationResult] = []
        
    def run_all_tests(self) -> Dict[str, bool]:
        """
        Run all test suites.
        
        Returns:
            Dict with test suite results
        """
        log.info("=" * 80)
        log.info("STEP 1: Running All Test Suites")
        log.info("=" * 80)
        
        test_results = {}
        
        # Run unit tests
        log.info("\n[1/3] Running unit tests...")
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "-x"],
                capture_output=True,
                text=True,
                timeout=300
            )
            test_results["unit_tests"] = result.returncode == 0
            if result.returncode == 0:
                log.info("✅ Unit tests PASSED")
            else:
                log.error(f"❌ Unit tests FAILED\n{result.stdout}\n{result.stderr}")
        except Exception as e:
            log.error(f"❌ Unit tests ERROR: {e}")
            test_results["unit_tests"] = False
        
        # Run property tests
        log.info("\n[2/3] Running property-based tests...")
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-v", "-m", "property", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=300
            )
            test_results["property_tests"] = result.returncode == 0
            if result.returncode == 0:
                log.info("✅ Property tests PASSED")
            else:
                log.warning(f"⚠️  Property tests FAILED (optional)\n{result.stdout}")
        except Exception as e:
            log.warning(f"⚠️  Property tests ERROR (optional): {e}")
            test_results["property_tests"] = False
        
        # Run integration tests
        log.info("\n[3/3] Running integration tests...")
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/test_integration_complete.py", "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=300
            )
            test_results["integration_tests"] = result.returncode == 0
            if result.returncode == 0:
                log.info("✅ Integration tests PASSED")
            else:
                log.error(f"❌ Integration tests FAILED\n{result.stdout}\n{result.stderr}")
        except Exception as e:
            log.error(f"❌ Integration tests ERROR: {e}")
            test_results["integration_tests"] = False
        
        return test_results
    
    def run_baseline_backtest(self) -> Dict:
        """
        Run backtest with baseline configuration (minimal features).
        
        Returns:
            Baseline performance metrics
        """
        log.info("\n" + "=" * 80)
        log.info("STEP 2: Running Baseline Backtest (Minimal Features)")
        log.info("=" * 80)
        
        # Disable all advanced features for baseline
        baseline_config = {
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "initial_capital": 10000,
            "risk_per_trade_pct": 1.0,
            "features_enabled": {
                "vsa": False,
                "wyckoff": False,
                "market_profile": False,
                "liquidity_engineering": False,
                "smart_money_divergence": False,
                "mtf_confluence": False,
                "orderbook_imbalance": False,
                "institutional_flow": False,
                "volatility_regime": False,
                "seasonality": False,
                "ml_calibration": False,
                "dynamic_tp": False,
                "adaptive_sl": False,
                "correlation_optimizer": False,
                "enhanced_risk": False,
                "news_sentiment": False,
                "microstructure": False,
            }
        }
        
        # Run 6-month backtest
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        
        log.info(f"Backtesting period: {start_date.date()} to {end_date.date()}")
        log.info("Features: BASELINE (ICT only)")
        
        try:
            result = self.backtest_engine.run_backtest(
                baseline_config,
                start_date,
                end_date,
                symbols=baseline_config["symbols"]
            )
            
            if result:
                metrics = result.metrics
                baseline_metrics = {
                    "win_rate": metrics.win_rate,
                    "profit_factor": metrics.profit_factor,
                    "sharpe_ratio": metrics.sharpe_ratio,
                    "max_drawdown": metrics.max_drawdown,
                    "avg_rr": metrics.avg_rr,
                    "total_return": metrics.total_return,
                    "total_trades": metrics.total_trades,
                }
                
                log.info("\n📊 Baseline Performance:")
                log.info(f"  Win Rate: {metrics.win_rate:.2f}%")
                log.info(f"  Profit Factor: {metrics.profit_factor:.2f}")
                log.info(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
                log.info(f"  Max Drawdown: {metrics.max_drawdown:.2f}%")
                log.info(f"  Avg R:R: {metrics.avg_rr:.2f}")
                log.info(f"  Total Return: {metrics.total_return:.2f}%")
                log.info(f"  Total Trades: {metrics.total_trades}")
                
                return baseline_metrics
            else:
                log.error("❌ Baseline backtest failed - no result")
                return {}
                
        except Exception as e:
            log.error(f"❌ Baseline backtest ERROR: {e}")
            return {}
    
    def run_full_system_backtest(self) -> Dict:
        """
        Run backtest with all 20 features enabled.
        
        Returns:
            Full system performance metrics
        """
        log.info("\n" + "=" * 80)
        log.info("STEP 3: Running Full System Backtest (All 20 Features)")
        log.info("=" * 80)
        
        # Enable all features
        full_config = {
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "initial_capital": 10000,
            "risk_per_trade_pct": 1.0,
            "features_enabled": {
                "vsa": True,
                "wyckoff": True,
                "market_profile": True,
                "liquidity_engineering": True,
                "smart_money_divergence": True,
                "mtf_confluence": True,
                "orderbook_imbalance": True,
                "institutional_flow": True,
                "volatility_regime": True,
                "seasonality": True,
                "ml_calibration": True,
                "dynamic_tp": True,
                "adaptive_sl": True,
                "correlation_optimizer": True,
                "enhanced_risk": True,
                "news_sentiment": True,
                "microstructure": True,
            }
        }
        
        # Run 6-month backtest
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        
        log.info(f"Backtesting period: {start_date.date()} to {end_date.date()}")
        log.info("Features: ALL 20 FEATURES ENABLED")
        
        try:
            result = self.backtest_engine.run_backtest(
                full_config,
                start_date,
                end_date,
                symbols=full_config["symbols"]
            )
            
            if result:
                metrics = result.metrics
                full_metrics = {
                    "win_rate": metrics.win_rate,
                    "profit_factor": metrics.profit_factor,
                    "sharpe_ratio": metrics.sharpe_ratio,
                    "max_drawdown": metrics.max_drawdown,
                    "avg_rr": metrics.avg_rr,
                    "total_return": metrics.total_return,
                    "total_trades": metrics.total_trades,
                }
                
                log.info("\n📊 Full System Performance:")
                log.info(f"  Win Rate: {metrics.win_rate:.2f}%")
                log.info(f"  Profit Factor: {metrics.profit_factor:.2f}")
                log.info(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
                log.info(f"  Max Drawdown: {metrics.max_drawdown:.2f}%")
                log.info(f"  Avg R:R: {metrics.avg_rr:.2f}")
                log.info(f"  Total Return: {metrics.total_return:.2f}%")
                log.info(f"  Total Trades: {metrics.total_trades}")
                
                return full_metrics
            else:
                log.error("❌ Full system backtest failed - no result")
                return {}
                
        except Exception as e:
            log.error(f"❌ Full system backtest ERROR: {e}")
            return {}
    
    def validate_success_criteria(
        self,
        baseline: Dict,
        full_system: Dict
    ) -> List[ValidationResult]:
        """
        Validate success criteria against targets.
        
        Success Criteria:
        - Win rate improved by ≥5%
        - Average R:R improved by ≥15%
        - Max drawdown reduced by ≥10%
        - Sharpe ratio improved by ≥0.2
        
        Returns:
            List of validation results
        """
        log.info("\n" + "=" * 80)
        log.info("STEP 4: Validating Success Criteria")
        log.info("=" * 80)
        
        results = []
        
        if not baseline or not full_system:
            log.error("❌ Cannot validate - missing backtest data")
            return results
        
        # 1. Win Rate: +5% improvement
        baseline_wr = baseline.get("win_rate", 0)
        full_wr = full_system.get("win_rate", 0)
        wr_improvement = full_wr - baseline_wr
        wr_passed = wr_improvement >= 5.0
        
        results.append(ValidationResult(
            check_name="Win Rate Improvement",
            passed=wr_passed,
            expected="≥+5.0%",
            actual=f"+{wr_improvement:.2f}%",
            details=f"Baseline: {baseline_wr:.2f}%, Full: {full_wr:.2f}%"
        ))
        
        log.info(f"\n[1/4] Win Rate Improvement:")
        log.info(f"  Expected: ≥+5.0%")
        log.info(f"  Actual: +{wr_improvement:.2f}%")
        log.info(f"  Status: {'✅ PASS' if wr_passed else '❌ FAIL'}")
        
        # 2. Average R:R: +15% improvement
        baseline_rr = baseline.get("avg_rr", 0)
        full_rr = full_system.get("avg_rr", 0)
        rr_improvement_pct = ((full_rr - baseline_rr) / baseline_rr * 100) if baseline_rr > 0 else 0
        rr_passed = rr_improvement_pct >= 15.0
        
        results.append(ValidationResult(
            check_name="Average R:R Improvement",
            passed=rr_passed,
            expected="≥+15.0%",
            actual=f"+{rr_improvement_pct:.2f}%",
            details=f"Baseline: {baseline_rr:.2f}, Full: {full_rr:.2f}"
        ))
        
        log.info(f"\n[2/4] Average R:R Improvement:")
        log.info(f"  Expected: ≥+15.0%")
        log.info(f"  Actual: +{rr_improvement_pct:.2f}%")
        log.info(f"  Status: {'✅ PASS' if rr_passed else '❌ FAIL'}")
        
        # 3. Max Drawdown: -10% reduction
        baseline_dd = baseline.get("max_drawdown", 0)
        full_dd = full_system.get("max_drawdown", 0)
        dd_reduction_pct = ((baseline_dd - full_dd) / baseline_dd * 100) if baseline_dd > 0 else 0
        dd_passed = dd_reduction_pct >= 10.0
        
        results.append(ValidationResult(
            check_name="Max Drawdown Reduction",
            passed=dd_passed,
            expected="≥-10.0%",
            actual=f"-{dd_reduction_pct:.2f}%",
            details=f"Baseline: {baseline_dd:.2f}%, Full: {full_dd:.2f}%"
        ))
        
        log.info(f"\n[3/4] Max Drawdown Reduction:")
        log.info(f"  Expected: ≥-10.0%")
        log.info(f"  Actual: -{dd_reduction_pct:.2f}%")
        log.info(f"  Status: {'✅ PASS' if dd_passed else '❌ FAIL'}")
        
        # 4. Sharpe Ratio: +0.2 improvement
        baseline_sharpe = baseline.get("sharpe_ratio", 0)
        full_sharpe = full_system.get("sharpe_ratio", 0)
        sharpe_improvement = full_sharpe - baseline_sharpe
        sharpe_passed = sharpe_improvement >= 0.2
        
        results.append(ValidationResult(
            check_name="Sharpe Ratio Improvement",
            passed=sharpe_passed,
            expected="≥+0.2",
            actual=f"+{sharpe_improvement:.2f}",
            details=f"Baseline: {baseline_sharpe:.2f}, Full: {full_sharpe:.2f}"
        ))
        
        log.info(f"\n[4/4] Sharpe Ratio Improvement:")
        log.info(f"  Expected: ≥+0.2")
        log.info(f"  Actual: +{sharpe_improvement:.2f}")
        log.info(f"  Status: {'✅ PASS' if sharpe_passed else '❌ FAIL'}")
        
        return results
    
    def generate_recommendation(
        self,
        test_results: Dict[str, bool],
        success_criteria: List[ValidationResult]
    ) -> Tuple[bool, str, str]:
        """
        Generate go/no-go recommendation.
        
        Returns:
            (overall_passed, recommendation, details)
        """
        log.info("\n" + "=" * 80)
        log.info("STEP 5: Generating Recommendation")
        log.info("=" * 80)
        
        # Check test results
        critical_tests_passed = (
            test_results.get("unit_tests", False) and
            test_results.get("integration_tests", False)
        )
        
        # Check success criteria
        criteria_passed = all(r.passed for r in success_criteria)
        
        # Overall pass/fail
        overall_passed = critical_tests_passed and criteria_passed
        
        # Generate recommendation
        if overall_passed:
            recommendation = "✅ GO FOR PRODUCTION DEPLOYMENT"
            details = (
                "All validation checks passed:\n"
                "- All critical tests passing\n"
                "- All success criteria met\n"
                "- System ready for production deployment\n\n"
                "Recommended next steps:\n"
                "1. Review final validation report\n"
                "2. Execute gradual rollout strategy (4 phases over 4 weeks)\n"
                "3. Monitor intensively during Phase 1 (first 48 hours)\n"
                "4. Keep rollback team on standby\n"
                "5. Follow deployment checklist in docs/DEPLOYMENT_CHECKLIST.md"
            )
        else:
            recommendation = "❌ NO-GO - Issues Found"
            issues = []
            
            if not test_results.get("unit_tests", False):
                issues.append("- Unit tests failing")
            if not test_results.get("integration_tests", False):
                issues.append("- Integration tests failing")
            
            for result in success_criteria:
                if not result.passed:
                    issues.append(f"- {result.check_name}: {result.actual} (expected {result.expected})")
            
            details = (
                "Validation failed with the following issues:\n" +
                "\n".join(issues) +
                "\n\nRecommended actions:\n"
                "1. Fix failing tests\n"
                "2. Investigate performance gaps\n"
                "3. Re-run validation after fixes\n"
                "4. Do NOT deploy to production until all checks pass"
            )
        
        log.info(f"\n{recommendation}")
        log.info(f"\n{details}")
        
        return overall_passed, recommendation, details
    
    def save_report(self, report: SystemValidationReport):
        """Save validation report to file."""
        report_path = Path("reports/final_validation_report.json")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, "w") as f:
            json.dump(asdict(report), f, indent=2, default=str)
        
        log.info(f"\n📄 Report saved to: {report_path}")
        
        # Also save human-readable version
        readable_path = Path("reports/final_validation_report.txt")
        with open(readable_path, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("FINAL SYSTEM VALIDATION REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Timestamp: {report.timestamp}\n\n")
            
            f.write("TEST RESULTS:\n")
            f.write("-" * 80 + "\n")
            for test_name, passed in report.test_results.items():
                status = "✅ PASS" if passed else "❌ FAIL"
                f.write(f"  {test_name}: {status}\n")
            
            f.write("\n\nBASELINE PERFORMANCE:\n")
            f.write("-" * 80 + "\n")
            for key, value in report.backtest_baseline.items():
                f.write(f"  {key}: {value}\n")
            
            f.write("\n\nFULL SYSTEM PERFORMANCE:\n")
            f.write("-" * 80 + "\n")
            for key, value in report.backtest_full_system.items():
                f.write(f"  {key}: {value}\n")
            
            f.write("\n\nSUCCESS CRITERIA VALIDATION:\n")
            f.write("-" * 80 + "\n")
            for result in report.success_criteria_results:
                status = "✅ PASS" if result.passed else "❌ FAIL"
                f.write(f"  {result.check_name}: {status}\n")
                f.write(f"    Expected: {result.expected}\n")
                f.write(f"    Actual: {result.actual}\n")
                f.write(f"    Details: {result.details}\n\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"OVERALL: {'✅ PASSED' if report.overall_passed else '❌ FAILED'}\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"RECOMMENDATION:\n{report.recommendation}\n\n")
            f.write(f"DETAILS:\n{report.details}\n")
        
        log.info(f"📄 Readable report saved to: {readable_path}")
    
    def run_validation(self) -> SystemValidationReport:
        """
        Run complete system validation.
        
        Returns:
            SystemValidationReport
        """
        log.info("\n" + "=" * 80)
        log.info("FINAL SYSTEM VALIDATION - TASK 11")
        log.info("=" * 80)
        log.info(f"Started at: {datetime.now()}")
        
        # Step 1: Run all tests
        test_results = self.run_all_tests()
        
        # Step 2: Run baseline backtest
        baseline_metrics = self.run_baseline_backtest()
        
        # Step 3: Run full system backtest
        full_system_metrics = self.run_full_system_backtest()
        
        # Step 4: Validate success criteria
        success_criteria = self.validate_success_criteria(
            baseline_metrics,
            full_system_metrics
        )
        
        # Step 5: Generate recommendation
        overall_passed, recommendation, details = self.generate_recommendation(
            test_results,
            success_criteria
        )
        
        # Create report
        report = SystemValidationReport(
            timestamp=datetime.now(),
            test_results=test_results,
            backtest_baseline=baseline_metrics,
            backtest_full_system=full_system_metrics,
            success_criteria_results=success_criteria,
            overall_passed=overall_passed,
            recommendation=recommendation,
            details=details
        )
        
        # Save report
        self.save_report(report)
        
        log.info("\n" + "=" * 80)
        log.info("VALIDATION COMPLETE")
        log.info("=" * 80)
        
        return report


def main():
    """Main entry point."""
    validator = FinalSystemValidator()
    report = validator.run_validation()
    
    # Exit with appropriate code
    sys.exit(0 if report.overall_passed else 1)


if __name__ == "__main__":
    main()
