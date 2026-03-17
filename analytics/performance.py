"""
Performance Reporter — Comprehensive trading analytics.

Generates detailed performance reports from signal outcomes:
- Win rate, R:R, PnL summaries
- Per-quality breakdown (A+, A, B, C)
- Per-symbol analysis
- Step-by-step confirmation accuracy
"""

from typing import Dict, List, Optional
from datetime import datetime

from storage.database import Database
from utils.logger import get_logger

log = get_logger("analytics.performance")


class PerformanceReporter:
    """Generates performance reports and analytics."""

    def __init__(self, db: Database):
        self.db = db

    def get_summary(self, days: int = 30) -> str:
        """Get a formatted performance summary string."""
        stats = self.db.get_performance_stats(days)

        if not stats or stats.get("total_signals", 0) == 0:
            return "[STATS] No signals generated yet. Waiting for market data..."

        wins = stats.get("wins") or 0
        losses = stats.get("losses") or 0
        total_outcomes = wins + losses
        win_rate = stats.get("win_rate") or 0
        avg_rr = stats.get("avg_rr") or 0
        total_pnl = stats.get("total_pnl", 0) or 0

        report = []
        report.append("=" * 50)
        report.append(f"[STATS] PERFORMANCE REPORT (Last {days} Days)")
        report.append("=" * 50)
        report.append("")

        # --- Overview -------------------------------------
        report.append("-- Overview -------------------------")
        report.append(f"  Total Signals:     {stats.get('total_signals', 0)}")
        report.append(f"  Resolved Trades:   {total_outcomes}")
        report.append(f"  Open Signals:      {stats.get('total_signals', 0) - total_outcomes}")
        report.append("")

        # --- Win/Loss -------------------------------------
        if total_outcomes > 0:
            report.append("-- Win/Loss -------------------------")
            report.append(f"  Wins:              {wins}")
            report.append(f"  Losses:            {losses}")
            report.append(f"  Win Rate:          {win_rate:.1f}%")
            report.append(f"  Avg R:R Achieved:  {avg_rr:.2f}:1")
            report.append(f"  Total PnL:         {total_pnl:+.2f}%")
            report.append(f"  Best Trade:        {stats.get('best_trade', 0) or 0:+.2f}%")
            report.append(f"  Worst Trade:       {stats.get('worst_trade', 0) or 0:+.2f}%")
            report.append(f"  Avg PnL/Trade:     {stats.get('avg_pnl', 0) or 0:+.3f}%")
            report.append("")

        # --- Quality Breakdown ----------------------------
        report.append("-- Signal Quality -------------------")
        report.append(f"  A+ (4/4):          {stats.get('a_plus', 0)}")
        report.append(f"  A  (3/4):          {stats.get('a_count', 0)}")
        report.append(f"  B  (2/4):          {stats.get('b_count', 0)}")
        report.append(f"  C  (1/4):          {stats.get('c_count', 0)}")
        report.append("")

        # --- Expectancy -----------------------------------
        if total_outcomes > 0 and win_rate > 0:
            avg_win = total_pnl / wins if wins > 0 else 0
            avg_loss = abs(total_pnl / losses) if losses > 0 else 0
            expectancy = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * avg_loss)
            report.append("-- Expectancy -----------------------")
            report.append(f"  Per-Trade Expect:  {expectancy:+.3f}%")
            if avg_rr > 0:
                kelly = (win_rate / 100) - ((1 - win_rate / 100) / avg_rr)
                report.append(f"  Kelly Criterion:   {kelly:.1%}")
            report.append("")

        report.append("=" * 50)
        return "\n".join(report)

    def get_per_symbol_stats(self, days: int = 30) -> Dict[str, Dict]:
        """Get performance breakdown per symbol."""
        signals = self.db.get_recent_signals(limit=1000)
        stats = {}

        for sig in signals:
            symbol = sig["symbol"]
            if symbol not in stats:
                stats[symbol] = {
                    "total": 0, "a_plus": 0, "a": 0, "b": 0, "c": 0,
                    "longs": 0, "shorts": 0,
                }
            stats[symbol]["total"] += 1
            q = sig["quality"]
            if q == "A+":
                stats[symbol]["a_plus"] += 1
            elif q == "A":
                stats[symbol]["a"] += 1
            elif q == "B":
                stats[symbol]["b"] += 1
            elif q == "C":
                stats[symbol]["c"] += 1

            if sig["signal_type"] == "LONG":
                stats[symbol]["longs"] += 1
            else:
                stats[symbol]["shorts"] += 1

        return stats

    def print_summary(self, days: int = 30):
        """Print summary to console and log."""
        summary = self.get_summary(days)
        print(summary)
        log.info("Performance report generated")
