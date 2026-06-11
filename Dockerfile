# stage 1: build frontend
FROM node:20-alpine AS frontend
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# stage 2: backend
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg ca-certificates curl && rm -rf /var/lib/apt/lists/*
COPY backend/pyproject.toml backend/uv.lock* ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev
COPY backend/ .
COPY --from=frontend /web/dist /app/any2m3u/web
ENV ANY2M3U_DATA=/data \
    ANY2M3U_WEB=/app/any2m3u/web
EXPOSE 8000
CMD ["uv", "run", "python", "-m", "any2m3u"]
