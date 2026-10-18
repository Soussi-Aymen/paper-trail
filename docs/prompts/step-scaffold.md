# Execute: scaffold

PLAN: [docs/plan.md](docs/plan.md)

STEP: scaffold
WAVE: B
DEPENDS ON: skills and clean-tree

NEEDED:
- Read: `docs/plan.md`
- Env: `TOKEN_FACTORY_API_KEY`, `TOKEN_FACTORY_BASE_URL`, `CHAT_MODEL_SMALL`, `CHAT_MODEL_LARGE`, `EMBEDDING_MODEL`

OWNS: `pnpm-workspace.yaml`, `package.json`, `.gitignore`, `.env.example`, `docker-compose.yml`, `app/backend/`, `app/frontend/`
MUST NOT TOUCH: `.cursor/`, `LICENSE`

DELIVERABLES:
- Vite React-TS app at `app/frontend` with `/api` proxy
- FastAPI `/` and `/health` (503 when Postgres or pgvector is down)
- Token Factory probe

VERIFY: `cd app/backend && uv run ruff check && uv run python -m scripts.check_token_factory`
COMMIT: git add app pnpm-workspace.yaml package.json pnpm-lock.yaml .gitignore .env.example docker-compose.yml && git commit -m "Scaffold the monorepo and health checks"
