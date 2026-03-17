"""
Query Optimization Utilities for OpenClaw Trading Dashboard

Provides utilities for profiling slow queries, batch operations, and selective column queries.

Features:
- Query profiling and timing
- Slow query detection and logging
- Batch operation helpers
- Selective column query builders
- Query performance statistics
"""

import logging
import time
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)


class QueryProfiler:
    """
    Query profiler for tracking and analyzing query performance.
    
    Responsibilities:
    - Time query execution
    - Log slow queries
    - Track query statistics
    - Generate performance reports
    """
    
    def __init__(self, slow_query_threshold_ms: float = 100.0):
        """
        Initialize query profiler.
        
        Args:
            slow_query_threshold_ms: Threshold for slow query logging (milliseconds)
        """
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self._query_stats: Dict[str, Dict[str, Any]] = {}
        self._enabled = True
        
        logger.info(f"QueryProfiler initialized with threshold: {slow_query_threshold_ms}ms")
    
    @contextmanager
    def profile(self, query_name: str, query: str = ""):
        """
        Context manager for profiling query execution.
        
        Args:
            query_name: Name/identifier for the query
            query: SQL query string (optional, for logging)
            
        Usage:
            with profiler.profile("get_signals", "SELECT * FROM signals"):
                # Execute query
                pass
        """
        start_time = time.perf_counter()
        
        try:
            yield
        finally:
            if self._enabled:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                
                # Update statistics
                if query_name not in self._query_stats:
                    self._query_stats[query_name] = {
                        'count': 0,
                        'total_time_ms': 0,
                        'min_time_ms': float('inf'),
                        'max_time_ms': 0,
                        'slow_count': 0
                    }
                
                stats = self._query_stats[query_name]
                stats['count'] += 1
                stats['total_time_ms'] += elapsed_ms
                stats['min_time_ms'] = min(stats['min_time_ms'], elapsed_ms)
                stats['max_time_ms'] = max(stats['max_time_ms'], elapsed_ms)
                
                # Log slow queries
                if elapsed_ms > self.slow_query_threshold_ms:
                    stats['slow_count'] += 1
                    logger.warning(
                        f"Slow query detected: {query_name} took {elapsed_ms:.2f}ms "
                        f"(threshold: {self.slow_query_threshold_ms}ms)"
                    )
                    if query:
                        logger.debug(f"Query: {query[:200]}")
    
    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get query statistics.
        
        Returns:
            dict: Query statistics for all profiled queries
        """
        stats = {}
        
        for query_name, data in self._query_stats.items():
            avg_time = data['total_time_ms'] / data['count'] if data['count'] > 0 else 0
            
            stats[query_name] = {
                'count': data['count'],
                'total_time_ms': round(data['total_time_ms'], 2),
                'avg_time_ms': round(avg_time, 2),
                'min_time_ms': round(data['min_time_ms'], 2),
                'max_time_ms': round(data['max_time_ms'], 2),
                'slow_count': data['slow_count']
            }
        
        return stats
    
    def reset_stats(self):
        """Reset all query statistics."""
        self._query_stats.clear()
        logger.info("Query profiler statistics reset")
    
    def enable(self):
        """Enable query profiling."""
        self._enabled = True
    
    def disable(self):
        """Disable query profiling."""
        self._enabled = False


# Global profiler instance
_global_profiler = QueryProfiler(slow_query_threshold_ms=100.0)


def get_profiler() -> QueryProfiler:
    """Get global profiler instance."""
    return _global_profiler


def profile_query(query_name: str):
    """
    Decorator for profiling query methods.
    
    Args:
        query_name: Name/identifier for the query
        
    Usage:
        @profile_query("get_signals")
        def get_signals(self):
            # Execute query
            return results
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            profiler = get_profiler()
            with profiler.profile(query_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


class BatchQueryHelper:
    """
    Helper for batch database operations.
    
    Provides utilities for batching inserts, updates, and queries
    to reduce database round-trips.
    """
    
    @staticmethod
    def batch_insert(
        conn: sqlite3.Connection,
        table: str,
        columns: List[str],
        rows: List[Tuple],
        batch_size: int = 100
    ) -> int:
        """
        Batch insert rows into table.
        
        Args:
            conn: Database connection
            table: Table name
            columns: Column names
            rows: List of row tuples
            batch_size: Number of rows per batch
            
        Returns:
            int: Number of rows inserted
        """
        if not rows:
            return 0
        
        placeholders = ','.join(['?'] * len(columns))
        columns_str = ','.join(columns)
        query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
        
        total_inserted = 0
        
        # Process in batches
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            conn.executemany(query, batch)
            total_inserted += len(batch)
        
        conn.commit()
        
        logger.debug(f"Batch inserted {total_inserted} rows into {table}")
        return total_inserted
    
    @staticmethod
    def batch_update(
        conn: sqlite3.Connection,
        table: str,
        set_columns: List[str],
        where_column: str,
        rows: List[Tuple],
        batch_size: int = 100
    ) -> int:
        """
        Batch update rows in table.
        
        Args:
            conn: Database connection
            table: Table name
            set_columns: Columns to update
            where_column: Column for WHERE clause
            rows: List of tuples (set_values..., where_value)
            batch_size: Number of rows per batch
            
        Returns:
            int: Number of rows updated
        """
        if not rows:
            return 0
        
        set_clause = ','.join([f"{col} = ?" for col in set_columns])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_column} = ?"
        
        total_updated = 0
        
        # Process in batches
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            conn.executemany(query, batch)
            total_updated += len(batch)
        
        conn.commit()
        
        logger.debug(f"Batch updated {total_updated} rows in {table}")
        return total_updated
    
    @staticmethod
    def batch_select(
        conn: sqlite3.Connection,
        table: str,
        columns: List[str],
        where_column: str,
        values: List[Any],
        batch_size: int = 100
    ) -> List[sqlite3.Row]:
        """
        Batch select rows using IN clause.
        
        Args:
            conn: Database connection
            table: Table name
            columns: Columns to select
            where_column: Column for WHERE IN clause
            values: List of values for IN clause
            batch_size: Number of values per batch
            
        Returns:
            list: All matching rows
        """
        if not values:
            return []
        
        columns_str = ','.join(columns) if columns else '*'
        all_rows = []
        
        # Process in batches
        for i in range(0, len(values), batch_size):
            batch = values[i:i + batch_size]
            placeholders = ','.join(['?'] * len(batch))
            query = f"SELECT {columns_str} FROM {table} WHERE {where_column} IN ({placeholders})"
            
            rows = conn.execute(query, batch).fetchall()
            all_rows.extend(rows)
        
        logger.debug(f"Batch selected {len(all_rows)} rows from {table}")
        return all_rows


