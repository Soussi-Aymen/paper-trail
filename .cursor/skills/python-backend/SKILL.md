---
name: python-backend
description: >-
  Writes the FastAPI backend in app/backend with uv, Ruff, and Pydantic v2.
  Use when editing Python, pyproject.toml, FastAPI routes, SQLAlchemy models,
  or app/backend. Do not use for the Vite frontend, repo-root workspace files,
  Dockerfiles, or git hooks.
---

# Python backend

Create files only inside `app/backend`. Anything outside it needs the user's go-ahead.

## Owns

`app/backend` source, `pyproject.toml`, `uv.lock`, Ruff config, Pydantic API models, settings.

## Does not cover

- `pnpm-workspace.yaml`, root `package.json`, root `.gitignore` (monorepo skill)
- `app/frontend`
- Dockerfiles and compose (docker-secure)
- Which tests to write (test-cases). When a step asks for tests, run them with `uv run pytest`.

## Commands

From `app/backend` only:

```bash
uv init
uv add fastapi
uv add --dev ruff
uv sync
uv run ruff check
uv run ruff format
uv run uvicorn papertrail.main:app --reload
```

Never pip, poetry, conda, pip-tools, or `python -m venv`. Commit `uv.lock`. Do not add a second `.gitignore`; the repo root file already ignores `.venv/`, `__pycache__/`, and `.ruff_cache/`.

## App

- Python 3.12. Import package `papertrail` at `app/backend/papertrail/`.
- FastAPI. Every request body and every response model is a Pydantic v2 model. Parse input with that model. Declare `response_model`.
- Settings: one `pydantic-settings` object loaded from the repo-root `.env`. No `os.environ` reads in handlers.
- HTTP status codes follow the http-api-status skill.
- Ruff is the only linter and formatter. Configure it in `pyproject.toml`. Do not add black, flake8, isort, pylint, autopep8, yapf, or mypy.
- Plain functions. Do not add a plugin system or a second package layout.
- Run caps live on `Settings` (`max_candidates`, `max_llm_calls_per_run`, `max_planner_iterations`).
- SQLAlchemy access follows the sqlalchemy-nplus1 skill. LLM JSON follows the llm-structured-output skill.
