---
name: test-cases
description: >-
  Writes tests for behavior a change added. Backend tests are pytest via uv
  run pytest from app/backend. Frontend tests are added only when a step asks.
  Use when writing tests. Do not add a test suite unless a step asks.
---

# Test cases

Write tests only when a step asks for them.

For each behavior that change added or touched:

- Happy: every distinct success outcome.
- Negative: every distinct rejection. Unauthorized, malformed, and not-found are different cases.
- Edge: every real boundary. Skip boundaries the types make impossible.

Do not invent behaviors. Do not repeat the same case with different dummy data.

- Backend: `uv run pytest` from `app/backend`. Tests live in `app/backend/tests/`.
- Frontend: add Vitest only if the step asks.

Run the tests that cover the files you touched. Add pytest-xdist only when a step asks for parallel runs.
