"""
Unit tests for QualityAnalysisService

Tests quality grade performance analysis including:
- Win rate calculation per quality grade
- Average PnL calculation per quality grade
- Trade count per quality grade
- Average confidence per quality grade
- Scatter plot data generation
- Calibration warning detection
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timezone

from api.services.quality_analysis_service import QualityAnalysisService
from storage.database import Database


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    db = Database(db_path=path)
    
    yield db
    
    # Cleanup
    db.close_connection()
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def quality_service(temp_db):
    """Create QualityAnalysisService with test database"""
    return QualityAnalysisService(database=temp_db)


def insert_test_signal(db: Database, signal_id: str, quality: str, confidence: float):
    """Helper to insert a test signal"""
    conn = db._get_conn()
    now = datetime.now(timezone.utc).isoformat()
    
    conn.execute("""
        INSERT INTO signals
        (signal_id, symbol, signal_type, quality, steps_confirmed, confidence,
         entry_price, sl_price, tp_price, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        signal_id, "BTCUSDT", "LONG", quality, 4, confidence,
        50000.0, 49000.0, 52000.0, now, now
    ))
    conn.commit()


def insert_test_outcome(db: Database, signal_id: str, outcome: str, pnl_pct: float):
    """Helper to insert a test signal outcome"""
    conn = db._get_conn()
    now = datetime.now(timezone.utc).isoformat()
    
    conn.execute("""
        INSERT INTO signal_outcomes
        (signal_id, outcome, pnl_pct, closed_at, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (signal_id, outcome, pnl_pct, now, now))
    conn.commit()


def test_quality_analysis_empty_database(quality_service):
    """Test quality analysis with empty database"""
    result = quality_service.get_quality_analysis()
    
    assert result["qualityMetrics"] == []
    assert result["scatterData"] == []
    assert result["calibrationWarnings"] == []


def test_quality_analysis_single_grade(temp_db, quality_service):
    """Test quality analysis with trades from single quality grade"""
    # Insert signals and outcomes for A+ grade
    for i in range(10):
        signal_id = f"SIG-A+-{i}"
        insert_test_signal(temp_db, signal_id, "A+", 85.0)
        
        # 7 wins, 3 losses (70% win rate)
        outcome = "WIN" if i < 7 else "LOSS"
        pnl_pct = 2.5 if outcome == "WIN" else -1.5
        insert_test_outcome(temp_db, signal_id, outcome, pnl_pct)
    
    result = quality_service.get_quality_analysis()
    
    # Check quality metrics
    assert len(result["qualityMetrics"]) == 4  # All 4 grades included
    
    a_plus_metrics = next(m for m in result["qualityMetrics"] if m["quality"] == "A+")
    assert a_plus_metrics["totalTrades"] == 10
    assert a_plus_metrics["winRate"] == 70.0
    assert a_plus_metrics["avgConfidence"] == 85.0
    assert a_plus_metrics["totalPnL"] == 7 * 2.5 + 3 * (-1.5)  # 13.0
    
    # Check scatter data (only includes grades with trades)
    assert len(result["scatterData"]) == 1
    a_plus_scatter = result["scatterData"][0]
    assert a_plus_scatter["quality"] == "A+"
    assert a_plus_scatter["confidence"] == 85.0
    assert a_plus_scatter["winRate"] == 70.0
    assert a_plus_scatter["tradeCount"] == 10
    
    # Check calibration warnings (should have low sample size warning for 10 trades)
    assert len(result["calibrationWarnings"]) == 1
    assert result["calibrationWarnings"][0]["quality"] == "A+"
    assert result["calibrationWarnings"][0]["severity"] == "info"
    assert "Low sample size" in result["calibrationWarnings"][0]["message"]


def test_quality_analysis_all_grades(temp_db, quality_service):
    """Test quality analysis with trades from all quality grades"""
    # A+ grade: 20 trades, 70% win rate
    for i in range(20):
        signal_id = f"SIG-A+-{i}"
        insert_test_signal(temp_db, signal_id, "A+", 85.0)
        outcome = "WIN" if i < 14 else "LOSS"
        pnl_pct = 2.5 if outcome == "WIN" else -1.5
        insert_test_outcome(temp_db, signal_id, outcome, pnl_pct)
    
    # A grade: 30 trades, 65% win rate
    for i in range(30):
        signal_id = f"SIG-A-{i}"
        insert_test_signal(temp_db, signal_id, "A", 75.0)
        outcome = "WIN" if i < 19 else "LOSS"  # 19/30 ≈ 63.33%
        pnl_pct = 2.0 if outcome == "WIN" else -1.2
        insert_test_outcome(temp_db, signal_id, outcome, pnl_pct)
    
    # B grade: 25 trades, 60% win rate
    for i in range(25):
        signal_id = f"SIG-B-{i}"
        insert_test_signal(temp_db, signal_id, "B", 65.0)
        outcome = "WIN" if i < 15 else "LOSS"
        pnl_pct = 1.5 if outcome == "WIN" else -1.0
        insert_test_outcome(temp_db, signal_id, outcome, pnl_pct)
    
    # C grade: 15 trades, 55% win rate
    for i in range(15):
        signal_id = f"SIG-C-{i}"
        insert_test_signal(temp_db, signal_id, "C", 55.0)
        outcome = "WIN" if i < 8 else "LOSS"  # 8/15 ≈ 53.33%
        pnl_pct = 1.0 if outcome == "WIN" else -0.8
        insert_test_outcome(temp_db, signal_id, outcome, pnl_pct)
    
    result = quality_service.get_quality_analysis()
    
    # Check all quality grades are present
    assert len(result["qualityMetrics"]) == 4
    
    # Verify A+ metrics
    a_plus = next(m for m in result["qualityMetrics"] if m["quality"] == "A+")
    assert a_plus["totalTrades"] == 20
    assert a_plus["winRate"] == 70.0
    assert a_plus["avgConfidence"] == 85.0
    
    # Verify A metrics
    a_grade = next(m for m in result["qualityMetrics"] if m["quality"] == "A")
    assert a_grade["totalTrades"] == 30
    assert abs(a_grade["winRate"] - 63.33) < 0.1
    assert a_grade["avgConfidence"] == 75.0
    
    # Verify B metrics
    b_grade = next(m for m in result["qualityMetrics"] if m["quality"] == "B")
    assert b_grade["totalTrades"] == 25
    assert b_grade["winRate"] == 60.0
    assert b_grade["avgConfidence"] == 65.0
    
    # Verify C metrics
    c_grade = next(m for m in result["qualityMetrics"] if m["quality"] == "C")
    assert c_grade["totalTrades"] == 15
    assert abs(c_grade["winRate"] - 53.33) < 0.1
    assert c_grade["avgConfidence"] == 55.0
    
    # Check scatter data
    assert len(result["scatterData"]) == 4
    
    # Check calibration warnings (C grade should have low sample size warning)
    assert len(result["calibrationWarnings"]) == 1
    assert result["calibrationWarnings"][0]["quality"] == "C"
    assert result["calibrationWarnings"][0]["severity"] == "info"
    assert "Low sample size" in result["calibrationWarnings"][0]["message"]


def test_calibration_warning_below_expected(temp_db, quality_service):
    """Test calibration warning when win rate is significantly below expected"""
    # A+ grade with 40% win rate (expected: 65-75%)
    for i in range(30):
        signal_id = f"SIG-A+-{i}"
        insert_test_signal(temp_db, signal_id, "A+", 85.0)
        outcome = "WIN" if i < 12 else "LOSS"  # 12/30 = 40%
        pnl_pct = 2.5 if outcome == "WIN" else -1.5
        insert_test_outcome(temp_db, signal_id, outcome, pnl_pct)
    
    result = quality_service.get_quality_analysis()
    
    # Should have calibration warning
    assert len(result["calibrationWarnings"]) == 1
    warning = result["calibrationWarnings"][0]
    assert warning["quality"] == "A+"
    assert warning["severity"] == "warning"
    assert "below expected" in warning["message"]
    assert warning["actualWinRate"] == 40.0
    assert warning["expectedRange"] == "65-75%"


def test_calibration_warning_above_expected(temp_db, quality_service):
    """Test calibration warning when win rate is significantly above expected"""
    # C grade with 85% win rate (expected: 50-60%)
    for i in range(30):
        signal_id = f"SIG-C-{i}"
        insert_test_signal(temp_db, signal_id, "C", 55.0)
        outcome = "WIN" if i < 25 else "LOSS"  # 25/30 ≈ 83.33%
        pnl_pct = 1.0 if outcome == "WIN" else -0.8
        insert_test_outcome(temp_db, signal_id, outcome, pnl_pct)
    
    result = quality_service.get_quality_analysis()
    
    # Should have calibration warning
    assert len(result["calibrationWarnings"]) == 1
    warning = result["calibrationWarnings"][0]
    assert warning["quality"] == "C"
    assert warning["severity"] == "info"
    assert "above expected" in warning["message"]


def test_service_status(temp_db, quality_service):
    """Test service status reporting"""
    # Empty database
    status = quality_service.get_service_status()
    assert status["initialized"] == True
    assert status["quality_count"] == 0
    assert status["trade_count"] == 0
    assert status["has_data"] == False
    
    # Add some trades
    for i in range(5):
        signal_id = f"SIG-A-{i}"
        insert_test_signal(temp_db, signal_id, "A", 75.0)
        insert_test_outcome(temp_db, signal_id, "WIN", 2.0)
    
    status = quality_service.get_service_status()
    assert status["initialized"] == True
    assert status["quality_count"] == 1  # Only A grade
    assert status["trade_count"] == 5
    assert status["has_data"] == True


def test_pnl_calculation(temp_db, quality_service):
    """Test PnL calculation accuracy"""
    # Insert trades with known PnL values
    trades = [
        ("SIG-1", "A+", 85.0, "WIN", 5.0),
        ("SIG-2", "A+", 85.0, "WIN", 3.0),
        ("SIG-3", "A+", 85.0, "LOSS", -2.0),
        ("SIG-4", "A+", 85.0, "WIN", 4.0),
        ("SIG-5", "A+", 85.0, "LOSS", -1.5),
    ]
    
    for signal_id, quality, confidence, outcome, pnl in trades:
        insert_test_signal(temp_db, signal_id, quality, confidence)
        insert_test_outcome(temp_db, signal_id, outcome, pnl)
    
    result = quality_service.get_quality_analysis()
    
    a_plus = next(m for m in result["qualityMetrics"] if m["quality"] == "A+")
    
    # Total PnL: 5.0 + 3.0 - 2.0 + 4.0 - 1.5 = 8.5
    assert a_plus["totalPnL"] == 8.5
    
    # Average PnL: 8.5 / 5 = 1.7
    assert a_plus["avgPnL"] == 1.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
