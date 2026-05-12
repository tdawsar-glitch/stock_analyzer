# Build context for this image is the oil_inventory_tracker/ root so we can
# include the sibling `config/` and `scripts/` directories.
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/app    /app/app
COPY config         /app/config
COPY scripts        /app/scripts

ENV PYTHONUNBUFFERED=1 \
    OIT_CONFIG_DIR=/app/config \
    CACHE_DB_PATH=/app/data/inventory_cache.duckdb

RUN mkdir -p /app/data

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
