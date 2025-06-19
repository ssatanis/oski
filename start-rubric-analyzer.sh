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
if [ -z "$AZURE_OPENAI_KEY" ] || [ "$AZURE_OPENAI_KEY" = "your_azure_openai_key_here" ]; then
    echo "⚠️  Warning: AZURE_OPENAI_KEY not set or using placeholder value"
    echo "   Please set your Azure OpenAI API key in the environment"
fi

if [ -z "$AZURE_OPENAI_ENDPOINT" ]; then
    echo "⚠️  Warning: AZURE_OPENAI_ENDPOINT not set"
    echo "   Please set your Azure OpenAI endpoint in the environment"
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

# Run the FastAPI server with auto-reload for development
uvicorn main:app --host 0.0.0.0 --port 8000 --reload 