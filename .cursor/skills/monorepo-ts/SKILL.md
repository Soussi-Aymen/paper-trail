---
name: monorepo-ts
description: >-
  Maintains this repo's layout: app/frontend (pnpm, Vite) and app/backend (uv,
  FastAPI), plus root pnpm-workspace.yaml, package.json, and .gitignore. Use
  when adding a workspace, editing those root files, or placing a new app. Do
  not use for application features, Docker, or lint config.
---

# Monorepo

Create files only at the repo root for workspace membership. App code belongs to the frontend or python-backend skill.

## Owns

`pnpm-workspace.yaml`, root `package.json`, root `.gitignore`.

## Layout

```
app/backend/     uv project, import package papertrail
app/frontend/    only pnpm workspace member
pnpm-workspace.yaml    packages: ["app/frontend"]
package.json           private: true
```

`app/backend` is not a pnpm package. One `.gitignore` at the repo root. No per-app `.gitignore`. No `packages/shared`. No root `tsconfig.base.json`. The Vite app keeps the tsconfig from its template.

## Install

- Frontend: pnpm from the repo root (`pnpm install`, `pnpm --filter frontend ...`).
- Backend: `uv` inside `app/backend`.
- Never npm, yarn, pip, poetry, or conda.
