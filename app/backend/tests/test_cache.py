from papertrail.cache import cache_get, cache_key, cache_put, json_key
from papertrail.config import Settings
from papertrail.db import database_status


def test_cache_key_changes_with_kind_and_payload():
    assert cache_key("http", "a") == cache_key("http", "a")
    assert cache_key("http", "a") != cache_key("http", "b")
    assert cache_key("http", "a") != cache_key("llm", "a")


def test_json_key_ignores_object_key_order():
    assert json_key("emb", {"b": 1, "a": 2}) == json_key("emb", {"a": 2, "b": 1})


def test_database_status_rejects_a_blank_url():
    status = database_status(Settings(database_url="  "))
    assert status["ok"] is False
    assert status["detail"] == "DATABASE_URL is not set"


def test_database_status_rejects_an_unreachable_host():
    status = database_status(
        Settings(database_url="postgresql+psycopg://papertrail:papertrail@127.0.0.1:1/none?connect_timeout=2")
    )
    assert status["ok"] is False
    assert status["detail"] == "database unreachable"


def test_cache_round_trip_and_missing_key(db):
    assert cache_get(db, "missing") is None
    key = cache_key("http", "body")
    cache_put(db, key, "http", {"ok": True})
    assert cache_get(db, key) == {"ok": True}
    cache_put(db, key, "http", {"ok": False})
    assert cache_get(db, key) == {"ok": False}
