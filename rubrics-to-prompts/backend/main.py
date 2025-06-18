import os
import io
import json
import yaml
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import pytesseract
import easyocr
from PIL import Image
import aiofiles
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
import openai
from models import RubricPrompt, RubricSection, RubricItem
import tempfile
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Rubrics to Prompts API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Azure OpenAI client
openai.api_type = "azure"
openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
openai.api_version = "2024-02-15-preview"
openai.api_key = os.getenv("AZURE_OPENAI_KEY")

# Initialize EasyOCR reader (lazy loading)
ocr_reader = None

def get_ocr_reader():
    global ocr_reader
    if ocr_reader is None:
        ocr_reader = easyocr.Reader(['en'])
    return ocr_reader

class ProcessingStatus(BaseModel):
    step: str
    message: str
    progress: float
    completed: bool = False

class ProcessingResponse(BaseModel):
    task_id: str
    status: str
    message: str

# In-memory task storage (use Redis in production)
task_storage = {}

async def extract_text_from_file(file_path: str, file_type: str) -> str:
    """Extract text from various file formats using OCR"""
    try:
        if file_type.lower() in ['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp']:
            # Use both Tesseract and EasyOCR for better accuracy
            
            # Tesseract OCR
            try:
                if file_type.lower() == 'pdf':
                    # For PDF, convert to image first (simplified approach)
                    # In production, use pdf2image library
                    image = Image.open(file_path).convert('RGB')
                else:
                    image = Image.open(file_path)
                
                tesseract_text = pytesseract.image_to_string(image, config='--psm 6')
                logger.info(f"Tesseract extracted {len(tesseract_text)} characters")
            except Exception as e:
                logger.warning(f"Tesseract OCR failed: {e}")
                tesseract_text = ""
            
            # EasyOCR
            try:
                reader = get_ocr_reader()
                easyocr_results = reader.readtext(file_path)
                easyocr_text = ' '.join([result[1] for result in easyocr_results])
                logger.info(f"EasyOCR extracted {len(easyocr_text)} characters")
            except Exception as e:
                logger.warning(f"EasyOCR failed: {e}")
                easyocr_text = ""
            
            # Combine results, preferring the longer extraction
            if len(easyocr_text) > len(tesseract_text):
                extracted_text = easyocr_text
                logger.info("Using EasyOCR result")
            else:
                extracted_text = tesseract_text
                logger.info("Using Tesseract result")
        
        elif file_type.lower() in ['txt', 'csv']:
            # Read text files directly
            async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
                extracted_text = await f.read()
        
        elif file_type.lower() in ['doc', 'docx', 'xls', 'xlsx']:
            # For now, treat as text (in production, use python-docx, openpyxl)
            try:
                async with aiofiles.open(file_path, mode='r', encoding='utf-8', errors='ignore') as f:
                    extracted_text = await f.read()
            except:
                # Fallback to OCR for complex documents
                image = Image.open(file_path)
                extracted_text = pytesseract.image_to_string(image)
        
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        return extracted_text.strip()
    
    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to extract text from file: {str(e)}")

async def generate_yaml_prompt(rubric_text: str, task_id: str) -> Dict[str, Any]:
    """Generate YAML prompt using Azure OpenAI with retry logic"""
    
    # Update task status
    task_storage[task_id]['status'] = ProcessingStatus(
        step="ai_generation",
        message="Generating YAML prompt with AI...",
        progress=60.0
    )
    
    prompt = f"""
You are an expert at converting OSCE exam rubrics into structured YAML prompts for AI assessment systems.

Convert the following rubric text into a well-structured YAML format:

RUBRIC TEXT:
{rubric_text}

Your task is to:
1. Identify different sections/categories in the rubric
2. Extract individual assessment items with their point values
3. Create meaningful IDs for each item
4. Structure everything into a clean YAML format

EXAMPLE OUTPUT FORMAT:
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
      - item_id: "lung_auscultation_posterior"
        description: "Auscultate posterior lung fields"
        points: 1
        criteria: "Student properly places stethoscope on posterior chest"
  
  - section_name: "Communication Skills"
    section_id: "communication"
    description: "Assessment of patient communication"
    items:
      - item_id: "greeting"
        description: "Appropriate greeting and introduction"
        points: 2
        criteria: "Student introduces themselves professionally"
```

Important guidelines:
- Generate descriptive but concise item_ids using snake_case
- Include point values for each item
- Add meaningful criteria descriptions
- Ensure the YAML is valid and well-structured
- If sections aren't clear, create logical groupings
- Total points should sum correctly

Please generate ONLY the YAML output, no explanations or markdown formatting.
"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Update progress
            task_storage[task_id]['status'] = ProcessingStatus(
                step="ai_generation",
                message=f"AI processing attempt {attempt + 1}/{max_retries}...",
                progress=60.0 + (attempt * 10)
            )
            
            response = openai.ChatCompletion.create(
                engine=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
                messages=[
                    {"role": "system", "content": "You are an expert at converting medical assessment rubrics into structured YAML formats."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            yaml_content = response.choices[0].message.content.strip()
            
            # Clean up the response (remove markdown if present)
            if yaml_content.startswith("```yaml"):
                yaml_content = yaml_content[7:]
            if yaml_content.startswith("```"):
                yaml_content = yaml_content[3:]
            if yaml_content.endswith("```"):
                yaml_content = yaml_content[:-3]
            
            yaml_content = yaml_content.strip()
            
            # Validate YAML
            try:
                parsed_yaml = yaml.safe_load(yaml_content)
                logger.info("YAML validation successful")
                
                # Update task status
                task_storage[task_id]['status'] = ProcessingStatus(
                    step="validation",
                    message="Validating generated YAML...",
                    progress=90.0
                )
                
                return {
                    "yaml_content": yaml_content,
                    "parsed_yaml": parsed_yaml,
                    "validation_success": True
                }
            
            except yaml.YAMLError as e:
                logger.warning(f"YAML validation failed on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    raise HTTPException(status_code=500, detail=f"Generated YAML is invalid: {str(e)}")
                continue
        
        except Exception as e:
            logger.error(f"AI generation failed on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise HTTPException(status_code=500, detail=f"Failed to generate YAML after {max_retries} attempts: {str(e)}")
            await asyncio.sleep(1)  # Brief delay before retry
    
    raise HTTPException(status_code=500, detail="Failed to generate valid YAML")

@app.post("/upload-rubric")
async def upload_rubric(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload and process a rubric file"""
    
    # Generate task ID
    import uuid
    task_id = str(uuid.uuid4())
    
    # Initialize task storage
    task_storage[task_id] = {
        'status': ProcessingStatus(
            step="upload",
            message="File uploaded successfully",
            progress=10.0
        ),
        'result': None,
        'error': None
    }
    
    # Validate file type
    allowed_extensions = ['pdf', 'xls', 'doc', 'docx', 'txt', 'xlsx', 'csv', 'png', 'jpg', 'jpeg']
    file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    
    if file_extension not in allowed_extensions:
        task_storage[task_id]['error'] = f"Unsupported file type: {file_extension}"
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}")
    
    # Read file content before background processing
    file_content = await file.read()
    
    # Start background processing
    background_tasks.add_task(process_rubric_background, file_content, file.filename, task_id, file_extension)
    
    return ProcessingResponse(
        task_id=task_id,
        status="processing",
        message="File uploaded successfully. Processing started."
    )

