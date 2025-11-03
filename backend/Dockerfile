# Multi-stage Dockerfile pour OHADA Backend

# ====================
# Stage 1: Builder
# ====================
FROM python:3.10-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# ====================
# Stage 2: Runtime
# ====================
FROM python:3.10-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app user (security best practice)
RUN useradd -m -u 1000 ohada && \
    mkdir -p /app /app/data /app/logs && \
    chown -R ohada:ohada /app

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=ohada:ohada . /app/

# Switch to non-root user
USER ohada

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Start application
CMD ["uvicorn", "src.api.ohada_api_server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
