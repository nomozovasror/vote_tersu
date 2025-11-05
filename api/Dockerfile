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

# Run database initialization and start server
# Set timeout to 300 seconds for long-running operations
CMD python -m app.init_db && uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 300
