# ============================================================
# Dockerfile — Queue Management System
# Multi-stage build: smaller final image, no build tools
# ============================================================

# ---- Stage 1: Build ----------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---- Stage 2: Runtime ---------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime OS deps only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN useradd -m -u 1000 appuser

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=appuser:appuser . .

# Remove dev/test files from the image
RUN rm -rf tests/ *.test.py __pycache__ .git .env

USER appuser

EXPOSE 8001

# Healthcheck (docker will mark container unhealthy if /health fails)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8001/health').raise_for_status()"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
