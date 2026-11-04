# ---- Build stage: build wheels for the project and its dependencies ----
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY config ./config
COPY src ./src
RUN pip wheel --no-cache-dir --wheel-dir /wheels .

# ---- Runtime stage: install from the wheels only ----
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels mcp-server \
    && rm -rf /wheels
COPY main.py .
RUN useradd --create-home appuser
USER appuser
# MCP_PORT has no default, so the probe reads the port the server was started with.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen(f\"http://localhost:{os.environ['MCP_PORT']}/health\")"]
CMD ["python", "main.py"]
