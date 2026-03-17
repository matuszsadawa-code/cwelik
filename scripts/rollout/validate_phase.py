#!/usr/bin/env python3
"""
Validate phase deployment by analyzing performance metrics.
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from storage.database import Database

class PhaseValidator:
    def __init__(self, db: Database):
        self.db = db
    
    def validate_phase(self, phase: int, days: int = 7) -> Dict:
        """
        Validate phase performance over specified days.
        
        Returns validation report with pass/fail status.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get metrics for validation period
        metrics = self.get_phase_metrics(phase, start_date, end_date)
        
        # Get baseline metrics (before deployment)
        baseline = self.get_baseline_metrics(start_date - timedelta(days=days), start_date)
        
        # Validate against success criteria
        validation_results = self.check_success_criteria(phase, metrics, baseline)
        
        return {
            "phase": phase,
            "validation_period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "metrics": metrics,
            "baseline": baseline,
            "validation_results": validation_results,
            "overall_status": "PASS" if all(v["passed"] for v in validation_results.values()) else "FAIL",
        }
    
    def get_phase_metrics(self, phase: int, start_date: datetime, end_date: datetime) -> Dict:
        """Get metrics for phase validation period."""
        query = """
            SELECT 
                COUNT(*) as total_signals,
                AVG(CASE WHEN outcome = 'TP' THEN 1.0 ELSE 0.0 END) * 100 as win_rate,
                AVG(confidence) as avg_confidence,
                AVG(pnl_pct) as avg_pnl_pct,
                AVG(rr_achieved) as avg_rr
            FROM signals
            WHERE created_at BETWEEN ? AND ?
        """
        result = self.db.execute(query, (start_date, end_date)).fetchone()
        
        if result:
            return {
                "total_signals": result[0] or 0,
                "win_rate": result[1] or 0,
                "avg_confidence": result[2] or 0,
                "avg_pnl_pct": result[3] or 0,
                "avg_rr": result[4] or 0,
            }
        
        return {
            "total_signals": 0,
            "win_rate": 0,
            "avg_confidence": 0,
            "avg_pnl_pct": 0,
            "avg_rr": 0,
        }

    def get_baseline_metrics(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get baseline metrics before deployment."""
        return self.get_phase_metrics(0, start_date, end_date)
    
    def check_success_criteria(self, phase: int, metrics: Dict, baseline: Dict) -> Dict:
        """Check phase-specific success criteria."""
        criteria = {
            1: {
                "win_rate_maintained": {
                    "check": abs(metrics["win_rate"] - baseline["win_rate"]) <= 5,
                    "message": f"Win rate: {metrics['win_rate']:.1f}% vs baseline {baseline['win_rate']:.1f}%",
                },
                "min_signals": {
                    "check": metrics["total_signals"] >= 50,
                    "message": f"Signals generated: {metrics['total_signals']} (min 50)",
                },
            },
            2: {
                "win_rate_improved": {
                    "check": metrics["win_rate"] >= baseline["win_rate"] - 2,
                    "message": f"Win rate: {metrics['win_rate']:.1f}% vs baseline {baseline['win_rate']:.1f}%",
                },
                "min_signals": {
                    "check": metrics["total_signals"] >= 100,
                    "message": f"Signals generated: {metrics['total_signals']} (min 100)",
                },
            },
            3: {
                "rr_improved": {
                    "check": metrics["avg_rr"] >= baseline["avg_rr"] * 1.10,
                    "message": f"Avg R:R: {metrics['avg_rr']:.2f} vs baseline {baseline['avg_rr']:.2f} (target +10%)",
                },
                "min_signals": {
                    "check": metrics["total_signals"] >= 150,
                    "message": f"Signals generated: {metrics['total_signals']} (min 150)",
                },
            },
            4: {
                "win_rate_improved": {
                    "check": metrics["win_rate"] >= baseline["win_rate"] * 1.05,
                    "message": f"Win rate: {metrics['win_rate']:.1f}% vs baseline {baseline['win_rate']:.1f}% (target +5%)",
                },
                "rr_improved": {
                    "check": metrics["avg_rr"] >= baseline["avg_rr"] * 1.15,
                    "message": f"Avg R:R: {metrics['avg_rr']:.2f} vs baseline {baseline['avg_rr']:.2f} (target +15%)",
                },
                "min_signals": {
                    "check": metrics["total_signals"] >= 200,
                    "message": f"Signals generated: {metrics['total_signals']} (min 200)",
                },
            },
        }
        
        phase_criteria = criteria.get(phase, criteria[1])
        
        results = {}
        for criterion_name, criterion in phase_criteria.items():
            results[criterion_name] = {
                "passed": criterion["check"],
                "message": criterion["message"],
            }
        
        return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_phase.py <phase> [--days 7]")
        print("  phase: 1-4")
        print("  --days: validation period (default: 7)")
        sys.exit(1)
    
    try:
        phase = int(sys.argv[1])
    except ValueError:
        print("Error: Phase must be a number (1-4)")
        sys.exit(1)
    
    if phase not in [1, 2, 3, 4]:
        print(f"Error: Invalid phase {phase}. Must be 1-4.")
        sys.exit(1)
    
    days = 7
    if "--days" in sys.argv:
        try:
            days = int(sys.argv[sys.argv.index("--days") + 1])
        except (ValueError, IndexError):
            print("Error: Invalid --days value")
            sys.exit(1)
    
    db = Database()
    validator = PhaseValidator(db)
    
    report = validator.validate_phase(phase, days)
    
    print(f"\n{'='*60}")
    print(f"PHASE {phase} VALIDATION REPORT")
    print(f"{'='*60}")
    print(f"Period: {report['validation_period']}")
    print(f"Overall Status: {report['overall_status']}")
    print(f"\nSuccess Criteria:")
    for criterion, result in report['validation_results'].items():
        status = "✅ PASS" if result['passed'] else "❌ FAIL"
        print(f"  {status} - {criterion}: {result['message']}")
    print(f"{'='*60}\n")
