# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os, requests; requests.get(f'http://localhost:{os.environ.get(\"PORT\", 8000)}/health')"

# Run the application. Shell form (not exec-form JSON array) so $PORT is
# substituted at container start; Railway's deploy.startCommand overrides
# this anyway, but this is the fallback if that override is ever removed.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
