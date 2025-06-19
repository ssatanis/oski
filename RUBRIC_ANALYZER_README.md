# 🏥 Comprehensive Rubric Analyzer

A professional medical rubric analysis system that converts PDF, Word, and Excel assessment documents into interactive, editable rubrics using advanced AI processing.

## ✨ Features

- **Multi-Format Support**: PDF, Word (.docx/.doc), Excel (.xlsx/.xls)
- **AI-Powered Analysis**: Uses Azure OpenAI for intelligent rubric extraction
- **Interactive Dashboard**: Edit criteria, adjust points, and export results
- **Medical Focus**: Specialized for OSCE and medical assessment rubrics
- **Professional UI**: Clean, responsive interface for production use

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.8+ 
- Node.js 16+ (optional, for development)
- Azure OpenAI API access

### 2. Setup Environment Variables

Create a `.env` file in the `rubrics-to-prompts/backend/` directory:

```bash
AZURE_OPENAI_KEY=your_azure_openai_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
```

### 3. Start the System

```bash
# Make startup script executable (first time only)
chmod +x start-rubric-analyzer.sh

# Start the system
./start-rubric-analyzer.sh
```

### 4. Access the Interface

- **Frontend**: Open `rubric-analyzer.html` in your browser
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📂 Supported File Formats

| Format | Extensions | Status |
|--------|------------|---------|
| PDF Documents | `.pdf` | ✅ Fully Supported |
| Word Documents | `.docx`, `.doc` | ✅ Fully Supported |
| Excel Spreadsheets | `.xlsx`, `.xls` | ✅ Fully Supported |

**Note**: Image formats have been removed for production stability. Only document formats are supported.

## 🎯 Medical Assessment Domains

The system automatically categorizes rubric criteria into four main domains:

### 1. History Taking (HT)
- **Categories**: CC, HPI, PMH, Med, All, FH, SH
- **Focus**: Patient history, symptoms, medications, allergies
- **Example Criteria**: 
  - Chief Concern identification
  - History of Present Illness details
  - Past Medical History review

### 2. Physical Examination (PE)
- **Categories**: PE
- **Focus**: Clinical examination techniques and findings
- **Example Criteria**:
  - Vital signs documentation
  - Physical inspection techniques
  - Examination findings description

### 3. Diagnostic Accuracy/Reasoning/Justification (DA/DR)
- **Categories**: DA, DR
- **Focus**: Clinical reasoning and diagnostic accuracy
- **Example Criteria**:
  - Correct primary diagnosis
  - Differential diagnosis consideration
  - Clinical reasoning demonstration

### 4. Management (M)
- **Categories**: M
- **Focus**: Treatment planning and patient management
- **Example Criteria**:
  - Appropriate treatment recommendations
  - Follow-up planning
  - Patient education

## 🔧 System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Frontend       │    │  FastAPI         │    │  Enhanced       │
│  (HTML/JS)      │◄──►│  Backend         │◄──►│  backend.py     │
│                 │    │  (main.py)       │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Azure OpenAI    │
                       │  GPT-4o-mini     │
                       └──────────────────┘
```

## 📊 Interactive Dashboard Features

### ✅ Rubric Display
- **Domain Organization**: Criteria grouped by medical domains
- **Point Management**: Increase/decrease points with arrow controls
- **Real-time Totals**: Dynamic score calculation
- **Category Tags**: Visual categorization (CC, HPI, PE, etc.)

### ✅ Editing Capabilities
- **Editable Criteria**: Modify criterion names and descriptions
- **Point Adjustments**: Flexible scoring with min/max constraints
- **Domain Protection**: Assessment domains cannot be deleted
- **Auto-save**: Changes preserved in session

### ✅ Export Options
- **JSON Export**: Complete rubric data structure
- **YAML Export**: Human-readable format
- **PDF Export**: Professional report format (coming soon)

## 🔍 File Processing Pipeline

1. **File Upload**: Drag & drop or browse interface
2. **Format Detection**: Automatic file type identification
3. **Content Extraction**: Text extraction using appropriate parsers
4. **AI Analysis**: Azure OpenAI processes content
5. **Structure Generation**: Creates standardized rubric format
6. **Interactive Display**: Renders editable dashboard

## 🛠️ Development

### Backend Development

```bash
cd rubrics-to-prompts/backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

The frontend is a single HTML file with embedded CSS and JavaScript. For development:

1. Edit `rubric-analyzer.html`
2. Refresh browser to see changes
3. Use browser dev tools for debugging

### API Endpoints

- `POST /upload-rubric` - Upload and process rubric file
- `GET /status/{task_id}` - Check processing status
- `GET /health` - Health check endpoint
- `GET /docs` - Interactive API documentation

## 🔐 Security Considerations

- **File Validation**: Strict file type checking
- **Size Limits**: 50MB maximum file size
- **Temporary Files**: Automatic cleanup after processing
- **CORS Protection**: Configured allowed origins
- **API Key Security**: Environment variable storage

## 📝 Error Handling

The system provides comprehensive error handling:

- **File Format Errors**: Clear messaging for unsupported formats
- **Processing Errors**: Detailed error descriptions
- **Timeout Handling**: 5-minute processing timeout
- **Graceful Degradation**: Fallback structures when AI fails

## 🚀 Production Deployment

### Environment Setup
```bash
export AZURE_OPENAI_KEY="your-production-key"
export AZURE_OPENAI_ENDPOINT="your-production-endpoint"
export DEBUG="false"
export ALLOWED_ORIGINS="https://yourdomain.com"
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY rubrics-to-prompts/backend/ .
RUN pip install -r requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📋 Testing

### Upload Test Files
1. Place test rubrics in `test-files/` directory
2. Upload via the interface
3. Verify extraction accuracy
4. Test interactive features

### Example Test Files
- `Station_1A_Psoriasis.pdf` - PDF rubric
- `Assessment_Criteria.docx` - Word document
- `Scoring_Guide.xlsx` - Excel spreadsheet

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📞 Support

- **Issues**: Create GitHub issues for bugs
- **Features**: Submit feature requests
- **Documentation**: Contribute to README improvements

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Built with ❤️ for medical education by Sahaj Satani & Aarash Zakeri** 