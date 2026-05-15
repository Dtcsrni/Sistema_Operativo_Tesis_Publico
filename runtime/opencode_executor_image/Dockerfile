FROM python:3.11-slim

LABEL maintainer="Erick Renato Vega Ceron"
LABEL description="OpenCode Executor Subordinado — Servidor headless para ejecución de tareas con RAG Weaviate"
LABEL version="1.0"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    nodejs \
    npm \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g opencode-ai
RUN pip install --upgrade pip setuptools wheel && \
    pip install litellm requests pydantic

ENV OPENCLAW_REPO_ROOT=/app
ENV OPENCLAW_DATA_DIR=/app/runtime/openclaw/state
ENV OPENCLAW_CACHE_DIR=/app/runtime/openclaw/cache
ENV OPENCLAW_LOG_DIR=/app/runtime/openclaw/logs
ENV PYTHONUNBUFFERED=1
ENV OPENCODE_MODEL=deepseek-r1:7b
ENV OPENCODE_PROVIDER=ollama
ENV OPENCODE_BASE_URL=http://ollama-pc:11434/v1
ENV OPENCODE_CONFIG=/app/opencode.json

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=20s \
    CMD opencode --version || exit 1

WORKDIR /app
CMD ["opencode", "serve", "--hostname", "0.0.0.0", "--port", "4096"]
