# Rubrics to Prompts - AI-Powered OSCE Rubric Converter

Transform OSCE exam rubrics into AI-ready YAML prompts with intelligent OCR processing and automated generation.

## 🚀 Features

- **Multi-format Support**: Upload PDF, DOC, DOCX, XLS, XLSX, TXT, CSV, and image files
- **Advanced OCR**: Dual OCR processing with Tesseract and EasyOCR for maximum accuracy
- **AI-Powered Conversion**: Azure OpenAI integration for intelligent YAML generation
- **Schema Validation**: Pydantic-based validation ensuring consistent YAML structure
- **Interactive Editor**: Built-in Monaco editor for YAML preview and editing
- **Modern UI**: Beautiful, responsive interface matching Oski's design system
- **Real-time Processing**: Live progress tracking with animated workflow steps

## 🏗️ Architecture

### Backend (FastAPI)
- **OCR Processing**: Tesseract + EasyOCR for text extraction
- **AI Integration**: Azure OpenAI for YAML generation with retry logic
- **Schema Validation**: Pydantic models ensuring data consistency
- **Background Processing**: Async file processing with status tracking
- **RESTful API**: Clean endpoints for upload, processing, and download

### Frontend (Next.js)
- **Modern React**: TypeScript + Tailwind CSS for type safety and styling
- **File Upload**: Drag-and-drop interface with progress tracking
- **Real-time Updates**: Polling-based status updates during processing
- **YAML Editor**: Monaco editor with syntax highlighting
- **Animations**: Framer Motion for smooth, engaging interactions

## 📋 Prerequisites

- **Python 3.8+**: For backend development
- **Node.js 18+**: For frontend development
- **Azure OpenAI API**: Valid subscription and deployment
- **Tesseract OCR**: For text extraction (install via brew/apt)

## 🔧 Installation

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd rubrics-to-prompts
   ```

2. **Backend Setup**
   ```bash
   chmod +x start-backend.sh
   ./start-backend.sh
   ```

3. **Frontend Setup** (in a new terminal)
   ```bash
   chmod +x start-frontend.sh
   ./start-frontend.sh
   ```

4. **Configure Environment**
   - Edit `backend/.env` with your Azure OpenAI credentials
   - Update `frontend/.env.local` if needed

### Manual Installation

#### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp env_example.txt .env
   # Edit .env file with your credentials
   ```

5. **Start the server**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

#### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure environment**
   ```bash
   cp env.example .env.local
   ```

4. **Start development server**
   ```bash
   npm run dev
   ```

## ⚙️ Configuration

### Backend Environment Variables

Create a `.env` file in the `backend` directory:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_KEY=your_azure_openai_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4

# Application Settings
DEBUG=True
LOG_LEVEL=INFO

# CORS Settings
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# File Upload Settings
MAX_FILE_SIZE_MB=50
TEMP_FILES_DIR=/tmp

# OCR Settings
TESSERACT_CONFIG=--psm 6
EASYOCR_LANGUAGES=en
```

### Frontend Environment Variables

Create a `.env.local` file in the `frontend` directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🎯 Usage

1. **Access the Application**
   - Open http://localhost:3000 in your browser
   - The backend API runs on http://localhost:8000

2. **Upload a Rubric**
   - Drag and drop or click to select a rubric file
   - Supported formats: PDF, DOC, DOCX, XLS, XLSX, TXT, CSV, images

3. **Process the File**
   - Click "Process Rubric" to start the conversion
   - Watch the real-time progress through workflow steps

4. **Review and Edit**
   - Preview the generated YAML
   - Use the built-in editor to make adjustments
   - Save changes if needed

5. **Download**
   - Click "Download YAML" to get your prompt file
   - File is named based on original document

## 🔌 API Endpoints

### POST `/upload-rubric`
Upload and process a rubric file
- **Body**: `multipart/form-data` with file
- **Response**: Task ID for tracking progress

### GET `/status/{task_id}`
Get processing status
- **Response**: Current step, progress, and result (when complete)

### POST `/update-yaml/{task_id}`
Update generated YAML content
- **Body**: `{"yaml_content": "updated yaml string"}`

### GET `/download-yaml/{task_id}`
Download the generated YAML file
- **Response**: YAML file download

### GET `/health`
Health check endpoint

## 📊 YAML Schema

The generated YAML follows this structure:

```yaml
rubric_info:
  title: "OSCE Assessment Rubric"
  total_points: 20
  description: "Brief description of what this rubric assesses"

sections:
  - section_name: "Physical Examination"
    section_id: "physical_exam"
    description: "Assessment of physical examination skills"
    items:
      - item_id: "lung_auscultation_anterior"
        description: "Auscultate anterior lung fields"
        points: 1
        criteria: "Student properly places stethoscope on anterior chest"
```

## 🚀 Deployment

### Production Build

#### Backend
```bash
cd backend
pip install -r requirements.txt
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

#### Frontend
```bash
cd frontend
npm run build
npm start
```

### Docker Deployment

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - AZURE_OPENAI_KEY=${AZURE_OPENAI_KEY}
      - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

## 🔍 Troubleshooting

### Common Issues

1. **OCR Not Working**
   - Install Tesseract: `brew install tesseract` (macOS) or `apt-get install tesseract-ocr` (Linux)
   - Verify installation: `tesseract --version`

2. **Azure OpenAI Errors**
   - Check API key and endpoint configuration
   - Verify deployment name matches your Azure setup
   - Ensure sufficient quota/credits

3. **File Upload Failures**
   - Check file size (max 50MB by default)
   - Verify file format is supported
   - Check network connectivity

4. **YAML Validation Errors**
   - Review generated YAML in editor
   - Check for proper indentation and structure
   - Use the edit feature to fix manual corrections

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Credits

Created by **Sahaj Satani** & **Aarash Zakeri**

Built with:
- FastAPI & Pydantic for robust backend processing
- Next.js & Tailwind CSS for modern frontend experience
- Azure OpenAI for intelligent content generation
- Tesseract & EasyOCR for accurate text extraction

---

For support or questions, please open an issue in the repository. 