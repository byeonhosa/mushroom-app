FROM node:26-bookworm-slim AS deps

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM node:26-bookworm-slim AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY frontend ./

# The pages call the API on their own origin, under /api (frontend/lib/api.ts).
# Behind the Caddy proxy that path never reaches this server. Without the
# proxy (the deploy checks on the loopback port, a local stack) this server
# forwards /api/* to the address below; next.config.js reads it at build time.
ARG API_PROXY_TARGET=http://api:8000
ENV API_PROXY_TARGET=${API_PROXY_TARGET} \
    NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# next.config.js sets output: "standalone", so the build leaves a self-contained
# server in .next/standalone with only the node_modules files it needs. The
# runtime image carries that and the static assets, nothing else.
FROM node:26-bookworm-slim AS runner

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0 \
    NEXT_TELEMETRY_DISABLED=1

COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static

USER node

EXPOSE 3000

CMD ["node", "server.js"]
