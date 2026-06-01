FROM node:20-alpine AS base
WORKDIR /app

RUN apk add --no-cache bash sudo shadow

ARG UID
ARG GID
ARG PORT

RUN deluser --remove-home node \
    && addgroup -g ${GID} alertadengue \
    && adduser -u ${UID} -G alertadengue -s /bin/bash -D alertadengue \
    && mkdir -p /opt/services/alertadengue /opt/conda \
    && chmod -R a+rwx /opt/conda /opt/services \
    && chown -R alertadengue:alertadengue /opt/services

FROM base AS deps
COPY frontend/package*.json ./

RUN npm ci --ignore-scripts
RUN mkdir -p .next && chown -R alertadengue:alertadengue .next node_modules

FROM deps AS builder

ENV PORT=${PORT}

USER root

RUN chown -R alertadengue:alertadengue /app

USER alertadengue

COPY --chown=alertadengue:alertadengue frontend/ .

RUN npm run build

FROM base AS runner

WORKDIR /app

ENV NODE_ENV=production

USER alertadengue

COPY --chown=alertadengue:alertadengue --from=builder /app/public ./public
COPY --chown=alertadengue:alertadengue --from=builder /app/.next/standalone ./
COPY --chown=alertadengue:alertadengue --from=builder /app/.next/static ./.next/static

ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
