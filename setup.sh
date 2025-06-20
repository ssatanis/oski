#!/bin/bash

echo "🚀 Setting up Rubricon Medical Rubric Processing System..."

# Check if .env.template exists
if [ ! -f ".env.template" ]; then
    echo "❌ Error: .env.template not found!"
    exit 1
fi

# Copy environment template if .env doesn't exist
if [ ! -f ".env" ]; then
    echo "📋 Creating .env file from template..."
    cp .env.template .env
    echo "✅ Created .env file"
    echo "⚠️  Please edit .env with your actual API keys before starting the server"
else
    echo "⚠️  .env file already exists"
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
if [ -f "backend-requirements.txt" ]; then
    pip install -r backend-requirements.txt
    echo "✅ Dependencies installed"
else
    echo "❌ Error: backend-requirements.txt not found!"
    exit 1
fi

# Make scripts executable
echo "🔧 Making scripts executable..."
chmod +x check_backend.sh
chmod +x test_integration.sh 
chmod +x keep_backend_running.sh
chmod +x start_backend.sh
echo "✅ Scripts are now executable"

# Check if backend can start
echo "🧪 Testing backend startup..."
python3 -c "import flask, pandas, openai, python_docx, PyPDF2, openpyxl, PIL; print('✅ All required modules available')" 2>/dev/null || {
    echo "❌ Some required modules are missing. Please run: pip install -r backend-requirements.txt"
    exit 1
}

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys:"
echo "   - AZURE_OPENAI_KEY=your_azure_key"
echo "   - CHATGPT_OPENAI_KEY=your_openai_key"
echo ""
echo "2. Start the backend:"
echo "   python3 backend.py --server"
echo ""
echo "3. Open rubricon.html in your browser"
echo ""
echo "4. Use monitoring scripts:"
echo "   ./check_backend.sh        # Check status"
echo "   ./test_integration.sh     # Test integration"
echo "   ./keep_backend_running.sh # Keep running"
echo ""
echo "📚 See README.md for detailed documentation" 