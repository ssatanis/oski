from pathlib import Path
from openai import OpenAI
from PIL import Image
import pandas as pd
from docx import Document
import mammoth
import pytesseract
import pdfplumber
import os
import yaml
import json
import re
from typing import List, Dict, Any
from enhanced_ocr import ocr_processor

# Initialize OpenAI client
openai_api_key = os.getenv("AZURE_OPENAI_KEY")
if openai_api_key:
    client = OpenAI(api_key=openai_api_key)
else:
    client = None
    print("Warning: OpenAI API key not found. Using fallback processing without LLM.")


def upload_file(file_path: str) -> dict:
    """Process uploaded file and generate rubric data with enhanced accuracy"""
    file = Path(file_path)
    suffix = file.suffix.lower()
    
    print(f"Processing file: {file.name} ({suffix})")
    
    # Use enhanced OCR for better text extraction
    ocr_result = ocr_processor.extract_text_from_file(file_path)
    extracted_text = ocr_result['text']
    confidence = ocr_result['confidence']
    method = ocr_result['method']
    
    print(f"Text extraction: {method} (confidence: {confidence:.2f})")
    print(f"Extracted text preview: {extracted_text[:200]}...")
    
    # Process with enhanced rubric analysis
    return generate_rubric_with_enhanced_analysis(extracted_text, file.name, method, confidence)


def generate_rubric_with_enhanced_analysis(text: str, filename: str, extraction_method: str, confidence: float) -> dict:
    """Generate rubric with enhanced analysis for accurate content detection"""
    
    if not text or len(text.strip()) < 10:
        print("Insufficient text extracted, using filename-based fallback")
        return format_rubric_response(generate_filename_based_rubric(filename))
    
    # Use LLM if available for high-quality extraction
    if client and confidence > 0.7:
        try:
            print("Using LLM for high-confidence extraction")
            return generate_rubric_with_llm([text], filename)
        except Exception as e:
            print(f"LLM processing failed: {e}")
    
    # Enhanced pattern-based analysis
    print("Using enhanced pattern analysis")
    return generate_rubric_with_enhanced_patterns(text, filename)


def generate_rubric_with_enhanced_patterns(text: str, filename: str) -> dict:
    """Advanced pattern-based rubric extraction"""
    
    # Clean and normalize text
    text_lower = text.lower()
    lines = text.split('\n')
    
    # Detect actual assessment criteria from the text
    detected_criteria = []
    
    # Enhanced pattern matching for medical assessments
    criteria_patterns = {
        # History taking patterns
        'history': {
            'patterns': ['history', 'chief complaint', 'symptom', 'hpi', 'present illness', 'patient interview'],
            'name': 'History Taking',
            'examples': ['Tell me about your symptoms', 'When did this start?', 'Can you describe the pain?']
        },
        # Physical examination patterns  
        'exam': {
            'patterns': ['physical exam', 'examination', 'inspect', 'palpat', 'auscult', 'percuss', 'vital signs'],
            'name': 'Physical Exam',
            'examples': ['I will examine you now', 'Let me listen to your heart', 'I need to check your pulse']
        },
        # Diagnostic/reasoning patterns
        'diagnosis': {
            'patterns': ['diagnos', 'reasoning', 'differential', 'assessment', 'clinical reasoning', 'justification'],
            'name': 'Diagnostic Accuracy/Reasoning/Justification', 
            'examples': ['Based on your symptoms', 'The most likely diagnosis', 'I need to consider']
        },
        # Management patterns
        'management': {
            'patterns': ['management', 'treatment', 'plan', 'intervention', 'therapy', 'medication'],
            'name': 'Management',
            'examples': ['I recommend we start with', 'Your treatment plan', 'Here is what we will do']
        },
        # Communication patterns
        'communication': {
            'patterns': ['communication', 'explain', 'patient education', 'counseling', 'rapport'],
            'name': 'Communication Skills',
            'examples': ['Do you have any questions?', 'Let me explain', 'I want to make sure you understand']
        },
        # Professionalism patterns
        'professional': {
            'patterns': ['professional', 'ethical', 'respectful', 'empathy', 'consent'],
            'name': 'Professionalism',
            'examples': ['I respect your concerns', 'With your permission', 'I understand this is difficult']
        }
    }
    
    # Score each pattern based on frequency and context
    pattern_scores = {}
    
    for pattern_id, pattern_data in criteria_patterns.items():
        score = 0
        matches = []
        
        for pattern in pattern_data['patterns']:
            # Count occurrences
            count = text_lower.count(pattern)
            score += count * 2
            
            # Bonus for line-starting matches (likely headers)
            for line in lines:
                if pattern in line.lower() and len(line.strip()) < 100:
                    score += 5
                    matches.append(line.strip())
        
        pattern_scores[pattern_id] = {
            'score': score,
            'data': pattern_data,
            'matches': matches
        }
    
    # Extract the top patterns that appear in the text
    sorted_patterns = sorted(pattern_scores.items(), key=lambda x: x[1]['score'], reverse=True)
    
    total_points = 0
    for pattern_id, pattern_info in sorted_patterns:
        if pattern_info['score'] > 0:  # Only include patterns found in text
            points = min(6, max(2, pattern_info['score']))  # 2-6 points based on relevance
            
            detected_criteria.append({
                'name': pattern_info['data']['name'],
                'points': points,
                'description': f"Assessment of {pattern_info['data']['name'].lower()}",
                'examples': pattern_info['data']['examples'],
                'matches_found': pattern_info['matches'][:3]  # Keep track of what was found
            })
            total_points += points
    
    # If no clear patterns found, try line-by-line analysis
    if not detected_criteria:
        print("No patterns found, analyzing lines directly")
        detected_criteria = analyze_lines_for_criteria(lines)
        total_points = sum(c['points'] for c in detected_criteria)
    
    # Fallback to intelligent defaults if still nothing found
    if not detected_criteria:
        print("Using intelligent defaults based on medical standards")
        detected_criteria = generate_smart_defaults(filename)
        total_points = sum(c['points'] for c in detected_criteria)
    
    rubric = {
        'title': f'Assessment Rubric for {Path(filename).stem}',
        'total_points': total_points,
        'criteria': detected_criteria,
        'extraction_info': {
            'method': 'enhanced_pattern_analysis',
            'patterns_detected': len([p for p in pattern_scores.values() if p['score'] > 0]),
            'text_length': len(text),
            'filename': filename
        }
    }
    
    return format_rubric_response(rubric)


