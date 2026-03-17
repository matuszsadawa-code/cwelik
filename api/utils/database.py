"""
Database connection utilities

Provides access to both the legacy Database class and the new DatabaseConnectionPool.
"""

from storage.database import Database
from api.database import DatabaseConnectionPool, get_database_pool
from functools import lru_cache


@lru_cache()
def get_database() -> Database:
    """
    Get legacy database instance (singleton pattern)
    
    This is maintained for backward compatibility with existing code.
    New code should use get_database_pool() instead.
    
    Returns:
        Database: Shared database instance
    """
    return Database()


def get_db_pool() -> DatabaseConnectionPool:
    """
    Get database connection pool instance (singleton pattern)
    
    Recommended for new API endpoints. Provides:
    - Thread-local connection pooling
    - WAL mode for better concurrency
    - Performance monitoring
    - Health check metrics
    
    Returns:
        DatabaseConnectionPool: Shared database pool instance
    """
    return get_database_pool()
