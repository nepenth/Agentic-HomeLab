# Multi-stage build for Python 3.12
FROM python:3.12-slim AS builder

# Set build arguments
ARG BUILD_DEPS="build-essential libpq-dev"

# Install build dependencies including Playwright requirements
RUN apt-get update && apt-get install -y $BUILD_DEPS \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    libcups2 \
    libxfixes3 \
    libpango-1.0-0 \
    libcairo2

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

# Production stage
FROM python:3.12-slim

# Install runtime dependencies including Playwright requirements
RUN apt-get update && apt-get install -y \
    libpq5 \
    libmagic1 \
    curl \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    libcups2 \
    libxfixes3 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Create logs and media directories
RUN mkdir -p /app/logs /app/media && chown -R app:app /app

# Switch to app user for browser installation
USER app

# Install Playwright browsers as app user
RUN playwright install chromium

# Switch back to root for final setup
USER root

# Create Playwright cache directory and set permissions
RUN mkdir -p /home/app/.cache && chown -R app:app /home/app/.cache

# Switch to app user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]