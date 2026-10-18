# Execute: skills

PLAN: [docs/plan.md](docs/plan.md)

STEP: skills
WAVE: A — parallel with clean-tree
DEPENDS ON: none

NEEDED:
- Existing files: `.cursor/skills/`, `.cursor/rules/`
- Env / secrets: none

OWNS: `.cursor/rules/python-uv.mdc`, `.cursor/rules/dev-conventions.mdc`, `.cursor/skills/python-backend/`, `.cursor/skills/monorepo-ts/`, `.cursor/skills/frontend-ts/`, `.cursor/skills/docker-secure/`, `.cursor/skills/lint-format-hooks-ts/`, `.cursor/skills/test-cases/`, `.cursor/skills/http-api-status/`
MUST NOT TOUCH: `LICENSE`, `README.md`, `.env`

DELIVERABLES:
- uv, Ruff, FastAPI, Pydantic skill and always-on rule
- Vite skill uses the React TypeScript template and an `/api` proxy
- Monorepo skill keeps `app/backend` and `app/frontend`
- Delete `.cursor/skills/backend-ts/`

VERIFY: `test -f .cursor/skills/python-backend/SKILL.md && test ! -d .cursor/skills/backend-ts`
COMMIT: git add .cursor && git commit -m "Adapt skills for the uv backend and Vite frontend"
