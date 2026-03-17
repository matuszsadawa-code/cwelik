"""
A/B Testing Framework for Trading System

This module provides comprehensive A/B testing capabilities for objectively
measuring the impact of new features before full deployment.

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8
"""

import json
import random
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from scipy import stats
import numpy as np


@dataclass
class Experiment:
    """Represents an A/B test experiment"""
    experiment_id: str
    name: str
    description: str
    variants: List[str]
    start_date: datetime
    end_date: Optional[datetime]
    status: str  # ACTIVE, COMPLETED, CANCELLED


@dataclass
class VariantMetrics:
    """Performance metrics for a single variant"""
    variant_name: str
    sample_size: int
    win_rate: float
    avg_profit: float
    confidence_accuracy: float
    total_pnl: float


@dataclass
class StatisticalTest:
    """Results of statistical significance testing"""
    test_type: str  # T_TEST, CHI_SQUARE
    p_value: float
    is_significant: bool  # p < 0.05
    confidence_interval: Tuple[float, float]


@dataclass
class DeploymentRecommendation:
    """Recommendation for deploying treatment variant"""
    should_deploy: bool
    reason: str
    performance_improvement_pct: float
    confidence_level: float


@dataclass
class ExperimentMetrics:
    """Complete metrics for an experiment"""
    variant_metrics: Dict[str, VariantMetrics]
    statistical_test: StatisticalTest
    recommendation: DeploymentRecommendation


@dataclass
class ComparisonReport:
    """Detailed comparison report for an experiment"""
    experiment: Experiment
    metrics: ExperimentMetrics
    charts: Dict[str, Any]  # Placeholder for visualization data
    summary: str


