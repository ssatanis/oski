# OSCE Video Assessment System - Setup Guide

This guide explains how to run the embedded OSCE Video Assessment System simulation on your Oski website.

## System Architecture

The simulation consists of:
- **Next.js Frontend** (`osce-video-grader/web/`) - React-based user interface
- **FastAPI Backend** (`osce-video-grader/backend/`) - Python API server
- **Vector Database** (Qdrant) - For storing video embeddings
- **Object Storage** (MinIO) - For storing video files

## Quick Start (Frontend Only)

To run just the frontend simulation (recommended for demo purposes):

```bash
# Navigate to the OSCE video grader web directory
cd osce-video-grader/web

# Install dependencies
npm install

# Start the development server
npm run dev
```

The simulation will be available at `http://localhost:3000` and automatically embedded in your `simulation.html` page.

## Full System Setup (With Backend)

For a fully functional system with video processing capabilities:

### Prerequisites
- Docker and Docker Compose
- Python 3.8+
- Node.js 18+

### 1. Start Backend Services
```bash
cd osce-video-grader

# Start Qdrant (vector database) and MinIO (object storage)
docker compose up -d

# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI backend
cd backend
python app.py
```

### 2. Start Frontend
```bash
cd osce-video-grader/web

# Install and start Next.js frontend
npm install
npm run dev
```

### 3. Access the System
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- MinIO Console: `http://localhost:9001`
- Qdrant Dashboard: `http://localhost:6333/dashboard`

## Features

The OSCE Video Assessment System includes:

### 🎥 Video Upload & Processing
- Upload OSCE examination videos
- Automatic keyframe extraction
- Audio transcription and analysis

### 🤖 Multi-Agent Assessment Pipeline
- **Planner Agent**: Determines which analysis tools to use
- **Executor Agent**: Runs the selected analysis tools
- **Scorer Agent**: Generates grades based on rubric questions
- **Reflector Agent**: Reviews and refines the assessment

### 📊 Real-time Analysis Tools
- Video keyframe retrieval
- Audio segment analysis
- Object detection
- Pose analysis
- Scene interaction analysis
- Temporal action segmentation

### 📋 Assessment Configuration
- Custom rubric questions
- Configurable confidence thresholds
- Multiple AI model options (CLIP, CLAP, GPT-4, etc.)

## Integration with Your Website

The simulation is embedded in your website via:

1. **simulation.html** - Contains the iframe embedding the simulation
2. **Navigation** - "Simulation" link added to header and footer
3. **Styling** - Matches your website's gradient theme (#667eea to #764ba2)

## Troubleshooting

### Frontend Issues
- Ensure Node.js 18+ is installed
- Run `npm install` to install dependencies
- Check that port 3000 is available

### Backend Issues
- Ensure Docker is running for Qdrant and MinIO
- Check Python dependencies with `pip install -r requirements.txt`
- Verify API keys are configured in environment variables

### Integration Issues
- Ensure the simulation is running on `http://localhost:3000`
- Check browser console for iframe loading errors
- Verify CORS settings allow embedding

## Environment Variables

Create a `.env` file in the `osce-video-grader` directory:

```env
# Qdrant Configuration
QDRANT_API_KEY=your_qdrant_api_key

# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key

# MinIO Configuration
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
```

## Support

For technical support or questions about the simulation:
- Email: support@oski.app
- Phone: (214) 648-3111 