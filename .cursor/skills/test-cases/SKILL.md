---
name: test-cases
description: >-
  Writes tests for behavior a change added. Backend tests are pytest via
  uv run pytest from app/backend. Frontend tests are added only when a step
  asks. Use when writing tests. Do not add a test suite unless a step asks.
---

# Test cases

Write tests only when a step asks for them.

For each behavior that change added: one happy case, each distinct failure, and each real boundary.

- Backend: `uv run pytest` from `app/backend`. Tests live in `app/backend/tests/`.
- Frontend: add Vitest only if the step asks. Until then, do not add it.

Run the tests that cover the files you touched. Use pytest-xdist `-n auto` only when that dependency is already installed.
