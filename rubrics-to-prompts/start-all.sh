#!/bin/bash

echo "🚀 Starting Rubrics to Prompts Application..."
echo "=========================================="

# Function to check if a port is available
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "❌ Port $1 is already in use. Please stop the service using this port."
        return 1
    fi
    return 0
}

# Check if required ports are available
echo "🔍 Checking port availability..."
if ! check_port 8000; then
    echo "Backend port 8000 is in use. Please stop the service and try again."
    exit 1
fi

if ! check_port 3000; then
    echo "Frontend port 3000 is in use. Please stop the service and try again."
    exit 1
fi

echo "✅ Ports are available!"

# Check if we have the required dependencies
echo "🔍 Checking dependencies..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ and try again."
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ and try again."
    exit 1
fi

# Check npm
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm and try again."
    exit 1
fi

echo "✅ All dependencies are available!"

# Create log directory
mkdir -p logs

echo "🔧 Setting up environment files..."

# Setup backend environment if not exists
if [ ! -f backend/.env ]; then
    echo "📝 Creating backend .env file..."
    cp backend/env_example.txt backend/.env
    echo "⚠️  IMPORTANT: Please edit backend/.env with your Azure OpenAI credentials:"
    echo "   - AZURE_OPENAI_KEY"
    echo "   - AZURE_OPENAI_ENDPOINT"
    echo "   - AZURE_OPENAI_DEPLOYMENT_NAME"
    echo ""
fi

# Setup frontend environment if not exists
if [ ! -f frontend/.env.local ]; then
    echo "📝 Creating frontend .env.local file..."
    cp frontend/env.example frontend/.env.local
    echo "✅ Frontend environment configured!"
fi

echo "🚀 Starting services..."

# Start backend in background
echo "🐍 Starting FastAPI backend..."
(
    cd backend
    source venv/bin/activate 2>/dev/null || {
        echo "❌ Virtual environment not found. Running setup..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    }
    pip install -r requirements.txt > ../logs/backend-install.log 2>&1
    echo "✅ Backend dependencies installed!"
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ../logs/backend.log 2>&1
) &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend in background
echo "⚛️ Starting Next.js frontend..."
(
    cd frontend
    npm install > ../logs/frontend-install.log 2>&1
    echo "✅ Frontend dependencies installed!"
    npm run dev > ../logs/frontend.log 2>&1
) &
FRONTEND_PID=$!

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 5

# Check if services are running
echo "🔍 Checking service status..."

if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is running on http://localhost:8000"
else
    echo "❌ Backend failed to start. Check logs/backend.log for details."
fi

if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Frontend is running on http://localhost:3000"
else
    echo "⏳ Frontend is still starting... This may take a moment."
fi

echo ""
echo "🎉 Rubrics to Prompts Application Started!"
echo "========================================="
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "📱 You can now visit r2b.html to see the integrated application!"
echo ""
echo "📋 Important Notes:"
echo "   • Make sure to configure your Azure OpenAI credentials in backend/.env"
echo "   • The application requires an internet connection for AI processing"
echo "   • Supported file types: PDF, DOC, DOCX, XLS, XLSX, TXT, CSV, images"
echo ""
echo "🛑 To stop the application, press Ctrl+C"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ Services stopped!"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Keep script running and show logs
echo "📋 Application logs (press Ctrl+C to stop):"
echo "==========================================="

# Wait for background processes
wait 