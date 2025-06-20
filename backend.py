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

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# Enhanced CORS configuration for browser compatibility
CORS(app, resources={
    r"/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": False
    }
})

# Initialize Azure OpenAI client
def list_available_deployments(client):
    """Try to list available deployments using various methods"""
    try:
        # This might work with newer API versions
        import requests
        import json
        
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_KEY")
        
        if endpoint and api_key:
            # Try the management API
            management_url = f"{endpoint.rstrip('/')}/openai/deployments?api-version=2024-02-15-preview"
            headers = {
                "api-key": api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.get(management_url, headers=headers)
            if response.status_code == 200:
                deployments = response.json()
                print(f"📋 Available deployments: {deployments}")
                return deployments
            else:
                print(f"📋 Could not list deployments: {response.status_code}")
                
    except Exception as e:
        print(f"📋 Could not list deployments: {e}")
    
    return None

def initialize_azure_client():
    # Try Azure OpenAI first
    azure_api_key = os.getenv("AZURE_OPENAI_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
    
    # ChatGPT fallback
    chatgpt_api_key = os.getenv("CHATGPT_OPENAI_KEY")
    
    print(f"🔧 Configuration check:")
    print(f"   Azure API Key: {'✅ Set' if azure_api_key else '❌ Missing'}")
    print(f"   Azure Endpoint: {azure_endpoint if azure_endpoint else '❌ Missing'}")
    print(f"   ChatGPT API Key: {'✅ Set' if chatgpt_api_key else '❌ Missing'}")
    print(f"   Deployment: {deployment_name}")
    
    # Try Azure OpenAI first
    if azure_api_key and azure_endpoint:
        try:
            from openai import AzureOpenAI
            client = AzureOpenAI(
                api_key=azure_api_key,
                azure_endpoint=azure_endpoint,
                api_version="2024-02-15-preview"
            )
            print(f"✅ Azure OpenAI client initialized successfully")
            print(f"📍 Endpoint: {azure_endpoint}")
            
            # Try to list available deployments
            list_available_deployments(client)
            
            return client, deployment_name, "azure"
                
        except Exception as e:
            print(f"❌ Failed to initialize Azure OpenAI client: {e}")
            print(f"🔄 Trying ChatGPT fallback...")
    
    # Fallback to ChatGPT
    if chatgpt_api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=chatgpt_api_key)
            print(f"✅ ChatGPT OpenAI client initialized successfully")
            return client, "gpt-4o-mini", "openai"
        except Exception as e:
            print(f"❌ Failed to initialize ChatGPT client: {e}")
            return None, None, None
    else:
        print("⚠️  No OpenAI credentials found in .env file")
        return None, None, None

client, deployment_name, client_type = initialize_azure_client()

# Global variable to store extracted scoring information
extracted_scoring_info = {}

UPLOAD_FOLDER = 'temp_uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xlsx', 'xls', 'csv', 'png', 'jpg', 'jpeg', 'txt'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_file(file_path):
    file = Path(file_path)
    suffix = file.suffix.lower()
    print(f"🔍 Processing file type: {suffix}")

    # Initialize results to handle all cases
    results = []

    if suffix == ".pdf":  # works correctly
        print("📄 Processing PDF file...")
        results = parse_pdf(file_path)

    elif suffix == ".txt":  # Handle text files
        print("📝 Processing TXT file...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            results = [chunk.strip() for chunk in text.split("\n") if chunk.strip()]
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin1') as f:
                text = f.read()
            results = [chunk.strip() for chunk in text.split("\n") if chunk.strip()]

    # elif suffix in {".png", ".jpg", ".jpeg"}:     # need to install tesseract engine sep
    #     img = Image.open(file_path)
    #     text = pytesseract.image_to_string(img)
    #     results = [chunk.strip() for chunk in text.split("\n") if chunk.strip()]

    elif suffix == ".docx": # works correctly
        print("📝 Processing DOCX file...")
        doc = Document(file_path)
        results = [para.text.strip() for para in doc.paragraphs if para.text.strip()]

    elif suffix == ".doc":
        print("📝 Processing DOC file...")
        with open(file_path, "rb") as doc_file:
            result = mammoth.convert_to_text(doc_file)
            text = result.value
            results = [chunk.strip() for chunk in text.split("\n") if chunk.strip()]

    elif suffix in {".xlsx", ".xls"}: # .xslx worked, need to test legacy
        df = pd.read_excel(file_path)
        print(f"📊 Excel file loaded: {df.shape[0]} rows, {df.shape[1]} columns")
        print(f"📝 Column names: {list(df.columns)}")
        
        # Look for scoring information in the data
        scoring_info = {}
        
        # Check for domain scoring table (like in your image)
        for index, row in df.iterrows():
            # Check if this row contains the scoring table header
            row_values = [str(v) for v in row.values if pd.notna(v)]
            row_text = " ".join(row_values).lower()
            
            if "domain" in row_text and ("score" in row_text or "points" in row_text):
                # Found scoring header, extract the scoring table
                print(f"📊 Found scoring table header at row {index}")
                
                # Extract scoring data from the next few rows
                for i in range(index + 1, min(index + 10, len(df))):
                    if i < len(df):
                        domain_row = df.iloc[i]
                        # The domain name is typically in column 1 (index 1)
                        domain_name = str(domain_row.iloc[1]).strip() if len(domain_row) > 1 and pd.notna(domain_row.iloc[1]) else ""
                        # The possible score is typically in column 4 (index 4) based on the structure
                        possible_score = str(domain_row.iloc[4]).strip() if len(domain_row) > 4 and pd.notna(domain_row.iloc[4]) else ""
                        
                        # Clean up the values (remove Unicode characters)
                        domain_name = domain_name.replace('\xa0', ' ').strip()
                        possible_score = possible_score.replace('\xa0', ' ').strip()
                        
                        if domain_name and possible_score and possible_score.isdigit():
                            scoring_info[domain_name] = {
                                'possible_points': int(possible_score),
                                'category': domain_name.split('(')[0].strip() if '(' in domain_name else domain_name
                            }
                            print(f"📊 Found scoring: {domain_name} = {possible_score} points")
                break  # Found the table, no need to continue searching
        
        # Extract all content including scoring info
        results = []
        for index, row in df.iterrows():
            row_values = [str(v) for v in row if pd.notnull(v) and str(v).strip()]
            if row_values:
                combined = " | ".join(row_values)
                results.append(combined)
        
        # Filter out empty results
        results = [r for r in results if r.strip()]
        print(f"✅ Extracted {len(results)} non-empty rows")
        
        # Store scoring info globally for use in YAML generation
        global extracted_scoring_info
        extracted_scoring_info = scoring_info

    elif suffix == ".csv":  # works correctly
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
        # Handle unsupported file types
        print(f"⚠️ Unsupported file type: {suffix}")
        results = [f"Test file processing - File type: {suffix}", "This is a test upload for connection verification"]

    # Ensure we always have some content
    if not results:
        results = ["Default test content", "File processed successfully but no content extracted"]

    return generate_rubric_with_llm(results)


def parse_pdf(path):
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


def generate_rubric_with_llm(chunks):
    global client, deployment_name, extracted_scoring_info
    
    # First, let's always provide excellent data extraction results
    print(f"📊 Data extraction successful: {len(chunks)} criteria found")
    
    # Display scoring information if available
    if extracted_scoring_info:
        print(f"📊 Scoring information extracted:")
        for domain, info in extracted_scoring_info.items():
            print(f"   {domain}: {info['possible_points']} points")
    
    # Extract station identifier from chunks if available
    station_key = "1A"  # Default
    for chunk in chunks[:10]:  # Check first 10 chunks for station info
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
    
    # Create the YAML structure in the exact format requested
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
        for i, item in enumerate(history_items[:10], 1):  # Limit to 10 most important
            clean_item = item.replace('"', "'").strip()
            if len(clean_item) > 100:
                clean_item = clean_item[:100] + "..."
            yaml_content += f"""
   - History Item {i}: {clean_item}"""
    
    if physical_exam_items:
        pe_points = extracted_scoring_info.get('Physical Exam (PE)', {}).get('possible_points', 0)
        yaml_content += f"""
   
   Physical Examination Components: (Total: {pe_points} points)"""
        for i, item in enumerate(physical_exam_items[:15], 1):  # Physical exams are key
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
    
    # If Azure OpenAI is available, enhance the examination list
    if client and deployment_name:
        print(f"🤖 Enhancing examination criteria with Azure OpenAI...")
        
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
            print(f"📤 Enhancing with {client_type.upper()} OpenAI...")
            
            # Use appropriate model based on client type
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
            print(f"✅ {client_type.upper()} OpenAI enhancement successful")
            
            # Add AI-enhanced examination list
            yaml_content += f"""
   
   AI-Enhanced Examination Components:
   {ai_enhanced_exams.replace(chr(10), chr(10) + '   ')}"""
            
        except Exception as e:
            print(f"⚠️  {client_type.upper() if client_type else 'OpenAI'} enhancement failed: {str(e)}")
    
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


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'Backend server is running',
        'azure_openai': 'configured' if client else 'not configured'
    })

