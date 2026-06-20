# FortiAnalyzer MCP Server Dockerfile
# Multi-stage build for optimized image size
#
# Build:  docker build -t fortianalyzer-mcp-server .
# Run:    docker run -p 8916:8916 -v ./config:/app/config fortianalyzer-mcp-server

# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml ./
COPY README.md ./
COPY src/ ./src/

RUN uv venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv pip install --no-cache -e .

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
COPY certs/ ./certs/

# Create non-root user
RUN useradd --create-home --shell /bin/bash fazmcp && \
    mkdir -p /app/config /app/logs && \
    chown -R fazmcp:fazmcp /app

USER fazmcp

EXPOSE 8915 8916

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8916/health')" || exit 1

# Default: HTTP on 8916 (for HTTPS, override CMD with --ssl-cert/--ssl-key)
CMD ["python", "-m", "src.fortianalyzer_mcp.server_http", \
     "--host", "0.0.0.0", "--port", "8916", "--transport", "all", \
     "--config", "/app/config/config.json"]
