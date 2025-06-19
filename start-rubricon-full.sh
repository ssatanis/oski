#!/bin/bash

echo "🚀 Starting Rubricon Application..."
echo "======================================"

# Function to kill processes on exit
cleanup() {
    echo "🛑 Shutting down servers..."
    pkill -f "uvicorn main:app"
    pkill -f "python -m http.server 3000"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check if we're in the right directory
if [ ! -f "rubricon.html" ]; then
    echo "❌ Error: rubricon.html not found in current directory"
    echo "Please run this script from the Oski root directory"
    exit 1
fi

# Start backend server
echo "📡 Starting Backend Server on http://localhost:8001..."
cd rubrics-to-prompts/backend

# Check if backend dependencies are installed
if ! python -c "import fastapi" &> /dev/null; then
    echo "📦 Installing backend dependencies..."
    pip install fastapi uvicorn python-multipart openai python-dotenv aiofiles PyYAML PyPDF2 python-docx mammoth openpyxl pdfplumber pandas
fi

# Start backend in background
nohup uvicorn main:app --host 127.0.0.1 --port 8001 --reload > backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to initialize..."
sleep 3

# Test backend health
if curl -s http://localhost:8001/health > /dev/null; then
    echo "✅ Backend running at http://localhost:8001"
else
    echo "❌ Backend failed to start. Check backend.log for errors"
    exit 1
fi

# Go back to root directory
cd ../..

# Start frontend server
echo "🌐 Starting Frontend Server on http://localhost:3000..."
nohup python -m http.server 3000 > frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 2

# Test frontend
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Frontend running at http://localhost:3000"
else
    echo "❌ Frontend failed to start. Check frontend.log for errors"
    exit 1
fi

echo ""
echo "🎉 Rubricon Application is now running!"
echo "======================================"
echo "📱 Frontend:  http://localhost:3000"
echo "🔧 Rubricon:  http://localhost:3000/rubricon.html"
echo "📡 Backend:   http://localhost:8001"
echo "📊 Health:    http://localhost:8001/health"
echo ""
echo "📋 Test file: test-rubric.txt is available for testing"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "======================================"

# Keep script running and wait for Ctrl+C
wait 