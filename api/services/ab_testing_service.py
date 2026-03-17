"""
A/B Testing Service for OpenClaw Trading Dashboard

Retrieves and manages A/B testing experiment results including control/treatment metrics,
statistical significance calculations, and confidence intervals.

Features:
- List active A/B test experiments
- Retrieve detailed experiment results
- Calculate metrics for control and treatment groups
- Calculate statistical significance (p-value, z-score)
- Calculate confidence intervals for metric differences
- Stop experiments early
"""

import logging
import json
import math
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from storage.database import Database

logger = logging.getLogger(__name__)


class ABTestingService:
    """
    Service for retrieving and managing A/B testing experiment results.
    
    Responsibilities:
    - List active experiments from database/storage
    - Retrieve detailed results for specific experiment
    - Calculate control vs treatment metrics
    - Calculate statistical significance
    - Calculate confidence intervals
    - Stop experiments early
    """
    
    def __init__(self, database: Database = None, experiments_dir: str = "testing/experiments"):
        """
        Initialize A/B testing service.
        
        Args:
            database: Database instance (creates new if None)
            experiments_dir: Directory containing experiment configuration files
        """
        self.database = database or Database()
        self.experiments_dir = experiments_dir
        
        # Ensure experiments directory exists
        Path(experiments_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ABTestingService initialized with directory: {experiments_dir}")
    
    def list_experiments(self, status: Optional[str] = None) -> List[Dict]:
        """
        List A/B test experiments with optional status filter.
        
        Args:
            status: Filter by status (running, completed, stopped, all)
            
        Returns:
            list: List of experiment summaries including:
                - id: Experiment ID
                - name: Experiment name
                - description: Experiment description
                - status: Status (running, completed, stopped)
                - start_date: Start timestamp
                - end_date: End timestamp (if completed/stopped)
                - control_group_size: Number of signals in control group
                - treatment_group_size: Number of signals in treatment group
                - primary_metric: Primary metric being tested
                - current_result: Current metric values (control vs treatment)
        """
        try:
            experiments = []
            
            # Scan experiments directory for configuration files
            experiments_path = Path(self.experiments_dir)
            
            if not experiments_path.exists():
                logger.warning(f"Experiments directory does not exist: {self.experiments_dir}")
                return []
            
            # Look for JSON experiment files
            for exp_file in experiments_path.glob("*.json"):
                try:
                    with open(exp_file, 'r') as f:
                        exp_data = json.load(f)
                    
                    exp_status = exp_data.get("status", "running")
                    
                    # Apply status filter
                    if status and status != "all" and exp_status != status:
                        continue
                    
                    # Get current results from database
                    exp_id = exp_file.stem
                    results = self._get_experiment_results_from_db(exp_id)
                    
                    summary = {
                        "id": exp_id,
                        "name": exp_data.get("name", exp_id),
                        "description": exp_data.get("description", ""),
                        "status": exp_status,
                        "start_date": exp_data.get("start_date"),
                        "end_date": exp_data.get("end_date"),
                        "control_group_size": results.get("control_size", 0),
                        "treatment_group_size": results.get("treatment_size", 0),
                        "primary_metric": exp_data.get("primary_metric", "win_rate"),
                        "current_result": {
                            "control": results.get("control_metrics", {}).get(exp_data.get("primary_metric", "win_rate"), 0),
                            "treatment": results.get("treatment_metrics", {}).get(exp_data.get("primary_metric", "win_rate"), 0),
                            "difference": results.get("difference", 0),
                            "significant": results.get("significant", False)
                        }
                    }
                    
                    experiments.append(summary)
                    
                except Exception as e:
                    logger.error(f"Error reading experiment file {exp_file}: {e}")
                    continue
            
            # Sort by start date (most recent first)
            experiments.sort(key=lambda x: x.get("start_date", ""), reverse=True)
            
            logger.info(f"Found {len(experiments)} experiments")
            return experiments
            
        except Exception as e:
            logger.error(f"Error listing experiments: {e}", exc_info=True)
            return []
    
    def get_experiment_results(self, experiment_id: str) -> Optional[Dict]:
        """
        Get detailed results for a specific A/B test experiment.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            dict: Detailed experiment results including:
                - id: Experiment ID
                - name: Experiment name
                - description: Experiment description
                - status: Status (running, completed, stopped)
                - start_date: Start timestamp
                - end_date: End timestamp
                - config: Experiment configuration
                - control_metrics: Control group metrics
                - treatment_metrics: Treatment group metrics
                - comparison: Metric comparison with differences
                - statistical_significance: Statistical test results
                - confidence_intervals: Confidence intervals for differences
                - sample_sizes: Sample sizes for each group
        """
        try:
            exp_file = Path(self.experiments_dir) / f"{experiment_id}.json"
            
            if not exp_file.exists():
                logger.warning(f"Experiment not found: {experiment_id}")
                return None
            
            with open(exp_file, 'r') as f:
                exp_data = json.load(f)
            
            # Get results from database
            results = self._get_experiment_results_from_db(experiment_id)
            
            # Calculate statistical significance
            significance = self._calculate_statistical_significance(
                results["control_metrics"],
                results["treatment_metrics"],
                results["control_size"],
                results["treatment_size"],
                exp_data.get("primary_metric", "win_rate")
            )
            
            # Calculate confidence intervals
            confidence_intervals = self._calculate_confidence_intervals(
                results["control_metrics"],
                results["treatment_metrics"],
                results["control_size"],
                results["treatment_size"]
            )
            
            return {
                "id": experiment_id,
                "name": exp_data.get("name", experiment_id),
                "description": exp_data.get("description", ""),
                "status": exp_data.get("status", "running"),
                "start_date": exp_data.get("start_date"),
                "end_date": exp_data.get("end_date"),
                "config": exp_data.get("config", {}),
                "control_metrics": results["control_metrics"],
                "treatment_metrics": results["treatment_metrics"],
                "comparison": self._compare_metrics(
                    results["control_metrics"],
                    results["treatment_metrics"]
                ),
                "statistical_significance": significance,
                "confidence_intervals": confidence_intervals,
                "sample_sizes": {
                    "control": results["control_size"],
                    "treatment": results["treatment_size"]
                }
            }
            
        except Exception as e:
            logger.error(f"Error retrieving experiment results for {experiment_id}: {e}", exc_info=True)
            return None
    
    def stop_experiment(self, experiment_id: str, reason: str = "Manual stop") -> Dict:
        """
        Stop an experiment early.
        
        Args:
            experiment_id: Experiment ID
            reason: Reason for stopping
            
        Returns:
            dict: Stop result including:
                - success: Whether stop was successful
                - message: Status message
                - final_results: Final experiment results
        """
        try:
            exp_file = Path(self.experiments_dir) / f"{experiment_id}.json"
            
            if not exp_file.exists():
                return {
                    "success": False,
                    "message": f"Experiment not found: {experiment_id}"
                }
            
            # Load experiment data
            with open(exp_file, 'r') as f:
                exp_data = json.load(f)
            
            # Check if already stopped
            if exp_data.get("status") in ["completed", "stopped"]:
                return {
                    "success": False,
                    "message": f"Experiment already {exp_data.get('status')}"
                }
            
            # Update status
            exp_data["status"] = "stopped"
            exp_data["end_date"] = datetime.now().isoformat()
            exp_data["stop_reason"] = reason
            
            # Save updated data
            with open(exp_file, 'w') as f:
                json.dump(exp_data, f, indent=2)
            
            # Get final results
            final_results = self.get_experiment_results(experiment_id)
            
            logger.info(f"Stopped experiment {experiment_id}: {reason}")
            
            return {
                "success": True,
                "message": f"Experiment stopped successfully",
                "final_results": final_results
            }
            
        except Exception as e:
            logger.error(f"Error stopping experiment {experiment_id}: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Error stopping experiment: {str(e)}"
            }
    
    def _get_experiment_results_from_db(self, experiment_id: str) -> Dict:
        """
        Get experiment results from database.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            dict: Results including control/treatment metrics and sample sizes
        """
        try:
            conn = self.database._get_conn()
            
            # Query signals for control group
            control_query = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN so.outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                    AVG(so.pnl_pct) as avg_pnl,
                    AVG(so.rr_achieved) as avg_rr
                FROM signals s
                LEFT JOIN signal_outcomes so ON s.signal_id = so.signal_id
                WHERE s.advanced_analytics LIKE ?
                AND so.closed_at IS NOT NULL
            """
            
            control_row = conn.execute(
                control_query,
                (f'%"experiment_id":"{experiment_id}","group":"control"%',)
            ).fetchone()
            
            # Query signals for treatment group
            treatment_row = conn.execute(
                control_query.replace("control", "treatment"),
                (f'%"experiment_id":"{experiment_id}","group":"treatment"%',)
            ).fetchone()
            
            # Calculate metrics
            control_data = dict(control_row) if control_row else {}
            treatment_data = dict(treatment_row) if treatment_row else {}
            
            control_total = control_data.get("total", 0) or 0
            treatment_total = treatment_data.get("total", 0) or 0
            
            control_metrics = {
                "win_rate": (control_data.get("wins", 0) / control_total * 100) if control_total > 0 else 0,
                "avg_pnl": control_data.get("avg_pnl", 0) or 0,
                "avg_rr": control_data.get("avg_rr", 0) or 0,
                "total_trades": control_total
            }
            
            treatment_metrics = {
                "win_rate": (treatment_data.get("wins", 0) / treatment_total * 100) if treatment_total > 0 else 0,
                "avg_pnl": treatment_data.get("avg_pnl", 0) or 0,
                "avg_rr": treatment_data.get("avg_rr", 0) or 0,
                "total_trades": treatment_total
            }
            
            return {
                "control_metrics": control_metrics,
                "treatment_metrics": treatment_metrics,
                "control_size": control_total,
                "treatment_size": treatment_total,
                "difference": treatment_metrics["win_rate"] - control_metrics["win_rate"],
                "significant": False  # Will be calculated properly in get_experiment_results
            }
            
        except Exception as e:
            logger.error(f"Error getting experiment results from database: {e}")
            return {
                "control_metrics": {},
                "treatment_metrics": {},
                "control_size": 0,
                "treatment_size": 0,
                "difference": 0,
                "significant": False
            }
    
    def _compare_metrics(self, control: Dict, treatment: Dict) -> Dict:
        """
        Compare control and treatment metrics.
        
        Args:
            control: Control group metrics
            treatment: Treatment group metrics
            
        Returns:
            dict: Metric comparisons with differences and percent changes
        """
        comparison = {}
        
        for metric in control.keys():
            control_val = control.get(metric, 0)
            treatment_val = treatment.get(metric, 0)
            
            difference = treatment_val - control_val
            pct_change = (difference / control_val * 100) if control_val != 0 else 0
            
            comparison[metric] = {
                "control": round(control_val, 2),
                "treatment": round(treatment_val, 2),
                "difference": round(difference, 2),
                "percent_change": round(pct_change, 2)
            }
        
        return comparison
    
    def _calculate_statistical_significance(
        self,
        control: Dict,
        treatment: Dict,
        control_size: int,
        treatment_size: int,
        primary_metric: str
    ) -> Dict:
        """
        Calculate statistical significance using z-test for proportions.
        
        Args:
            control: Control group metrics
            treatment: Treatment group metrics
            control_size: Control group sample size
            treatment_size: Treatment group sample size
            primary_metric: Primary metric to test
            
        Returns:
            dict: Statistical test results including p-value, z-score, significant flag
        """
        try:
            # Get metric values (convert percentages to proportions)
            p1 = control.get(primary_metric, 0) / 100 if primary_metric == "win_rate" else control.get(primary_metric, 0)
            p2 = treatment.get(primary_metric, 0) / 100 if primary_metric == "win_rate" else treatment.get(primary_metric, 0)
            
            n1 = control_size
            n2 = treatment_size
            
            # Check minimum sample size
            if n1 < 30 or n2 < 30:
                return {
                    "significant": False,
                    "p_value": None,
                    "z_score": None,
                    "message": "Insufficient sample size (minimum 30 per group)"
                }
            
            # Calculate pooled proportion
            p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)
            
            # Calculate standard error
            se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
            
            if se == 0:
                return {
                    "significant": False,
                    "p_value": None,
                    "z_score": None,
                    "message": "Cannot calculate significance (zero standard error)"
                }
            
            # Calculate z-score
            z_score = (p2 - p1) / se
            
            # Calculate p-value (two-tailed test)
            # Using approximation: p-value ≈ 2 * (1 - Φ(|z|))
            # where Φ is the standard normal CDF
            p_value = 2 * (1 - self._normal_cdf(abs(z_score)))
            
            # Determine significance (α = 0.05)
            significant = p_value < 0.05
            
            return {
                "significant": significant,
                "p_value": round(p_value, 4),
                "z_score": round(z_score, 4),
                "alpha": 0.05,
                "message": "Statistically significant" if significant else "Not statistically significant"
            }
            
        except Exception as e:
            logger.error(f"Error calculating statistical significance: {e}")
            return {
                "significant": False,
                "p_value": None,
                "z_score": None,
                "message": f"Error: {str(e)}"
            }
    
    def _calculate_confidence_intervals(
        self,
        control: Dict,
        treatment: Dict,
        control_size: int,
        treatment_size: int,
        confidence_level: float = 0.95
    ) -> Dict:
        """
        Calculate confidence intervals for metric differences.
        
        Args:
            control: Control group metrics
            treatment: Treatment group metrics
            control_size: Control group sample size
            treatment_size: Treatment group sample size
            confidence_level: Confidence level (default 0.95 for 95% CI)
            
        Returns:
            dict: Confidence intervals for each metric
        """
        try:
            # Z-score for 95% confidence interval
            z = 1.96 if confidence_level == 0.95 else 2.576  # 99% CI
            
            intervals = {}
            
            for metric in control.keys():
                p1 = control.get(metric, 0) / 100 if metric == "win_rate" else control.get(metric, 0)
                p2 = treatment.get(metric, 0) / 100 if metric == "win_rate" else treatment.get(metric, 0)
                
                n1 = control_size
                n2 = treatment_size
                
                if n1 < 30 or n2 < 30:
                    intervals[metric] = {
                        "lower": None,
                        "upper": None,
                        "message": "Insufficient sample size"
                    }
                    continue
                
                # Calculate standard error for difference
                se = math.sqrt((p1 * (1 - p1) / n1) + (p2 * (1 - p2) / n2))
                
                # Calculate difference
                diff = p2 - p1
                
                # Calculate confidence interval
                margin = z * se
                lower = diff - margin
                upper = diff + margin
                
                # Convert back to percentage if win_rate
                if metric == "win_rate":
                    lower *= 100
                    upper *= 100
                    diff *= 100
                
                intervals[metric] = {
                    "difference": round(diff, 2),
                    "lower": round(lower, 2),
                    "upper": round(upper, 2),
                    "confidence_level": confidence_level
                }
            
            return intervals
            
        except Exception as e:
            logger.error(f"Error calculating confidence intervals: {e}")
            return {}
    
    def _normal_cdf(self, x: float) -> float:
        """
        Approximate standard normal cumulative distribution function.
        
        Args:
            x: Value
            
        Returns:
            float: CDF value
        """
        # Using error function approximation
        return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0
    
    def get_service_status(self) -> Dict:
        """
        Get service status for health monitoring.
        
        Returns:
            dict: Service status including data availability
        """
        try:
            experiments = self.list_experiments(status="all")
            running = [e for e in experiments if e["status"] == "running"]
            
            return {
                "initialized": True,
                "experiments_dir": self.experiments_dir,
                "total_experiments": len(experiments),
                "running_experiments": len(running),
                "has_data": len(experiments) > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                "initialized": False,
                "total_experiments": 0,
                "running_experiments": 0,
                "has_data": False,
                "error": str(e)
            }