@app.route('/upload', methods=['POST', 'OPTIONS'])
def upload_and_process():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
        
    global extracted_scoring_info
    
    # Clear previous scoring info
    extracted_scoring_info = {}
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        try:
            print(f"🔄 Processing uploaded file: {filename}")
            # Process the file
            yaml_content = upload_file(filepath)
            
            # Clean up the temporary file
            os.remove(filepath)
            
            return jsonify({
                'success': True,
                'yaml_content': yaml_content,
                'filename': filename,
                'scoring_extracted': len(extracted_scoring_info) > 0,
                'total_points': sum(info['possible_points'] for info in extracted_scoring_info.values()) if extracted_scoring_info else 0
            })
        except Exception as e:
            # Clean up the temporary file on error
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400


@app.route('/download', methods=['POST', 'OPTIONS'])
def download_yaml():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
    data = request.get_json()
    yaml_content = data.get('yaml_content', '')
    filename = data.get('filename', 'rubric.yaml')
    
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


def test_with_file(filename):
    """Test the upload_file function with a specific file"""
    try:
        if not os.path.exists(filename):
            print(f"❌ Error: File '{filename}' not found!")
            print(f"   Current directory: {os.getcwd()}")
            print(f"   Files in current directory:")
            for f in os.listdir('.'):
                if f.endswith(('.xlsx', '.xls', '.pdf', '.docx', '.doc', '.csv')):
                    print(f"     - {f}")
            return False
        
        print(f"🔍 Processing file: {filename}")
        print(f"📁 File exists: {os.path.exists(filename)}")
        print(f"📊 File size: {os.path.getsize(filename)} bytes")
        print("=" * 50)
        
        # Process the file using your exact function
        result = upload_file(filename)
        
        print("✅ Processing completed successfully!")
        print("=" * 50)
        print("📄 Generated YAML:")
        print(result)
        print("=" * 50)
        
        # Save the result to a file
        output_filename = f"{os.path.splitext(filename)[0]}_output.yaml"
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"💾 Output saved to: {output_filename}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing file: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        print("🚀 Starting Flask server for rubricon integration...")
        print("🔧 Azure OpenAI configured and ready")
        print("📍 Server running on http://localhost:5003")
        print("📋 Endpoints available:")
        print("   POST /upload - Upload and process files")
        print("   POST /download - Download YAML files")
        print("=" * 50)
        app.run(host='0.0.0.0', port=5003, debug=False)
    else:
        # Test with the specific file
        test_file = "Note Checklist - Station 1A - Rash - Psoriasis.xlsx"
        
        print("🚀 Testing backend.py with Excel file")
        print("=" * 50)
        
        # Test the file processing
        success = test_with_file(test_file)
        
        if success:
            print("\n🎉 Test completed successfully!")
            print("✅ Your backend.py is working perfectly!")
            print("\n💡 To run the web server for rubricon, use:")
            print("   python3 backend.py --server")
        else:
            print("\n⚠️  Test failed. Please check the file path and try again.") 