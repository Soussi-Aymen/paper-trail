# Papertrail

Researcher adds seeds and a question, runs Analyze, and gets new papers with sources, a grounded explanation, and a trust badge.

## Decisions

- `app/backend` is uv, Ruff, FastAPI, Pydantic. `app/frontend` is the Vite React TypeScript template.
- Models go through Nebius Token Factory. Discovery uses OpenAlex, then Crossref.
- Analyze is a fixed sequence that writes `agent_events`.
- A missing DOI is not a hard fail. A present DOI that does not resolve is.

## Waves

- A: skills, clean-tree
- B: scaffold
- C: discover
- D: verify
- E: ui
- F: readme

## Run

- Option A: paste one `docs/prompts/step-*.md` into a new Agent session.
- Option B: Build the todos in wave order.

## Steps

- **skills** — Python, Vite, and monorepo skills agree on `app/backend` and `app/frontend`.
- **clean-tree** — Remove the old root apps. Keep `.cursor`, `LICENSE`, `README.md`, `.env`.
- **scaffold** — Workspace, Vite app, FastAPI `/` and `/health`, Postgres pgvector, Token Factory probe.
- **discover** — Seeds, citation and query expansion, dedupe, embeddings, rank, trace.
- **verify** — Trust checks, explanations, analyze job, feedback, leave-one-out.
- **ui** — Screens on the Vite template.
- **readme** — Judge commands, Dockerfiles, demo fixture.
