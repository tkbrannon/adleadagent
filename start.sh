#!/bin/bash
set -e

# Start Redis in background
redis-server --daemonize yes --bind 127.0.0.1 --port 6379

# Wait for Redis to be ready
echo "Waiting for Redis..."
until redis-cli ping > /dev/null 2>&1; do
  sleep 1
done
echo "Redis is ready!"

# Start Celery worker in background
celery -A app.celery_app worker --loglevel=info --concurrency=2 &

# Start Gmail poller in background
python poller.py &

# Start FastAPI (foreground)
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
