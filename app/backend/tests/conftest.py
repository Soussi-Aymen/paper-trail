import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://papertrail:papertrail@localhost:5432/papertrail_test"

import pytest
from sqlalchemy import text

from papertrail.config import get_settings

get_settings.cache_clear()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from papertrail.main import app
    from papertrail.models import Base

    with TestClient(app) as test_client:
        engine = app.state.engine
        assert engine is not None
        names = ", ".join(table.name for table in reversed(Base.metadata.sorted_tables))
        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
        yield test_client


@pytest.fixture
def db(client):
    from papertrail.main import _factory

    assert _factory is not None
    session = _factory()
    try:
        yield session
    finally:
        session.close()
