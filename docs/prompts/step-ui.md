# Execute: ui

PLAN: [docs/plan.md](docs/plan.md)

STEP: ui
WAVE: E
DEPENDS ON: verify

NEEDED:
- Read: `app/frontend/`, API routes in `app/backend/papertrail/main.py`

OWNS: `app/frontend/`
MUST NOT TOUCH: `app/backend/`, `pnpm-workspace.yaml`, root `package.json`

DELIVERABLES:
- Project form, seeds, Analyze, trace, result cards with badge, evidence, accept/reject
- Calls go through the Vite `/api` proxy
- Zod schemas for responses

VERIFY: `pnpm --filter frontend exec tsc --noEmit`
COMMIT: git add app/frontend && git commit -m "Add the research workspace screens"
