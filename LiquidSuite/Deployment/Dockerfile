# ============================================================================
# Dockerfile - Production-ready for Render.com
# ============================================================================
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 lsuite && \
    chown -R lsuite:lsuite /app && \
    mkdir -p /var/log && \
    touch /var/log/lsuite.log && \
    chown lsuite:lsuite /var/log/lsuite.log

# Switch to non-root user
USER lsuite

# Expose port (Render uses PORT env variable, defaults to 10000)
EXPOSE 10000

# Health check - using a simple curl to root endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/ || exit 1

# Start command - Render will override PORT via env
CMD gunicorn --workers=4 \
             --bind=0.0.0.0:${PORT:-10000} \
             --timeout=120 \
             --keep-alive=5 \
             --log-level=info \
             --access-logfile=- \
             --error-logfile=- \
             app:app
