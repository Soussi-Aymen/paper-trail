---
name: frontend-ts
description: >-
  Writes the Vite React TypeScript app in app/frontend. Use when editing
  app/frontend, vite.config.ts, or frontend screens. Do not use for the Python
  backend, repo-root workspace files, Dockerfiles, or git hooks.
---

# Frontend

Create files only inside `app/frontend`. Anything outside it needs the user's go-ahead.

## Owns

The Vite app in `app/frontend`.

## Does not cover

- Root workspace files (monorepo skill)
- `app/backend`
- Dockerfiles and compose
- Linters and git hooks

## Scaffold

Create the app with the current Vite React TypeScript template:

```bash
pnpm create vite@latest app/frontend --template react-ts
```

Keep the template's Vite, React plugin, TypeScript, and scripts. The only config change is `server.proxy` so `/api` reaches the backend. Do not set Rolldown, Lightning CSS, or minify options. Do not add Babel, SWC, Rspack, a router, or a component library.

Use pnpm, never npm or yarn. Do not add a second `.gitignore`.

## API calls

Parse each API response with a Zod schema in `app/frontend/src/schemas/`. Show parse failures. Pydantic models in `app/backend` are the contract. Do not add `packages/shared`.

Do not add Vitest unless a step asks for tests.
