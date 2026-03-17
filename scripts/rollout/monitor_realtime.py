#!/usr/bin/env python3
"""
Real-time monitoring script for gradual rollout.
Tracks key metrics and alerts on anomalies.
"""

import time
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from storage.database import Database
from config.feature_flags import get_enabled_features

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RolloutMonitor:
    def __init__(self, db: Database):
        self.db = db
        self.alert_thresholds = {
            "win_rate_drop_pct": 10,  # Alert if win rate drops >10%
            "latency_increase_pct": 50,  # Alert if latency increases >50%
            "error_rate_threshold": 5,  # Alert if >5 errors per hour
            "memory_increase_mb": 500,  # Alert if memory increases >500MB
        }
    
    def monitor_phase(self, phase: int, duration_hours: int = 48):
        """Monitor phase deployment for specified duration."""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=duration_hours)
        
        logger.info(f"Starting Phase {phase} monitoring until {end_time}")
        logger.info(f"Monitoring duration: {duration_hours} hours")
        
        # Get baseline metrics
        baseline_metrics = self.get_baseline_metrics()
        logger.info(f"Baseline metrics: Win Rate={baseline_metrics.get('win_rate', 0):.1f}%, "
                   f"Avg Latency={baseline_metrics.get('avg_latency_ms', 0):.0f}ms")
        
        iteration = 0
        
        try:
            while datetime.now() < end_time:
                iteration += 1
                current_metrics = self.get_current_metrics()
                
                # Check for anomalies
                anomalies = self.detect_anomalies(baseline_metrics, current_metrics)
                
                if anomalies:
                    self.send_alerts(phase, anomalies)
                
                # Log status
                self.log_status(phase, iteration, current_metrics)
                
                # Sleep for 5 minutes
                logger.info(f"Next check in 5 minutes... (Ctrl+C to stop)")
                time.sleep(300)
        
        except KeyboardInterrupt:
            logger.info("\nMonitoring stopped by user")
        
        logger.info(f"Phase {phase} monitoring completed")
        return self.generate_monitoring_report(phase, baseline_metrics)
    
    def get_baseline_metrics(self) -> Dict:
        """Get baseline metrics from before deployment (last 7 days)."""
        end_date = datetime.now() - timedelta(days=1)  # Yesterday
        start_date = end_date - timedelta(days=7)  # 7 days before
        
        query = """
            SELECT 
                COUNT(*) as total_signals,
                AVG(CASE WHEN outcome = 'TP' THEN 1.0 ELSE 0.0 END) * 100 as win_rate,
                AVG(confidence) as avg_confidence,
                COUNT(CASE WHEN outcome = 'ERROR' THEN 1 END) as error_count
            FROM signals
            WHERE created_at BETWEEN ? AND ?
        """
        
        try:
            result = self.db.execute(query, (start_date, end_date)).fetchone()
            if result:
                return {
                    "total_signals": result[0] or 0,
                    "win_rate": result[1] or 0,
                    "avg_confidence": result[2] or 0,
                    "error_count": result[3] or 0,
                    "avg_latency_ms": 50,  # Default baseline
                    "errors_per_hour": (result[3] or 0) / (7 * 24),
                }
        except Exception as e:
            logger.warning(f"Could not fetch baseline metrics: {e}")
        
        # Return default baseline if query fails
        return {
            "total_signals": 0,
            "win_rate": 60.0,
            "avg_confidence": 70.0,
            "error_count": 0,
            "avg_latency_ms": 50,
            "errors_per_hour": 0,
        }
    
    def get_current_metrics(self) -> Dict:
        """Get current system metrics (last hour)."""
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=1)
        
        query = """
            SELECT 
                COUNT(*) as total_signals,
                AVG(CASE WHEN outcome = 'TP' THEN 1.0 ELSE 0.0 END) * 100 as win_rate,
                AVG(confidence) as avg_confidence,
                COUNT(CASE WHEN outcome = 'ERROR' THEN 1 END) as error_count
            FROM signals
            WHERE created_at BETWEEN ? AND ?
        """
        
        try:
            result = self.db.execute(query, (start_date, end_date)).fetchone()
            if result:
                return {
                    "signals_count": result[0] or 0,
                    "win_rate": result[1] or 0,
                    "avg_confidence": result[2] or 0,
                    "error_count": result[3] or 0,
                    "avg_latency_ms": 50,  # TODO: Implement actual latency tracking
                    "errors_per_hour": result[3] or 0,
                }
        except Exception as e:
            logger.warning(f"Could not fetch current metrics: {e}")
        
        # Return default if query fails
        return {
            "signals_count": 0,
            "win_rate": 0,
            "avg_confidence": 0,
            "error_count": 0,
            "avg_latency_ms": 50,
            "errors_per_hour": 0,
        }
    
    def detect_anomalies(self, baseline: Dict, current: Dict) -> List[str]:
        """Detect anomalies by comparing current vs baseline."""
        anomalies = []
        
        # Check win rate (only if we have enough signals)
        if current["signals_count"] >= 10:
            win_rate_threshold = baseline["win_rate"] * (1 - self.alert_thresholds["win_rate_drop_pct"] / 100)
            if current["win_rate"] < win_rate_threshold:
                anomalies.append(
                    f"Win rate dropped from {baseline['win_rate']:.1f}% to {current['win_rate']:.1f}% "
                    f"(threshold: {win_rate_threshold:.1f}%)"
                )
        
        # Check latency
        latency_threshold = baseline["avg_latency_ms"] * (1 + self.alert_thresholds["latency_increase_pct"] / 100)
        if current["avg_latency_ms"] > latency_threshold:
            anomalies.append(
                f"Latency increased from {baseline['avg_latency_ms']:.0f}ms to {current['avg_latency_ms']:.0f}ms "
                f"(threshold: {latency_threshold:.0f}ms)"
            )
        
        # Check error rate
        if current["errors_per_hour"] > self.alert_thresholds["error_rate_threshold"]:
            anomalies.append(
                f"Error rate: {current['errors_per_hour']:.1f} errors/hour "
                f"(threshold: {self.alert_thresholds['error_rate_threshold']})"
            )
        
        return anomalies
    
    def send_alerts(self, phase: int, anomalies: List[str]):
        """Send alerts for detected anomalies."""
        logger.warning("="*70)
        logger.warning(f"⚠️  PHASE {phase} ANOMALIES DETECTED:")
        for anomaly in anomalies:
            logger.warning(f"  - {anomaly}")
        logger.warning("="*70)
        
        # TODO: Send email/Slack/SMS alerts
        # Example:
        # send_slack_alert(f"Phase {phase} Anomalies", anomalies)
        # send_email_alert(f"Phase {phase} Anomalies", anomalies)
    
    def log_status(self, phase: int, iteration: int, metrics: Dict):
        """Log current status."""
        logger.info(
            f"[Iteration {iteration}] Phase {phase} Status: "
            f"Signals={metrics['signals_count']}, "
            f"Win Rate={metrics['win_rate']:.1f}%, "
            f"Confidence={metrics['avg_confidence']:.1f}, "
            f"Latency={metrics['avg_latency_ms']:.0f}ms, "
            f"Errors={metrics['error_count']}"
        )
    
    def generate_monitoring_report(self, phase: int, baseline: Dict) -> Dict:
        """Generate monitoring report."""
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=48)
        
        query = """
            SELECT 
                COUNT(*) as total_signals,
                AVG(CASE WHEN outcome = 'TP' THEN 1.0 ELSE 0.0 END) * 100 as win_rate,
                AVG(confidence) as avg_confidence,
                COUNT(CASE WHEN outcome = 'ERROR' THEN 1 END) as error_count
            FROM signals
            WHERE created_at BETWEEN ? AND ?
        """
        
        try:
            result = self.db.execute(query, (start_date, end_date)).fetchone()
            if result:
                report = {
                    "phase": phase,
                    "monitoring_period": f"{start_date} to {end_date}",
                    "total_signals": result[0] or 0,
                    "win_rate": result[1] or 0,
                    "avg_confidence": result[2] or 0,
                    "error_count": result[3] or 0,
                    "baseline_win_rate": baseline["win_rate"],
                    "win_rate_change": (result[1] or 0) - baseline["win_rate"],
                }
                
                logger.info("\n" + "="*70)
                logger.info("MONITORING REPORT")
                logger.info("="*70)
                logger.info(f"Phase: {report['phase']}")
                logger.info(f"Period: {report['monitoring_period']}")
                logger.info(f"Total Signals: {report['total_signals']}")
                logger.info(f"Win Rate: {report['win_rate']:.1f}% (baseline: {report['baseline_win_rate']:.1f}%, change: {report['win_rate_change']:+.1f}%)")
                logger.info(f"Avg Confidence: {report['avg_confidence']:.1f}")
                logger.info(f"Errors: {report['error_count']}")
                logger.info("="*70)
                
                return report
        except Exception as e:
            logger.error(f"Could not generate monitoring report: {e}")
        
        return {"phase": phase, "error": "Could not generate report"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python monitor_realtime.py <phase> [--hours 48]")
        print("  phase: 1-4")
        print("  --hours: monitoring duration (default: 48)")
        sys.exit(1)
    
    try:
        phase = int(sys.argv[1])
    except ValueError:
        print("Error: Phase must be a number (1-4)")
        sys.exit(1)
    
    if phase not in [1, 2, 3, 4]:
        print(f"Error: Invalid phase {phase}. Must be 1-4.")
        sys.exit(1)
    
    # Get duration
    duration_hours = 48
    if "--hours" in sys.argv:
        try:
            duration_hours = int(sys.argv[sys.argv.index("--hours") + 1])
        except (ValueError, IndexError):
            print("Error: Invalid --hours value")
            sys.exit(1)
    
    # Initialize database and monitor
    db = Database()
    monitor = RolloutMonitor(db)
    
    # Show enabled features
    enabled = get_enabled_features()
    logger.info(f"Currently enabled features: {len(enabled)}")
    for feature_name in enabled.keys():
        logger.info(f"  - {feature_name}")
    
    # Start monitoring
    report = monitor.monitor_phase(phase, duration_hours=duration_hours)