class SelectiveQueryBuilder:
    """
    Builder for selective column queries (avoid SELECT *).
    
    Provides utilities for building queries with only required columns.
    """
    
    # Common column sets for different query types
    SIGNAL_SUMMARY_COLUMNS = [
        'signal_id', 'symbol', 'signal_type', 'quality', 'confidence',
        'entry_price', 'sl_price', 'tp_price', 'market_regime', 'created_at'
    ]
    
    SIGNAL_DETAIL_COLUMNS = SIGNAL_SUMMARY_COLUMNS + [
        'steps_confirmed', 'sl_distance_pct', 'rr_ratio', 'reasoning',
        'step1_data', 'step2_data', 'step3_data', 'step4_data', 'advanced_analytics'
    ]
    
    OUTCOME_SUMMARY_COLUMNS = [
        'id', 'signal_id', 'outcome', 'exit_price', 'pnl_pct', 'rr_achieved',
        'duration_minutes', 'closed_at'
    ]
    
    OUTCOME_DETAIL_COLUMNS = OUTCOME_SUMMARY_COLUMNS + [
        'exit_reason', 'tp_hit', 'sl_hit', 'max_favorable', 'max_adverse',
        'price_at_5m', 'price_at_15m', 'price_at_30m', 'price_at_1h', 'price_at_4h'
    ]
    
    EXECUTION_SUMMARY_COLUMNS = [
        'execution_id', 'signal_id', 'symbol', 'direction', 'status',
        'entry_price', 'exit_price', 'realised_pnl', 'created_at', 'closed_at'
    ]
    
    EQUITY_COLUMNS = [
        'timestamp', 'equity', 'open_positions', 'daily_pnl'
    ]
    
    @staticmethod
    def build_select(
        table: str,
        columns: List[str],
        where: Optional[str] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None
    ) -> str:
        """
        Build SELECT query with specified columns.
        
        Args:
            table: Table name
            columns: List of column names
            where: WHERE clause (without WHERE keyword)
            order_by: ORDER BY clause (without ORDER BY keyword)
            limit: LIMIT value
            
        Returns:
            str: SQL query string
        """
        columns_str = ','.join(columns)
        query = f"SELECT {columns_str} FROM {table}"
        
        if where:
            query += f" WHERE {where}"
        
        if order_by:
            query += f" ORDER BY {order_by}"
        
        if limit:
            query += f" LIMIT {limit}"
        
        return query
    
    @staticmethod
    def build_join_select(
        main_table: str,
        main_columns: List[str],
        join_table: str,
        join_columns: List[str],
        join_on: str,
        join_type: str = "LEFT JOIN",
        where: Optional[str] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None
    ) -> str:
        """
        Build SELECT query with JOIN and specified columns.
        
        Args:
            main_table: Main table name
            main_columns: Columns from main table (with table prefix)
            join_table: Join table name
            join_columns: Columns from join table (with table prefix)
            join_on: JOIN ON condition
            join_type: Type of join (LEFT JOIN, INNER JOIN, etc.)
            where: WHERE clause
            order_by: ORDER BY clause
            limit: LIMIT value
            
        Returns:
            str: SQL query string
        """
        all_columns = main_columns + join_columns
        columns_str = ','.join(all_columns)
        
        query = f"SELECT {columns_str} FROM {main_table} {join_type} {join_table} ON {join_on}"
        
        if where:
            query += f" WHERE {where}"
        
        if order_by:
            query += f" ORDER BY {order_by}"
        
        if limit:
            query += f" LIMIT {limit}"
        
        return query


def optimize_query_plan(conn: sqlite3.Connection, query: str) -> str:
    """
    Get query execution plan for optimization analysis.
    
    Args:
        conn: Database connection
        query: SQL query
        
    Returns:
        str: Query plan explanation
    """
    try:
        rows = conn.execute(f"EXPLAIN QUERY PLAN {query}").fetchall()
        plan = '\n'.join([str(dict(row)) for row in rows])
        return plan
    except Exception as e:
        logger.error(f"Error getting query plan: {e}")
        return f"Error: {str(e)}"
