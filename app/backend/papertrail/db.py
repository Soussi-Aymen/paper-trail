from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from papertrail.config import Settings


def make_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def prepare_database(engine: Engine) -> None:
    from papertrail.models import Base

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def database_status(settings: Settings) -> dict[str, object]:
    if not settings.database_url.strip():
        return {"ok": False, "detail": "DATABASE_URL is not set"}
    engine: Engine | None = None
    try:
        engine = make_engine(settings.database_url)
        with engine.connect() as conn:
            version = conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            ).scalar_one_or_none()
    except Exception:
        return {"ok": False, "detail": "database unreachable"}
    finally:
        if engine is not None:
            engine.dispose()
    if version is None:
        return {"ok": False, "detail": "pgvector extension is not installed"}
    return {"ok": True, "pgvector": str(version)}


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
    finally:
        session.close()
