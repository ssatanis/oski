#!/bin/bash

# Start Rubric Analyzer - Comprehensive OCR Document Processing System
# This script starts the FastAPI backend for rubric analysis

echo "🏥 Starting Comprehensive Rubric Analyzer"
echo "=========================================="

# Check if we're in the right directory
if [ ! -d "rubrics-to-prompts" ]; then
    echo "❌ Error: rubrics-to-prompts directory not found"
    echo "Please run this script from the main Oski directory"
    exit 1
fi

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)/rubrics-to-prompts/backend"

# Change to backend directory
cd rubrics-to-prompts/backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade requirements
echo "📋 Installing requirements..."
pip install -r requirements.txt

# Install additional dependencies for our enhanced backend
echo "📦 Installing additional dependencies..."
pip install pandas openpyxl python-docx mammoth pdfplumber

# Check for environment variables
echo "🔑 Checking Azure OpenAI configuration..."
if [ -z "$AZURE_OPENAI_KEY" ] || [ "$AZURE_OPENAI_KEY" = "your_azure_openai_key_here" ]; then
    echo "⚠️  Warning: AZURE_OPENAI_KEY not set or using placeholder value"
    echo "   Please set your Azure OpenAI API key:"
    echo "   export AZURE_OPENAI_KEY='your-actual-key-here'"
    echo ""
fi

if [ -z "$AZURE_OPENAI_ENDPOINT" ]; then
    echo "⚠️  Warning: AZURE_OPENAI_ENDPOINT not set"
    echo "   Please set your Azure OpenAI endpoint:"
    echo "   export AZURE_OPENAI_ENDPOINT='https://your-resource.openai.azure.com/'"
    echo ""
fi

if [ -z "$AZURE_OPENAI_DEPLOYMENT_NAME" ]; then
    echo "ℹ️  AZURE_OPENAI_DEPLOYMENT_NAME not set, using default 'gpt-4o-mini'"
    export AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o-mini"
fi

# Start the FastAPI server
echo "🚀 Starting FastAPI backend on http://localhost:8000"
echo ""
echo "📂 Supported file formats:"
echo "   • PDF documents (.pdf)"
echo "   • Word documents (.docx, .doc)" 
echo "   • Excel spreadsheets (.xlsx, .xls)"
echo ""
echo "🌐 Frontend available at: file://$(pwd)/../../rubric-analyzer.html"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================="

# Test the backend first
echo "🧪 Testing backend functionality..."
python -c "
try:
    from backend import upload_file
    print('✅ Backend import successful')
except Exception as e:
    print(f'❌ Backend import failed: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo "✅ Backend tests passed"
else
    echo "❌ Backend tests failed - please check configuration"
    exit 1
fi

echo ""

# Run the FastAPI server with auto-reload for development
uvicorn main:app --host 0.0.0.0 --port 8000 --reload 