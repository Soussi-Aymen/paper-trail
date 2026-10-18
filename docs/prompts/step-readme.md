# Execute: readme

PLAN: [docs/plan.md](docs/plan.md)

STEP: readme
WAVE: F
DEPENDS ON: ui

NEEDED:
- Env / secrets: none in the files
- Read: `docs/plan.md`, `docker-compose.yml`

OWNS: `README.md`, `app/backend/Dockerfile`, `app/frontend/Dockerfile`, `.dockerignore` files
MUST NOT TOUCH: application logic

DELIVERABLES:
- Judge commands, architecture, checks, evaluation, demo fixture
- Separate backend and frontend images

VERIFY: `test -f app/backend/Dockerfile && test -f app/frontend/Dockerfile`
COMMIT: git add README.md app/backend/Dockerfile app/frontend/Dockerfile && git commit -m "Document how to run and deploy papertrail"
