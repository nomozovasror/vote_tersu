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
# IMPORTANT: WebSocket with in-memory ConnectionManager requires single worker
# Multi-worker setup breaks WebSocket broadcast (each worker has own ConnectionManager)
# For production with multiple workers, implement Redis pub/sub or use sticky sessions
CMD python -m app.init_db && \
    uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --timeout-keep-alive 120 \
    --limit-concurrency 2000 \
    --backlog 2048 \
    --ws-ping-interval 20 \
    --ws-ping-timeout 30
