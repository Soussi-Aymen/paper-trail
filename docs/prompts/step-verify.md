# Execute: verify

PLAN: [docs/plan.md](docs/plan.md)

STEP: verify
WAVE: D
DEPENDS ON: discover

NEEDED:
- Env: Token Factory vars and `DATABASE_URL`
- Read: `app/backend/papertrail/`

OWNS: verification, explanations, analyze job, feedback, leave-one-out, JSON fixture
MUST NOT TOUCH: `app/frontend/`

DELIVERABLES:
- Trust badge with evidence
- Grounded explanations
- `POST /projects/{id}/analyze`, events, results, feedback, evaluate

VERIFY: `cd app/backend && uv run ruff check`
COMMIT: git add app/backend && git commit -m "Verify papers and explain the top results"
