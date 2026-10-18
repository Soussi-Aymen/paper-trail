import hashlib
import json

from sqlalchemy.orm import Session

from papertrail.models import CacheEntry


def cache_key(kind: str, payload: str) -> str:
    digest = hashlib.sha256(f"{kind}:{payload}".encode()).hexdigest()
    return digest


def cache_get(session: Session, key: str) -> dict | None:
    row = session.get(CacheEntry, key)
    if row is None:
        return None
    return row.body


def cache_put(session: Session, key: str, kind: str, body: dict) -> None:
    existing = session.get(CacheEntry, key)
    if existing is None:
        session.add(CacheEntry(cache_key=key, kind=kind, body=body))
    else:
        existing.body = body
        existing.kind = kind
    session.commit()


def json_key(kind: str, payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return cache_key(kind, encoded)
