#!/bin/bash

# Rubricon Application Startup Script
echo "🚀 Starting Rubricon Application..."

# Kill any existing servers
echo "📋 Cleaning up existing servers..."
pkill -f "python.*main.py" 2>/dev/null
pkill -f "python.*http.server" 2>/dev/null
pkill -f "uvicorn" 2>/dev/null
sleep 2

# Start Backend Server (Port 8000)
echo "🔧 Starting Backend Server on http://localhost:8000..."
cd /Users/sahajsatani/Documents/Oski/rubrics-to-prompts/backend
python3 main.py &
BACKEND_PID=$!

# Start Frontend Server (Port 3000)
echo "🌐 Starting Frontend Server on http://localhost:3000..."
cd /Users/sahajsatani/Documents/Oski
python3 -m http.server 3000 &
FRONTEND_PID=$!

# Wait for servers to start
echo "⏳ Waiting for servers to initialize..."
sleep 5

# Test Backend
echo "🧪 Testing Backend Health..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is healthy!"
else
    echo "❌ Backend failed to start"
    exit 1
fi

# Test Frontend
echo "🧪 Testing Frontend Server..."
if curl -s -I http://localhost:3000/rubricon.html | grep -q "200 OK"; then
    echo "✅ Frontend is serving files!"
else
    echo "❌ Frontend failed to start"
    exit 1
fi

echo ""
echo "🎉 SUCCESS! Rubricon is now running!"
echo ""
echo "📍 ACCESS URLS:"
echo "   Frontend: http://localhost:3000/rubricon.html"
echo "   Clean Version: http://localhost:3000/rubricon-clean.html"
echo "   Test Interface: http://localhost:3000/test-rubricon.html"
echo "   Backend API: http://localhost:8000"
echo "   Backend Health: http://localhost:8000/health"
echo ""
echo "🔧 Process IDs:"
echo "   Backend PID: $BACKEND_PID"
echo "   Frontend PID: $FRONTEND_PID"
echo ""
echo "🛑 To stop servers: pkill -f 'python.*main.py' && pkill -f 'python.*http.server'"
echo ""
echo "📱 Ready to use! Open http://localhost:3000/rubricon.html in your browser" 