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
from typing import List, Dict, Any

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def upload_file(file_path: str) -> dict:
    """Process uploaded file and generate rubric data"""
    file = Path(file_path)
    suffix = file.suffix.lower()

    # Extract text based on file type
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
        # For other file types, return empty results
        results = []

    return generate_rubric_with_llm(results)


def parse_pdf(path: str) -> List[str]:
    """Extract text chunks from PDF"""
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


def generate_rubric_with_llm(chunks: List[str]) -> dict:
    """Generate structured rubric using LLM"""
    if not chunks:
        # Return default rubric if no text extracted
        return generate_default_rubric()
    
    rubric_text = "\n".join(f"- {chunk}" for chunk in chunks[:50])  # Limit to first 50 chunks
    
    prompt = f"""
    You're an expert assistant. Based on the following extracted rubric text, generate a structured OSCE assessment rubric.
    
    Return a JSON object with this structure:
    {{
        "title": "Assessment Title",
        "total_points": 20,
        "criteria": [
            {{
                "name": "Criterion Name",
                "points": 5,
                "description": "What is being assessed",
                "examples": ["Example verbalization 1", "Example verbalization 2"]
            }}
        ]
    }}

    Rubric Text:
    {rubric_text}
    
    Generate 3-6 criteria based on the content. Make sure the points add up to a reasonable total (15-30 points).
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {
                    "role": "system",
                    "content": "You help convert medical assessment rubrics into structured JSON format."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )

        result = json.loads(response.choices[0].message.content)
        return format_rubric_response(result)
    
    except Exception as e:
        print(f"LLM generation failed: {e}")
        return generate_default_rubric()


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