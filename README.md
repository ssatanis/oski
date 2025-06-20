# Oski Complete Application Suite

🚀 **Complete medical education platform with AI-powered tools**

## 🌟 Features

### 📄 PromptGen
- **Transform OSCE rubrics into AI-ready prompts**
- Intelligent OCR processing (Tesseract + EasyOCR)
- Azure OpenAI integration for YAML generation
- Support for multiple file formats (PDF, DOC, XLS, images, etc.)
- Real-time processing workflow visualization
- Monaco editor for YAML preview and editing
- Automated schema validation with correction loops

### 🎥 OSCE Video Grader
- **Multi-Agent AI assessment system**
- Planner-Executor-Scorer-Reflector-Consensus Framework
- Video and audio analysis using CLIP and CLAP models
- Real-time grading with detailed feedback
- Configurable AI models and processing parameters

### 🌐 Oski Website
- **Modern, responsive website** 
- Seamless navigation between tools
- Professional animations and UI
- Integrated applications with iframe embedding

## 🚀 Quick Start

### One-Command Setup
```bash
# Install and start everything
npm run dev
```

This will:
- Install all dependencies
- Start PromptGen Frontend (http://localhost:3000)
- Start PromptGen Backend (http://localhost:8000)
- Start OSCE Video Grader Frontend (http://localhost:3001)
- Start OSCE Video Grader Backend (http://localhost:8001)

### Alternative Commands
```bash
# Start all services
npm start

# Start only PromptGen
npm run start:promptgen

# Start only OSCE Video Grader  
npm run start:osce

# Install dependencies only
npm run install:all

# Check service health
npm run health

# Clean all installations
npm run clean
```

## 📱 Application URLs

### Live Applications
- **PromptGen**: http://localhost:3000
- **PromptGen API**: http://localhost:8000/docs
- **OSCE Video Grader**: http://localhost:3001
- **OSCE API**: http://localhost:8001/docs

### Website Pages
- **Home Page**: Open `index.html` in browser
- **PromptGen Page**: Open `promptgen.html` in browser  
- **Simulation Page**: Open `simulation.html` in browser

## 🛠️ Manual Setup

### Prerequisites
- Node.js 18+ and npm 8+
- Python 3.8+
- Git

### PromptGen Setup
```bash
# Frontend
cd rubrics-to-prompts/frontend
npm install
npm run dev

# Backend (new terminal)
cd rubrics-to-prompts/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn main:app --reload --port 8000
```

### OSCE Video Grader Setup
```bash
# Frontend
cd osce-video-grader/web
npm install
npm run dev -- --port 3001

# Backend (new terminal)
cd osce-video-grader/backend
python3 -m uvicorn app:app --reload --port 8001
```

## ⚙️ Configuration

### Environment Variables

#### PromptGen Backend (.env)
```env
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=your_endpoint_here
AZURE_OPENAI_MODEL=gpt-4
AZURE_OPENAI_API_VERSION=2024-05-01-preview
```

#### PromptGen Frontend (.env)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📊 Architecture

### PromptGen Architecture
```
┌─────────────────┐    ┌─────────────────┐
│   Next.js       │    │   FastAPI       │
│   Frontend      │◄──►│   Backend       │
│   (Port 3000)   │    │   (Port 8000)   │
└─────────────────┘    └─────────────────┘
         │                        │
         │                        ▼
         ▼               ┌─────────────────┐
┌─────────────────┐     │   Azure OpenAI  │
│   Monaco Editor │     │   OCR Services  │
│   YAML Preview  │     │   Pydantic      │
└─────────────────┘     └─────────────────┘
```

### OSCE Video Grader Architecture
```
┌─────────────────┐    ┌─────────────────┐
│   Next.js       │    │   FastAPI       │
│   Frontend      │◄──►│   Backend       │
│   (Port 3001)   │    │   (Port 8001)   │
└─────────────────┘    └─────────────────┘
         │                        │
         │                        ▼
         ▼               ┌─────────────────┐
┌─────────────────┐     │   CLIP Models   │
│   Video Player  │     │   CLAP Models   │
│   Grade Display │     │   LLM Models    │
└─────────────────┘     └─────────────────┘
```

## 🎯 Usage

### PromptGen Workflow
1. **Upload**: Drag & drop rubric files (PDF, DOC, XLS, images)
2. **Process**: Watch real-time OCR and AI generation
3. **Edit**: Use Monaco editor to refine YAML output
4. **Download**: Get structured YAML prompt files

### OSCE Video Grader Workflow
1. **Upload**: Select video files for assessment
2. **Configure**: Set rubric questions and AI parameters
3. **Process**: Multi-agent assessment pipeline
4. **Review**: Detailed grades with evidence and feedback

## 🔧 Development

### Project Structure
```
oski/
├── index.html                 # Home page
├── promptgen.html            # PromptGen page
├── simulation.html           # OSCE simulation page
├── package.json              # Root package configuration
├── start-all-services.sh     # Main startup script
├── rubrics-to-prompts/       # PromptGen application
│   ├── frontend/             # Next.js frontend
│   ├── backend/              # FastAPI backend
│   └── README.md             # PromptGen documentation
├── osce-video-grader/        # OSCE Video Grader
│   ├── web/                  # Next.js frontend
│   ├── backend/              # FastAPI backend
│   └── core/                 # AI processing core
├── js/                       # Shared JavaScript
├── css/                      # Shared stylesheets
└── images/                   # Static assets
```

### Adding New Features
1. **Frontend**: Edit React components in respective `frontend/` or `web/` directories
2. **Backend**: Add API endpoints in FastAPI applications
3. **Styling**: Update Tailwind CSS classes and custom styles
4. **Navigation**: Modify `js/header.js` and `js/footer.js`

## 📋 Troubleshooting

### Common Issues
- **Port conflicts**: The startup script automatically kills conflicting processes
- **Dependencies**: Run `npm run install:all` to reinstall everything
- **Blank screens**: Check logs in the `logs/` directory
- **API errors**: Verify environment variables are set correctly

### Log Files
```bash
logs/
├── promptgen-frontend.log
├── promptgen-backend.log
├── osce-frontend.log
└── osce-backend.log
```

### Health Checks
```bash
# Check if all services are running
npm run health

# Manual health checks
curl http://localhost:3000
curl http://localhost:8000/docs
curl http://localhost:3001  
curl http://localhost:8001/docs
```

## 🤝 Contributing

Created by **Sahaj Satani & Aarash Zakeri**

## 📄 License

MIT License - see LICENSE file for details

---

## 🎉 Success! 

If you see this message after running `npm run dev`, all services are running:

- ✅ PromptGen Frontend: http://localhost:3000
- ✅ PromptGen Backend: http://localhost:8000/docs  
- ✅ OSCE Video Grader: http://localhost:3001
- ✅ OSCE Backend: http://localhost:8001/docs

**Press Ctrl+C to stop all services**

# Rubricon - Medical Rubric Processing System

A web-based application for processing medical rubrics and generating YAML assessment files.

## Features

- Upload medical rubric files (Excel, PDF, Word, CSV, Images)
- Extract scoring information automatically
- Generate structured YAML assessment files
- AI-enhanced examination criteria (Azure OpenAI + ChatGPT fallback)
- Modern drag-and-drop interface

## Setup Instructions

### 1. Environment Configuration

Copy the template environment file:
```bash
cp .env.template .env
```

Edit `.env` with your API keys:
```bash
# Azure OpenAI Configuration (Primary)
AZURE_OPENAI_KEY=your_azure_openai_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name

# ChatGPT OpenAI Configuration (Fallback)
CHATGPT_OPENAI_KEY=your_openai_api_key_here
```

### 2. Install Dependencies

```bash
pip install -r backend-requirements.txt
```

### 3. Start the Backend

```bash
python3 backend.py --server
```

The server will start on `http://localhost:5003`

### 4. Open the Frontend

Open `rubricon.html` in your web browser or serve it via a local server.

## Usage

1. **Upload File**: Drag and drop or click to upload a medical rubric file
2. **Processing**: The system extracts criteria and scoring information
3. **AI Enhancement**: Uses OpenAI to enhance examination components
4. **Download**: Get the generated YAML file for assessment

## Supported File Formats

- Excel (.xlsx, .xls)
- PDF (.pdf)
- Word Documents (.docx, .doc)
- CSV (.csv)
- Images (.png, .jpg, .jpeg, .gif, .bmp, .tiff)

## API Endpoints

- `GET /health` - Health check
- `POST /upload` - Upload and process file
- `POST /download` - Download generated YAML

## Monitoring

Use the provided scripts for backend management:
```bash
./check_backend.sh        # Check status and restart if needed
./test_integration.sh     # Test full integration
./keep_backend_running.sh # Keep backend running continuously
```

## Troubleshooting

### Backend Issues
- Ensure port 5002 is available
- Check that all dependencies are installed
- Verify API keys in `.env` file

### Frontend Issues
- Test backend connectivity with: `curl -X GET http://localhost:5003/health`
- Check browser console for error messages
- Ensure CORS is properly configured

### API Key Issues
- Azure OpenAI: Check deployment names and endpoint URLs
- ChatGPT: Verify API key has proper permissions
- The system falls back to ChatGPT if Azure OpenAI fails

## Security Note

Never commit `.env` files with actual API keys. The `.env` file is excluded from git tracking.
