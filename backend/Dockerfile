# syntax=docker/dockerfile:1
# ==============================================================================
# ORACLE Backend Container (Local Build Context: backend/)
# Multi-runtime image providing Python 3.12, Node.js (TypeScript AST Worker),
# and OpenJDK 17 (Java AST Worker) in a hardened, non-root environment.
# ==============================================================================

FROM python:3.12-slim AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    NODE_PATH=/usr/local/lib/node_modules \
    PYTHONPATH=/app

# Install system runtime dependencies: OpenJDK 17 headless, Node.js, npm, curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jdk-headless \
    nodejs \
    npm \
    curl \
    ca-certificates \
    && npm install -g typescript \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated unprivileged user and group (least privilege principle)
RUN groupadd -g 10001 oracle && \
    useradd -u 10001 -g oracle -m -s /bin/bash oracle

WORKDIR /app

# Install Python backend dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application source code, Alembic configuration, and migrations
COPY oracle /app/oracle
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

# Precompile Java AST worker ahead of time for low-latency static analysis
RUN javac /app/oracle/inspection/JavaAstWorker.java

# Ensure the unprivileged user owns the application directory
RUN chown -R oracle:oracle /app

# Switch to non-root execution
USER oracle:oracle

# Expose internal FastAPI HTTP port
EXPOSE 8000

# Container liveness health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "oracle.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
