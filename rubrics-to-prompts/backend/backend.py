from pathlib import Path
from openai import OpenAI
from PIL import Image
import pandas as pd
from docx import Document
import mammoth
import pytesseract
import pdfplumber
import os
import json
import yaml

# Initialize OpenAI client with error handling
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key)
    else:
        client = None
        print("OpenAI API key not found, using fallback processing")
except Exception as e:
    client = None
    print(f"OpenAI initialization failed: {e}")


def upload_file(file_path):
    """Main function that processes uploaded files and returns structured rubric data"""
    file = Path(file_path)
    suffix = file.suffix.lower()
    
    print(f"Processing file: {file.name} ({suffix})")

    if suffix == ".pdf":
        results = parse_pdf(file_path)
    elif suffix == ".docx":
        doc = Document(file_path)
        results = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
    elif suffix == ".doc":
        with open(file_path, "rb") as doc_file:
            result = mammoth.convert_to_text(doc_file)
            text = result.value
            results = [chunk.strip() for chunk in text.split("\n") if chunk.strip()]
    elif suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(file_path)
        results = df.apply(
            lambda row: " | ".join(str(v) for v in row if pd.notnull(v)), axis=1
        ).tolist()
    elif suffix == ".csv":
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
        # Unsupported file type, return default
        results = []

    return generate_rubric_with_llm(results, file.name)


def parse_pdf(path):
    """Extract text from PDF files"""
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


def generate_rubric_with_llm(chunks, filename="uploaded_file"):
    """Generate rubric using LLM or fallback to pattern analysis"""
    
    # If no content extracted, use fallback
    if not chunks:
        return generate_fallback_rubric(filename)
    
    # If OpenAI client available, use LLM
    if client:
        try:
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
            return generate_pattern_based_rubric(chunks, filename)
    
    # Fallback to pattern-based processing
    return generate_pattern_based_rubric(chunks, filename)


def generate_pattern_based_rubric(chunks, filename):
    """Generate rubric using pattern matching when LLM is not available"""
    
    full_text = " ".join(chunks).lower()
    
    # Medical assessment patterns
    patterns = {
        'history': ['history', 'chief complaint', 'symptoms', 'hpi', 'present illness'],
        'physical': ['physical exam', 'examination', 'inspect', 'palpat', 'auscult', 'vital'],
        'communication': ['communication', 'explain', 'rapport', 'patient education'],
        'diagnosis': ['diagnosis', 'reasoning', 'differential', 'assessment', 'clinical'],
        'management': ['management', 'treatment', 'plan', 'intervention', 'therapy'],
        'professional': ['professional', 'ethical', 'respectful', 'empathy', 'consent']
    }
    
    criteria = []
    total_points = 0
    
    # Extract criteria based on patterns found in text
    for category, keywords in patterns.items():
        if any(keyword in full_text for keyword in keywords):
            if category == 'history':
                name = "History Taking"
                points = 6
                examples = ["Tell me about your symptoms", "When did this start?", "Any family history?"]
            elif category == 'physical':
                name = "Physical Examination"
                points = 8
                examples = ["I'm going to examine you now", "Let me check this area", "Does this hurt?"]
            elif category == 'communication':
                name = "Communication Skills"
                points = 4
                examples = ["Do you have any questions?", "Let me explain what I found", "I want to make sure you understand"]
            elif category == 'diagnosis':
                name = "Clinical Reasoning"
                points = 4
                examples = ["Based on my findings", "The most likely diagnosis", "I need to consider"]
            elif category == 'management':
                name = "Management Plan"
                points = 4
                examples = ["I recommend this treatment", "Your management plan", "We should monitor"]
            elif category == 'professional':
                name = "Professional Behavior"
                points = 2
                examples = ["I respect your concerns", "With your permission", "Your privacy is important"]
            
            criteria.append({
                "name": name,
                "points": points,
                "description": f"Assessment of {name.lower()}",
                "examples": examples
            })
            total_points += points
    
    # If no patterns found, use default medical criteria
    if not criteria:
        return generate_fallback_rubric(filename)
    
    rubric = {
        "title": f"OSCE Assessment - {Path(filename).stem}",
        "total_points": total_points,
        "criteria": criteria
    }
    
    return format_rubric_response(rubric)


def generate_fallback_rubric(filename):
    """Generate default medical assessment rubric"""
    rubric = {
        "title": f"Clinical Assessment - {Path(filename).stem}",
        "total_points": 20,
        "criteria": [
            {
                "name": "History Taking",
                "points": 6,
                "description": "Gathers relevant patient history",
                "examples": ["Tell me about your symptoms", "When did this start?", "Any family history?"]
            },
            {
                "name": "Physical Examination",
                "points": 8,
                "description": "Performs appropriate physical examination",
                "examples": ["I'm going to examine you now", "Let me check this area", "Does this hurt?"]
            },
            {
                "name": "Communication Skills",
                "points": 4,
                "description": "Communicates clearly and professionally",
                "examples": ["Do you have any questions?", "Let me explain what I found", "I want to make sure you understand"]
            },
            {
                "name": "Professional Behavior",
                "points": 2,
                "description": "Demonstrates professional conduct",
                "examples": ["I respect your concerns", "With your permission", "Your privacy is important"]
            }
        ]
    }
    
    return format_rubric_response(rubric)


def format_rubric_response(rubric_data):
    """Format rubric data for frontend consumption"""
    return {
        "success": True,
        "rubric": rubric_data,
        "yaml_content": generate_yaml_from_rubric(rubric_data)
    }


def generate_yaml_from_rubric(rubric_data):
    """Generate YAML content from rubric data"""
    
    criteria_text = ""
    for criterion in rubric_data["criteria"]:
        criteria_text += f"  - {criterion['name']} ({criterion['points']} points): {criterion['description']}\n"
    
    yaml_content = f"""# OSCE Assessment Rubric
# {rubric_data['title']}
# Total Points: {rubric_data['total_points']}

system_message: |
  You are a helpful assistant tasked with analyzing and scoring a recorded medical examination between a medical student and a patient. Provide your response in JSON format.

user_message: |
  Your task is to identify and score the following assessment criteria in the medical examination.
  
  Assessment Criteria:
{criteria_text}

response_config:
  structured_output: true
  format: json

assessment_config:
  type: "medical_osce_assessment"
  version: "2.0"
  criteria_count: {len(rubric_data['criteria'])}
  total_points: {rubric_data['total_points']}

assessment_criteria:"""

    for i, criterion in enumerate(rubric_data["criteria"]):
        yaml_content += f"""
  - id: "criterion_{i + 1}"
    name: "{criterion['name']}"
    max_points: {criterion['points']}
    description: "{criterion['description']}"
    verbalization_examples:"""
        
        for example in criterion["examples"]:
            yaml_content += f"""
      - "{example}\""""
    
    return yaml_content


def main():
    """Test function"""
    test_file = "test_rubric.txt"
    if os.path.exists(test_file):
        result = upload_file(test_file)
        print(json.dumps(result, indent=2))
    else:
        print("Test file not found")


if __name__ == "__main__":
    main()