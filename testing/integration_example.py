"""
Example: Integrating A/B Testing Framework with Signal Engine

This example demonstrates how to integrate A/B testing into the trading system
to test new features before full deployment.

Requirement: 15.8
"""

from testing.ab_framework import ABTestingFramework
from typing import Dict, Optional


class ABTestingIntegration:
    """
    Integration layer between A/B Testing Framework and Signal Engine.
    
    This class shows how to:
    1. Create experiments for new features
    2. Assign signals to variants
    3. Track signal outcomes
    4. Evaluate feature performance
    """
    
    def __init__(self):
        self.framework = ABTestingFramework()
    
    def setup_feature_test(
        self,
        feature_name: str,
        feature_description: str
    ) -> str:
        """
        Set up A/B test for a new feature.
        
        Args:
            feature_name: Name of feature being tested
            feature_description: Description of what's being tested
            
        Returns:
            Experiment ID
        """
        experiment = self.framework.create_experiment(
            name=feature_name,
            description=feature_description,
            variants=["control", "treatment"]
        )
        
        return experiment.experiment_id
    
    def process_signal_with_ab_test(
        self,
        signal: Dict,
        experiment_name: str,
        apply_feature_fn: callable
    ) -> Dict:
        """
        Process signal with A/B testing.
        
        Args:
            signal: Trading signal
            experiment_name: Name of active experiment
            apply_feature_fn: Function to apply treatment feature
            
        Returns:
            Processed signal with variant assignment
        """
        signal_id = signal.get('signal_id', f"sig_{signal['symbol']}_{signal['timestamp']}")
        
        # Assign to variant
        variant = self.framework.assign_variant(signal_id, experiment_name)
        
        # Apply feature if treatment variant
        if variant == "treatment":
            signal = apply_feature_fn(signal)
        
        # Track assignment
        self.framework.track_signal(
            signal_id=signal_id,
            experiment_name=experiment_name,
            variant=variant,
            signal_data={
                'symbol': signal['symbol'],
                'direction': signal['direction'],
                'confidence': signal['confidence'],
                'quality': signal['quality']
            }
        )
        
        # Add variant info to signal
        signal['ab_test'] = {
            'experiment': experiment_name,
            'variant': variant
        }
        
        return signal
    
    def track_signal_outcome(
        self,
        signal_id: str,
        hit_tp: bool,
        pnl: float
    ):
        """
        Track outcome of a signal that was part of an A/B test.
        
        Args:
            signal_id: Signal identifier
            hit_tp: Whether TP was hit (True) or SL was hit (False)
            pnl: Profit/Loss amount
        """
        outcome = "WIN" if hit_tp else "LOSS"
        self.framework.track_outcome(signal_id, outcome, pnl)
    
    def evaluate_feature(self, experiment_name: str) -> Dict:
        """
        Evaluate feature performance and get deployment recommendation.
        
        Args:
            experiment_name: Name of experiment
            
        Returns:
            Dictionary with evaluation results
        """
        metrics = self.framework.calculate_metrics(experiment_name)
        
        return {
            'should_deploy': metrics.recommendation.should_deploy,
            'reason': metrics.recommendation.reason,
            'improvement_pct': metrics.recommendation.performance_improvement_pct,
            'confidence_level': metrics.recommendation.confidence_level,
            'control_metrics': metrics.variant_metrics.get('control'),
            'treatment_metrics': metrics.variant_metrics.get('treatment'),
            'p_value': metrics.statistical_test.p_value,
            'is_significant': metrics.statistical_test.is_significant
        }


# Example usage
def example_vsa_feature_test():
    """
    Example: Testing VSA (Volume Spread Analysis) feature impact.
    """
    integration = ABTestingIntegration()
    
    # 1. Setup experiment
    experiment_id = integration.setup_feature_test(
        feature_name="VSA Integration",
        feature_description="Test impact of VSA signals on win rate and confidence accuracy"
    )
    
    print(f"Created experiment: {experiment_id}")
    
    # 2. Define feature application function
    def apply_vsa_feature(signal: Dict) -> Dict:
        """Apply VSA feature to signal (treatment variant)"""
        # This would call the actual VSA analyzer
        # For example purposes, we'll simulate a confidence boost
        if 'vsa_score' in signal.get('advanced_analytics', {}):
            vsa_score = signal['advanced_analytics']['vsa_score']
            if vsa_score > 70:
                signal['confidence'] = min(100, signal['confidence'] + 10)
        return signal
    
    # 3. Process signals with A/B testing
    example_signal = {
        'signal_id': 'sig_BTCUSDT_20250101_120000',
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'confidence': 75,
        'quality': 'A',
        'timestamp': '2025-01-01T12:00:00',
        'advanced_analytics': {
            'vsa_score': 80
        }
    }
    
    processed_signal = integration.process_signal_with_ab_test(
        signal=example_signal,
        experiment_name="VSA Integration",
        apply_feature_fn=apply_vsa_feature
    )
    
    print(f"Signal assigned to variant: {processed_signal['ab_test']['variant']}")
    
    # 4. Later, track outcome
    integration.track_signal_outcome(
        signal_id='sig_BTCUSDT_20250101_120000',
        hit_tp=True,
        pnl=150.0
    )
    
    # 5. After collecting enough data, evaluate
    # (In practice, wait for 100+ samples per variant)
    evaluation = integration.evaluate_feature("VSA Integration")
    
    print("\nFeature Evaluation:")
    print(f"  Should Deploy: {evaluation['should_deploy']}")
    print(f"  Reason: {evaluation['reason']}")
    print(f"  Improvement: {evaluation['improvement_pct']:.2f}%")
    print(f"  Confidence: {evaluation['confidence_level']:.2f}%")


if __name__ == '__main__':
    example_vsa_feature_test()
