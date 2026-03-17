"""
A/B Testing Framework for Trading System

This module provides A/B testing capabilities for objectively measuring
the impact of new features before full deployment.
"""

from testing.ab_framework import (
    ABTestingFramework,
    Experiment,
    ExperimentMetrics,
    VariantMetrics,
    StatisticalTest,
    DeploymentRecommendation,
    ComparisonReport,
)

__all__ = [
    "ABTestingFramework",
    "Experiment",
    "ExperimentMetrics",
    "VariantMetrics",
    "StatisticalTest",
    "DeploymentRecommendation",
    "ComparisonReport",
]
