"""
Database connection pooling for OpenClaw Trading Dashboard API

Provides thread-local SQLite connection pooling with WAL mode for better concurrency.
Implements database health checks and performance monitoring.
"""

import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DatabaseConnectionPool:
    """
    SQLite connection manager with thread-local storage for connection pooling.
    
    Features:
    - Thread-local connections (each thread gets its own connection)
    - WAL (Write-Ahead Logging) mode for better concurrency
    - Connection reuse within threads
    - Performance monitoring for health checks
    - Automatic index creation for frequently queried columns
    """
    
    def __init__(self, db_path: str = "db/trading_system.db"):
        """
        Initialize database connection pool
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._local = threading.local()
        self._lock = threading.Lock()
        self._query_times = []  # Track query performance
        self._max_query_samples = 100
        
        # Ensure database directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database schema and indexes
        self._init_database()
        
        logger.info(f"Database connection pool initialized: {db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get thread-local connection (connection pooling).
        
        Each thread gets its own connection that's reused across requests.
        Connections are configured with WAL mode and optimized settings.
        
        Returns:
            sqlite3.Connection: Thread-local database connection
        """
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            # Create new connection for this thread
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0  # 30 second timeout for lock acquisition
            )
            
            # Configure connection
            self._local.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            
            # Enable WAL mode for better concurrency
            # WAL allows multiple readers and one writer simultaneously
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            
            # Set synchronous mode to NORMAL for better performance
            # NORMAL is safe with WAL mode
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            
            # Increase cache size to 64MB for better performance
            self._local.conn.execute("PRAGMA cache_size=-64000")
            
            # Store temporary tables in memory
            self._local.conn.execute("PRAGMA temp_store=MEMORY")
            
            # Enable foreign key constraints
            self._local.conn.execute("PRAGMA foreign_keys=ON")
            
            logger.debug(f"Created new database connection for thread {threading.current_thread().name}")
        
        return self._local.conn
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections with automatic cleanup.
        
        Usage:
            with db_pool.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM signals")
                results = cursor.fetchall()
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = self._get_connection()
        try:
            yield conn
        except Exception as e:
            logger.error(f"Database error: {e}")
            raise
    
    @contextmanager
    def transaction(self):
        """
        Context manager for transactions with automatic commit/rollback.
        
        Usage:
            with db_pool.transaction() as conn:
                conn.execute("INSERT INTO signals ...")
                conn.execute("UPDATE signal_outcomes ...")
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction failed, rolled back: {e}")
            raise
    
    def execute_query(self, query: str, params: tuple = ()) -> list:
        """
        Execute a SELECT query and return results.
        
        Tracks query execution time for health monitoring.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            list: Query results as list of dictionaries
        """
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                results = [dict(row) for row in cursor.fetchall()]
            
            # Track query performance
            query_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            self._track_query_time(query_time)
            
            return results
        
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def execute_write(self, query: str, params: tuple = ()) -> int:
        """
        Execute an INSERT/UPDATE/DELETE query.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            int: Number of affected rows
        """
        start_time = time.time()
        
        try:
            with self.transaction() as conn:
                cursor = conn.execute(query, params)
                affected_rows = cursor.rowcount
            
            # Track query performance
            query_time = (time.time() - start_time) * 1000
            self._track_query_time(query_time)
            
            return affected_rows
        
        except Exception as e:
            logger.error(f"Write query execution failed: {e}")
            raise
    
    def _track_query_time(self, query_time_ms: float):
        """
        Track query execution time for health monitoring.
        
        Args:
            query_time_ms: Query execution time in milliseconds
        """
        with self._lock:
            self._query_times.append(query_time_ms)
            
            # Keep only recent samples
            if len(self._query_times) > self._max_query_samples:
                self._query_times.pop(0)
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """
        Get database health metrics for system monitoring.
        
        Returns:
            dict: Health metrics including:
                - status: 'healthy' or 'degraded'
                - avg_query_time_ms: Average query execution time
                - max_query_time_ms: Maximum query execution time
                - total_queries: Total queries tracked
                - connection_count: Number of active connections
                - wal_enabled: Whether WAL mode is enabled
        """
        try:
            with self._lock:
                query_times = self._query_times.copy()
            
            # Calculate metrics
            if query_times:
                avg_query_time = sum(query_times) / len(query_times)
                max_query_time = max(query_times)
            else:
                avg_query_time = 0
                max_query_time = 0
            
            # Check WAL mode
            with self.get_connection() as conn:
                cursor = conn.execute("PRAGMA journal_mode")
                journal_mode = cursor.fetchone()[0]
                wal_enabled = journal_mode.upper() == 'WAL'
            
            # Determine health status
            # Degraded if average query time > 100ms or max > 1000ms
            status = 'healthy'
            if avg_query_time > 100 or max_query_time > 1000:
                status = 'degraded'
            
            return {
                'status': status,
                'avg_query_time_ms': round(avg_query_time, 2),
                'max_query_time_ms': round(max_query_time, 2),
                'total_queries': len(query_times),
                'wal_enabled': wal_enabled,
                'db_path': self.db_path
            }
        
        except Exception as e:
            logger.error(f"Failed to get health metrics: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _init_database(self):
        """
        Initialize database schema and create performance indexes.
        
        Creates indexes for frequently queried columns:
        - signals.symbol
        - signals.created_at
        - signal_outcomes.signal_id
        
        Note: Indexes are only created if the corresponding tables exist.
        This allows the connection pool to work with both existing databases
        and new/test databases.
        """
        try:
            with self.get_connection() as conn:
                # Check if tables exist before creating indexes
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('signals', 'signal_outcomes', 'executions', 'equity_snapshots')
                """)
                existing_tables = {row[0] for row in cursor.fetchall()}
                
                # Only create indexes if the tables exist
                if 'signals' in existing_tables:
                    # Index on signals.symbol for filtering by symbol
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_signals_symbol 
                        ON signals(symbol)
                    """)
                    
                    # Index on signals.created_at for time-based queries
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_signals_created_at 
                        ON signals(created_at DESC)
                    """)
                    
                    # Index on signals.quality for quality-based filtering
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_signals_quality 
                        ON signals(quality)
                    """)
                    
                    # Composite index for symbol + created_at queries
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_signals_symbol_created 
                        ON signals(symbol, created_at DESC)
                    """)
                    
                    logger.info("Created indexes for signals table")
                
                if 'signal_outcomes' in existing_tables:
                    # Index on signal_outcomes.signal_id for joining with signals
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_signal_outcomes_signal_id 
                        ON signal_outcomes(signal_id)
                    """)
                    
                    # Index on signal_outcomes.created_at for time-based queries
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_signal_outcomes_created_at 
                        ON signal_outcomes(created_at DESC)
                    """)
                    
                    logger.info("Created indexes for signal_outcomes table")
                
                if 'executions' in existing_tables:
                    # Index on executions.status for filtering open/closed positions
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_executions_status 
                        ON executions(status)
                    """)
                    
                    # Index on executions.symbol for symbol-based queries
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_executions_symbol 
                        ON executions(symbol)
                    """)
                    
                    logger.info("Created indexes for executions table")
                
                if 'equity_snapshots' in existing_tables:
                    # Index on equity_snapshots.timestamp for equity curve queries
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_equity_snapshots_timestamp 
                        ON equity_snapshots(timestamp DESC)
                    """)
                    
                    logger.info("Created indexes for equity_snapshots table")
                
                conn.commit()
                
                if existing_tables:
                    logger.info(f"Database indexes initialized for tables: {existing_tables}")
                else:
                    logger.info("No tables found, skipping index creation")
        
        except Exception as e:
            logger.error(f"Failed to initialize database indexes: {e}")
            # Don't raise - allow the pool to be created even if index creation fails
            # This is important for test databases that may not have the schema yet
    
    def close_connection(self):
        """Close thread-local connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
            logger.debug(f"Closed database connection for thread {threading.current_thread().name}")
    
    def close_all_connections(self):
        """
        Close all connections (call on application shutdown).
        
        Note: This only closes the connection for the current thread.
        Other threads will close their connections when they exit.
        """
        self.close_connection()


# Global database pool instance
_db_pool: Optional[DatabaseConnectionPool] = None
_db_pool_lock = threading.Lock()


def get_database_pool(db_path: str = "db/trading_system.db") -> DatabaseConnectionPool:
    """
    Get global database connection pool instance (singleton pattern).
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        DatabaseConnectionPool: Global database pool instance
    """
    global _db_pool
    
    if _db_pool is None:
        with _db_pool_lock:
            if _db_pool is None:
                _db_pool = DatabaseConnectionPool(db_path)
    
    return _db_pool


def get_health_check() -> Dict[str, Any]:
    """
    Get database health check for system monitoring endpoint.
    
    Returns:
        dict: Database health metrics
    """
    db_pool = get_database_pool()
    return db_pool.get_health_metrics()
