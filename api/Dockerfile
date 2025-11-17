FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directory for SQLite
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Set environment variables for production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run database initialization and start server
# Multi-worker setup for handling 200+ concurrent WebSocket connections
# --workers: Number of worker processes (default 6, can be overridden via env)
# --timeout-keep-alive: Keep WebSocket connections alive longer
# --limit-concurrency: Max concurrent connections per worker
# --backlog: Connection queue size
CMD python -m app.init_db && \
    uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers ${WEB_CONCURRENCY:-6} \
    --timeout-keep-alive 120 \
    --limit-concurrency 500 \
    --backlog 2048 \
    --ws-ping-interval 20 \
    --ws-ping-timeout 30
