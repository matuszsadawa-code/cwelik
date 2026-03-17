"""
A/B Testing Experiments API Routes

Provides endpoints for retrieving A/B test experiment results and managing experiments.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Path

from api.services.ab_testing_service import ABTestingService
from api.utils.database import get_database

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/experiments", tags=["experiments"])

# Initialize service
ab_testing_service = None


def init_ab_testing_service():
    """Initialize A/B testing service with database connection"""
    global ab_testing_service
    db = get_database()
    ab_testing_service = ABTestingService(db)
    logger.info("A/B testing service initialized")


@router.get("")
async def list_experiments(
    status: Optional[str] = Query(None, description="Filter by status (running, completed, stopped, all)")
):
    """
    List A/B test experiments with optional status filter.
    
    Retrieves all experiments or filters by status (running, completed, stopped).
    Returns summary information including current results and sample sizes.
    
    Args:
        status: Filter by status (running, completed, stopped, all). If not specified, returns all.
        
    Returns:
        dict: Experiments list including:
            - experiments: List of experiment summaries with:
                - id: Experiment ID
                - name: Experiment name
                - description: Experiment description
                - status: Status (running, completed, stopped)
                - start_date: Start timestamp
                - end_date: End timestamp (if completed/stopped)
                - control_group_size: Number of signals in control group
                - treatment_group_size: Number of signals in treatment group
                - primary_metric: Primary metric being tested
                - current_result: Current metric values (control vs treatment, difference, significant)
            - total: Total number of experiments
    
    Example:
        GET /api/experiments?status=running
    """
    if not ab_testing_service:
        init_ab_testing_service()
    
    try:
        # Validate status parameter
        if status and status not in ["running", "completed", "stopped", "all"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid status parameter. Must be 'running', 'completed', 'stopped', or 'all'"
            )
        
        experiments = ab_testing_service.list_experiments(status=status)
        
        return {
            "experiments": experiments,
            "total": len(experiments)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing experiments: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{experiment_id}")
async def get_experiment_results(
    experiment_id: str = Path(..., description="Experiment ID")
):
    """
    Get detailed results for a specific A/B test experiment.
    
    Retrieves comprehensive experiment results including control/treatment metrics,
    statistical significance analysis, and confidence intervals.
    
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
            - control_metrics: Control group metrics (win_rate, avg_pnl, avg_rr, total_trades)
            - treatment_metrics: Treatment group metrics
            - comparison: Metric comparison with differences and percent changes
            - statistical_significance: Statistical test results (p-value, z-score, significant flag)
            - confidence_intervals: Confidence intervals for metric differences
            - sample_sizes: Sample sizes for control and treatment groups
    
    Example:
        GET /api/experiments/vsa_feature_test
    """
    if not ab_testing_service:
        init_ab_testing_service()
    
    try:
        results = ab_testing_service.get_experiment_results(experiment_id)
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment not found: {experiment_id}"
            )
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving experiment results: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/{experiment_id}/stop")
async def stop_experiment(
    experiment_id: str = Path(..., description="Experiment ID"),
    reason: str = Query("Manual stop", description="Reason for stopping the experiment")
):
    """
    Stop an A/B test experiment early.
    
    Stops a running experiment and marks it as stopped. Returns final results.
    Useful when results are conclusive before planned end date or when issues are detected.
    
    Args:
        experiment_id: Experiment ID
        reason: Reason for stopping (default: "Manual stop")
        
    Returns:
        dict: Stop result including:
            - success: Whether stop was successful
            - message: Status message
            - final_results: Final experiment results (same format as GET /{experiment_id})
    
    Example:
        POST /api/experiments/vsa_feature_test/stop?reason=Results+conclusive
    """
    if not ab_testing_service:
        init_ab_testing_service()
    
    try:
        result = ab_testing_service.stop_experiment(experiment_id, reason)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("message", "Failed to stop experiment")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping experiment: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/status")
async def get_service_status():
    """
    Get A/B testing service status.
    
    Returns service health information including total experiment count,
    running experiments, and data availability status.
    
    Returns:
        dict: Service status including:
            - initialized: Whether service is initialized
            - experiments_dir: Directory containing experiment configurations
            - total_experiments: Total number of experiments
            - running_experiments: Number of currently running experiments
            - has_data: Whether any experiment data is available
    """
    if not ab_testing_service:
        init_ab_testing_service()
    
    try:
        return ab_testing_service.get_service_status()
    except Exception as e:
        logger.error(f"Error getting service status: {e}", exc_info=True)
        return {
            "initialized": False,
            "total_experiments": 0,
            "running_experiments": 0,
            "has_data": False,
            "error": str(e)
        }
