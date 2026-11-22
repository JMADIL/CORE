FROM python:3.12-slim

# 1. Install system utilities and Node.js 22 LTS (for MCP server stdio execution)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Copy uv package manager binaries
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 3. Cache dependencies and virtual environment
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# 4. Pre-install external MCP servers globally for fast tool execution
RUN npm install -g \
    @h1deya/mcp-server-weather@0.1.3 \
    researchmcp@1.0.2 \
    @modelcontextprotocol/server-sequential-thinking@2026.7.4

# 5. Copy backend source code
COPY src/ ./src/
RUN uv sync --frozen --no-dev --no-editable

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

RUN groupadd --system core && useradd --system --gid core core \
    && mkdir -p /app/data && chown -R core:core /app
USER core

# 6. Health check on /health endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["/app/.venv/bin/core-api"]
