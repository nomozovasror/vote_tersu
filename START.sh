#!/bin/bash

echo "🚀 Starting Real-Time Voting System"
echo "===================================="

# Check if Docker is available
if command -v docker-compose &> /dev/null; then
    echo "✅ Docker Compose found"
    echo "🔨 Building containers..."
    docker-compose build
    echo "🚀 Starting containers..."
    docker-compose up -d
    echo ""
    echo "✅ Application started!"
    echo "📱 Frontend: http://localhost:5173"
    echo "🔧 Backend API: http://localhost:8000"
    echo "📚 API Docs: http://localhost:8000/docs"
    echo ""
    echo "👤 Default login:"
    echo "   Username: admin"
    echo "   Password: admin123"
    echo ""
    echo "📋 To view logs: docker-compose logs -f"
    echo "🛑 To stop: docker-compose down"
else
    echo "⚠️  Docker not found. Starting manually..."
    echo ""

    # Start Backend
    echo "🔧 Starting Backend..."
    cd api

    # Check if venv exists
    if [ ! -d "venv" ]; then
        echo "📦 Creating virtual environment..."
        python3 -m venv venv
    fi

    source venv/bin/activate

    # Install dependencies if needed
    if [ ! -f "venv/.installed" ]; then
        echo "📦 Installing dependencies..."
        pip install -r requirements.txt
        touch venv/.installed
    fi

    # Initialize database
    if [ ! -f "../data/voting.db" ]; then
        echo "🗄️  Initializing database..."
        mkdir -p ../data
        python -m app.init_db
    fi

    # Start backend in background
    echo "🚀 Starting backend server..."
    uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
    BACKEND_PID=$!
    echo "✅ Backend started (PID: $BACKEND_PID)"

    cd ..

    # Start Frontend
    echo ""
    echo "🌐 Starting Frontend..."
    cd web

    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo "📦 Installing dependencies..."
        npm install
    fi

    # Create .env if not exists
    if [ ! -f ".env" ]; then
        echo "VITE_API_URL=http://localhost:8000" > .env
    fi

    # Start frontend in background
    echo "🚀 Starting frontend server..."
    npm run dev > ../frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "✅ Frontend started (PID: $FRONTEND_PID)"

    cd ..

    # Save PIDs
    echo $BACKEND_PID > backend.pid
    echo $FRONTEND_PID > frontend.pid

    echo ""
    echo "✅ Application started!"
    echo "📱 Frontend: http://localhost:5173"
    echo "🔧 Backend API: http://localhost:8000"
    echo "📚 API Docs: http://localhost:8000/docs"
    echo ""
    echo "👤 Default login:"
    echo "   Username: admin"
    echo "   Password: admin123"
    echo ""
    echo "📋 Backend logs: tail -f backend.log"
    echo "📋 Frontend logs: tail -f frontend.log"
    echo ""
    echo "🛑 To stop: ./STOP.sh"
fi
