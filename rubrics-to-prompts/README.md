# Rubricon | Oski

**Standalone Webapp for Transforming Medical Rubrics into AI Assessment Prompts**

Rubricon is a powerful, standalone web application that converts medical assessment rubrics into structured YAML prompts optimized for AI evaluation systems. Upload any rubric file (Excel, CSV, PDF, or image) and get a comprehensive, ready-to-use assessment prompt.

## 🚀 Features

- **Universal File Support**: Accepts Excel (.xlsx, .xls), CSV, PDF, and image files
- **Adaptive Intelligence**: Automatically analyzes filename and content to determine relevant medical domains
- **Dynamic Criteria Generation**: Creates 1-8 assessment criteria based on file complexity
- **Comprehensive Medical Coverage**: Supports all major medical specialties and assessment areas
- **YAML Output**: Generates structured, AI-ready prompts in standard YAML format
- **Professional UI**: Clean, modern interface with drag-and-drop functionality
- **Offline Capable**: Runs entirely in the browser without external dependencies
- **Export Options**: Download YAML files or copy to clipboard

## 🏥 Supported Medical Domains

### Core Assessment Areas
- **History Taking**: Patient interview and complaint gathering
- **Physical Examination**: Systematic examination techniques
- **Communication Skills**: Professional patient interaction
- **Clinical Reasoning**: Diagnostic thinking and decision-making
- **Procedural Skills**: Technical procedure execution

### Specialty Areas
- **Cardiovascular Assessment**: Heart sounds, pulses, circulation
- **Respiratory Evaluation**: Lung examination and breathing assessment
- **Neurological Examination**: Mental status, reflexes, motor function
- **Musculoskeletal Assessment**: Joint, muscle, and movement evaluation
- **Dermatological Examination**: Skin inspection and lesion assessment
- **Abdominal Examination**: Systematic abdominal assessment
- **Genitourinary Assessment**: Specialized examination techniques

### Professional Skills
- **Patient Safety**: Hygiene, infection control, safety protocols
- **Documentation**: Accurate recording and terminology
- **Professional Behavior**: Ethics, boundaries, cultural sensitivity

## 📁 File Structure

```
rubrics-to-prompts/
├── index.html          # Main application interface
├── js/
│   └── app.js          # Core application logic
├── api/
│   ├── upload.js       # File processing and OCR simulation
│   └── generate-prompt.js # YAML generation logic
├── css/                # Additional stylesheets (if needed)
├── images/             # Application images and icons
└── README.md           # This file
```

## 🔧 Setup and Installation

### Local Development
1. Clone or download this directory
2. Open `index.html` in any modern web browser
3. Start uploading rubric files immediately - no server required!

### Web Server Deployment
1. Upload the entire `rubrics-to-prompts` folder to your web server
2. Navigate to the directory in your browser
3. Application is ready to use

### Local Server (Optional)
```bash
# Using Python 3
python -m http.server 8000

# Using Node.js (if you have http-server installed)
npx http-server

# Using PHP
php -S localhost:8000
```

Then visit `http://localhost:8000` in your browser.

## 💻 Usage

### Basic Usage
1. **Upload File**: Drag and drop or click to select your rubric file
2. **Processing**: Watch as Rubricon analyzes your file and identifies assessment criteria
3. **Review Results**: Examine the generated YAML prompt with criteria, scoring, and examples
4. **Export**: Download the YAML file or copy to clipboard for use in AI systems

### Supported File Types
- **Excel Files**: `.xlsx`, `.xls` - Ideal for structured rubrics
- **CSV Files**: `.csv` - Simple tabular data
- **PDF Files**: `.pdf` - Scanned or digital rubric documents
- **Images**: `.png`, `.jpg`, `.jpeg` - Photos or screenshots of rubrics

### Advanced Features
- **Filename Intelligence**: Name your files descriptively (e.g., "cardiology_exam.xlsx") for better domain detection
- **Content Adaptation**: The system automatically adjusts criteria count and content based on file complexity
- **Scoring Scales**: Each criterion includes 5-point scoring scales (Excellent to Unsatisfactory)
- **Verbalization Examples**: Realistic medical communication examples for each assessment area

## 📊 Output Format

The generated YAML prompt includes:

