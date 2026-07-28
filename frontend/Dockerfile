# ── Stilliu frontend (Vite dev server) ────────────────────────────────────────
# Dev server rather than a production build: this is a demo you're meant to poke
# at, and HMR against a bind mount is the point.
FROM node:20-slim

WORKDIR /app

# package*.json first so `npm ci` is cached independently of source changes.
COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
