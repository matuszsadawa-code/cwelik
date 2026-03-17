"""
CLI Interface for A/B Testing Framework

Usage:
    python -m testing create --name "VSA Integration" --description "Test VSA feature impact" --variants control treatment
    python -m testing list [--status ACTIVE]
    python -m testing metrics --name "VSA Integration"
    python -m testing report --name "VSA Integration"
    python -m testing end --name "VSA Integration"
"""

import argparse
import sys
from testing.ab_framework import ABTestingFramework


def create_experiment(args):
    """Create a new experiment"""
    framework = ABTestingFramework()
    
    experiment = framework.create_experiment(
        name=args.name,
        description=args.description,
        variants=args.variants
    )
    
    print(f"✓ Created experiment: {experiment.name}")
    print(f"  ID: {experiment.experiment_id}")
    print(f"  Variants: {', '.join(experiment.variants)}")
    print(f"  Status: {experiment.status}")


def list_experiments(args):
    """List experiments"""
    framework = ABTestingFramework()
    
    experiments = framework.list_experiments(status=args.status)
    
    if not experiments:
        print("No experiments found")
        return
    
    print(f"\nFound {len(experiments)} experiment(s):\n")
    
    for exp in experiments:
        print(f"  {exp.name}")
        print(f"    ID: {exp.experiment_id}")
        print(f"    Status: {exp.status}")
        print(f"    Variants: {', '.join(exp.variants)}")
        print(f"    Started: {exp.start_date.strftime('%Y-%m-%d %H:%M:%S')}")
        if exp.end_date:
            print(f"    Ended: {exp.end_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print()


def show_metrics(args):
    """Show experiment metrics"""
    framework = ABTestingFramework()
    
    try:
        metrics = framework.calculate_metrics(args.name)
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    print(f"\nMetrics for experiment: {args.name}\n")
    
    print("Variant Performance:")
    for variant_name, variant_metrics in metrics.variant_metrics.items():
        print(f"  {variant_name}:")
        print(f"    Sample Size: {variant_metrics.sample_size}")
        print(f"    Win Rate: {variant_metrics.win_rate:.2f}%")
        print(f"    Avg Profit: ${variant_metrics.avg_profit:.2f}")
        print(f"    Confidence Accuracy: {variant_metrics.confidence_accuracy:.2f}%")
        print(f"    Total PnL: ${variant_metrics.total_pnl:.2f}")
        print()
    
    print("Statistical Test:")
    print(f"  Type: {metrics.statistical_test.test_type}")
    print(f"  P-Value: {metrics.statistical_test.p_value:.4f}")
    print(f"  Significant: {'Yes' if metrics.statistical_test.is_significant else 'No'}")
    if metrics.statistical_test.confidence_interval != (0.0, 0.0):
        ci_lower, ci_upper = metrics.statistical_test.confidence_interval
        print(f"  95% CI: [{ci_lower:.2f}, {ci_upper:.2f}]")
    print()
    
    print("Deployment Recommendation:")
    print(f"  Should Deploy: {'Yes' if metrics.recommendation.should_deploy else 'No'}")
    print(f"  Reason: {metrics.recommendation.reason}")
    print(f"  Improvement: {metrics.recommendation.performance_improvement_pct:.2f}%")
    print(f"  Confidence: {metrics.recommendation.confidence_level:.2f}%")


def generate_report(args):
    """Generate comparison report"""
    framework = ABTestingFramework()
    
    try:
        report = framework.generate_comparison_report(args.name)
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    print("\n" + "=" * 80)
    print(report.summary)
    print("=" * 80)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report.summary)
        print(f"\n✓ Report saved to: {args.output}")


def end_experiment(args):
    """End an experiment"""
    framework = ABTestingFramework()
    
    try:
        framework.end_experiment(args.name)
        print(f"✓ Ended experiment: {args.name}")
    except ValueError as e:
        print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="A/B Testing Framework CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Create experiment
    create_parser = subparsers.add_parser('create', help='Create new experiment')
    create_parser.add_argument('--name', required=True, help='Experiment name')
    create_parser.add_argument('--description', required=True, help='Experiment description')
    create_parser.add_argument('--variants', nargs='+', required=True, help='Variant names')
    
    # List experiments
    list_parser = subparsers.add_parser('list', help='List experiments')
    list_parser.add_argument('--status', choices=['ACTIVE', 'COMPLETED', 'CANCELLED'], 
                            help='Filter by status')
    
    # Show metrics
    metrics_parser = subparsers.add_parser('metrics', help='Show experiment metrics')
    metrics_parser.add_argument('--name', required=True, help='Experiment name')
    
    # Generate report
    report_parser = subparsers.add_parser('report', help='Generate comparison report')
    report_parser.add_argument('--name', required=True, help='Experiment name')
    report_parser.add_argument('--output', help='Output file path')
    
    # End experiment
    end_parser = subparsers.add_parser('end', help='End experiment')
    end_parser.add_argument('--name', required=True, help='Experiment name')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'create':
        create_experiment(args)
    elif args.command == 'list':
        list_experiments(args)
    elif args.command == 'metrics':
        show_metrics(args)
    elif args.command == 'report':
        generate_report(args)
    elif args.command == 'end':
        end_experiment(args)


if __name__ == '__main__':
    main()