class ABTestingFramework:
    """
    A/B Testing Framework for objectively measuring feature impact.
    
    Supports:
    - Experiment creation and management
    - Random variant assignment (50/50 split)
    - Signal tracking (assignment and outcomes)
    - Metrics calculation per variant
    - Statistical significance testing
    - Deployment recommendations
    """
    
    def __init__(self, db_path: str = "db/trading_system.db"):
        """
        Initialize A/B Testing Framework.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.active_experiments: Dict[str, Experiment] = {}
        self._load_active_experiments()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.Connection(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _load_active_experiments(self):
        """Load active experiments from database"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT experiment_id, name, description, variants_json, 
                   start_date, end_date, status
            FROM experiments
            WHERE status = 'ACTIVE'
        """)
        
        for row in cursor.fetchall():
            experiment = Experiment(
                experiment_id=row['experiment_id'],
                name=row['name'],
                description=row['description'],
                variants=json.loads(row['variants_json']),
                start_date=datetime.fromisoformat(row['start_date']),
                end_date=datetime.fromisoformat(row['end_date']) if row['end_date'] else None,
                status=row['status']
            )
            self.active_experiments[experiment.experiment_id] = experiment
        
        conn.close()
    
    def create_experiment(
        self,
        name: str,
        description: str,
        variants: List[str]
    ) -> Experiment:
        """
        Create new A/B test experiment.
        
        Args:
            name: Experiment name
            description: What is being tested
            variants: List of variant names (e.g., ["control", "treatment"])
            
        Returns:
            Experiment object
            
        Requirement: 15.1
        """
        experiment_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_date = datetime.now()
        
        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            variants=variants,
            start_date=start_date,
            end_date=None,
            status="ACTIVE"
        )
        
        # Save to database
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO experiments 
            (experiment_id, name, description, variants_json, start_date, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            experiment_id,
            name,
            description,
            json.dumps(variants),
            start_date.isoformat(),
            "ACTIVE",
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        self.active_experiments[experiment_id] = experiment
        return experiment
    
    def assign_variant(self, signal_id: str, experiment_name: str) -> str:
        """
        Randomly assign signal to variant (50/50 split).
        
        Args:
            signal_id: Signal identifier
            experiment_name: Name of experiment
            
        Returns:
            Variant name assigned
            
        Requirement: 15.2
        """
        # Find experiment by name
        experiment = None
        for exp in self.active_experiments.values():
            if exp.name == experiment_name:
                experiment = exp
                break
        
        if not experiment:
            raise ValueError(f"Experiment '{experiment_name}' not found or not active")
        
        # Random 50/50 assignment
        variant = random.choice(experiment.variants)
        
        return variant
    
    def track_signal(
        self,
        signal_id: str,
        experiment_name: str,
        variant: str,
        signal_data: Dict
    ):
        """
        Track signal assignment and data.
        
        Args:
            signal_id: Signal identifier
            experiment_name: Name of experiment
            variant: Assigned variant
            signal_data: Signal data to track
            
        Requirement: 15.3
        """
        # Find experiment by name
        experiment = None
        for exp in self.active_experiments.values():
            if exp.name == experiment_name:
                experiment = exp
                break
        
        if not experiment:
            raise ValueError(f"Experiment '{experiment_name}' not found")
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO experiment_assignments
            (experiment_id, signal_id, variant, signal_data_json, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            experiment.experiment_id,
            signal_id,
            variant,
            json.dumps(signal_data),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def track_outcome(self, signal_id: str, outcome: str, pnl: float):
        """
        Track signal outcome (TP/SL hit, PnL).
        
        Args:
            signal_id: Signal identifier
            outcome: Outcome type (WIN, LOSS)
            pnl: Profit/Loss amount
            
        Requirement: 15.3
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO experiment_outcomes
            (signal_id, outcome, pnl, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            signal_id,
            outcome,
            pnl,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def calculate_metrics(self, experiment_name: str) -> ExperimentMetrics:
        """
        Calculate metrics for each variant.
        
        Metrics per variant:
        - Win Rate
        - Average Profit
        - Confidence Accuracy
        - Sample Size
        
        Args:
            experiment_name: Name of experiment
            
        Returns:
            ExperimentMetrics with per-variant metrics
            
        Requirement: 15.4
        """
        # Find experiment
        experiment = None
        for exp in self.active_experiments.values():
            if exp.name == experiment_name:
                experiment = exp
                break
        
        if not experiment:
            raise ValueError(f"Experiment '{experiment_name}' not found")
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        variant_metrics = {}
        
        for variant in experiment.variants:
            # Get all signals for this variant
            cursor.execute("""
                SELECT 
                    ea.signal_id,
                    ea.signal_data_json,
                    eo.outcome,
                    eo.pnl
                FROM experiment_assignments ea
                LEFT JOIN experiment_outcomes eo ON ea.signal_id = eo.signal_id
                WHERE ea.experiment_id = ? AND ea.variant = ?
            """, (experiment.experiment_id, variant))
            
            rows = cursor.fetchall()
            sample_size = len(rows)
            
            if sample_size == 0:
                variant_metrics[variant] = VariantMetrics(
                    variant_name=variant,
                    sample_size=0,
                    win_rate=0.0,
                    avg_profit=0.0,
                    confidence_accuracy=0.0,
                    total_pnl=0.0
                )
                continue
            
            # Calculate metrics
            wins = sum(1 for row in rows if row['outcome'] == 'WIN')
            total_pnl = sum(row['pnl'] for row in rows if row['pnl'] is not None)
            
            win_rate = (wins / sample_size * 100) if sample_size > 0 else 0.0
            avg_profit = total_pnl / sample_size if sample_size > 0 else 0.0
            
            # Calculate confidence accuracy (predicted confidence vs actual win rate)
            confidence_accuracy = 0.0
            confidence_count = 0
            for row in rows:
                if row['signal_data_json'] and row['outcome']:
                    signal_data = json.loads(row['signal_data_json'])
                    if 'confidence' in signal_data:
                        predicted_conf = signal_data['confidence']
                        actual_outcome = 1 if row['outcome'] == 'WIN' else 0
                        # Brier score component
                        confidence_accuracy += (predicted_conf / 100 - actual_outcome) ** 2
                        confidence_count += 1
            
            if confidence_count > 0:
                # Convert Brier score to accuracy (lower Brier = higher accuracy)
                brier_score = confidence_accuracy / confidence_count
                confidence_accuracy = (1 - brier_score) * 100
            
            variant_metrics[variant] = VariantMetrics(
                variant_name=variant,
                sample_size=sample_size,
                win_rate=win_rate,
                avg_profit=avg_profit,
                confidence_accuracy=confidence_accuracy,
                total_pnl=total_pnl
            )
        
        conn.close()
        
        # Calculate statistical significance
        statistical_test = self.calculate_statistical_significance(experiment_name)
        
        # Generate deployment recommendation
        recommendation = self.should_deploy_treatment(experiment_name)
        
        return ExperimentMetrics(
            variant_metrics=variant_metrics,
            statistical_test=statistical_test,
            recommendation=recommendation
        )
    
    def calculate_statistical_significance(
        self,
        experiment_name: str
    ) -> StatisticalTest:
        """
        Calculate p-value using t-test or chi-square test.
        
        Args:
            experiment_name: Name of experiment
            
        Returns:
            StatisticalTest with p-value and significance
            
        Requirement: 15.5
        """
        # Find experiment
        experiment = None
        for exp in self.active_experiments.values():
            if exp.name == experiment_name:
                experiment = exp
                break
        
        if not experiment:
            raise ValueError(f"Experiment '{experiment_name}' not found")
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get PnL data for each variant
        variant_pnls = {}
        
        for variant in experiment.variants:
            cursor.execute("""
                SELECT eo.pnl
                FROM experiment_assignments ea
                JOIN experiment_outcomes eo ON ea.signal_id = eo.signal_id
                WHERE ea.experiment_id = ? AND ea.variant = ?
            """, (experiment.experiment_id, variant))
            
            pnls = [row['pnl'] for row in cursor.fetchall()]
            variant_pnls[variant] = pnls
        
        conn.close()
        
        # Perform t-test if we have 2 variants
        if len(experiment.variants) == 2:
            variant1, variant2 = experiment.variants
            pnls1 = variant_pnls[variant1]
            pnls2 = variant_pnls[variant2]
            
            if len(pnls1) < 2 or len(pnls2) < 2:
                return StatisticalTest(
                    test_type="T_TEST",
                    p_value=1.0,
                    is_significant=False,
                    confidence_interval=(0.0, 0.0)
                )
            
            # Two-sample t-test
            t_stat, p_value = stats.ttest_ind(pnls1, pnls2)
            
            # Calculate confidence interval for difference in means
            mean_diff = np.mean(pnls1) - np.mean(pnls2)
            se_diff = np.sqrt(np.var(pnls1) / len(pnls1) + np.var(pnls2) / len(pnls2))
            ci_lower = mean_diff - 1.96 * se_diff
            ci_upper = mean_diff + 1.96 * se_diff
            
            return StatisticalTest(
                test_type="T_TEST",
                p_value=float(p_value),
                is_significant=p_value < 0.05,
                confidence_interval=(float(ci_lower), float(ci_upper))
            )
        
        # For more than 2 variants, use chi-square test on win rates
        else:
            # Chi-square test for independence
            wins = []
            losses = []
            
            for variant in experiment.variants:
                pnls = variant_pnls[variant]
                wins.append(sum(1 for pnl in pnls if pnl > 0))
                losses.append(sum(1 for pnl in pnls if pnl <= 0))
            
            if sum(wins) == 0 or sum(losses) == 0:
                return StatisticalTest(
                    test_type="CHI_SQUARE",
                    p_value=1.0,
                    is_significant=False,
                    confidence_interval=(0.0, 0.0)
                )
            
            chi2, p_value, dof, expected = stats.chi2_contingency([wins, losses])
            
            return StatisticalTest(
                test_type="CHI_SQUARE",
                p_value=float(p_value),
                is_significant=p_value < 0.05,
                confidence_interval=(0.0, 0.0)  # Not applicable for chi-square
            )
    
    def should_deploy_treatment(
        self,
        experiment_name: str
    ) -> DeploymentRecommendation:
        """
        Recommend deployment based on results.
        
        Deploy if:
        - p-value <0.05 (statistically significant)
        - Treatment performance >10% better than control
        - Minimum 100 samples per variant
        
        Args:
            experiment_name: Name of experiment
            
        Returns:
            DeploymentRecommendation
            
        Requirement: 15.6
        """
        # Find experiment
        experiment = None
        for exp in self.active_experiments.values():
            if exp.name == experiment_name:
                experiment = exp
                break
        
        if not experiment:
            raise ValueError(f"Experiment '{experiment_name}' not found")
        
        # Get metrics
        conn = self._get_connection()
        cursor = conn.cursor()
        
        variant_metrics = {}
        
        for variant in experiment.variants:
            cursor.execute("""
                SELECT 
                    COUNT(*) as sample_size,
                    AVG(CASE WHEN eo.outcome = 'WIN' THEN 1.0 ELSE 0.0 END) as win_rate,
                    AVG(eo.pnl) as avg_profit
                FROM experiment_assignments ea
                LEFT JOIN experiment_outcomes eo ON ea.signal_id = eo.signal_id
                WHERE ea.experiment_id = ? AND ea.variant = ?
            """, (experiment.experiment_id, variant))
            
            row = cursor.fetchone()
            variant_metrics[variant] = {
                'sample_size': row['sample_size'],
                'win_rate': row['win_rate'] or 0.0,
                'avg_profit': row['avg_profit'] or 0.0
            }
        
        conn.close()
        
        # Calculate statistical significance
        stat_test = self.calculate_statistical_significance(experiment_name)
        
        # Assume first variant is control, second is treatment
        if len(experiment.variants) < 2:
            return DeploymentRecommendation(
                should_deploy=False,
                reason="Need at least 2 variants for comparison",
                performance_improvement_pct=0.0,
                confidence_level=0.0
            )
        
        control_variant = experiment.variants[0]
        treatment_variant = experiment.variants[1]
        
        control_metrics = variant_metrics[control_variant]
        treatment_metrics = variant_metrics[treatment_variant]
        
        # Check minimum sample size
        if control_metrics['sample_size'] < 100 or treatment_metrics['sample_size'] < 100:
            return DeploymentRecommendation(
                should_deploy=False,
                reason=f"Insufficient samples (need 100 per variant, have {control_metrics['sample_size']} control, {treatment_metrics['sample_size']} treatment)",
                performance_improvement_pct=0.0,
                confidence_level=0.0
            )
        
        # Calculate performance improvement
        if control_metrics['avg_profit'] == 0:
            improvement_pct = 0.0
        else:
            improvement_pct = ((treatment_metrics['avg_profit'] - control_metrics['avg_profit']) 
                             / abs(control_metrics['avg_profit']) * 100)
        
        # Check deployment criteria
        should_deploy = (
            stat_test.is_significant and
            improvement_pct > 10.0 and
            control_metrics['sample_size'] >= 100 and
            treatment_metrics['sample_size'] >= 100
        )
        
        if should_deploy:
            reason = f"Treatment shows {improvement_pct:.1f}% improvement with p={stat_test.p_value:.4f}"
        elif not stat_test.is_significant:
            reason = f"Not statistically significant (p={stat_test.p_value:.4f})"
        elif improvement_pct <= 10.0:
            reason = f"Improvement ({improvement_pct:.1f}%) below 10% threshold"
        else:
            reason = "Unknown reason"
        
        confidence_level = (1 - stat_test.p_value) * 100 if stat_test.is_significant else 0.0
        
        return DeploymentRecommendation(
            should_deploy=should_deploy,
            reason=reason,
            performance_improvement_pct=improvement_pct,
            confidence_level=confidence_level
        )
    
    def generate_comparison_report(
        self,
        experiment_name: str
    ) -> ComparisonReport:
        """
        Generate detailed comparison report with visualizations.
        
        Args:
            experiment_name: Name of experiment
            
        Returns:
            ComparisonReport with detailed analysis
            
        Requirement: 15.7
        """
        # Find experiment
        experiment = None
        for exp in self.active_experiments.values():
            if exp.name == experiment_name:
                experiment = exp
                break
        
        if not experiment:
            raise ValueError(f"Experiment '{experiment_name}' not found")
        
        # Calculate metrics
        metrics = self.calculate_metrics(experiment_name)
        
        # Generate summary
        summary_lines = [
            f"Experiment: {experiment.name}",
            f"Description: {experiment.description}",
            f"Status: {experiment.status}",
            f"Started: {experiment.start_date.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Variant Performance:"
        ]
        
        for variant_name, variant_metrics in metrics.variant_metrics.items():
            summary_lines.extend([
                f"  {variant_name}:",
                f"    Sample Size: {variant_metrics.sample_size}",
                f"    Win Rate: {variant_metrics.win_rate:.2f}%",
                f"    Avg Profit: ${variant_metrics.avg_profit:.2f}",
                f"    Confidence Accuracy: {variant_metrics.confidence_accuracy:.2f}%",
                f"    Total PnL: ${variant_metrics.total_pnl:.2f}",
                ""
            ])
        
        summary_lines.extend([
            f"Statistical Test: {metrics.statistical_test.test_type}",
            f"P-Value: {metrics.statistical_test.p_value:.4f}",
            f"Significant: {metrics.statistical_test.is_significant}",
            "",
            "Deployment Recommendation:",
            f"  Should Deploy: {metrics.recommendation.should_deploy}",
            f"  Reason: {metrics.recommendation.reason}",
            f"  Improvement: {metrics.recommendation.performance_improvement_pct:.2f}%",
            f"  Confidence: {metrics.recommendation.confidence_level:.2f}%"
        ])
        
        summary = "\n".join(summary_lines)
        
        # Placeholder for charts (would integrate with matplotlib/plotly)
        charts = {
            "win_rate_comparison": "Chart data placeholder",
            "avg_profit_comparison": "Chart data placeholder",
            "pnl_distribution": "Chart data placeholder"
        }
        
        return ComparisonReport(
            experiment=experiment,
            metrics=metrics,
            charts=charts,
            summary=summary
        )
    
    def end_experiment(self, experiment_name: str):
        """
        End an active experiment.
        
        Args:
            experiment_name: Name of experiment to end
        """
        # Find experiment
        experiment = None
        for exp in self.active_experiments.values():
            if exp.name == experiment_name:
                experiment = exp
                break
        
        if not experiment:
            raise ValueError(f"Experiment '{experiment_name}' not found")
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE experiments
            SET status = 'COMPLETED', end_date = ?
            WHERE experiment_id = ?
        """, (datetime.now().isoformat(), experiment.experiment_id))
        
        conn.commit()
        conn.close()
        
        # Remove from active experiments
        del self.active_experiments[experiment.experiment_id]
    
    def list_experiments(self, status: Optional[str] = None) -> List[Experiment]:
        """
        List all experiments, optionally filtered by status.
        
        Args:
            status: Optional status filter (ACTIVE, COMPLETED, CANCELLED)
            
        Returns:
            List of experiments
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT experiment_id, name, description, variants_json,
                       start_date, end_date, status
                FROM experiments
                WHERE status = ?
                ORDER BY start_date DESC
            """, (status,))
        else:
            cursor.execute("""
                SELECT experiment_id, name, description, variants_json,
                       start_date, end_date, status
                FROM experiments
                ORDER BY start_date DESC
            """)
        
        experiments = []
        for row in cursor.fetchall():
            experiment = Experiment(
                experiment_id=row['experiment_id'],
                name=row['name'],
                description=row['description'],
                variants=json.loads(row['variants_json']),
                start_date=datetime.fromisoformat(row['start_date']),
                end_date=datetime.fromisoformat(row['end_date']) if row['end_date'] else None,
                status=row['status']
            )
            experiments.append(experiment)
        
        conn.close()
        return experiments
