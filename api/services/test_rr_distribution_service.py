"""
Unit tests for RRDistributionService

Tests R:R distribution analysis including:
- Grouping trades into R:R buckets
- Calculating average and median R:R
- Comparing actual vs. target distribution
- Warning detection when average R:R < 1.0
"""

import pytest
import sqlite3
from datetime import datetime, timedelta
from api.services.rr_distribution_service import RRDistributionService
from storage.database import Database


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing"""
    db_path = tmp_path / "test_rr_distribution.db"
    db = Database(str(db_path))
    # Database.__init__ already creates all tables with correct schema
    yield db
    db.close_connection()


@pytest.fixture
def rr_service(temp_db):
    """Create RRDistributionService instance with temp database"""
    return RRDistributionService(temp_db)


def test_rr_distribution_empty_database(rr_service):
    """Test R:R distribution with empty database"""
    result = rr_service.get_rr_distribution()
    
    assert result["totalTrades"] == 0
    assert result["avgRR"] == 0.0
    assert result["medianRR"] == 0.0
    assert all(count == 0 for count in result["buckets"].values())
    assert all(pct == 0.0 for pct in result["percentages"].values())
    assert result["warning"] is None


def test_rr_distribution_single_bucket(temp_db, rr_service):
    """Test R:R distribution with trades in single bucket"""
    conn = temp_db._get_conn()
    
    # Insert signal
    conn.execute("""
        INSERT INTO signals (signal_id, symbol, signal_type, entry_price, sl_price, tp_price, quality, confidence, created_at)
        VALUES ('sig1', 'BTCUSDT', 'LONG', 50000, 49500, 51000, 'A', 75.0, ?)
    """, (datetime.now().isoformat(), datetime.now().isoformat()))
    
    # Insert 5 outcomes in 1.0-1.5 bucket
    for i in range(5):
        conn.execute("""
            INSERT INTO signal_outcomes (signal_id, outcome, exit_price, exit_reason, pnl_pct, rr_achieved, duration_minutes, closed_at, created_at)
            VALUES (?, 'WIN', 50600, 'TP', 1.2, 1.2, 120, ?, ?)
        """, (f'sig1', (datetime.now() - timedelta(days=i)).isoformat(), datetime.now().isoformat()))
    
    conn.commit()
    
    result = rr_service.get_rr_distribution()
    
    assert result["totalTrades"] == 5
    assert result["avgRR"] == 1.2
    assert result["medianRR"] == 1.2
    assert result["buckets"]["1.0-1.5"] == 5
    assert result["percentages"]["1.0-1.5"] == 100.0
    assert result["warning"] is None


def test_rr_distribution_all_buckets(temp_db, rr_service):
    """Test R:R distribution with trades across all buckets"""
    conn = temp_db._get_conn()
    
    # Insert signal
    conn.execute("""
        INSERT INTO signals (signal_id, symbol, signal_type, entry_price, sl_price, tp_price, quality, confidence, created_at)
        VALUES ('sig1', 'BTCUSDT', 'LONG', 50000, 49500, 51000, 'A', 75.0, ?)
    """, (datetime.now().isoformat(), datetime.now().isoformat()))
    
    # Insert trades in each bucket
    test_data = [
        (0.3, "<0.5"),      # Very poor
        (0.7, "0.5-1.0"),   # Below target
        (1.2, "1.0-1.5"),   # Acceptable
        (1.8, "1.5-2.0"),   # Good
        (2.5, ">2.0"),      # Excellent
    ]
    
    for rr_value, expected_bucket in test_data:
        conn.execute("""
            INSERT INTO signal_outcomes (signal_id, outcome, exit_price, exit_reason, pnl_pct, rr_achieved, duration_minutes, closed_at, created_at)
            VALUES ('sig1', 'WIN', 50600, 'TP', 1.2, ?, 120, ?, ?)
        """, (rr_value, datetime.now().isoformat(), datetime.now().isoformat()))
    
    conn.commit()
    
    result = rr_service.get_rr_distribution()
    
    assert result["totalTrades"] == 5
    assert result["buckets"]["<0.5"] == 1
    assert result["buckets"]["0.5-1.0"] == 1
    assert result["buckets"]["1.0-1.5"] == 1
    assert result["buckets"]["1.5-2.0"] == 1
    assert result["buckets"][">2.0"] == 1
    assert result["percentages"]["<0.5"] == 20.0
    assert result["percentages"]["0.5-1.0"] == 20.0
    assert result["percentages"]["1.0-1.5"] == 20.0
    assert result["percentages"]["1.5-2.0"] == 20.0
    assert result["percentages"][">2.0"] == 20.0


def test_rr_distribution_average_calculation(temp_db, rr_service):
    """Test average R:R calculation accuracy"""
    conn = temp_db._get_conn()
    
    # Insert signal
    conn.execute("""
        INSERT INTO signals (signal_id, symbol, signal_type, entry_price, sl_price, tp_price, quality, confidence, created_at)
        VALUES ('sig1', 'BTCUSDT', 'LONG', 50000, 49500, 51000, 'A', 75.0, ?)
    """, (datetime.now().isoformat(), datetime.now().isoformat()))
    
    # Insert trades with known R:R values: 0.5, 1.0, 1.5, 2.0, 2.5
    # Average should be 1.5
    rr_values = [0.5, 1.0, 1.5, 2.0, 2.5]
    
    for rr_value in rr_values:
        conn.execute("""
            INSERT INTO signal_outcomes (signal_id, outcome, exit_price, exit_reason, pnl_pct, rr_achieved, duration_minutes, closed_at, created_at)
            VALUES ('sig1', 'WIN', 50600, 'TP', 1.2, ?, 120, ?, ?)
        """, (rr_value, datetime.now().isoformat(), datetime.now().isoformat()))
    
    conn.commit()
    
    result = rr_service.get_rr_distribution()
    
    assert result["totalTrades"] == 5
    assert result["avgRR"] == 1.5
    assert result["medianRR"] == 1.5


def test_rr_distribution_median_calculation(temp_db, rr_service):
    """Test median R:R calculation with odd and even number of trades"""
    conn = temp_db._get_conn()
    
    # Insert signal
    conn.execute("""
        INSERT INTO signals (signal_id, symbol, signal_type, entry_price, sl_price, tp_price, quality, confidence, created_at)
        VALUES ('sig1', 'BTCUSDT', 'LONG', 50000, 49500, 51000, 'A', 75.0, ?)
    """, (datetime.now().isoformat(), datetime.now().isoformat()))
    
    # Insert trades with R:R values: 0.5, 1.0, 1.5, 2.0, 3.0
    # Median should be 1.5 (middle value)
    rr_values = [0.5, 1.0, 1.5, 2.0, 3.0]
    
    for rr_value in rr_values:
        conn.execute("""
            INSERT INTO signal_outcomes (signal_id, outcome, exit_price, exit_reason, pnl_pct, rr_achieved, duration_minutes, closed_at, created_at)
            VALUES ('sig1', 'WIN', 50600, 'TP', 1.2, ?, 120, ?, ?)
        """, (rr_value, datetime.now().isoformat(), datetime.now().isoformat()))
    
    conn.commit()
    
    result = rr_service.get_rr_distribution()
    
    assert result["totalTrades"] == 5
    assert result["medianRR"] == 1.5


def test_rr_distribution_warning_below_one(temp_db, rr_service):
    """Test warning generation when average R:R < 1.0"""
    conn = temp_db._get_conn()
    
    # Insert signal
    conn.execute("""
        INSERT INTO signals (signal_id, symbol, signal_type, entry_price, sl_price, tp_price, quality, confidence, created_at)
        VALUES ('sig1', 'BTCUSDT', 'LONG', 50000, 49500, 51000, 'A', 75.0, ?)
    """, (datetime.now().isoformat(), datetime.now().isoformat()))
    
    # Insert trades with low R:R values (average = 0.6)
    rr_values = [0.3, 0.5, 0.7, 0.8, 0.7]
    
    for rr_value in rr_values:
        conn.execute("""
            INSERT INTO signal_outcomes (signal_id, outcome, exit_price, exit_reason, pnl_pct, rr_achieved, duration_minutes, closed_at, created_at)
            VALUES ('sig1', 'LOSS', 49700, 'SL', -0.6, ?, 60, ?, ?)
        """, (rr_value, datetime.now().isoformat(), datetime.now().isoformat()))
    
    conn.commit()
    
    result = rr_service.get_rr_distribution()
    
    assert result["totalTrades"] == 5
    assert result["avgRR"] == 0.6
    assert result["warning"] is not None
    assert result["warning"]["severity"] == "warning"
    assert "below 1.0" in result["warning"]["message"]
    assert result["warning"]["avgRR"] == 0.6
    assert "recommendation" in result["warning"]


def test_rr_distribution_no_warning_above_one(temp_db, rr_service):
    """Test no warning when average R:R >= 1.0"""
    conn = temp_db._get_conn()
    
    # Insert signal
    conn.execute("""
        INSERT INTO signals (signal_id, symbol, signal_type, entry_price, sl_price, tp_price, quality, confidence, created_at)
        VALUES ('sig1', 'BTCUSDT', 'LONG', 50000, 49500, 51000, 'A', 75.0, ?)
    """, (datetime.now().isoformat(), datetime.now().isoformat()))
    
    # Insert trades with good R:R values (average = 1.5)
    rr_values = [1.2, 1.5, 1.8, 1.6, 1.4]
    
    for rr_value in rr_values:
        conn.execute("""
            INSERT INTO signal_outcomes (signal_id, outcome, exit_price, exit_reason, pnl_pct, rr_achieved, duration_minutes, closed_at, created_at)
            VALUES ('sig1', 'WIN', 50800, 'TP', 1.6, ?, 120, ?, ?)
        """, (rr_value, datetime.now().isoformat(), datetime.now().isoformat()))
    
    conn.commit()
    
    result = rr_service.get_rr_distribution()
    
    assert result["totalTrades"] == 5
    assert result["avgRR"] == 1.5
    assert result["warning"] is None


def test_rr_distribution_bucket_boundaries(temp_db, rr_service):
    """Test correct bucket assignment at boundaries"""
    conn = temp_db._get_conn()
    
    # Insert signal
    conn.execute("""
        INSERT INTO signals (signal_id, symbol, signal_type, entry_price, sl_price, tp_price, quality, confidence, created_at)
        VALUES ('sig1', 'BTCUSDT', 'LONG', 50000, 49500, 51000, 'A', 75.0, ?)
    """, (datetime.now().isoformat(), datetime.now().isoformat()))
    
    # Test boundary values
    boundary_tests = [
        (0.5, "0.5-1.0"),   # Exactly 0.5 should go to 0.5-1.0
        (1.0, "1.0-1.5"),   # Exactly 1.0 should go to 1.0-1.5
        (1.5, "1.5-2.0"),   # Exactly 1.5 should go to 1.5-2.0
        (2.0, ">2.0"),      # Exactly 2.0 should go to >2.0
    ]
    
    for rr_value, expected_bucket in boundary_tests:
        conn.execute("""
            INSERT INTO signal_outcomes (signal_id, outcome, exit_price, exit_reason, pnl_pct, rr_achieved, duration_minutes, closed_at, created_at)
            VALUES ('sig1', 'WIN', 50600, 'TP', 1.2, ?, 120, ?, ?)
        """, (rr_value, datetime.now().isoformat(), datetime.now().isoformat()))
    
    conn.commit()
    
    result = rr_service.get_rr_distribution()
    
    assert result["totalTrades"] == 4
    assert result["buckets"]["0.5-1.0"] == 1
    assert result["buckets"]["1.0-1.5"] == 1
    assert result["buckets"]["1.5-2.0"] == 1
    assert result["buckets"][">2.0"] == 1


def test_service_status(temp_db, rr_service):
    """Test service status reporting"""
    # Empty database
    status = rr_service.get_service_status()
    assert status["initialized"] is True
    assert status["trade_count"] == 0
    assert status["has_data"] is False
    
    # Add some data
    conn = temp_db._get_conn()
    conn.execute("""
        INSERT INTO signals (signal_id, symbol, signal_type, entry_price, sl_price, tp_price, quality, confidence, created_at)
        VALUES ('sig1', 'BTCUSDT', 'LONG', 50000, 49500, 51000, 'A', 75.0, ?)
    """, (datetime.now().isoformat(), datetime.now().isoformat()))
    
    conn.execute("""
        INSERT INTO signal_outcomes (signal_id, outcome, exit_price, exit_reason, pnl_pct, rr_achieved, duration_minutes, closed_at, created_at)
        VALUES ('sig1', 'WIN', 50600, 'TP', 1.2, 1.5, 120, ?, ?)
    """, (datetime.now().isoformat(), datetime.now().isoformat()))
    
    conn.commit()
    
    status = rr_service.get_service_status()
    assert status["initialized"] is True
    assert status["trade_count"] == 1
    assert status["has_data"] is True


def test_target_distribution_included(rr_service):
    """Test that target distribution is included in response"""
    result = rr_service.get_rr_distribution()
    
    assert "targetDistribution" in result
    assert result["targetDistribution"]["<0.5"] == 15.0
    assert result["targetDistribution"]["0.5-1.0"] == 20.0
    assert result["targetDistribution"]["1.0-1.5"] == 30.0
    assert result["targetDistribution"]["1.5-2.0"] == 25.0
    assert result["targetDistribution"][">2.0"] == 10.0


def test_percentage_calculation_accuracy(temp_db, rr_service):
    """Test percentage calculation accuracy"""
    conn = temp_db._get_conn()
    
    # Insert signal
    conn.execute("""
        INSERT INTO signals (signal_id, symbol, signal_type, entry_price, sl_price, tp_price, quality, confidence, created_at)
        VALUES ('sig1', 'BTCUSDT', 'LONG', 50000, 49500, 51000, 'A', 75.0, ?)
    """, (datetime.now().isoformat(), datetime.now().isoformat()))
    
    # Insert 100 trades: 10 in each bucket
    for bucket_idx in range(5):
        for i in range(10):
            if bucket_idx == 0:
                rr_value = 0.3
            elif bucket_idx == 1:
                rr_value = 0.7
            elif bucket_idx == 2:
                rr_value = 1.2
            elif bucket_idx == 3:
                rr_value = 1.7
            else:
                rr_value = 2.5
            
            conn.execute("""
                INSERT INTO signal_outcomes (signal_id, outcome, exit_price, exit_reason, pnl_pct, rr_achieved, duration_minutes, closed_at, created_at)
                VALUES ('sig1', 'WIN', 50600, 'TP', 1.2, ?, 120, ?, ?)
            """, (rr_value, datetime.now().isoformat(), datetime.now().isoformat()))
    
    conn.commit()
    
    result = rr_service.get_rr_distribution()
    
    assert result["totalTrades"] == 50
    # Each bucket should have exactly 10% (10 out of 50 trades)
    assert result["percentages"]["<0.5"] == 20.0
    assert result["percentages"]["0.5-1.0"] == 20.0
    assert result["percentages"]["1.0-1.5"] == 20.0
    assert result["percentages"]["1.5-2.0"] == 20.0
    assert result["percentages"][">2.0"] == 20.0
