# syntax=docker/dockerfile:1

# ---- build ----
FROM node:24-slim AS build
WORKDIR /app
RUN corepack enable

# postinstall (nuxt prepare) needs the sources
COPY . .
RUN --mount=type=cache,id=pnpm,target=/root/.local/share/pnpm/store \
  pnpm install --frozen-lockfile
RUN pnpm build

# ---- runtime ----
FROM node:24-slim
WORKDIR /app
ENV NODE_ENV=production \
  HOST=0.0.0.0 \
  PORT=3000

# the game itself runs in the browser; the server delivers it and passes the freeware
# CD images through (/api/game-data), nothing is stored
COPY --from=build --chown=node:node /app/.output ./.output

USER node
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
