"""
Complete A/B Testing Workflow Example

This script demonstrates a complete A/B testing workflow:
1. Create experiment
2. Simulate signal processing with A/B testing
3. Track outcomes
4. Evaluate results
5. Get deployment recommendation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
from testing.ab_framework import ABTestingFramework


def simulate_ab_test_workflow():
    """Simulate complete A/B testing workflow"""
    
    print("=" * 80)
    print("A/B Testing Framework - Complete Workflow Example")
    print("=" * 80)
    
    # Initialize framework
    framework = ABTestingFramework()
    
    # Step 1: Create experiment
    print("\n[Step 1] Creating experiment...")
    experiment = framework.create_experiment(
        name="VSA Feature Test",
        description="Testing impact of VSA signals on win rate and profitability",
        variants=["control", "treatment"]
    )
    print(f"✓ Created experiment: {experiment.name}")
    print(f"  ID: {experiment.experiment_id}")
    print(f"  Variants: {', '.join(experiment.variants)}")
    
    # Step 2: Simulate signal processing
    print("\n[Step 2] Simulating signal processing...")
    print("Processing 150 signals (75 per variant)...")
    
    for i in range(150):
        signal_id = f"sig_{i:04d}"
        
        # Assign to variant
        variant = framework.assign_variant(signal_id, "VSA Feature Test")
        
        # Simulate signal data
        base_confidence = 70
        if variant == "treatment":
            # Treatment: VSA feature adds 5-10 points to confidence
            confidence = base_confidence + random.randint(5, 10)
        else:
            confidence = base_confidence
        
        # Track signal
        framework.track_signal(
            signal_id=signal_id,
            experiment_name="VSA Feature Test",
            variant=variant,
            signal_data={
                "symbol": "BTCUSDT",
                "confidence": confidence,
                "direction": "LONG"
            }
        )
        
        # Simulate outcome
        # Treatment has slightly better win rate (60% vs 50%)
        if variant == "treatment":
            hit_tp = random.random() < 0.60
            pnl = random.uniform(80, 150) if hit_tp else random.uniform(-60, -40)
        else:
            hit_tp = random.random() < 0.50
            pnl = random.uniform(80, 150) if hit_tp else random.uniform(-60, -40)
        
        outcome = "WIN" if hit_tp else "LOSS"
        framework.track_outcome(signal_id, outcome, pnl)
    
    print("✓ Processed 150 signals")
    
    # Step 3: Calculate metrics
    print("\n[Step 3] Calculating metrics...")
    metrics = framework.calculate_metrics("VSA Feature Test")
    
    print("\nVariant Performance:")
    for variant_name, variant_metrics in metrics.variant_metrics.items():
        print(f"\n  {variant_name.upper()}:")
        print(f"    Sample Size: {variant_metrics.sample_size}")
        print(f"    Win Rate: {variant_metrics.win_rate:.2f}%")
        print(f"    Avg Profit: ${variant_metrics.avg_profit:.2f}")
        print(f"    Total PnL: ${variant_metrics.total_pnl:.2f}")
        print(f"    Confidence Accuracy: {variant_metrics.confidence_accuracy:.2f}%")
    
    # Step 4: Statistical significance
    print("\n[Step 4] Statistical Analysis:")
    print(f"  Test Type: {metrics.statistical_test.test_type}")
    print(f"  P-Value: {metrics.statistical_test.p_value:.4f}")
    print(f"  Significant: {'Yes ✓' if metrics.statistical_test.is_significant else 'No ✗'}")
    
    if metrics.statistical_test.confidence_interval != (0.0, 0.0):
        ci_lower, ci_upper = metrics.statistical_test.confidence_interval
        print(f"  95% CI: [${ci_lower:.2f}, ${ci_upper:.2f}]")
    
    # Step 5: Deployment recommendation
    print("\n[Step 5] Deployment Recommendation:")
    rec = metrics.recommendation
    print(f"  Should Deploy: {'YES ✓' if rec.should_deploy else 'NO ✗'}")
    print(f"  Reason: {rec.reason}")
    print(f"  Performance Improvement: {rec.performance_improvement_pct:.2f}%")
    if rec.confidence_level > 0:
        print(f"  Confidence Level: {rec.confidence_level:.2f}%")
    
    # Step 6: Generate report
    print("\n[Step 6] Generating comparison report...")
    report = framework.generate_comparison_report("VSA Feature Test")
    
    print("\n" + "=" * 80)
    print("COMPARISON REPORT")
    print("=" * 80)
    print(report.summary)
    print("=" * 80)
    
    # Step 7: End experiment
    print("\n[Step 7] Ending experiment...")
    framework.end_experiment("VSA Feature Test")
    print("✓ Experiment ended")
    
    print("\n" + "=" * 80)
    print("Workflow Complete!")
    print("=" * 80)
    
    # Summary
    print("\nSummary:")
    if rec.should_deploy:
        print("  ✓ Treatment variant shows significant improvement")
        print("  ✓ Recommend deploying VSA feature to production")
    else:
        print("  ✗ Treatment variant does not meet deployment criteria")
        print(f"  ✗ Reason: {rec.reason}")
        print("  → Consider collecting more data or improving feature")


if __name__ == '__main__':
    simulate_ab_test_workflow()
