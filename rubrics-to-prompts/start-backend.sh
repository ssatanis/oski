#!/bin/bash

echo "Starting Rubrics to Prompts Backend..."

# Navigate to backend directory
cd backend

# Activate virtual environment
source venv/bin/activate

# Check if .env exists, create from template if not
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp env_example.txt .env
    echo "Please edit .env file with your Azure OpenAI credentials!"
    echo "Required variables:"
    echo "- AZURE_OPENAI_KEY"
    echo "- AZURE_OPENAI_ENDPOINT"  
    echo "- AZURE_OPENAI_DEPLOYMENT_NAME"
fi

# Install dependencies if needed
pip install -r requirements.txt

# Start the FastAPI server
echo "Starting FastAPI server on port 8000..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload 