from pathlib import Path
from openai import AzureOpenAI
from PIL import Image
import pandas as pd
from docx import Document
import mammoth
import pytesseract
import pdfplumber
import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import tempfile
import json
from dotenv import load_dotenv
import logging
import traceback
import sys

# Configure logging for better debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backend.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file - CRITICAL FOR SERVER MODE
load_dotenv()

app = Flask(__name__)

# ENHANCED CORS CONFIGURATION - CRITICAL FIX
CORS(app, resources={
    r"/*": {
        "origins": ["*"],  # In production, restrict this to specific domains
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        "supports_credentials": False,
        "expose_headers": ["Content-Type", "Authorization"]
    }
})

# Global variable to store extracted scoring information
extracted_scoring_info = {}

UPLOAD_FOLDER = 'temp_uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xlsx', 'xls', 'csv', 'png', 'jpg', 'jpeg', 'txt'}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def list_available_deployments(client):
    """Try to list available deployments using various methods"""
    try:
        import requests
        
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_KEY")
        
        if endpoint and api_key:
            management_url = f"{endpoint.rstrip('/')}/openai/deployments?api-version=2024-02-15-preview"
            headers = {
                "api-key": api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.get(management_url, headers=headers)
            if response.status_code == 200:
                deployments = response.json()
                logger.info(f"📋 Available deployments: {deployments}")
                return deployments
            else:
                logger.warning(f"📋 Could not list deployments: {response.status_code}")
                
    except Exception as e:
        logger.warning(f"📋 Could not list deployments: {e}")
    
    return None

def initialize_azure_client():
    """Initialize Azure OpenAI client with comprehensive error handling"""
    try:
        # Get environment variables
        azure_api_key = os.getenv("AZURE_OPENAI_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
        chatgpt_api_key = os.getenv("CHATGPT_OPENAI_KEY")
        
        logger.info(f"🔧 Configuration check:")
        logger.info(f"   Azure API Key: {'✅ Set' if azure_api_key else '❌ Missing'}")
        logger.info(f"   Azure Endpoint: {azure_endpoint if azure_endpoint else '❌ Missing'}")
        logger.info(f"   ChatGPT API Key: {'✅ Set' if chatgpt_api_key else '❌ Missing'}")
        logger.info(f"   Deployment: {deployment_name}")
        
        # Try Azure OpenAI first
        if azure_api_key and azure_endpoint and azure_api_key != "your_azure_openai_key_here":
            try:
                from openai import AzureOpenAI
                client = AzureOpenAI(
                    api_key=azure_api_key,
                    azure_endpoint=azure_endpoint,
                    api_version="2024-02-15-preview"
                )
                logger.info(f"✅ Azure OpenAI client initialized successfully")
                logger.info(f"📍 Endpoint: {azure_endpoint}")
                
                # Try to list available deployments
                list_available_deployments(client)
                
                return client, deployment_name, "azure"
                    
            except Exception as e:
                logger.error(f"❌ Failed to initialize Azure OpenAI client: {e}")
                logger.info(f"🔄 Trying ChatGPT fallback...")
        
        # Fallback to ChatGPT
        if chatgpt_api_key and chatgpt_api_key != "your_chatgpt_api_key_here":
            try:
                from openai import OpenAI
                client = OpenAI(api_key=chatgpt_api_key)
                logger.info(f"✅ ChatGPT OpenAI client initialized successfully")
                return client, "gpt-4o-mini", "openai"
            except Exception as e:
                logger.error(f"❌ Failed to initialize ChatGPT client: {e}")
                return None, None, None
        else:
            logger.warning("⚠️  No valid OpenAI credentials found in .env file")
            return None, None, None
            
    except Exception as e:
        logger.error(f"❌ Critical error in initialize_azure_client: {e}")
        return None, None, None

# Initialize the client
client, deployment_name, client_type = initialize_azure_client()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_file(file_path):
    """Process uploaded file with comprehensive error handling"""
    try:
        file = Path(file_path)
        suffix = file.suffix.lower()
        logger.info(f"🔍 Processing file type: {suffix}")

        # Initialize results to handle all cases
        results = []

        if suffix == ".pdf":
            logger.info("📄 Processing PDF file...")
            results = parse_pdf(file_path)

        elif suffix == ".txt":
            logger.info("📝 Processing TXT file...")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                results = [chunk.strip() for chunk in text.split("\n") if chunk.strip()]
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='latin1') as f:
                    text = f.read()
                results = [chunk.strip() for chunk in text.split("\n") if chunk.strip()]

        elif suffix == ".docx":
            logger.info("📝 Processing DOCX file...")
            doc = Document(file_path)
            results = [para.text.strip() for para in doc.paragraphs if para.text.strip()]

        elif suffix == ".doc":
            logger.info("📝 Processing DOC file...")
            with open(file_path, "rb") as doc_file:
                result = mammoth.convert_to_text(doc_file)
                text = result.value
                results = [chunk.strip() for chunk in text.split("\n") if chunk.strip()]

        elif suffix in {".xlsx", ".xls"}:
            logger.info("📊 Processing Excel file...")
            df = pd.read_excel(file_path)
            logger.info(f"📊 Excel file loaded: {df.shape[0]} rows, {df.shape[1]} columns")
            logger.info(f"📝 Column names: {list(df.columns)}")
            
            # Look for scoring information in the data
            scoring_info = {}
            
            # Check for domain scoring table
            for index, row in df.iterrows():
                row_values = [str(v) for v in row.values if pd.notna(v)]
                row_text = " ".join(row_values).lower()
                
                if "domain" in row_text and ("score" in row_text or "points" in row_text):
                    logger.info(f"📊 Found scoring table header at row {index}")
                    
                    for i in range(index + 1, min(index + 10, len(df))):
                        if i < len(df):
                            domain_row = df.iloc[i]
                            domain_name = str(domain_row.iloc[1]).strip() if len(domain_row) > 1 and pd.notna(domain_row.iloc[1]) else ""
                            possible_score = str(domain_row.iloc[4]).strip() if len(domain_row) > 4 and pd.notna(domain_row.iloc[4]) else ""
                            
                            domain_name = domain_name.replace('\xa0', ' ').strip()
                            possible_score = possible_score.replace('\xa0', ' ').strip()
                            
                            if domain_name and possible_score and possible_score.isdigit():
                                scoring_info[domain_name] = {
                                    'possible_points': int(possible_score),
                                    'category': domain_name.split('(')[0].strip() if '(' in domain_name else domain_name
                                }
                                logger.info(f"📊 Found scoring: {domain_name} = {possible_score} points")
                    break
            
            # Extract all content including scoring info
            results = []
            for index, row in df.iterrows():
                row_values = [str(v) for v in row if pd.notnull(v) and str(v).strip()]
                if row_values:
                    combined = " | ".join(row_values)
                    results.append(combined)
            
            results = [r for r in results if r.strip()]
            logger.info(f"✅ Extracted {len(results)} non-empty rows")
            
            # Store scoring info globally
            global extracted_scoring_info
            extracted_scoring_info = scoring_info

        elif suffix == ".csv":
            logger.info("📊 Processing CSV file...")
            try:
                df = pd.read_csv(file_path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding="latin1")

            headers = df.columns.tolist()
            results = []
            for _, row in df.iterrows():
                row_values = [
                    str(row[col]).strip() if pd.notnull(row[col]) else "" for col in headers
                ]
                combined = " | ".join(
                    f"{col}: {val}" for col, val in zip(headers, row_values) if val
                )
                if combined:
                    results.append(combined)

        else:
            logger.warning(f"⚠️ Unsupported file type: {suffix}")
            results = [f"Test file processing - File type: {suffix}", "This is a test upload for connection verification"]

        # Ensure we always have some content
        if not results:
            results = ["Default test content", "File processed successfully but no content extracted"]

        return generate_rubric_with_llm(results)
        
    except Exception as e:
        logger.error(f"❌ Error in upload_file: {str(e)}")
        logger.error(traceback.format_exc())
        raise e

def parse_pdf(path):
    """Parse PDF with enhanced error handling"""
    try:
        chunks = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                lines = text.split("\n")
                buffer = ""
                for line in lines:
                    line = line.strip()
                    if not line:
                        if buffer:
                            chunks.append(buffer.strip())
                            buffer = ""
                    else:
                        buffer += " " + line
                if buffer:
                    chunks.append(buffer.strip())

        return chunks
    except Exception as e:
        logger.error(f"❌ Error parsing PDF: {str(e)}")
        return [f"Error parsing PDF: {str(e)}"]

def generate_rubric_with_llm(chunks):
    """Generate rubric with enhanced error handling and fallback processing"""
    global client, deployment_name, extracted_scoring_info
    
    try:
        logger.info(f"📊 Data extraction successful: {len(chunks)} criteria found")
        
        if extracted_scoring_info:
            logger.info(f"📊 Scoring information extracted:")
            for domain, info in extracted_scoring_info.items():
                logger.info(f"   {domain}: {info['possible_points']} points")
        
        # Extract station identifier from chunks
        station_key = "1A"
        for chunk in chunks[:10]:
            if "station" in chunk.lower():
                import re
                station_match = re.search(r'station\s*(\w+)', chunk.lower())
                if station_match:
                    station_key = station_match.group(1).upper()
                    break
        
        # Organize chunks into examination categories
        history_items = []
        physical_exam_items = []
        diagnostic_items = []
        management_items = []
        other_items = []
        
        for chunk in chunks:
            chunk_lower = chunk.lower()
            if any(term in chunk_lower for term in ["history", "hpi", "ht", "chief concern", "pmh", "medications", "allergies", "family history", "social history"]):
                history_items.append(chunk)
            elif any(term in chunk_lower for term in ["physical", "exam", "pe", "vitals", "inspection", "palpation", "auscultation"]):
                physical_exam_items.append(chunk)
            elif any(term in chunk_lower for term in ["diagnosis", "diagnostic", "da", "dr", "assessment", "reasoning"]):
                diagnostic_items.append(chunk)
            elif any(term in chunk_lower for term in ["management", "treatment", "plan", "m |"]):
                management_items.append(chunk)
            else:
                other_items.append(chunk)
        
        # Create the YAML structure
        yaml_content = f"""key: 
  {station_key}
system_message: 
  |
   You are a helpful assistant tasked with analyzing and scoring a recorded medical examination between a medical student and a patient. Provide your response in JSON format.
   
user_message: 
  |   
   Important Instruction:
   When determining the start and end times of each examination, focus on the moments where the doctor instructs the patient to perform an action (e.g., "look up at the ceiling", "look straight ahead"). Give these phrases priority for setting the `start_time` and `end_time` over phrases where the doctor states their own actions (e.g., "I'm going to look at your nose and eyes").
      
   You need to identify the following physical exams from this conversation:"""
           
        # Add examination sections based on extracted data with scoring info
        if history_items:
            history_points = extracted_scoring_info.get('History (HT)', {}).get('possible_points', 0)
            yaml_content += f"""
       
   History Taking Assessment: (Total: {history_points} points)"""
            for i, item in enumerate(history_items[:10], 1):
                clean_item = item.replace('"', "'").strip()
                if len(clean_item) > 100:
                    clean_item = clean_item[:100] + "..."
                yaml_content += f"""
   - History Item {i}: {clean_item}"""
        
        if physical_exam_items:
            pe_points = extracted_scoring_info.get('Physical Exam (PE)', {}).get('possible_points', 0)
            yaml_content += f"""
       
   Physical Examination Components: (Total: {pe_points} points)"""
            for i, item in enumerate(physical_exam_items[:15], 1):
                clean_item = item.replace('"', "'").strip()
                if len(clean_item) > 100:
                    clean_item = clean_item[:100] + "..."
                yaml_content += f"""
   - Physical Exam {i}: {clean_item}"""
        
        if diagnostic_items:
            da_points = extracted_scoring_info.get('Diagnostic Accuracy (DA)', {}).get('possible_points', 0)
            dr_points = extracted_scoring_info.get('Diagnostic Reasoning/Justification (DR)', {}).get('possible_points', 0)
            total_diag_points = da_points + dr_points
            yaml_content += f"""
       
   Diagnostic Assessment: (Total: {total_diag_points} points)"""
            for i, item in enumerate(diagnostic_items[:8], 1):
                clean_item = item.replace('"', "'").strip()
                if len(clean_item) > 100:
                    clean_item = clean_item[:100] + "..."
                yaml_content += f"""
   - Diagnostic {i}: {clean_item}"""
        
        if management_items:
            mgmt_points = extracted_scoring_info.get('Management (M)', {}).get('possible_points', 0)
            yaml_content += f"""
       
   Management and Treatment: (Total: {mgmt_points} points)"""
            for i, item in enumerate(management_items[:8], 1):
                clean_item = item.replace('"', "'").strip()
                if len(clean_item) > 100:
                    clean_item = clean_item[:100] + "..."
                yaml_content += f"""
   - Management {i}: {clean_item}"""
        
        # Enhanced AI processing if client is available
        if client and deployment_name:
            logger.info(f"🤖 Enhancing examination criteria with {client_type.upper()} OpenAI...")
            
            enhancement_prompt = f"""
Based on the following medical assessment criteria extracted from a rubric, create a comprehensive list of specific physical examinations and assessment components that should be identified in a medical student examination.

Focus on:
1. Specific physical examination maneuvers
2. History taking components  
3. Diagnostic reasoning elements
4. Management decisions

Criteria extracted:
{chr(10).join(chunks[:20])}

Format as a list of specific, actionable examination components that can be identified in a recorded medical encounter.
"""

            try:
                logger.info(f"📤 Enhancing with {client_type.upper()} OpenAI...")
                
                model_name = deployment_name if client_type == "azure" else "gpt-4o-mini"
                
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert medical educator who creates specific, actionable assessment criteria for OSCE examinations."
                        },
                        {
                            "role": "user", 
                            "content": enhancement_prompt
                        }
                    ],
                    max_tokens=1000,
                    temperature=0.3
                )
                
                ai_enhanced_exams = response.choices[0].message.content
                logger.info(f"✅ {client_type.upper()} OpenAI enhancement successful")
                
                yaml_content += f"""
       
   AI-Enhanced Examination Components:
   {ai_enhanced_exams.replace(chr(10), chr(10) + '   ')}"""
                
            except Exception as e:
                logger.error(f"⚠️  {client_type.upper() if client_type else 'OpenAI'} enhancement failed: {str(e)}")
        
        # Add scoring summary if available
        if extracted_scoring_info:
            total_possible = sum(info['possible_points'] for info in extracted_scoring_info.values())
            yaml_content += f"""
       
   SCORING BREAKDOWN:"""
            for domain, info in extracted_scoring_info.items():
                yaml_content += f"""
   - {domain}: {info['possible_points']} points"""
            yaml_content += f"""
   - TOTAL POSSIBLE: {total_possible} points"""
        
        # Add the closing instruction and scoring format
        yaml_content += f"""
       
   For each examination component identified:
   1. Provide the exact start_time and end_time (in MM:SS format)
   2. Include a brief description of what was performed
   3. Assign appropriate scoring based on completeness and technique
   4. Note any missed components or areas for improvement
   
   Return your analysis in JSON format with the following structure:
   {{
     "examination_components": [
       {{
         "component": "examination_name",
         "performed": true/false,
         "start_time": "MM:SS",
         "end_time": "MM:SS", 
         "description": "detailed description",
         "score": "points_earned/total_points",
         "feedback": "specific feedback"
       }}
     ],
     "overall_score": "total_points_earned/{sum(info['possible_points'] for info in extracted_scoring_info.values()) if extracted_scoring_info else 'total_possible'}",
     "summary": "overall assessment summary"
   }}

# Generated from {len(chunks)} assessment criteria
# Processing date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
# Station: {station_key}
# Scoring: {len(extracted_scoring_info)} domains, {sum(info['possible_points'] for info in extracted_scoring_info.values()) if extracted_scoring_info else 0} total points
# OpenAI: {'✅ Enhanced' if client else '📋 Extracted only'}
"""
        
        return yaml_content
        
    except Exception as e:
        logger.error(f"❌ Error in generate_rubric_with_llm: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Return a basic YAML structure even if processing fails
        return f"""key: 
  1A
system_message: 
  |
   You are a helpful assistant tasked with analyzing medical examinations.
   
user_message: 
  |   
   Please analyze the medical examination recording.
   
# Error occurred during processing: {str(e)}
# Fallback basic structure provided
"""

@app.route('/health', methods=['GET', 'OPTIONS'])
def health_check():
    """Enhanced health check endpoint"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
    
    try:
        return jsonify({
            'status': 'healthy',
            'message': 'Backend server is running successfully',
            'azure_openai': 'configured' if client else 'not configured',
            'client_type': client_type if client_type else 'none',
            'deployment': deployment_name if deployment_name else 'none',
            'port': 5003,
            'cors': 'enabled',
            'upload_folder': os.path.exists(UPLOAD_FOLDER),
            'allowed_extensions': list(ALLOWED_EXTENSIONS)
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/upload', methods=['POST', 'OPTIONS'])
def upload_and_process():
    """Enhanced upload endpoint with comprehensive error handling"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
        
    global extracted_scoring_info
    
    try:
        # Clear previous scoring info
        extracted_scoring_info = {}
        
        if 'file' not in request.files:
            logger.error('No file part in request')
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            logger.error('No selected file')
            return jsonify({'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
            # Save the file
            file.save(filepath)
            logger.info(f"🔄 Processing uploaded file: {filename}")
            
            try:
                # Process the file
                yaml_content = upload_file(filepath)
                
                # Clean up the temporary file
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                response_data = {
                    'success': True,
                    'yaml_content': yaml_content,
                    'filename': filename,
                    'scoring_extracted': len(extracted_scoring_info) > 0,
                    'total_points': sum(info['possible_points'] for info in extracted_scoring_info.values()) if extracted_scoring_info else 0,
                    'processing_info': {
                        'openai_used': client is not None,
                        'client_type': client_type,
                        'deployment': deployment_name
                    }
                }
                
                logger.info(f"✅ Successfully processed {filename}")
                return jsonify(response_data)
                
            except Exception as processing_error:
                # Clean up the temporary file on error
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                logger.error(f"❌ Processing error: {str(processing_error)}")
                logger.error(traceback.format_exc())
                
                return jsonify({
                    'error': f'File processing failed: {str(processing_error)}',
                    'details': 'Check server logs for more information'
                }), 500
        
        return jsonify({'error': 'Invalid file type. Allowed: ' + ', '.join(ALLOWED_EXTENSIONS)}), 400
        
    except Exception as e:
        logger.error(f"❌ Upload endpoint error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': f'Server error: {str(e)}',
            'details': 'Check server logs for more information'
        }), 500

@app.route('/download', methods=['POST', 'OPTIONS'])
def download_yaml():
    """Enhanced download endpoint"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
            
        yaml_content = data.get('yaml_content', '')
        filename = data.get('filename', 'rubric.yaml')
        
        if not yaml_content:
            return jsonify({'error': 'No YAML content provided'}), 400
        
        # Create a temporary file with the YAML content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            temp_file.write(yaml_content)
            temp_file_path = temp_file.name
        
        return send_file(
            temp_file_path,
            as_attachment=True,
            download_name=f"{os.path.splitext(filename)[0]}.yaml",
            mimetype='application/x-yaml'
        )
        
    except Exception as e:
        logger.error(f"❌ Download error: {str(e)}")
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

# Add a new endpoint for API information
@app.route('/api/info', methods=['GET', 'OPTIONS'])
def api_info():
    """API information endpoint"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
    
    return jsonify({
        'name': 'Oski Rubricon Backend',
        'version': '1.0.0',
        'description': 'AI-Powered Rubric to Assessment Prompt Generator',
        'endpoints': {
            '/health': 'Health check',
            '/upload': 'Upload and process rubric files',
            '/download': 'Download generated YAML',
            '/api/info': 'API information'
        },
        'supported_formats': list(ALLOWED_EXTENSIONS),
        'openai_status': {
            'configured': client is not None,
            'type': client_type,
            'deployment': deployment_name
        }
    })

def test_with_file(filename):
    """Test the upload_file function with a specific file"""
    try:
        if not os.path.exists(filename):
            logger.error(f"❌ Error: File '{filename}' not found!")
            logger.info(f"   Current directory: {os.getcwd()}")
            logger.info(f"   Files in current directory:")
            for f in os.listdir('.'):
                if f.endswith(('.xlsx', '.xls', '.pdf', '.docx', '.doc', '.csv')):
                    logger.info(f"     - {f}")
            return False
        
        logger.info(f"🔍 Processing file: {filename}")
        logger.info(f"📁 File exists: {os.path.exists(filename)}")
        logger.info(f"📊 File size: {os.path.getsize(filename)} bytes")
        logger.info("=" * 50)
        
        # Process the file
        result = upload_file(filename)
        
        logger.info("✅ Processing completed successfully!")
        logger.info("=" * 50)
        logger.info("📄 Generated YAML:")
        logger.info(result)
        logger.info("=" * 50)
        
        # Save the result to a file
        output_filename = f"{os.path.splitext(filename)[0]}_output.yaml"
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(result)
        logger.info(f"💾 Output saved to: {output_filename}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error processing file: {str(e)}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        logger.info("🚀 Starting Flask server for Rubricon integration...")
        logger.info("🔧 Azure OpenAI configured and ready" if client else "⚠️  OpenAI not configured - using fallback processing")
        logger.info("📍 Server running on http://localhost:5003")
        logger.info("📋 Endpoints available:")
        logger.info("   GET  /health - Health check")
        logger.info("   POST /upload - Upload and process files")
        logger.info("   POST /download - Download YAML files")
        logger.info("   GET  /api/info - API information")
        logger.info("=" * 50)
        
        # Run the Flask app with better configuration
        app.run(host='0.0.0.0', port=5003, debug=False, threaded=True)
    else:
        # Test with the specific file
        test_file = "Note Checklist - Station 1A - Rash - Psoriasis.xlsx"
        
        logger.info("🚀 Testing backend.py with Excel file")
        logger.info("=" * 50)
        
        # Test the file processing
        success = test_with_file(test_file)
        
        if success:
            logger.info("\n🎉 Test completed successfully!")
            logger.info("✅ Your backend.py is working perfectly!")
            logger.info("\n💡 To run the web server for rubricon, use:")
            logger.info("   python3 backend.py --server")
        else:
            logger.info("\n⚠️  Test failed. Please check the file path and try again.")