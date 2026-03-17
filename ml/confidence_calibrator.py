"""
Machine Learning Signal Confidence Calibration

Calibrates confidence scores using Isotonic Regression to ensure predicted
probabilities match actual outcomes. Addresses overconfidence/underconfidence
in signal predictions.

Requirements: 10.1-10.8
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Tuple
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss

from storage.database import Database
from utils.logger import get_logger

log = get_logger("ml.calibrator")


@dataclass
class CalibrationSample:
    """Training sample for calibration model."""
    predicted_confidence: float  # 0-100
    actual_outcome: bool  # True if TP hit, False if SL hit
    signal_id: str
    timestamp: datetime


@dataclass
class CalibrationCurve:
    """Calibration curve data for visualization."""
    predicted_bins: List[float]  # Binned predicted probabilities
    actual_frequencies: List[float]  # Actual success rate per bin
    sample_counts: List[int]  # Samples per bin
    brier_score: float


class MLConfidenceCalibrator:
    """
    ML-based confidence calibration using Isotonic Regression.
    
    Collects historical (predicted_confidence, actual_outcome) pairs from database,
    trains calibration model, and adjusts raw confidence scores to match reality.
    
    Auto-retrains every 1000 signals to adapt to changing market conditions.
    """
    
    def __init__(self, db: Database, config: Optional[Dict] = None):
        """
        Initialize ML confidence calibrator.
        
        Args:
            db: Database instance for accessing historical signals
            config: Optional configuration overrides
        """
        self.db = db
        self.config = config or self._default_config()
        
        self.model: Optional[IsotonicRegression] = None
        self.training_data: List[CalibrationSample] = []
        self.last_train_time: Optional[datetime] = None
        self.last_train_sample_count: int = 0
        
        log.info("MLConfidenceCalibrator initialized")
    
    def _default_config(self) -> Dict:
        """Default configuration for calibration."""
        return {
            "min_samples_for_training": 100,
            "retrain_interval_signals": 1000,
            "calibration_method": "isotonic",
            "confidence_bins": 10,
            "max_adjustment_pct": 20,
        }
    
    def collect_training_data(self) -> List[CalibrationSample]:
        """
        Collect historical signals with outcomes from database.
        
        Queries signals that have outcomes (TP or SL hit) and extracts:
        - predicted_confidence: Original confidence score
        - actual_outcome: True if TP hit, False if SL hit
        
        Returns:
            List of CalibrationSample objects
        """
        try:
            conn = self.db._get_conn()
            
            # Query signals with outcomes
            rows = conn.execute("""
                SELECT 
                    s.signal_id,
                    s.confidence as predicted_confidence,
                    o.tp_hit,
                    o.sl_hit,
                    o.closed_at
                FROM signals s
                INNER JOIN signal_outcomes o ON s.signal_id = o.signal_id
                WHERE o.tp_hit IS NOT NULL AND o.sl_hit IS NOT NULL
                ORDER BY o.closed_at ASC
            """).fetchall()
            
            samples = []
            for row in rows:
                # Determine actual outcome: True if TP hit, False if SL hit
                actual_outcome = bool(row['tp_hit'])
                
                sample = CalibrationSample(
                    predicted_confidence=float(row['predicted_confidence']),
                    actual_outcome=actual_outcome,
                    signal_id=row['signal_id'],
                    timestamp=datetime.fromisoformat(row['closed_at'])
                )
                samples.append(sample)
            
            log.info(f"Collected {len(samples)} calibration samples from database")
            return samples
            
        except Exception as e:
            log.error(f"Failed to collect training data: {e}")
            return []
    
    def train_model(self):
        """
        Train calibration model using Isotonic Regression.
        
        Isotonic Regression learns a monotonic mapping from raw confidence
        to calibrated probability that matches actual win rates.
        
        Requires minimum samples as specified in config.
        """
        # Collect fresh training data
        self.training_data = self.collect_training_data()
        
        if len(self.training_data) < self.config["min_samples_for_training"]:
            log.warning(
                f"Insufficient samples for training: {len(self.training_data)} < "
                f"{self.config['min_samples_for_training']}"
            )
            return
        
        try:
            # Prepare training arrays
            X = np.array([s.predicted_confidence / 100.0 for s in self.training_data])
            y = np.array([1.0 if s.actual_outcome else 0.0 for s in self.training_data])
            
            # Train Isotonic Regression model
            self.model = IsotonicRegression(out_of_bounds='clip')
            self.model.fit(X, y)
            
            self.last_train_time = datetime.utcnow()
            self.last_train_sample_count = len(self.training_data)
            
            # Calculate Brier score for model quality
            brier = self.calculate_brier_score()
            
            log.info(
                f"Model trained on {len(self.training_data)} samples. "
                f"Brier Score: {brier:.4f}"
            )
            
            # Save training samples to database for tracking
            self._save_training_samples()
            
        except Exception as e:
            log.error(f"Failed to train calibration model: {e}")
    
    def calibrate_confidence(self, raw_confidence: float) -> float:
        """
        Apply calibration to raw confidence score.
        
        Args:
            raw_confidence: 0-100 raw confidence from signal engine
            
        Returns:
            Calibrated confidence (0-100) matching actual win probability
        """
        if self.model is None:
            log.debug("No calibration model available, returning raw confidence")
            return raw_confidence
        
        try:
            # Convert to 0-1 scale
            raw_prob = raw_confidence / 100.0
            
            # Apply calibration
            calibrated_prob = self.model.predict([raw_prob])[0]
            
            # Apply max adjustment limit
            max_adjustment = self.config["max_adjustment_pct"] / 100.0
            adjustment = calibrated_prob - raw_prob
            
            if abs(adjustment) > max_adjustment:
                adjustment = max_adjustment if adjustment > 0 else -max_adjustment
                calibrated_prob = raw_prob + adjustment
            
            # Convert back to 0-100 scale
            calibrated_confidence = calibrated_prob * 100.0
            
            # Ensure bounds
            calibrated_confidence = max(0.0, min(100.0, calibrated_confidence))
            
            log.debug(
                f"Calibrated confidence: {raw_confidence:.1f}% -> "
                f"{calibrated_confidence:.1f}% (Δ{calibrated_confidence - raw_confidence:+.1f}%)"
            )
            
            return calibrated_confidence
            
        except Exception as e:
            log.error(f"Calibration failed: {e}, returning raw confidence")
            return raw_confidence
    
    def calculate_brier_score(self) -> float:
        """
        Calculate Brier Score to evaluate calibration quality.
        
        Brier Score measures the mean squared difference between predicted
        probabilities and actual outcomes. Lower is better (0 = perfect).
        
        Returns:
            Brier Score (0-1, lower is better)
        """
        if self.model is None or not self.training_data:
            return 1.0  # Worst possible score
        
        try:
            X = np.array([s.predicted_confidence / 100.0 for s in self.training_data])
            y_true = np.array([1.0 if s.actual_outcome else 0.0 for s in self.training_data])
            y_pred = self.model.predict(X)
            
            brier = brier_score_loss(y_true, y_pred)
            return float(brier)
            
        except Exception as e:
            log.error(f"Failed to calculate Brier score: {e}")
            return 1.0
    
    def should_retrain(self) -> bool:
        """
        Check if model should be retrained.
        
        Retrains when:
        - No model exists yet
        - 1000+ new signals since last training
        
        Returns:
            True if retraining is needed
        """
        if self.model is None:
            return True
        
        # Count current samples
        current_samples = self.collect_training_data()
        new_samples = len(current_samples) - self.last_train_sample_count
        
        if new_samples >= self.config["retrain_interval_signals"]:
            log.info(
                f"Retraining triggered: {new_samples} new samples since last training"
            )
            return True
        
        return False
    
    def get_calibration_curve(self) -> CalibrationCurve:
        """
        Get calibration curve for visualization.
        
        Bins predicted probabilities and calculates actual success rate per bin.
        
        Returns:
            CalibrationCurve with binned data
        """
        if not self.training_data:
            return CalibrationCurve(
                predicted_bins=[],
                actual_frequencies=[],
                sample_counts=[],
                brier_score=1.0
            )
        
        try:
            num_bins = self.config["confidence_bins"]
            
            # Create bins
            bins = np.linspace(0, 100, num_bins + 1)
            predicted_bins = []
            actual_frequencies = []
            sample_counts = []
            
            for i in range(num_bins):
                bin_start = bins[i]
                bin_end = bins[i + 1]
                bin_center = (bin_start + bin_end) / 2
                
                # Filter samples in this bin
                bin_samples = [
                    s for s in self.training_data
                    if bin_start <= s.predicted_confidence < bin_end
                ]
                
                if bin_samples:
                    # Calculate actual success rate
                    successes = sum(1 for s in bin_samples if s.actual_outcome)
                    frequency = successes / len(bin_samples)
                    
                    predicted_bins.append(bin_center)
                    actual_frequencies.append(frequency * 100)  # Convert to percentage
                    sample_counts.append(len(bin_samples))
            
            brier = self.calculate_brier_score()
            
            return CalibrationCurve(
                predicted_bins=predicted_bins,
                actual_frequencies=actual_frequencies,
                sample_counts=sample_counts,
                brier_score=brier
            )
            
        except Exception as e:
            log.error(f"Failed to generate calibration curve: {e}")
            return CalibrationCurve(
                predicted_bins=[],
                actual_frequencies=[],
                sample_counts=[],
                brier_score=1.0
            )
    
    def _save_training_samples(self):
        """Save training samples to database for tracking."""
        try:
            conn = self.db._get_conn()
            
            for sample in self.training_data:
                conn.execute("""
                    INSERT OR IGNORE INTO calibration_samples
                    (signal_id, predicted_confidence, actual_outcome, timestamp, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    sample.signal_id,
                    sample.predicted_confidence,
                    1 if sample.actual_outcome else 0,
                    sample.timestamp.isoformat(),
                    datetime.utcnow().isoformat()
                ))
            
            conn.commit()
            log.debug(f"Saved {len(self.training_data)} calibration samples to database")
            
        except Exception as e:
            log.error(f"Failed to save training samples: {e}")
    
    def get_calibration_stats(self) -> Dict:
        """
        Get calibration statistics for monitoring.
        
        Returns:
            Dictionary with calibration metrics
        """
        if not self.training_data:
            return {
                "model_trained": False,
                "sample_count": 0,
                "brier_score": None,
                "last_train_time": None
            }
        
        return {
            "model_trained": self.model is not None,
            "sample_count": len(self.training_data),
            "brier_score": self.calculate_brier_score() if self.model else None,
            "last_train_time": self.last_train_time.isoformat() if self.last_train_time else None,
            "next_retrain_samples": self.config["retrain_interval_signals"] - (
                len(self.training_data) - self.last_train_sample_count
            )
        }
