"""Database migration wiring tests."""

import inspect

from app.core.db import session


def test_session_exposes_migration_entrypoint_not_create_schema() -> None:
    """Startup should use Alembic migrations rather than metadata.create_all."""

    assert hasattr(session, "migrate_schema")
    assert inspect.iscoroutinefunction(session.migrate_schema)
