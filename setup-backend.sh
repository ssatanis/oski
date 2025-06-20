#!/bin/bash

# Setup script for Python backend integration
echo "Setting up Python backend for rubric processing..."

# Create virtual environment if it doesn't exist
BACKEND_DIR="./rubrics-to-prompts/backend"
VENV_DIR="$BACKEND_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment..."
    cd "$BACKEND_DIR"
    python3 -m venv venv
    cd - > /dev/null
fi

# Activate virtual environment and install dependencies
echo "Installing Python dependencies..."
cd "$BACKEND_DIR"
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Test the backend
echo "Testing backend functionality..."
python3 -c "
import sys
sys.path.append('.')
from backend import generate_default_rubric
import json

# Test default rubric generation
result = generate_default_rubric()
print('Backend test successful!')
print(f'Generated rubric with {len(result[\"criteria\"])} criteria')
"

if [ $? -eq 0 ]; then
    echo "✅ Python backend setup complete and working!"
else
    echo "❌ Backend test failed. Please check dependencies."
    exit 1
fi

cd - > /dev/null

# Create environment file for OpenAI if it doesn't exist
ENV_FILE="$BACKEND_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "Creating .env file template..."
    cat > "$ENV_FILE" << EOF
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Azure OpenAI Configuration
AZURE_OPENAI_KEY=your_azure_openai_key_here
AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint_here
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name_here

# Debug mode
DEBUG=true
EOF
    echo "Created .env file at $ENV_FILE"
    echo "Please update it with your actual API keys."
fi

echo "Backend setup complete! 🎉"
echo ""
echo "Next steps:"
echo "1. Update $ENV_FILE with your OpenAI API key"
echo "2. The backend will now be used for intelligent rubric processing"
echo "3. Upload a file to test the integration" 