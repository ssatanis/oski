#!/bin/bash

echo "🔍 Checking Rubricon Backend Status..."

# Check if backend is responding
if curl -s http://localhost:5002/health > /dev/null 2>&1; then
    echo "✅ Backend is running and healthy"
    echo "📊 Health check:"
    curl -s http://localhost:5002/health | jq
    echo
    echo "🧪 Quick upload test:"
    if [ -f "Note Checklist - Station 1A - Rash - Psoriasis.xlsx" ]; then
        RESULT=$(curl -s -X POST http://localhost:5002/upload -F "file=@Note Checklist - Station 1A - Rash - Psoriasis.xlsx" | jq -r '.success, (.yaml_content | length)')
        echo "   Success: $(echo "$RESULT" | head -1)"
        echo "   YAML Length: $(echo "$RESULT" | tail -1) characters"
    else
        echo "   Test file not found"
    fi
else
    echo "❌ Backend not responding"
    echo "🔧 Checking port usage:"
    lsof -i :5002 || echo "   Port 5002 is free"
    echo
    echo "🚀 Starting backend..."
    python3 run_backend_stable.py &
    sleep 5
    if curl -s http://localhost:5002/health > /dev/null 2>&1; then
        echo "✅ Backend started successfully"
    else
        echo "❌ Failed to start backend"
        exit 1
    fi
fi

echo
echo "🌐 Ready for browser testing at: rubricon.html" 