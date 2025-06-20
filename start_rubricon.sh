#!/bin/bash

# Rubricon Backend Startup Script for Oski
# This script ensures your Flask backend works with your Rubricon frontend

echo "🚀 Starting Oski Rubricon Backend..."
echo "===================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ and try again."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if backend.py exists
if [ ! -f "backend.py" ]; then
    echo "❌ backend.py not found in current directory."
    echo "   Please run this script in the same directory as backend.py"
    exit 1
fi

echo "✅ backend.py found"

# Check if .env file exists, create template if not
if [ ! -f ".env" ]; then
    echo "📝 Creating .env template file..."
    cat > .env << 'EOF'
# Azure OpenAI Configuration
AZURE_OPENAI_KEY=your_azure_openai_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini

# Alternative: ChatGPT API (if Azure OpenAI not available)  
CHATGPT_OPENAI_KEY=your_chatgpt_api_key_here

# Server Configuration
FLASK_PORT=5003
FLASK_HOST=0.0.0.0
FLASK_DEBUG=False
EOF
    echo "⚠️  IMPORTANT: Edit .env file with your actual API credentials!"
    echo "   Required: AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT"
else
    echo "✅ .env file found"
fi

# Check and install required packages
echo "🔧 Checking Python dependencies..."

REQUIRED_PACKAGES="flask flask-cors openai python-dotenv pandas openpyxl pdfplumber python-docx mammoth pillow"

for package in $REQUIRED_PACKAGES; do
    if ! python3 -c "import ${package//-/_}" 2>/dev/null; then
        echo "📦 Installing missing package: $package"
        pip3 install $package
    fi
done

echo "✅ All dependencies installed"

# Check if port 5003 is available
if lsof -Pi :5003 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 5003 is already in use."
    echo "   Attempting to stop existing process..."
    
    # Try to find and kill the process
    PID=$(lsof -ti :5003)
    if [ ! -z "$PID" ]; then
        kill $PID 2>/dev/null
        sleep 2
        echo "✅ Stopped existing process on port 5003"
    fi
fi

# Create temp directory if it doesn't exist
mkdir -p temp_uploads

# Test the backend first
echo "🧪 Testing backend functionality..."
if python3 backend.py 2>/dev/null; then
    echo "✅ Backend test passed"
else
    echo "⚠️  Backend test had issues, but continuing..."
fi

# Start the Flask server
echo ""
echo "🚀 Starting Flask server for Rubricon integration..."
echo "📍 Server will run on: http://localhost:5003"
echo "📋 Available endpoints:"
echo "   GET  /health        - Health check"  
echo "   POST /upload        - Upload and process files"
echo "   POST /download      - Download YAML files"
echo "   GET  /api/info      - API information"
echo ""
echo "🌐 For Rubricon frontend, ensure BACKEND_URL is set to:"
echo "   http://localhost:5003"
echo ""
echo "📊 Backend logs will be written to: backend.log"
echo "🛑 Press Ctrl+C to stop the server"
echo "===================================="

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping Rubricon backend..."
    echo "✅ Backend stopped successfully!"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Start the backend server
python3 backend.py --server

# If we get here, something went wrong
echo "❌ Backend server failed to start"
echo "🔍 Check backend.log for error details"
echo "💡 Common fixes:"
echo "   • Ensure .env file has valid API credentials"
echo "   • Check that port 5003 is available"
echo "   • Verify all dependencies are installed"
exit 1