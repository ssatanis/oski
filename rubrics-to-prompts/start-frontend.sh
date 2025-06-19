#!/bin/bash

echo "Starting Rubrics to Prompts Frontend..."

# Navigate to frontend directory
cd frontend

# Check if .env.local exists, create from template if not
if [ ! -f .env.local ]; then
    echo "Creating .env.local file from template..."
    cp env.example .env.local
    echo ".env.local created successfully!"
fi

# Install dependencies
echo "Installing dependencies..."
npm install

# Start the development server
echo "Starting Next.js development server on port 3000..."
npm run dev 