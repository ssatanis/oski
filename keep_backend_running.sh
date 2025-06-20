#!/bin/bash

echo "🔄 Keeping backend running continuously..."
echo "Press Ctrl+C to stop"

while true; do
    # Check if backend is running
    if ! pgrep -f "python.*backend.*--server" > /dev/null; then
        echo "🚀 Starting backend server..."
        python3 backend.py --server &
        sleep 5
    fi
    
    # Check if server is responding
    if curl -s http://localhost:5002/health > /dev/null 2>&1; then
        echo "✅ Backend is running and healthy"
    else
        echo "❌ Backend not responding, restarting..."
        pkill -f "python.*backend"
        sleep 2
        python3 backend.py --server &
        sleep 5
    fi
    
    sleep 10
done 