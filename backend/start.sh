#!/bin/bash

echo "🚀 Starting NeuralGen Backend Services..."

# Start Redis
echo "📦 Starting Redis..."
docker-compose up -d

# Wait for Redis
echo "⏳ Waiting for Redis..."
sleep 2

# Start FastAPI in background
echo "🌐 Starting FastAPI server..."
uvicorn main:app --reload --port 8000 &
API_PID=$!

# Start Celery Worker in background
echo "⚙️  Starting Celery Worker..."
celery -A celery_app worker --loglevel=info &
WORKER_PID=$!

# Start Celery Beat in background
echo "⏰ Starting Celery Beat..."
celery -A celery_app beat --loglevel=info &
BEAT_PID=$!

echo ""
echo "✅ All services started!"
echo ""
echo "📊 Service URLs:"
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo "   Redis: localhost:6379"
echo ""
echo "🛑 To stop all services, run: ./stop.sh"

# Keep script running
wait $API_PID $WORKER_PID $BEAT_PID
