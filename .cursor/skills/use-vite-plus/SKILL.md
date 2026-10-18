---
name: use-vite-plus
description: >-
  Writes the Vite+ React TypeScript app in app/frontend with one vite.config.ts
  and Zod at the API boundary. Use when editing app/frontend, vite.config.ts,
  frontend screens, Zod schemas, or API response parsing. Do not use for the
  Python backend, repo-root workspace files, Dockerfiles, or git hooks.
---

# Vite+

One config file: `app/frontend/vite.config.ts`. Import `defineConfig` from `vite-plus`.

## Scaffold

```bash
pnpm create vite@latest app/frontend --template react-ts
```

Add `vite-plus` with pnpm. Keep pnpm. Do not switch to npm or yarn.

## Config

Keep the React plugin. The only app setting beyond the template is `server.proxy` so `/api` reaches the backend.

Put the Oxlint rules in the `lint` block of that same file. Do not keep `.oxlintrc.json` beside it.

Do not add `test`, `fmt`, `staged`, `run`, `pack`, Rolldown, Lightning CSS, or minify options until something uses them. Do not add Babel, SWC, Rspack, a router, or a component library. Do not add Vitest or git hooks unless a step asks.

Scripts call `vp` (`vp dev`, `vp build`, `vp lint`). The production build still typechecks with `tsc -b`.

## Zod

Parse every JSON body that comes back from the API with a Zod schema in `app/frontend/src/schemas/` before the UI reads it. Go through `api(schema, path)` in `src/api.ts`, and surface a parse failure. Derive the TypeScript types with `z.infer`.

Use Zod for that boundary and for any other value that arrives untyped (a response, a stored payload). Do not wrap values the screen already typed, and do not add a schema for a request body the form already checks.

Pydantic models in `app/backend` are the contract. Do not add `packages/shared`.
