FROM node:22-bookworm-slim AS build

WORKDIR /src
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY app/frontend/package.json app/frontend/package.json
RUN pnpm install --frozen-lockfile
COPY app/frontend app/frontend
RUN pnpm --filter frontend build

FROM node:22-bookworm-slim

WORKDIR /app
COPY --from=build --chown=node:node /src/app/frontend/dist ./dist
COPY --chown=node:node app/frontend/serve.mjs ./serve.mjs
USER node
EXPOSE 5173
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:5173').then((r)=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
CMD ["node", "serve.mjs"]
