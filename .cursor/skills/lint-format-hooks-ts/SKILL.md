---
name: lint-format-hooks-ts
description: >-
  Sets up lint and format for this repo. Python uses Ruff via the python-backend
  skill. The frontend uses the Vite template's toolchain. Use when editing
  Ruff, oxlint, oxfmt, or husky hooks. Do not install git hooks until a test
  suite exists and passes.
---

# Lint and format

## Python

Ruff only, configured in `app/backend/pyproject.toml`, run with `uv run ruff check` and `uv run ruff format`. Do not add black, flake8, isort, pylint, or mypy.

## Frontend

Do not add a second linter beside what the Vite template already includes. If a step asks for a JS linter, use oxlint. Do not add ESLint, Prettier, or Biome beside it.

## Hooks

Install husky only after a real test suite exists and passes. This POC does not add hooks unless a step asks.
