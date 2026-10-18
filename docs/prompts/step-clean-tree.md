# Execute: clean-tree

PLAN: [docs/plan.md](docs/plan.md)

STEP: clean-tree
WAVE: A — parallel with skills
DEPENDS ON: none

NEEDED:
- Env / secrets: none

OWNS: delete root `backend/`, `frontend/`, `docker-compose.yml`, `.env.example`, `.gitignore`
MUST NOT TOUCH: `.cursor/`, `LICENSE`, `README.md`, `.env`

DELIVERABLES:
- Those paths are gone

VERIFY: `test ! -d frontend && test ! -f docker-compose.yml`
COMMIT: git add -A && git commit -m "Remove the old root apps"
