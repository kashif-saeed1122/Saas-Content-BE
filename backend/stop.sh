#!/bin/bash

echo "🛑 Stopping NeuralGen Backend Services..."

# Kill FastAPI
echo "Stopping FastAPI..."
pkill -f "uvicorn main:app"

# Kill Celery Worker
echo "Stopping Celery Worker..."
pkill -f "celery -A celery_app worker"

# Kill Celery Beat
echo "Stopping Celery Beat..."
pkill -f "celery -A celery_app beat"

# Stop Redis
echo "Stopping Redis..."
docker-compose down

echo "✅ All services stopped!"
