"""
Unit tests for TradeJournalService

Tests trade history retrieval with pagination, filtering, and sorting.
"""

import pytest
import sqlite3
from datetime import datetime, timedelta
from api.services.trade_journal_service import TradeJournalService
from storage.database import Database


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database with sample data"""
    db_path = tmp_path / "test_trades.db"
    db = Database(str(db_path))
    
    # Insert sample signals
    signals = [
        {
            "signal_id": "SIG-001",
            "symbol": "BTCUSDT",
            "signal_type": "LONG",
            "quality": "A+",
            "steps_confirmed": 4,
            "confidence": 85.5,
            "entry_price": 50000.0,
            "sl_price": 49000.0,
            "tp_price": 52000.0,
            "sl_distance_pct": 2.0,
            "rr_ratio": 2.0,
            "market_regime": "TRENDING",
            "reasoning": "Strong uptrend with volume confirmation"
        },
        {
            "signal_id": "SIG-002",
            "symbol": "ETHUSDT",
            "signal_type": "SHORT",
            "quality": "A",
            "steps_confirmed": 4,
            "confidence": 75.0,
            "entry_price": 3000.0,
            "sl_price": 3100.0,
            "tp_price": 2800.0,
            "sl_distance_pct": 3.33,
            "rr_ratio": 2.0,
            "market_regime": "RANGING",
            "reasoning": "Resistance rejection with bearish orderflow"
        },
        {
            "signal_id": "SIG-003",
            "symbol": "BTCUSDT",
            "signal_type": "LONG",
            "quality": "B",
            "steps_confirmed": 3,
            "confidence": 65.0,
            "entry_price": 51000.0,
            "sl_price": 50500.0,
            "tp_price": 52000.0,
            "sl_distance_pct": 0.98,
            "rr_ratio": 2.0,
            "market_regime": "VOLATILE",
            "reasoning": "Breakout attempt"
        }
    ]
    
    for signal in signals:
        db.save_signal(signal)
    
    # Insert sample outcomes
    now = datetime.utcnow()
    outcomes = [
        {
            "signal_id": "SIG-001",
            "outcome": "WIN",
            "exit_price": 52000.0,
            "exit_reason": "TP hit",
            "pnl_pct": 4.0,
            "rr_achieved": 2.0,
            "tp_hit": 1,
            "sl_hit": 0,
            "max_favorable": 4.5,
            "max_adverse": -0.5,
            "duration_minutes": 120,
            "closed_at": (now - timedelta(days=2)).isoformat()
        },
        {
            "signal_id": "SIG-002",
            "outcome": "LOSS",
            "exit_price": 3100.0,
            "exit_reason": "SL hit",
            "pnl_pct": -3.33,
            "rr_achieved": -1.0,
            "tp_hit": 0,
            "sl_hit": 1,
            "max_favorable": 1.0,
            "max_adverse": -3.33,
            "duration_minutes": 60,
            "closed_at": (now - timedelta(days=1)).isoformat()
        },
        {
            "signal_id": "SIG-003",
            "outcome": "WIN",
            "exit_price": 52000.0,
            "exit_reason": "TP hit",
            "pnl_pct": 1.96,
            "rr_achieved": 2.0,
            "tp_hit": 1,
            "sl_hit": 0,
            "max_favorable": 2.0,
            "max_adverse": -0.3,
            "duration_minutes": 90,
            "closed_at": now.isoformat()
        }
    ]
    
    for outcome in outcomes:
        db.save_outcome(outcome)
    
    return db


def test_get_trade_history_basic(test_db):
    """Test basic trade history retrieval"""
    service = TradeJournalService(test_db)
    
    result = service.get_trade_history(page=1, page_size=10)
    
    assert "trades" in result
    assert "pagination" in result
    assert len(result["trades"]) == 3
    assert result["pagination"]["totalTrades"] == 3
    assert result["pagination"]["totalPages"] == 1


def test_get_trade_history_pagination(test_db):
    """Test pagination"""
    service = TradeJournalService(test_db)
    
    # Page 1 with page_size=2
    result = service.get_trade_history(page=1, page_size=2)
    
    assert len(result["trades"]) == 2
    assert result["pagination"]["totalTrades"] == 3
    assert result["pagination"]["totalPages"] == 2
    assert result["pagination"]["page"] == 1
    
    # Page 2 with page_size=2
    result = service.get_trade_history(page=2, page_size=2)
    
    assert len(result["trades"]) == 1
    assert result["pagination"]["page"] == 2


def test_get_trade_history_filter_by_symbol(test_db):
    """Test filtering by symbol"""
    service = TradeJournalService(test_db)
    
    result = service.get_trade_history(symbol="BTCUSDT")
    
    assert len(result["trades"]) == 2
    assert all(trade["symbol"] == "BTCUSDT" for trade in result["trades"])


def test_get_trade_history_filter_by_outcome(test_db):
    """Test filtering by outcome"""
    service = TradeJournalService(test_db)
    
    # Filter for wins
    result = service.get_trade_history(outcome="WIN")
    assert len(result["trades"]) == 2
    assert all(trade["outcome"] == "WIN" for trade in result["trades"])
    
    # Filter for losses
    result = service.get_trade_history(outcome="LOSS")
    assert len(result["trades"]) == 1
    assert all(trade["outcome"] == "LOSS" for trade in result["trades"])


def test_get_trade_history_filter_by_quality(test_db):
    """Test filtering by quality grade"""
    service = TradeJournalService(test_db)
    
    result = service.get_trade_history(quality="A+")
    
    assert len(result["trades"]) == 1
    assert result["trades"][0]["quality"] == "A+"


def test_get_trade_history_sort_by_pnl(test_db):
    """Test sorting by PnL"""
    service = TradeJournalService(test_db)
    
    # Sort descending (best first)
    result = service.get_trade_history(sort_by="pnl", sort_order="desc")
    
    assert len(result["trades"]) == 3
    assert result["trades"][0]["pnl"] >= result["trades"][1]["pnl"]
    assert result["trades"][1]["pnl"] >= result["trades"][2]["pnl"]
    
    # Sort ascending (worst first)
    result = service.get_trade_history(sort_by="pnl", sort_order="asc")
    
    assert result["trades"][0]["pnl"] <= result["trades"][1]["pnl"]
    assert result["trades"][1]["pnl"] <= result["trades"][2]["pnl"]


def test_get_trade_history_sort_by_duration(test_db):
    """Test sorting by duration"""
    service = TradeJournalService(test_db)
    
    result = service.get_trade_history(sort_by="duration", sort_order="desc")
    
    assert len(result["trades"]) == 3
    assert result["trades"][0]["duration"] >= result["trades"][1]["duration"]


def test_get_trade_history_combined_filters(test_db):
    """Test combining multiple filters"""
    service = TradeJournalService(test_db)
    
    result = service.get_trade_history(
        symbol="BTCUSDT",
        outcome="WIN",
        sort_by="pnl",
        sort_order="desc"
    )
    
    assert len(result["trades"]) == 2
    assert all(trade["symbol"] == "BTCUSDT" for trade in result["trades"])
    assert all(trade["outcome"] == "WIN" for trade in result["trades"])
    assert result["trades"][0]["pnl"] >= result["trades"][1]["pnl"]


def test_get_trade_detail(test_db):
    """Test retrieving detailed trade information"""
    service = TradeJournalService(test_db)
    
    # Get trade ID from history
    history = service.get_trade_history(page=1, page_size=1)
    trade_id = history["trades"][0]["tradeId"]
    
    # Get detailed trade info
    detail = service.get_trade_detail(trade_id)
    
    assert detail is not None
    assert "tradeId" in detail
    assert "signalId" in detail
    assert "featureContributions" in detail
    assert "step1Data" in detail
    assert "step2Data" in detail
    assert "step3Data" in detail
    assert "step4Data" in detail


def test_get_trade_detail_not_found(test_db):
    """Test retrieving non-existent trade"""
    service = TradeJournalService(test_db)
    
    detail = service.get_trade_detail("99999")
    
    assert detail is None


def test_get_service_status(test_db):
    """Test service status retrieval"""
    service = TradeJournalService(test_db)
    
    status = service.get_service_status()
    
    assert status["initialized"] is True
    assert status["total_trades"] == 3
    assert status["has_data"] is True
    assert status["earliest_trade"] is not None
    assert status["latest_trade"] is not None


def test_empty_database(tmp_path):
    """Test service with empty database"""
    db_path = tmp_path / "empty.db"
    db = Database(str(db_path))
    service = TradeJournalService(db)
    
    result = service.get_trade_history()
    
    assert len(result["trades"]) == 0
    assert result["pagination"]["totalTrades"] == 0
    assert result["pagination"]["totalPages"] == 0
    
    # Close database connection to avoid Windows file locking issues
    db.close_connection()


def test_trade_data_formatting(test_db):
    """Test that trade data is properly formatted for frontend"""
    service = TradeJournalService(test_db)
    
    result = service.get_trade_history(page=1, page_size=1)
    trade = result["trades"][0]
    
    # Check all required fields are present
    required_fields = [
        "tradeId", "signalId", "symbol", "direction", "quality", "confidence",
        "entryPrice", "exitPrice", "stopLoss", "takeProfit", "pnl", "outcome",
        "rrAchieved", "mfe", "mae", "duration", "entryTime", "exitTime",
        "entryReason", "exitReason", "tpHit", "slHit", "marketRegime"
    ]
    
    for field in required_fields:
        assert field in trade, f"Missing field: {field}"
    
    # Check numeric fields are rounded
    assert isinstance(trade["pnl"], (int, float))
    assert isinstance(trade["confidence"], (int, float))
    assert isinstance(trade["entryPrice"], (int, float))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
