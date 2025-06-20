#!/bin/bash

echo "🚀 Starting Rubricon Backend Server..."
echo "=================================="

# Check if backend.py exists
if [ ! -f "backend.py" ]; then
    echo "❌ Error: backend.py not found in current directory"
    echo "   Please make sure you're in the correct directory"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   Azure OpenAI features may not work"
fi

# Kill any existing backend processes
echo "🔄 Stopping any existing backend processes..."
pkill -f "python.*backend" 2>/dev/null || true

# Wait a moment
sleep 2

# Start the backend server
echo "🚀 Starting backend server on port 5001..."
echo "📍 Health check: http://localhost:5001/health"
echo "📋 Upload endpoint: http://localhost:5001/upload"
echo "📥 Download endpoint: http://localhost:5001/download"
echo "=================================="
echo "✅ Backend ready for Rubricon!"
echo "   Open rubricon.html in your browser"
echo "   Press Ctrl+C to stop the server"
echo "=================================="

python3 backend.py --server 