def analyze_lines_for_criteria(lines: List[str]) -> List[Dict]:
    """Analyze individual lines to extract criteria"""
    criteria = []
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue
            
        # Skip obvious non-criteria lines
        if any(skip in line.lower() for skip in ['total', 'points', 'score', 'grade', 'yes', 'no', 'page']):
            continue
            
        # Look for lines that could be criteria
        if (len(line) > 10 and len(line) < 200 and 
            not line.startswith('http') and 
            not line.isdigit()):
            
            # Extract points if mentioned
            points_match = re.search(r'(\d+)\s*(?:points?|pts?)', line.lower())
            points = int(points_match.group(1)) if points_match else 3
            
            # Clean the criterion name
            clean_name = re.sub(r'\(\d+\s*(?:points?|pts?)\)', '', line).strip()
            clean_name = re.sub(r'^\d+[\.\-\)]\s*', '', clean_name).strip()
            
            if clean_name:
                criteria.append({
                    'name': clean_name,
                    'points': min(6, max(1, points)),
                    'description': f"Assessment of {clean_name.lower()}",
                    'examples': generate_examples_for_text(clean_name)
                })
    
    return criteria[:6]  # Limit to 6 criteria


def generate_examples_for_text(text: str) -> List[str]:
    """Generate contextually relevant examples based on the criterion text"""
    text_lower = text.lower()
    
    # Medical-specific example generation
    if any(word in text_lower for word in ['wash', 'hand', 'hygiene', 'clean']):
        return ["I will wash my hands before examining you", "Let me clean my hands", "Hand hygiene is important"]
    
    if any(word in text_lower for word in ['inspect', 'look', 'visual', 'examine']):
        return ["I'm going to examine this area visually", "Let me take a closer look", "I need to inspect this carefully"]
    
    if any(word in text_lower for word in ['introduce', 'greet', 'name']):
        return ["Hello, I'm Dr. Smith", "May I introduce myself?", "I'll be your doctor today"]
    
    if any(word in text_lower for word in ['consent', 'permission', 'okay']):
        return ["Is it okay if I examine you?", "Do I have your permission?", "May I proceed with the examination?"]
    
    if any(word in text_lower for word in ['skin', 'dermat', 'rash', 'lesion']):
        return ["I'm going to examine your skin", "Let me look at this area", "I need to check your skin condition"]
    
    if any(word in text_lower for word in ['pain', 'comfort', 'hurt']):
        return ["Does this hurt?", "Let me know if you feel any discomfort", "Rate your pain on a scale of 1-10"]
    
    # Generic medical examples
    return [
        f"Assessment related to {text.lower()}",
        f"I will evaluate {text.lower()}",
        f"Let me check {text.lower()}"
    ]


