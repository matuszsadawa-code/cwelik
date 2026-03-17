---
name: database-persistence
description: Guidelines for database interactions, migrations, and performance. Use when working with SQLAlchemy models, database connections, or data persistence logic.
---

# Database Persistence

Infrastructure for reliable and efficient data storage using SQLAlchemy and SQLite/PostgreSQL.

## Core Architecture
OpenClaw uses a centralized database manager to handle connections, sessions, and transaction lifecycles.

## Best Practices
- **Use Context Managers**: Always handle sessions using `with` or `async with` to ensure connections are returned to the pool.
- **Model Validation**: Define all database models with clear type hints and constraints.
- **Alembic Migrations**: Never modify production schemas manually; use migration scripts for all structural changes.
- **Indexing**: Always index columns used frequently in `WHERE` or `JOIN` clauses to maintain query performance.

## Example Usage
```python
from core.database import get_db_session
from models.trade import Trade

with get_db_session() as session:
    trades = session.query(Trade).filter(Trade.status == "OPEN").all()
```
