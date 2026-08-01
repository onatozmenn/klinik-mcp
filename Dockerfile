# Container image for the Klinik MCP server.
# Serves the MCP HTTP transport at /mcp on $PORT (default 8080).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src \
    MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0

WORKDIR /app

# Pinned runtime dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Application source (includes bundled data/*.json).
COPY src/ ./src/

RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Cloud Run / Spaces inject $PORT (defaults to 8080). Bind it on all interfaces.
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8080') + '/health', timeout=4)"]
CMD ["sh", "-c", "exec python -m health_mcp --transport http --host 0.0.0.0 --port ${PORT:-8080}"]