def generate_smart_defaults(filename: str) -> List[Dict]:
    """Generate intelligent default criteria based on filename and medical standards"""
    filename_lower = filename.lower()
    
    # File-specific patterns
    if any(word in filename_lower for word in ['skin', 'dermat', 'rash']):
        return [
            {'name': 'Skin Inspection', 'points': 4, 'description': 'Visual examination of skin', 'examples': ['I will examine your skin', 'Let me look at this area']},
            {'name': 'History Taking', 'points': 3, 'description': 'Gathering relevant history', 'examples': ['Tell me about the rash', 'When did this start?']},
            {'name': 'Physical Examination', 'points': 3, 'description': 'Physical assessment', 'examples': ['I need to feel this area', 'Let me check the texture']}
        ]
    
    if any(word in filename_lower for word in ['cardiac', 'heart', 'chest']):
        return [
            {'name': 'Cardiac History', 'points': 3, 'description': 'Cardiovascular history', 'examples': ['Any chest pain?', 'Tell me about your heart']},
            {'name': 'Cardiac Examination', 'points': 4, 'description': 'Heart examination', 'examples': ['I will listen to your heart', 'Let me check your pulse']},
            {'name': 'Assessment', 'points': 3, 'description': 'Clinical assessment', 'examples': ['Based on my findings', 'Your heart sounds normal']}
        ]
    
    # Standard OSCE defaults
    return [
        {'name': 'History Taking', 'points': 4, 'description': 'Patient history gathering', 'examples': ['Tell me about your symptoms', 'When did this start?']},
        {'name': 'Physical Exam', 'points': 4, 'description': 'Physical examination', 'examples': ['I will examine you now', 'Let me check this area']},
        {'name': 'Diagnostic Accuracy/Reasoning/Justification', 'points': 2, 'description': 'Clinical reasoning', 'examples': ['Based on my findings', 'The most likely diagnosis']}
    ]


