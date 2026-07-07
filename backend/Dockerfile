# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Add src to Python path so internal imports work
ENV PYTHONPATH=/app:/app/src

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r ./requirements.txt

# Copy application code and ML pipeline
COPY backend/ .
COPY src/ ./src/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Cache bust: 2026-07-07T06:00:00Z
# Run the application with verbose logging to debug startup issues
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level debug
