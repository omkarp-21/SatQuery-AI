# Build context is the repo root (see docker-compose.yml).
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev build-essential && rm -rf /var/lib/apt/lists/*

# Workspace packages first (better layer caching).
COPY packages/ ./packages/
COPY apps/backend/pyproject.toml ./apps/backend/pyproject.toml
RUN for p in core geospatial agents evidence model_adapters; do \
        pip install --no-cache-dir -e "packages/$p"; done
RUN pip install --no-cache-dir -e "apps/backend[dev]"

COPY apps/backend/ ./apps/backend/
WORKDIR /app/apps/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