async def process_rubric_background(file_content: bytes, filename: str, task_id: str, file_extension: str):
    """Background task to process the rubric file"""
    try:
        # Update status: File processing
        task_storage[task_id]['status'] = ProcessingStatus(
            step="file_processing",
            message="Processing uploaded file...",
            progress=20.0
        )
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            # Update status: Text extraction
            task_storage[task_id]['status'] = ProcessingStatus(
                step="ocr_processing",
                message="Extracting text from document...",
                progress=40.0
            )
            
            # Extract text
            extracted_text = await extract_text_from_file(temp_file_path, file_extension)
            
            if not extracted_text.strip():
                raise HTTPException(status_code=400, detail="No text could be extracted from the file")
            
            logger.info(f"Extracted text length: {len(extracted_text)} characters")
            
            # Generate YAML prompt
            result = await generate_yaml_prompt(extracted_text, task_id)
            
            # Update final status
            task_storage[task_id]['status'] = ProcessingStatus(
                step="completed",
                message="Processing completed successfully!",
                progress=100.0,
                completed=True
            )
            
            # Store result
            task_storage[task_id]['result'] = {
                'original_text': extracted_text,
                'yaml_content': result['yaml_content'],
                'parsed_yaml': result['parsed_yaml'],
                'filename': filename
            }
            
        finally:
            # Cleanup temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass
    
    except Exception as e:
        logger.error(f"Background processing failed: {e}")
        task_storage[task_id]['error'] = str(e)
        task_storage[task_id]['status'] = ProcessingStatus(
            step="error",
            message=f"Processing failed: {str(e)}",
            progress=0.0
        )

@app.get("/status/{task_id}")
async def get_processing_status(task_id: str):
    """Get the processing status of a task"""
    if task_id not in task_storage:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = task_storage[task_id]
    
    if task_data.get('error'):
        return {
            "status": "error",
            "error": task_data['error']
        }
    
    status = task_data['status']
    response = {
        "status": "completed" if status.completed else "processing",
        "step": status.step,
        "message": status.message,
        "progress": status.progress
    }
    
    if status.completed and task_data.get('result'):
        response['result'] = task_data['result']
    
    return response

@app.post("/update-yaml/{task_id}")
async def update_yaml(task_id: str, updated_yaml: Dict[str, Any]):
    """Update the generated YAML content"""
    if task_id not in task_storage:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = task_storage[task_id]
    if not task_data.get('result'):
        raise HTTPException(status_code=400, detail="No result found to update")
    
    try:
        # Validate the updated YAML
        yaml_content = updated_yaml.get('yaml_content', '')
        parsed_yaml = yaml.safe_load(yaml_content)
        
        # Update the stored result
        task_data['result']['yaml_content'] = yaml_content
        task_data['result']['parsed_yaml'] = parsed_yaml
        
        return {"message": "YAML updated successfully", "status": "success"}
    
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML format: {str(e)}")

@app.get("/download-yaml/{task_id}")
async def download_yaml(task_id: str):
    """Download the generated YAML file"""
    if task_id not in task_storage:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = task_storage[task_id]
    result = task_data.get('result')
    
    if not result:
        raise HTTPException(status_code=400, detail="No result found to download")
    
    # Create temporary YAML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
        temp_file.write(result['yaml_content'])
        temp_file_path = temp_file.name
    
    # Generate filename
    original_filename = result.get('filename', 'rubric')
    yaml_filename = f"{original_filename.split('.')[0]}_prompt.yaml"
    
    return FileResponse(
        path=temp_file_path,
        filename=yaml_filename,
        media_type='application/x-yaml'
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Rubrics to Prompts API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 