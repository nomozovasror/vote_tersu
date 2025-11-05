#!/bin/bash

echo "🛑 Stopping Real-Time Voting System"
echo "====================================="

# Check if using Docker
if docker ps | grep -q voting_; then
    echo "🐳 Stopping Docker containers..."
    docker-compose down
    echo "✅ Docker containers stopped"
else
    echo "🔧 Stopping manual processes..."

    # Stop backend
    if [ -f "backend.pid" ]; then
        BACKEND_PID=$(cat backend.pid)
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            kill $BACKEND_PID
            echo "✅ Backend stopped (PID: $BACKEND_PID)"
        fi
        rm backend.pid
    fi

    # Stop frontend
    if [ -f "frontend.pid" ]; then
        FRONTEND_PID=$(cat frontend.pid)
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            kill $FRONTEND_PID
            echo "✅ Frontend stopped (PID: $FRONTEND_PID)"
        fi
        rm frontend.pid
    fi

    # Kill any remaining processes on ports
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    lsof -ti:5173 | xargs kill -9 2>/dev/null

    echo "✅ All processes stopped"
fi
