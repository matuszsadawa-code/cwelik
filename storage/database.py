"""
SQLite database for signals, candles, and analytics.
Thread-safe connection pooling for better performance.
Optimized with indexes, caching, and batch operations.
"""

import sqlite3
import json
import threading
from contextlib import contextmanager
from dataclasses import is_dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import config
from utils.logger import get_logger

log = get_logger("storage.db")


class DataclassJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles dataclass objects and datetime objects."""
    
    def default(self, obj):
        """
        Override default method to handle dataclass and datetime serialization.
        
        Converts datetime objects to ISO format strings.
        Converts dataclass objects to dictionaries using asdict(),
        which recursively handles nested dataclasses.
        Falls back to default encoder for non-dataclass, non-datetime objects.
        """
        # Handle datetime objects first (before dataclass conversion)
        if isinstance(obj, datetime):
            return obj.isoformat()
        # Handle dataclass objects
        if is_dataclass(obj):
            return asdict(obj)
        return super().default(obj)


class Database:
    """SQLite database manager with connection pooling."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DATABASE_PATH
        self._local = threading.local()  # Thread-local storage for connections
        self._init_db()
        log.info(f"Database initialized with connection pooling: {db_path}")

    def _get_conn(self) -> sqlite3.Connection:
        """
        Get thread-local connection (connection pooling).
        Each thread gets its own connection that's reused.
        """
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=30.0  # 30 second timeout
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
            self._local.conn.execute("PRAGMA temp_store=MEMORY")
        return self._local.conn
    
    @contextmanager
    def transaction(self):
        """
        Context manager for transactions with automatic commit/rollback.
        
        Usage:
            with db.transaction() as conn:
                conn.execute("INSERT INTO ...")
                conn.execute("UPDATE ...")
        """
        conn = self._get_conn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            log.error(f"Transaction failed, rolled back: {e}")
            raise
    
    def close_connection(self):
        """Close thread-local connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    def _init_db(self):
        """Create all tables."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    quality TEXT NOT NULL,
                    steps_confirmed INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    sl_price REAL NOT NULL,
                    tp_price REAL NOT NULL,
                    sl_distance_pct REAL,
                    rr_ratio REAL,
                    market_regime TEXT,
                    reasoning TEXT,
                    step1_data TEXT,
                    step2_data TEXT,
                    step3_data TEXT,
                    step4_data TEXT,
                    advanced_analytics TEXT,
                    exchange TEXT DEFAULT 'cross',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS signal_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT NOT NULL,
                    outcome TEXT,
                    exit_price REAL,
                    exit_reason TEXT,
                    pnl_pct REAL,
                    rr_achieved REAL,
                    tp_hit INTEGER DEFAULT 0,
                    sl_hit INTEGER DEFAULT 0,
                    max_favorable REAL,
                    max_adverse REAL,
                    duration_minutes INTEGER,
                    price_at_5m REAL,
                    price_at_15m REAL,
                    price_at_30m REAL,
                    price_at_1h REAL,
                    price_at_4h REAL,
                    closed_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (signal_id) REFERENCES signals(signal_id)
                );

                CREATE TABLE IF NOT EXISTS candle_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    open_time INTEGER NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    turnover REAL DEFAULT 0,
                    UNIQUE(symbol, timeframe, exchange, open_time)
                );

                CREATE TABLE IF NOT EXISTS orderbook_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    bid_total REAL,
                    ask_total REAL,
                    imbalance_ratio REAL,
                    spread REAL,
                    best_bid REAL,
                    best_ask REAL,
                    depth_data TEXT
                );

                CREATE TABLE IF NOT EXISTS trade_clusters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    cluster_type TEXT NOT NULL,
                    price REAL NOT NULL,
                    total_volume REAL NOT NULL,
                    trade_count INTEGER NOT NULL,
                    time_start TEXT NOT NULL,
                    time_end TEXT NOT NULL,
                    is_aggressive_buy INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS analytics_daily (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    total_signals INTEGER DEFAULT 0,
                    signals_a_plus INTEGER DEFAULT 0,
                    signals_a INTEGER DEFAULT 0,
                    signals_b INTEGER DEFAULT 0,
                    signals_c INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    avg_rr REAL DEFAULT 0,
                    total_pnl_pct REAL DEFAULT 0,
                    best_trade_pnl REAL DEFAULT 0,
                    worst_trade_pnl REAL DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
                CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);
                CREATE INDEX IF NOT EXISTS idx_signals_quality ON signals(quality);
                CREATE INDEX IF NOT EXISTS idx_signals_regime ON signals(market_regime);
                CREATE INDEX IF NOT EXISTS idx_signals_exchange ON signals(exchange);
                CREATE INDEX IF NOT EXISTS idx_outcomes_signal ON signal_outcomes(signal_id);
                CREATE INDEX IF NOT EXISTS idx_outcomes_outcome ON signal_outcomes(outcome);
                CREATE INDEX IF NOT EXISTS idx_outcomes_closed ON signal_outcomes(closed_at);
                CREATE INDEX IF NOT EXISTS idx_outcomes_created ON signal_outcomes(created_at);
                CREATE INDEX IF NOT EXISTS idx_candles_lookup ON candle_cache(symbol, timeframe, exchange);
                CREATE INDEX IF NOT EXISTS idx_candles_time ON candle_cache(open_time);
                CREATE INDEX IF NOT EXISTS idx_clusters_symbol ON trade_clusters(symbol, created_at);
                CREATE INDEX IF NOT EXISTS idx_orderbook_symbol ON orderbook_snapshots(symbol, timestamp);

                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT UNIQUE NOT NULL,
                    signal_id TEXT,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    leverage INTEGER DEFAULT 10,
                    qty REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    fill_price REAL,
                    sl_price REAL,
                    tp_price REAL,
                    status TEXT NOT NULL,
                    exit_price REAL,
                    exit_reason TEXT,
                    realised_pnl REAL DEFAULT 0,
                    mfe REAL DEFAULT 0,
                    mae REAL DEFAULT 0,
                    tp_hit INTEGER DEFAULT 0,
                    sl_hit INTEGER DEFAULT 0,
                    duration_minutes REAL DEFAULT 0,
                    orders_json TEXT,
                    created_at TEXT NOT NULL,
                    closed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS equity_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    equity REAL NOT NULL,
                    open_positions INTEGER DEFAULT 0,
                    daily_pnl REAL DEFAULT 0,
                    mode TEXT DEFAULT 'paper'
                );

                CREATE INDEX IF NOT EXISTS idx_exec_symbol ON executions(symbol);
                CREATE INDEX IF NOT EXISTS idx_exec_created ON executions(created_at);
                CREATE INDEX IF NOT EXISTS idx_exec_status ON executions(status);
                CREATE INDEX IF NOT EXISTS idx_exec_signal ON executions(signal_id);
                CREATE INDEX IF NOT EXISTS idx_equity_ts ON equity_snapshots(timestamp);
                CREATE INDEX IF NOT EXISTS idx_equity_mode ON equity_snapshots(mode);
            """)
            conn.commit()
        except Exception as e:
            log.error(f"Failed to initialize database: {e}")
            raise

    # ─── Signals ──────────────────────────────────────────────────────────

    def save_signal(self, signal: Dict[str, Any]) -> str:
        """Save a new signal with full analytics context. Returns signal_id."""
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()
        signal_id = signal.get("signal_id", f"SIG-{now.replace(':', '').replace('-', '')}")
        try:
            conn.execute("""
                INSERT OR REPLACE INTO signals
                (signal_id, symbol, signal_type, quality, steps_confirmed, confidence,
                 entry_price, sl_price, tp_price, sl_distance_pct,
                 rr_ratio, market_regime, reasoning,
                 step1_data, step2_data, step3_data, step4_data,
                 advanced_analytics, exchange, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_id, signal["symbol"], signal["signal_type"],
                signal["quality"], signal["steps_confirmed"], signal["confidence"],
                signal["entry_price"], signal["sl_price"],
                signal["tp_price"],
                signal.get("sl_distance_pct"),
                signal.get("rr_ratio"),
                signal.get("market_regime"),
                signal.get("reasoning"),
                json.dumps(signal.get("step1_data"), cls=DataclassJSONEncoder),
                json.dumps(signal.get("step2_data"), cls=DataclassJSONEncoder),
                json.dumps(signal.get("step3_data"), cls=DataclassJSONEncoder),
                json.dumps(signal.get("step4_data"), cls=DataclassJSONEncoder),
                json.dumps(signal.get("advanced_analytics"), cls=DataclassJSONEncoder),
                signal.get("exchange", "cross"),
                now, now,
            ))
            conn.commit()
            return signal_id
        except Exception as e:
            log.error(f"Failed to save signal: {e}")
            raise

    def get_recent_signals(self, limit: int = 20, symbol: Optional[str] = None) -> List[Dict]:
        """Get recent signals, optionally filtered by symbol."""
        conn = self._get_conn()
        # Use selective columns instead of SELECT *
        columns = [
            'signal_id', 'symbol', 'signal_type', 'quality', 'confidence',
            'entry_price', 'sl_price', 'tp_price', 'market_regime', 'created_at',
            'steps_confirmed', 'rr_ratio'
        ]
        columns_str = ', '.join(columns)
        
        if symbol:
            rows = conn.execute(
                f"SELECT {columns_str} FROM signals WHERE symbol = ? ORDER BY created_at DESC LIMIT ?",
                (symbol, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {columns_str} FROM signals ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_open_signals(self) -> List[Dict]:
        """Get signals that haven't been closed yet (no outcome)."""
        conn = self._get_conn()
        # Use selective columns and optimized join
        columns = [
            's.signal_id', 's.symbol', 's.signal_type', 's.quality', 's.confidence',
            's.entry_price', 's.sl_price', 's.tp_price', 's.market_regime', 's.created_at',
            's.steps_confirmed', 's.rr_ratio'
        ]
        columns_str = ', '.join(columns)
        
        rows = conn.execute(f"""
            SELECT {columns_str} FROM signals s
            LEFT JOIN signal_outcomes o ON s.signal_id = o.signal_id
            WHERE o.id IS NULL
            ORDER BY s.created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]

    # ─── Signal Outcomes ──────────────────────────────────────────────────

    def save_outcome(self, outcome: Dict[str, Any]):
        """Save signal outcome."""
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()
        conn.execute("""
            INSERT INTO signal_outcomes
            (signal_id, outcome, exit_price, exit_reason, pnl_pct, rr_achieved,
             tp_hit, sl_hit,
             max_favorable, max_adverse, duration_minutes,
             price_at_5m, price_at_15m, price_at_30m, price_at_1h, price_at_4h,
             closed_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            outcome["signal_id"], outcome.get("outcome"),
            outcome.get("exit_price"), outcome.get("exit_reason"),
            outcome.get("pnl_pct"), outcome.get("rr_achieved"),
            outcome.get("tp_hit", 0), outcome.get("sl_hit", 0),
            outcome.get("max_favorable"), outcome.get("max_adverse"),
            outcome.get("duration_minutes"),
            outcome.get("price_at_5m"), outcome.get("price_at_15m"),
            outcome.get("price_at_30m"), outcome.get("price_at_1h"),
            outcome.get("price_at_4h"),
            outcome.get("closed_at"), now,
        ))
        conn.commit()

    # ─── Candle Cache ─────────────────────────────────────────────────────

    def cache_candles(self, symbol: str, timeframe: str, exchange: str,
                      candles: List[Dict]):
        """Cache candles to database."""
        conn = self._get_conn()
        for c in candles:
            conn.execute("""
                INSERT OR IGNORE INTO candle_cache
                (symbol, timeframe, exchange, open_time, open, high, low, close, volume, turnover)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, timeframe, exchange, c["open_time"],
                c["open"], c["high"], c["low"], c["close"],
                c["volume"], c.get("turnover", 0),
            ))
        conn.commit()

    def get_cached_candles(self, symbol: str, timeframe: str,
                          exchange: str, limit: int = 100) -> List[Dict]:
        """Get cached candles."""
        conn = self._get_conn()
        # Use selective columns
        columns = ['symbol', 'timeframe', 'exchange', 'open_time', 'open', 'high', 'low', 'close', 'volume']
        columns_str = ', '.join(columns)
        
        rows = conn.execute(f"""
            SELECT {columns_str} FROM candle_cache
            WHERE symbol = ? AND timeframe = ? AND exchange = ?
            ORDER BY open_time DESC LIMIT ?
        """, (symbol, timeframe, exchange, limit)).fetchall()
        return [dict(r) for r in reversed(rows)]

    # ─── Analytics ────────────────────────────────────────────────────────

    def get_performance_stats(self, days: int = 30) -> Dict:
        """Get performance statistics for the last N days."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT
                COUNT(*) as total_signals,
                SUM(CASE WHEN quality = 'A+' THEN 1 ELSE 0 END) as a_plus,
                SUM(CASE WHEN quality = 'A' THEN 1 ELSE 0 END) as a_count,
                SUM(CASE WHEN quality = 'B' THEN 1 ELSE 0 END) as b_count,
                SUM(CASE WHEN quality = 'C' THEN 1 ELSE 0 END) as c_count
            FROM signals
            WHERE created_at >= datetime('now', ?)
        """, (f"-{days} days",)).fetchone()

        outcome_row = conn.execute("""
            SELECT
                COUNT(*) as total_outcomes,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
                AVG(pnl_pct) as avg_pnl,
                AVG(rr_achieved) as avg_rr,
                MAX(pnl_pct) as best_trade,
                MIN(pnl_pct) as worst_trade,
                SUM(pnl_pct) as total_pnl
            FROM signal_outcomes
            WHERE created_at >= datetime('now', ?)
        """, (f"-{days} days",)).fetchone()

        stats = dict(row) if row else {}
        if outcome_row:
            stats.update(dict(outcome_row))
            wins = stats.get("wins") or 0
            losses = stats.get("losses") or 0
            total = wins + losses
            stats["win_rate"] = (wins / total * 100) if total > 0 else 0

        return stats

    # ─── Trade Clusters ───────────────────────────────────────────────────

    def save_trade_cluster(self, cluster: Dict):
        """Save a detected trade cluster."""
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()
        conn.execute("""
            INSERT INTO trade_clusters
            (symbol, exchange, cluster_type, price, total_volume, trade_count,
             time_start, time_end, is_aggressive_buy, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cluster["symbol"], cluster["exchange"], cluster["cluster_type"],
            cluster["price"], cluster["total_volume"], cluster["trade_count"],
            cluster["time_start"], cluster["time_end"],
            1 if cluster["is_aggressive_buy"] else 0, now,
        ))
        conn.commit()

    # ─── Executions ──────────────────────────────────────────────────────

    def save_execution(self, execution: Dict[str, Any]):
        """Save an execution result from OrderExecutor."""
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()
        conn.execute("""
            INSERT OR REPLACE INTO executions
            (execution_id, signal_id, symbol, direction, mode, leverage,
             qty, entry_price, fill_price, sl_price, tp_price,
             status, exit_price, exit_reason, realised_pnl, mfe, mae,
             tp_hit, sl_hit, duration_minutes,
             orders_json, created_at, closed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            execution["execution_id"], execution.get("signal_id"),
            execution["symbol"], execution["direction"],
            execution.get("mode", "paper"), execution.get("leverage", 10),
            execution["qty"], execution["entry_price"],
            execution.get("fill_price"), execution.get("sl_price"),
            execution.get("tp_price"), execution["status"],
            execution.get("exit_price"), execution.get("exit_reason"),
            execution.get("realised_pnl", 0),
            execution.get("mfe", 0), execution.get("mae", 0),
            execution.get("tp_hit", 0), execution.get("sl_hit", 0),
            execution.get("duration_minutes", 0),
            json.dumps(execution.get("orders", [])),
            execution.get("created_at", now),
            execution.get("closed_at"),
        ))
        conn.commit()

    def get_executions(self, status: Optional[str] = None,
                       limit: int = 50) -> List[Dict]:
        """Get executions, optionally filtered by status."""
        conn = self._get_conn()
        # Use selective columns
        columns = [
            'execution_id', 'signal_id', 'symbol', 'direction', 'status',
            'entry_price', 'exit_price', 'realised_pnl', 'mfe', 'mae',
            'created_at', 'closed_at', 'duration_minutes'
        ]
        columns_str = ', '.join(columns)
        
        if status:
            rows = conn.execute(
                f"SELECT {columns_str} FROM executions WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {columns_str} FROM executions ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ─── Equity Snapshots ────────────────────────────────────────────────

    def save_equity_snapshot(self, snapshot: Dict[str, Any]):
        """Save equity snapshot for the equity curve."""
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO equity_snapshots
            (timestamp, equity, open_positions, daily_pnl, mode)
            VALUES (?, ?, ?, ?, ?)
        """, (
            snapshot.get("timestamp", datetime.utcnow().isoformat()),
            snapshot["equity"],
            snapshot.get("open_positions", 0),
            snapshot.get("daily_pnl", 0),
            snapshot.get("mode", "paper"),
        ))
        conn.commit()

    def get_equity_history(self, limit: int = 720) -> List[Dict]:
        """Get equity curve data."""
        conn = self._get_conn()
        # Use selective columns
        columns = ['timestamp', 'equity', 'open_positions', 'daily_pnl']
        columns_str = ', '.join(columns)
        
        rows = conn.execute(
            f"SELECT {columns_str} FROM equity_snapshots ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    # ─── Signal Statistics ───────────────────────────────────────────────

    def get_signal_stats(self) -> Dict[str, Any]:
        """Get detailed signal statistics for analytics dashboard."""
        conn = self._get_conn()
        quality_rows = conn.execute("""
            SELECT quality, COUNT(*) as count, AVG(confidence) as avg_confidence
            FROM signals GROUP BY quality
        """).fetchall()
        symbol_rows = conn.execute("""
            SELECT symbol, COUNT(*) as count, AVG(confidence) as avg_confidence
            FROM signals GROUP BY symbol
        """).fetchall()
        regime_rows = conn.execute("""
            SELECT market_regime, COUNT(*) as count
            FROM signals WHERE market_regime IS NOT NULL GROUP BY market_regime
        """).fetchall()
        wr_rows = conn.execute("""
            SELECT s.quality, COUNT(*) as total,
                   SUM(CASE WHEN o.outcome = 'WIN' THEN 1 ELSE 0 END) as wins
            FROM signals s
            JOIN signal_outcomes o ON s.signal_id = o.signal_id
            GROUP BY s.quality
        """).fetchall()
        total_row = conn.execute("SELECT COUNT(*) as total FROM signals").fetchone()
        return {
            "total_signals": dict(total_row)["total"] if total_row else 0,
            "by_quality": [dict(r) for r in quality_rows],
            "by_symbol": [dict(r) for r in symbol_rows],
            "by_regime": [dict(r) for r in regime_rows],
            "win_rate_by_quality": [dict(r) for r in wr_rows],
        }

    # ─── Batch Operations ────────────────────────────────────────────────

    def batch_save_signals(self, signals: List[Dict[str, Any]]) -> int:
        """
        Batch save multiple signals for better performance.
        
        Args:
            signals: List of signal dictionaries
            
        Returns:
            int: Number of signals saved
        """
        if not signals:
            return 0
        
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()
        
        rows = []
        for signal in signals:
            signal_id = signal.get("signal_id", f"SIG-{now.replace(':', '').replace('-', '')}")
            rows.append((
                signal_id, signal["symbol"], signal["signal_type"],
                signal["quality"], signal["steps_confirmed"], signal["confidence"],
                signal["entry_price"], signal["sl_price"], signal["tp_price"],
                signal.get("sl_distance_pct"), signal.get("rr_ratio"),
                signal.get("market_regime"), signal.get("reasoning"),
                json.dumps(signal.get("step1_data"), cls=DataclassJSONEncoder),
                json.dumps(signal.get("step2_data"), cls=DataclassJSONEncoder),
                json.dumps(signal.get("step3_data"), cls=DataclassJSONEncoder),
                json.dumps(signal.get("step4_data"), cls=DataclassJSONEncoder),
                json.dumps(signal.get("advanced_analytics"), cls=DataclassJSONEncoder),
                signal.get("exchange", "cross"), now, now
            ))
        
        try:
            conn.executemany("""
                INSERT OR REPLACE INTO signals
                (signal_id, symbol, signal_type, quality, steps_confirmed, confidence,
                 entry_price, sl_price, tp_price, sl_distance_pct,
                 rr_ratio, market_regime, reasoning,
                 step1_data, step2_data, step3_data, step4_data,
                 advanced_analytics, exchange, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)
            conn.commit()
            log.info(f"Batch saved {len(rows)} signals")
            return len(rows)
        except Exception as e:
            log.error(f"Failed to batch save signals: {e}")
            raise

    def batch_save_outcomes(self, outcomes: List[Dict[str, Any]]) -> int:
        """
        Batch save multiple signal outcomes for better performance.
        
        Args:
            outcomes: List of outcome dictionaries
            
        Returns:
            int: Number of outcomes saved
        """
        if not outcomes:
            return 0
        
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()
        
        rows = []
        for outcome in outcomes:
            rows.append((
                outcome["signal_id"], outcome.get("outcome"),
                outcome.get("exit_price"), outcome.get("exit_reason"),
                outcome.get("pnl_pct"), outcome.get("rr_achieved"),
                outcome.get("tp_hit", 0), outcome.get("sl_hit", 0),
                outcome.get("max_favorable"), outcome.get("max_adverse"),
                outcome.get("duration_minutes"),
                outcome.get("price_at_5m"), outcome.get("price_at_15m"),
                outcome.get("price_at_30m"), outcome.get("price_at_1h"),
                outcome.get("price_at_4h"),
                outcome.get("closed_at"), now
            ))
        
        try:
            conn.executemany("""
                INSERT INTO signal_outcomes
                (signal_id, outcome, exit_price, exit_reason, pnl_pct, rr_achieved,
                 tp_hit, sl_hit, max_favorable, max_adverse, duration_minutes,
                 price_at_5m, price_at_15m, price_at_30m, price_at_1h, price_at_4h,
                 closed_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)
            conn.commit()
            log.info(f"Batch saved {len(rows)} outcomes")
            return len(rows)
        except Exception as e:
            log.error(f"Failed to batch save outcomes: {e}")
            raise

    def batch_save_equity_snapshots(self, snapshots: List[Dict[str, Any]]) -> int:
        """
        Batch save multiple equity snapshots for better performance.
        
        Args:
            snapshots: List of snapshot dictionaries
            
        Returns:
            int: Number of snapshots saved
        """
        if not snapshots:
            return 0
        
        conn = self._get_conn()
        
        rows = []
        for snapshot in snapshots:
            rows.append((
                snapshot.get("timestamp", datetime.utcnow().isoformat()),
                snapshot["equity"],
                snapshot.get("open_positions", 0),
                snapshot.get("daily_pnl", 0),
                snapshot.get("mode", "paper")
            ))
        
        try:
            conn.executemany("""
                INSERT INTO equity_snapshots
                (timestamp, equity, open_positions, daily_pnl, mode)
                VALUES (?, ?, ?, ?, ?)
            """, rows)
            conn.commit()
            log.info(f"Batch saved {len(rows)} equity snapshots")
            return len(rows)
        except Exception as e:
            log.error(f"Failed to batch save equity snapshots: {e}")
            raise