### Assessment Configuration
- Assessment type and version
- Criteria count and total points
- Metadata and timestamps

### Assessment Criteria
- Unique criterion IDs and names
- Detailed descriptions and assessment items
- Point values and scoring scales
- Time limits and formats

### Verbalization Examples
- Realistic medical communication examples
- Professional interaction phrases
- Patient-centered language samples

### Assessment Instructions
- Detailed scoring guidelines
- Output format specifications
- Quality assurance criteria

## 🎯 Example Output

```yaml
assessment_config:
  type: "medical_osce_assessment"
  version: "2.0"
  criteria_count: 4
  total_points: 28

assessment_criteria:
  - id: "criterion_1"
    name: "Physical Examination"
    code: "PE"
    description: "Comprehensive assessment of physical examination skills"
    max_points: 7
    assessment_items:
      - "Performed systematic examination"
      - "Used appropriate techniques"
      - "Maintained patient dignity"
    scoring:
      excellent: 7
      good: 5
      satisfactory: 4
      needs_improvement: 2
      unsatisfactory: 0

verbalization_examples:
  - "I'm going to examine this area now."
  - "Please let me know if you feel any discomfort."
  - "Hello, I'm Dr. Smith, and I'll be examining you today."

assessment_instructions: |
  This prompt is designed for AI assessment of medical interactions.
  
  ASSESSMENT CRITERIA:
  - Evaluate each criterion based on specific assessment items
  - Assign points according to the scoring scale provided
  - Provide specific examples and feedback for each criterion
```

## 🔄 Browser Compatibility

- **Chrome**: ✅ Full support
- **Firefox**: ✅ Full support
- **Safari**: ✅ Full support
- **Edge**: ✅ Full support
- **Mobile Browsers**: ✅ Responsive design

## 🛠️ Technical Details

### Core Technologies
- **Frontend**: Pure HTML5, CSS3, and JavaScript (ES6+)
- **Processing**: Client-side file analysis and content generation
- **Dependencies**: None - completely standalone
- **Storage**: Local browser storage only (no data leaves your device)

### File Processing
- **OCR Simulation**: Intelligent filename and content analysis
- **Domain Detection**: Keyword matching for medical specialties
- **Adaptive Scaling**: Dynamic point distribution and criteria generation
- **Error Handling**: Comprehensive validation and user feedback

### Security & Privacy
- **Local Processing**: All file analysis happens in your browser
- **No Data Transmission**: Files never leave your device
- **No Storage**: No persistent data storage or tracking
- **Secure**: No external API calls or dependencies

## 🐛 Troubleshooting

### Common Issues

**File Not Processing**
- Ensure file is a supported format (.xlsx, .xls, .csv, .pdf, .png, .jpg, .jpeg)
- Check file size (recommend < 10MB for optimal performance)
- Try refreshing the page and uploading again

**YAML Not Generating**
- Wait for processing to complete (may take 3-5 seconds)
- Check browser console for any errors
- Ensure JavaScript is enabled in your browser

**Download Not Working**
- Check if browser allows file downloads
- Disable popup blockers temporarily
- Try right-clicking and "Save As" if automatic download fails

### Performance Tips
- Use descriptive filenames for better domain detection
- Prefer Excel/CSV formats for best results
- Keep image files under 5MB for faster processing
- Use modern browsers for optimal performance

## 📝 Changelog

### Version 1.0.0
- Initial release with full rubric processing capabilities
- Support for Excel, CSV, PDF, and image files
- Adaptive medical domain detection
- Complete YAML generation pipeline
- Professional UI with drag-and-drop functionality

## 🤝 Contributing

This is a standalone application designed for easy deployment and modification. To customize:

1. **Modify Medical Domains**: Edit the `medicalDomains` array in `js/app.js`
2. **Update Styling**: Modify the CSS in `index.html` or add external stylesheets
3. **Enhance Processing**: Extend the `generateAdaptiveCriteria` function for new assessment types
4. **Add Features**: Build on the modular JavaScript architecture

## 📄 License

This project is available for educational and non-commercial use. For commercial licensing, please contact the development team.

## 📞 Support

For technical support or feature requests, please refer to the main Oski platform documentation or contact the development team.

---

**Rubricon** - Transforming medical assessment, one rubric at a time. 🏥✨ 