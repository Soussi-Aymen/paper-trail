---
name: lint-format
description: >-
  Sets lint and format for this repo. Python uses Ruff in app/backend.
  The frontend keeps the Vite template toolchain. Use when editing
  pyproject.toml tool.ruff, oxlint, or git hooks. Do not install hooks
  until a step asks and a test suite passes.
---

# Lint and format

## Python

Ruff only, in `app/backend/pyproject.toml`. Run `uv run ruff check` and `uv run ruff format` from `app/backend`. Do not add black, flake8, isort, pylint, or mypy.

## Frontend

Keep the linter the Vite template generated. Do not add ESLint, Prettier, or Biome beside it.

## Hooks

Do not add pre-commit, husky, or GitHub Actions unless a step asks. If a step asks, install hooks only after the tests pass, and run them through `uv run` or `pnpm`.
