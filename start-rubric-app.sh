#!/bin/bash

echo "🚀 Starting Oski Rubric Upload Application..."
echo "=============================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r backend-requirements.txt

# Check if AZURE_OPENAI_KEY is set
if [ -z "$AZURE_OPENAI_KEY" ]; then
    echo "⚠️  WARNING: AZURE_OPENAI_KEY environment variable is not set."
    echo "   Please set it before running the application:"
    echo "   export AZURE_OPENAI_KEY='your-api-key-here'"
    echo ""
fi

# Start the backend server in the background
echo "🖥️  Starting backend server on http://localhost:5000..."
python backend.py &
BACKEND_PID=$!

# Give backend time to start
sleep 3

# Check if backend is running
if ! curl -s http://localhost:5000 > /dev/null; then
    echo "⚠️  Backend server may not be running properly"
fi

# Start a simple HTTP server for the frontend
echo "🌐 Starting frontend server on http://localhost:8080..."
echo ""
echo "📱 Open your browser and go to: http://localhost:8080/rubricon.html"
echo ""
echo "🛑 Press Ctrl+C to stop both servers"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    exit 0
}

# Trap Ctrl+C
trap cleanup INT

# Start frontend server
python3 -m http.server 8080

# Cleanup when script exits
cleanup 