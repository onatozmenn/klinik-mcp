# Cloud Run image for the health-mcp server.
# Serves the MCP HTTP transport at /mcp on Cloud Run's $PORT (default 8080).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src \
    MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0

WORKDIR /app

# Runtime dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Application source (includes bundled data/*.json).
COPY src/ ./src/

# Cloud Run injects $PORT (defaults to 8080). Bind it on all interfaces.
EXPOSE 8080
CMD ["sh", "-c", "exec python -m health_mcp --transport http --host 0.0.0.0 --port ${PORT:-8080}"]