def generate_rubric_with_llm(chunks: List[str], filename: str = "uploaded_file") -> dict:
    """Generate structured rubric using LLM"""
    if not chunks:
        return format_rubric_response(generate_default_rubric())
    
    # If no OpenAI client, use enhanced fallback processing
    if client is None:
        return process_rubric_without_llm(chunks)
    
    rubric_text = "\n".join(f"- {chunk}" for chunk in chunks[:50])
    
    prompt = f"""
    You're an expert medical assessment specialist. Based on the following extracted rubric text, generate a structured OSCE assessment rubric that accurately reflects the SPECIFIC content provided.

    IMPORTANT: Extract the ACTUAL criteria mentioned in the text, not generic ones. Pay attention to:
    - Specific assessment elements mentioned
    - Point values if indicated
    - Exact wording used in the original rubric
    
    Return a JSON object with this structure:
    {{
        "title": "Assessment Title",
        "total_points": 20,
        "criteria": [
            {{
                "name": "Exact Criterion Name from Text",
                "points": 5,
                "description": "What is being assessed",
                "examples": ["Specific verbalization example 1", "Specific verbalization example 2"]
            }}
        ]
    }}

    Rubric Text:
    {rubric_text}
    
    Extract ONLY the criteria that are actually mentioned in the text. Be precise and specific.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {
                    "role": "system",
                    "content": "You are a medical education expert who extracts precise assessment criteria from rubric text. Always use the exact wording from the source material."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )

        result = json.loads(response.choices[0].message.content)
        return format_rubric_response(result)
    
    except Exception as e:
        print(f"LLM generation failed: {e}")
        return format_rubric_response(generate_default_rubric())


def process_rubric_without_llm(chunks: List[str]) -> dict:
    """Process rubric text without LLM using pattern matching"""
    # Combine all chunks
    full_text = " ".join(chunks)
    
    # Use the enhanced pattern analysis
    return generate_rubric_with_enhanced_patterns(full_text, "uploaded_file.txt")


def generate_examples_for_criterion(criterion_name: str) -> List[str]:
    """Generate relevant examples for each criterion"""
    examples_map = {
        'Patient Introduction': [
            "Hello, I'm Dr. Smith and I'll be examining you today",
            "May I introduce myself?",
            "I'd like to start by getting to know you"
        ],
        'History Taking': [
            "Tell me about your symptoms",
            "When did this start?",
            "Can you describe the pain?",
            "Any family history of this condition?"
        ],
        'Physical Examination': [
            "I'm going to examine you now",
            "Let me listen to your heart",
            "I'll check your reflexes",
            "Does this hurt when I press here?"
        ],
        'Physical Exam': [
            "I'm going to examine you now",
            "Let me check this area",
            "I'll be gentle during the examination"
        ],
        'Communication Skills': [
            "Do you have any questions?",
            "Let me explain what I found",
            "I want to make sure you understand",
            "How are you feeling about this?"
        ],
        'Clinical Reasoning': [
            "Based on your symptoms and my examination",
            "The most likely diagnosis is",
            "I need to consider several possibilities",
            "Let me explain my thinking"
        ],
        'Diagnostic Accuracy/Reasoning/Justification': [
            "Based on my examination findings",
            "The evidence suggests",
            "My clinical reasoning leads me to",
            "I believe the diagnosis is"
        ],
        'Management Plan': [
            "I recommend we start with",
            "Here's what we should do next",
            "Your treatment plan includes",
            "We'll monitor your progress"
        ],
        'Management': [
            "I recommend this treatment",
            "Let's start with this approach",
            "Your management plan will include"
        ],
        'Professionalism': [
            "I respect your concerns",
            "Your privacy is important",
            "I want to ensure your comfort",
            "Thank you for your cooperation"
        ]
    }
    
    return examples_map.get(criterion_name, [
        f"Demonstrates {criterion_name.lower()}",
        f"Shows competency in {criterion_name.lower()}"
    ])


def generate_filename_based_rubric(filename: str) -> dict:
    """Generate rubric based on filename when no content can be extracted"""
    return {
        'title': f'Assessment for {Path(filename).stem}',
        'total_points': 10,
        'criteria': [
            {
                'name': 'Clinical Assessment',
                'points': 5,
                'description': 'Overall clinical performance',
                'examples': ['Demonstrates clinical competency', 'Shows appropriate assessment skills']
            },
            {
                'name': 'Professional Behavior',
                'points': 5,
                'description': 'Professional conduct and communication',
                'examples': ['Maintains professionalism', 'Communicates effectively']
            }
        ]
    }


def generate_default_rubric() -> dict:
    """Generate a default rubric when processing fails"""
    return {
        "title": "Clinical OSCE Assessment",
        "total_points": 20,
        "criteria": [
            {
                "name": "Patient Introduction",
                "points": 2,
                "description": "Introduces self and establishes rapport",
                "examples": ["Hello, I'm Dr. Smith", "I'll be examining you today"]
            },
            {
                "name": "History Taking",
                "points": 6,
                "description": "Gathers relevant patient history",
                "examples": ["Tell me about your symptoms", "When did this start?"]
            },
            {
                "name": "Physical Examination",
                "points": 8,
                "description": "Performs appropriate physical examination",
                "examples": ["I'm going to examine you now", "Let me check this area"]
            },
            {
                "name": "Communication Skills",
                "points": 4,
                "description": "Communicates clearly and professionally",
                "examples": ["Do you have any questions?", "Let me explain what I found"]
            }
        ]
    }


def format_rubric_response(rubric_data: dict) -> dict:
    """Format the rubric data for frontend consumption"""
    return {
        "success": True,
        "rubric": rubric_data,
        "yaml_content": generate_yaml_from_rubric(rubric_data)
    }


def generate_yaml_from_rubric(rubric_data: dict) -> str:
    """Convert rubric data to YAML format"""
    criteria = rubric_data.get("criteria", [])
    total_points = sum(c.get("points", 0) for c in criteria)
    
    yaml_content = f"""# OSCE Assessment Rubric
# {rubric_data.get('title', 'Clinical Assessment')}
# Total Points: {total_points}

system_message: |
  You are a helpful assistant tasked with analyzing and scoring a recorded medical examination between a medical student and a patient. Provide your response in JSON format.

user_message: |
  Your task is to identify and score the following assessment criteria in the medical examination.
  
  Assessment Criteria:
{chr(10).join(f'  - {c["name"]} ({c["points"]} points): {c.get("description", "")}' for c in criteria)}

response_config:
  structured_output: true
  format: json

assessment_config:
  type: "medical_osce_assessment"
  version: "2.0"
  criteria_count: {len(criteria)}
  total_points: {total_points}

assessment_criteria:
"""
    
    for i, criterion in enumerate(criteria):
        yaml_content += f"""  - id: "criterion_{i + 1}"
    name: "{criterion['name']}"
    max_points: {criterion['points']}
    description: "{criterion.get('description', '')}"
    verbalization_examples:
"""
        for example in criterion.get('examples', []):
            yaml_content += f'      - "{example}"\n'
    
    return yaml_content


def main():
    """Test the rubric generation"""
    test_file = "Station 1B - Skin Concern - Tinea.docx"
    if os.path.exists(test_file):
        result = upload_file(test_file)
        print("Generated Rubric:")
        print(json.dumps(result.get("rubric"), indent=2))
        print("\nYAML Content:")
        print(result.get("yaml_content"))
    else:
        print(f"Test file '{test_file}' not found")
        print("Generating default rubric:")
        result = generate_default_rubric()
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()