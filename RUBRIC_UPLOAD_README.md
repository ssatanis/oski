# 🎯 Oski Rubric Upload Application

A modern, sleek web application for uploading and processing OSCE rubrics into structured YAML format.

## ✨ Features

- **🎨 Modern Design**: Beautiful, animated interface with smooth transitions
- **📄 Multi-format Support**: PDF, DOC, DOCX, Excel, CSV, and image files
- **⚡ Real-time Processing**: Instant file upload with animated loading indicators
- **🤖 AI-Powered**: Uses OpenAI to convert rubrics to structured YAML
- **💾 Easy Download**: One-click YAML download functionality
- **📱 Responsive**: Works perfectly on desktop and mobile devices

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- Azure OpenAI API key

### Setup

1. **Set your OpenAI API key:**
   ```bash
   export AZURE_OPENAI_KEY='your-api-key-here'
   ```

2. **Run the application:**
   ```bash
   ./start-rubric-app.sh
   ```

3. **Open your browser:**
   Navigate to `http://localhost:8080/rubricon.html`

## 🎬 How It Works

1. **Upload**: Drag and drop or click to upload your rubric file
2. **Process**: Click "Process Rubric" to convert to YAML format
3. **Download**: Download the structured YAML file

## 📁 Supported File Types

- **Documents**: PDF, DOC, DOCX
- **Spreadsheets**: XLS, XLSX, CSV
- **Images**: PNG, JPG, JPEG (requires Tesseract)
- **Text**: TXT

## 🛠️ Manual Setup

If you prefer to set up manually:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r backend-requirements.txt

# Start backend
python backend.py

# In another terminal, start frontend
python3 -m http.server 8080
```

## 🎨 Design Features

- **Glassmorphism**: Beautiful backdrop blur effects
- **Smooth Animations**: CSS3 transitions and keyframe animations
- **Loading States**: Elegant spinning loader during processing
- **Success Feedback**: Animated success indicators
- **Error Handling**: User-friendly error messages

## 🔧 Configuration

The backend runs on `http://localhost:5000` and serves the following endpoints:

- `POST /upload` - Upload and process rubric files
- `POST /download` - Download processed YAML files

## 🎯 Architecture

- **Frontend**: Pure HTML/CSS/JavaScript with modern animations
- **Backend**: Flask server with OpenAI integration
- **Processing**: Python-based file parsing and AI conversion

## 🐛 Troubleshooting

**Backend not starting?**
- Ensure AZURE_OPENAI_KEY is set
- Check Python 3.7+ is installed
- Verify all dependencies are installed

**File upload failing?**
- Check file format is supported
- Ensure file size is reasonable
- Verify backend server is running

**YAML generation issues?**
- Verify OpenAI API key is valid
- Check network connectivity
- Ensure sufficient API credits

## 📝 Example Usage

1. Upload a PDF rubric file
2. The AI extracts rubric criteria
3. Download structured YAML output:

```yaml
rubric:
  title: "OSCE Assessment Rubric"
  sections:
    - name: "History Taking"
      points: 5
      criteria: "Demonstrates effective history taking skills"
    - name: "Physical Examination"
      points: 7
      criteria: "Performs systematic physical examination"
```

## 🎉 Enjoy!

Your modern rubric processing platform is ready to use. Upload files, see the magic happen, and download perfectly structured YAML files! 