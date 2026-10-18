---
name: sqlalchemy-nplus1
description: >-
  Writes SQLAlchemy 2.0 access for Postgres and pgvector. Use when editing
  models, sessions, or queries in app/backend.
---

# SQLAlchemy

- Typed style: `Mapped`, `mapped_column`, `select()`. One session per request. The analyze job opens its own session.
- Do not query inside a loop over rows. Load related rows with one `IN` query, `selectinload`, or `joinedload`.
- Postgres URL: `postgresql+psycopg://...`. Embeddings use pgvector. JSON columns use JSONB.
- `create_all` on startup is enough. Do not add a migration tool unless a step asks.
- UUID primary keys are strings. Timestamps are UTC.
