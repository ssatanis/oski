#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -i:$port >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill processes on specific ports
kill_port() {
    local port=$1
    print_warning "Killing processes on port $port..."
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
}

# Function to wait for service to be ready
wait_for_service() {
    local port=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $service_name to be ready on port $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:$port/health >/dev/null 2>&1 || curl -s http://localhost:$port >/dev/null 2>&1; then
            print_success "$service_name is ready on port $port!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to start on port $port after $((max_attempts * 2)) seconds"
    return 1
}

# Cleanup function
cleanup() {
    print_warning "Shutting down all services..."
    kill_port 3000  # PromptGen Frontend
    kill_port 8000  # PromptGen Backend
    kill_port 3001  # OSCE Video Grader Frontend  
    kill_port 8001  # OSCE Video Grader Backend
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

print_status "🚀 Starting Oski Complete Application Suite..."
print_status "This will start:"
print_status "  - PromptGen Frontend (http://localhost:3000)"
print_status "  - PromptGen Backend (http://localhost:8000)" 
print_status "  - OSCE Video Grader Frontend (http://localhost:3001)"
print_status "  - OSCE Video Grader Backend (http://localhost:8001)"
echo ""

# Check if ports are available and kill if necessary
for port in 3000 8000 3001 8001; do
    if check_port $port; then
        print_warning "Port $port is already in use."
        kill_port $port
        sleep 2
    fi
done

# Create log directory
mkdir -p logs

print_status "📦 Installing dependencies..."

# Install PromptGen dependencies
cd rubrics-to-prompts/frontend
if [ ! -d "node_modules" ]; then
    print_status "Installing PromptGen frontend dependencies..."
    npm install --silent
fi

cd ../backend
if [ ! -d "venv" ]; then
    print_status "Creating PromptGen backend virtual environment..."
    python3 -m venv venv
fi

print_status "Installing PromptGen backend dependencies..."
source venv/bin/activate
pip install -r requirements.txt --quiet

# Install OSCE Video Grader dependencies
cd ../../osce-video-grader/web
if [ ! -d "node_modules" ]; then
    print_status "Installing OSCE Video Grader frontend dependencies..."
    npm install --silent
fi

cd ../backend
if [ ! -f ".env" ]; then
    print_warning "Creating OSCE Video Grader backend .env file..."
    touch .env
fi

cd ../../

print_success "Dependencies installed successfully!"

# Create .env files if they don't exist
if [ ! -f "rubrics-to-prompts/frontend/.env" ]; then
    print_status "Creating PromptGen frontend .env file..."
    echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > rubrics-to-prompts/frontend/.env
fi

if [ ! -f "rubrics-to-prompts/backend/.env" ]; then
    print_status "Creating PromptGen backend .env file..."
    cp rubrics-to-prompts/backend/env_example.txt rubrics-to-prompts/backend/.env
fi

print_status "🎬 Starting OSCE Video Grader Backend (Port 8001)..."
cd osce-video-grader/backend
python3 -m uvicorn app:app --host 0.0.0.0 --port 8001 --reload > ../../logs/osce-backend.log 2>&1 &
OSCE_BACKEND_PID=$!

cd ../../

print_status "📄 Starting PromptGen Backend (Port 8000)..."
cd rubrics-to-prompts/backend
source venv/bin/activate
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ../../logs/promptgen-backend.log 2>&1 &
PROMPTGEN_BACKEND_PID=$!

cd ../../

print_status "⚛️ Starting OSCE Video Grader Frontend (Port 3001)..."
cd osce-video-grader/web
npm run dev -- --port 3001 > ../../logs/osce-frontend.log 2>&1 &
OSCE_FRONTEND_PID=$!

cd ../../

print_status "🎨 Starting PromptGen Frontend (Port 3000)..."
cd rubrics-to-prompts/frontend
npm run dev > ../../logs/promptgen-frontend.log 2>&1 &
PROMPTGEN_FRONTEND_PID=$!

cd ../../

# Wait for services to be ready
print_status "⏳ Waiting for all services to start..."

sleep 5

# Check if all services are running
services_ready=true

if ! wait_for_service 8001 "OSCE Video Grader Backend"; then
    services_ready=false
fi

if ! wait_for_service 8000 "PromptGen Backend"; then
    services_ready=false
fi

if ! wait_for_service 3001 "OSCE Video Grader Frontend"; then
    services_ready=false
fi

if ! wait_for_service 3000 "PromptGen Frontend"; then
    services_ready=false
fi

if [ "$services_ready" = true ]; then
    echo ""
    print_success "🎉 All services are running successfully!"
    echo ""
    print_status "📱 Application URLs:"
    print_status "  PromptGen:           http://localhost:3000"
    print_status "  PromptGen API:       http://localhost:8000/docs"
    print_status "  OSCE Video Grader:   http://localhost:3001" 
    print_status "  OSCE API:            http://localhost:8001/docs"
    echo ""
    print_status "🌐 Website URLs:"
    print_status "  Home Page:           file://$(pwd)/index.html"
    print_status "  PromptGen Page:      file://$(pwd)/promptgen.html"
    print_status "  Simulation Page:     file://$(pwd)/simulation.html"
    echo ""
    print_status "📋 Log files are available in the 'logs' directory"
    print_status "💡 Press Ctrl+C to stop all services"
    echo ""
    
    # Keep the script running and monitor services
    while true; do
        # Check if any service has died
        if ! kill -0 $PROMPTGEN_BACKEND_PID 2>/dev/null; then
            print_error "PromptGen Backend has stopped!"
            break
        fi
        if ! kill -0 $PROMPTGEN_FRONTEND_PID 2>/dev/null; then
            print_error "PromptGen Frontend has stopped!"
            break
        fi
        if ! kill -0 $OSCE_BACKEND_PID 2>/dev/null; then
            print_error "OSCE Video Grader Backend has stopped!"
            break
        fi
        if ! kill -0 $OSCE_FRONTEND_PID 2>/dev/null; then
            print_error "OSCE Video Grader Frontend has stopped!"
            break
        fi
        
        sleep 5
    done
else
    print_error "Some services failed to start. Check the logs for details:"
    print_error "  PromptGen Backend:   logs/promptgen-backend.log"
    print_error "  PromptGen Frontend:  logs/promptgen-frontend.log" 
    print_error "  OSCE Backend:        logs/osce-backend.log"
    print_error "  OSCE Frontend:       logs/osce-frontend.log"
fi

cleanup 