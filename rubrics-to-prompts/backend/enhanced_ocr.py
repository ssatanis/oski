import os
import json
import base64
import boto3
from typing import List, Dict, Any, Optional
from pathlib import Path
import tempfile
from PIL import Image
import pdf2image
import io

# Google Vision API
try:
    from google.cloud import vision
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    GOOGLE_VISION_AVAILABLE = False
    print("Google Vision API not available. Install: pip install google-cloud-vision")

# AWS Services
try:
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

class EnhancedOCRProcessor:
    def __init__(self):
        self.google_client = None
        self.aws_textract = None
        self.aws_comprehend = None
        
        # Initialize Google Vision
        if GOOGLE_VISION_AVAILABLE and os.getenv('GOOGLE_VISION_API_KEY'):
            try:
                # Set up Google Vision with API key
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self._create_google_credentials()
                self.google_client = vision.ImageAnnotatorClient()
            except Exception as e:
                print(f"Failed to initialize Google Vision: {e}")
        
        # Initialize AWS services
        if AWS_AVAILABLE and all([
            os.getenv('AWS_ACCESS_KEY_ID'),
            os.getenv('AWS_SECRET_ACCESS_KEY'),
            os.getenv('AWS_REGION')
        ]):
            try:
                session = boto3.Session(
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                    region_name=os.getenv('AWS_REGION', 'us-east-1')
                )
                self.aws_textract = session.client('textract')
                self.aws_comprehend = session.client('comprehend')
            except Exception as e:
                print(f"Failed to initialize AWS services: {e}")
    
    def _create_google_credentials(self) -> str:
        """Create temporary Google credentials file from API key"""
        api_key = os.getenv('GOOGLE_VISION_API_KEY')
        if not api_key:
            return None
            
        credentials = {
            "type": "service_account",
            "project_id": "rubric-processor",
            "private_key_id": "1",
            "private_key": f"-----BEGIN PRIVATE KEY-----\n{api_key}\n-----END PRIVATE KEY-----\n",
            "client_email": "vision@rubric-processor.iam.gserviceaccount.com",
            "client_id": "1",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(credentials, temp_file)
        temp_file.close()
        return temp_file.name
    
    def extract_text_from_file(self, file_path: str) -> Dict[str, Any]:
        """Extract text using multiple OCR methods for best results"""
        file_ext = Path(file_path).suffix.lower()
        
        results = {
            'text': '',
            'confidence': 0.0,
            'method': 'none',
            'structured_data': [],
            'medical_entities': []
        }
        
        try:
            if file_ext == '.pdf':
                results = self._process_pdf(file_path)
            elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                results = self._process_image(file_path)
            elif file_ext in ['.docx', '.doc']:
                results = self._process_document(file_path)
            elif file_ext in ['.xlsx', '.xls', '.csv']:
                results = self._process_spreadsheet(file_path)
            else:
                # Try reading as text
                with open(file_path, 'r', encoding='utf-8') as f:
                    results['text'] = f.read()
                    results['method'] = 'direct_text'
                    results['confidence'] = 1.0
        
        except Exception as e:
            print(f"Error processing file: {e}")
            results['text'] = f"Error processing file: {str(e)}"
        
        return results
    
    def _process_pdf(self, file_path: str) -> Dict[str, Any]:
        """Process PDF with multiple extraction methods"""
        best_result = {'text': '', 'confidence': 0.0, 'method': 'none'}
        
        # Method 1: Convert to images and use OCR
        try:
            images = pdf2image.convert_from_path(file_path)
            combined_text = ""
            total_confidence = 0
            
            for i, image in enumerate(images):
                # Save to temp file for processing
                temp_image = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                image.save(temp_image.name, 'PNG')
                
                # Try multiple OCR methods
                page_results = self._extract_from_image(temp_image.name)
                combined_text += f"\n--- Page {i+1} ---\n{page_results['text']}\n"
                total_confidence += page_results['confidence']
                
                os.unlink(temp_image.name)
            
            best_result = {
                'text': combined_text,
                'confidence': total_confidence / len(images) if images else 0,
                'method': 'pdf_to_image_ocr'
            }
        
        except Exception as e:
            print(f"PDF processing failed: {e}")
        
        # Method 2: Direct PDF text extraction
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                
                if len(text.strip()) > len(best_result['text']):
                    best_result = {
                        'text': text,
                        'confidence': 0.9,
                        'method': 'pdfplumber'
                    }
        except Exception as e:
            print(f"PDFPlumber extraction failed: {e}")
        
        return best_result
    
    def _process_image(self, file_path: str) -> Dict[str, Any]:
        """Process image file with multiple OCR methods"""
        return self._extract_from_image(file_path)
    
    def _extract_from_image(self, image_path: str) -> Dict[str, Any]:
        """Extract text from image using available OCR services"""
        results = []
        
        # Method 1: Google Vision API
        if self.google_client:
            try:
                result = self._google_vision_ocr(image_path)
                results.append(result)
            except Exception as e:
                print(f"Google Vision failed: {e}")
        
        # Method 2: AWS Textract
        if self.aws_textract:
            try:
                result = self._aws_textract_ocr(image_path)
                results.append(result)
            except Exception as e:
                print(f"AWS Textract failed: {e}")
        
        # Method 3: Tesseract fallback
        try:
            import pytesseract
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, config='--psm 6')
            results.append({
                'text': text,
                'confidence': 0.7,
                'method': 'tesseract'
            })
        except Exception as e:
            print(f"Tesseract failed: {e}")
        
        # Return the best result
        if results:
            best = max(results, key=lambda x: x['confidence'])
            return best
        
        return {'text': '', 'confidence': 0.0, 'method': 'none'}
    
    def _google_vision_ocr(self, image_path: str) -> Dict[str, Any]:
        """Extract text using Google Vision API"""
        with open(image_path, 'rb') as image_file:
            content = image_file.read()
        
        image = vision.Image(content=content)
        response = self.google_client.text_detection(image=image)
        
        if response.error.message:
            raise Exception(f'Google Vision API error: {response.error.message}')
        
        texts = response.text_annotations
        if texts:
            return {
                'text': texts[0].description,
                'confidence': 0.95,
                'method': 'google_vision'
            }
        
        return {'text': '', 'confidence': 0.0, 'method': 'google_vision'}
    
    def _aws_textract_ocr(self, image_path: str) -> Dict[str, Any]:
        """Extract text using AWS Textract"""
        with open(image_path, 'rb') as image_file:
            image_bytes = image_file.read()
        
        response = self.aws_textract.detect_document_text(
            Document={'Bytes': image_bytes}
        )
        
        text_lines = []
        confidence_scores = []
        
        for block in response['Blocks']:
            if block['BlockType'] == 'LINE':
                text_lines.append(block['Text'])
                confidence_scores.append(block['Confidence'])
        
        combined_text = '\n'.join(text_lines)
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        return {
            'text': combined_text,
            'confidence': avg_confidence / 100.0,  # Convert to 0-1 scale
            'method': 'aws_textract'
        }
    
    def _process_document(self, file_path: str) -> Dict[str, Any]:
        """Process DOCX/DOC files"""
        try:
            from docx import Document
            doc = Document(file_path)
            text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            
            return {
                'text': text,
                'confidence': 1.0,
                'method': 'docx_parser'
            }
        except Exception as e:
            # Fallback to mammoth for DOC files
            try:
                import mammoth
                with open(file_path, 'rb') as doc_file:
                    result = mammoth.convert_to_text(doc_file)
                    return {
                        'text': result.value,
                        'confidence': 0.9,
                        'method': 'mammoth'
                    }
            except Exception as e2:
                return {'text': f'Error: {str(e2)}', 'confidence': 0.0, 'method': 'error'}
    
    def _process_spreadsheet(self, file_path: str) -> Dict[str, Any]:
        """Process Excel/CSV files"""
        try:
            import pandas as pd
            
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            # Convert to text representation
            text_lines = []
            text_lines.append("SPREADSHEET DATA:")
            text_lines.append(f"Columns: {', '.join(df.columns.tolist())}")
            text_lines.append("")
            
            for _, row in df.iterrows():
                row_text = " | ".join([f"{col}: {str(val)}" for col, val in row.items() if pd.notna(val)])
                text_lines.append(row_text)
            
            return {
                'text': '\n'.join(text_lines),
                'confidence': 1.0,
                'method': 'pandas'
            }
        except Exception as e:
            return {'text': f'Error: {str(e)}', 'confidence': 0.0, 'method': 'error'}
    
    def analyze_medical_content(self, text: str) -> Dict[str, Any]:
        """Analyze extracted text for medical assessment patterns"""
        if self.aws_comprehend:
            try:
                # Use AWS Comprehend Medical for entity extraction
                response = self.aws_comprehend.detect_entities_v2(
                    Text=text[:5000],  # Limit text length
                    LanguageCode='en'
                )
                
                medical_entities = []
                for entity in response.get('Entities', []):
                    if entity['Type'] in ['MEDICAL_CONDITION', 'PROCEDURE', 'ANATOMY']:
                        medical_entities.append({
                            'text': entity['Text'],
                            'type': entity['Type'],
                            'confidence': entity['Score']
                        })
                
                return {'medical_entities': medical_entities}
            except Exception as e:
                print(f"Medical analysis failed: {e}")
        
        return {'medical_entities': []}

# Global instance
ocr_processor = EnhancedOCRProcessor() 