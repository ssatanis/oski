#!/bin/bash

echo "🚀 Starting Oski Platform..."

# Kill any existing processes on port 8000
echo "Checking for existing processes on port 8000..."
PID=$(lsof -ti:8000)
if [ ! -z "$PID" ]; then
    echo "Killing existing process on port 8000 (PID: $PID)"
    kill $PID
    sleep 2
fi

# Start the backend
echo "Starting backend server..."
cd rubrics-to-prompts/backend

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env configuration file..."
    cat > .env << EOF
# Backend Configuration
DEBUG=true

# Azure OpenAI Configuration (Replace with your actual credentials)
AZURE_OPENAI_KEY=your_azure_openai_key_here
AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint_here
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name_here

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080,file://

# Tesseract Configuration
TESSERACT_CONFIG=--psm 6
EOF
fi

# Activate virtual environment and start backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "Backend started with PID: $BACKEND_PID"

# Wait for backend to start
echo "Waiting for backend to initialize..."
sleep 5

# Test backend health
echo "Testing backend connection..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is healthy and running!"
else
    echo "❌ Backend failed to start properly"
    exit 1
fi

# Go back to root directory
cd ../..

# Open the frontend in browser
echo "Opening frontend in browser..."
if command -v open &> /dev/null; then
    # macOS
    open promptgen.html
elif command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open promptgen.html
elif command -v start &> /dev/null; then
    # Windows
    start promptgen.html
else
    echo "Please manually open promptgen.html in your browser"
fi

echo ""
echo "🎉 Oski Platform is now running!"
echo ""
echo "📊 Backend API: http://localhost:8000"
echo "🌐 Frontend: Open promptgen.html in your browser"
echo "📋 Main Page: Open index.html in your browser"
echo ""
echo "To stop the backend, press Ctrl+C or run: kill $BACKEND_PID"
echo ""

# Keep the script running
wait $BACKEND_PID 