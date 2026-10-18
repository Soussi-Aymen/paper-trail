---
name: docker-secure
description: >-
  Writes Dockerfiles, .dockerignore, and compose for app/backend (uv) and
  app/frontend (Vite). Use when editing Dockerfile, .dockerignore, or
  docker-compose.yml. Do not use for application source.
---

# Containers

## Owns

`app/backend/Dockerfile`, `app/frontend/Dockerfile`, their `.dockerignore` files, and root `docker-compose.yml`.

## Backend image

- Multi-stage. Builder installs with uv. Runtime is `python:3.12-slim`.
- Copy `pyproject.toml` and `uv.lock`, then `uv sync`, then sources.
- BuildKit cache mount for the uv cache.
- Numeric non-root `USER`. `HEALTHCHECK` against `/health`.
- Do not bake secrets into the image.

## Frontend image

- Multi-stage Node build, then a runtime stage that serves the built files.
- Non-root `USER node`. `HEALTHCHECK`.
- Same Node major in build and runtime.

## Compose

- `db` uses `pgvector/pgvector:pg16` and a named data volume. The database service is the exception to a read-only root filesystem.
- `backend` builds from `./app/backend`. The frontend image uses the repo root as its build context so the pnpm lockfile is included, with dockerfile `app/frontend/Dockerfile`.
- `cap_drop: [ALL]`, `security_opt: ["no-new-privileges:true"]`, and `read_only: true` on the backend. Give the backend a tmpfs on `/tmp`.
- Env comes from the repo-root `.env` at runtime. Do not copy `.env` into images.
- One root `.gitignore`. Do not add another.
