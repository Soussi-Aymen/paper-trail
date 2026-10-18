# Execute: discover

PLAN: [docs/plan.md](docs/plan.md)

STEP: discover
WAVE: C
DEPENDS ON: scaffold

NEEDED:
- Env: `DATABASE_URL`, `SCHOLARLY_CONTACT_EMAIL`, Token Factory vars
- Read: `app/backend/papertrail/`

OWNS: `app/backend` discovery code
MUST NOT TOUCH: `app/frontend/`, `pnpm-workspace.yaml`, root `package.json`

DELIVERABLES:
- Projects and seeds (DOI, title, BibTeX) via OpenAlex then Crossref
- Citation neighbors and query expansion, dedupe, embeddings, rank cap 30
- `agent_events` for each tool

VERIFY: `cd app/backend && uv run ruff check`
COMMIT: git add app/backend && git commit -m "Discover and rank papers from seeds"
