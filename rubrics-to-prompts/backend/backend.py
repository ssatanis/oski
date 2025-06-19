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

client = OpenAI(api_key=os.getenv("AZURE_OPENAI_KEY"))


def upload_file(file_path):
    """Process uploaded file and return structured rubric data"""
    file = Path(file_path)
    suffix = file.suffix.lower()

    if suffix == ".pdf":  # works correctly
        results = parse_pdf(file_path)

    elif suffix == ".docx": # works correctly
        doc = Document(file_path)
        results = [para.text.strip() for para in doc.paragraphs if para.text.strip()]

    elif suffix == ".doc":
        with open(file_path, "rb") as doc_file:
            result = mammoth.convert_to_text(doc_file)
            text = result.value
            results = [chunk.strip() for chunk in text.split("\n") if chunk.strip()]

    elif suffix in {".xlsx", ".xls"}: # .xlsx worked, need to test legacy
        df = pd.read_excel(file_path)
        results = df.apply(
            lambda row: " | ".join(str(v) for v in row if pd.notnull(v)), axis=1
        ).tolist()

    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    # Generate structured rubric data
    rubric_data = generate_rubric_with_llm(results)
    
    # Wrap in the expected response format
    return {
        "success": True,
        "interactiveRubric": rubric_data,
        "processedFiles": 1,
        "timestamp": pd.Timestamp.now().isoformat(),
        "analysisResult": {
            "combined_analysis": {
                "total_files": 1,
                "successful_extractions": 1,
                "failed_extractions": 0,
                "merged_criteria": extract_all_criteria(rubric_data),
                "confidence_scores": {"overall_average": 95}
            }
        }
    }

def extract_all_criteria(rubric_data):
    """Extract all criteria from rubric data for analysis"""
    all_criteria = []
    for domain in rubric_data.get("assessment_domains", []):
        for criterion in domain.get("subcategories", []):
            all_criteria.append({
                "name": criterion.get("name", ""),
                "points": criterion.get("points", 0),
                "category": criterion.get("category", ""),
                "description": criterion.get("description", "")
            })
    return all_criteria


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
    combined_text = '\n'.join(chunks)
    
    prompt = f"""
    You are an expert medical education assistant specializing in OSCE rubric analysis. 
    
    Based on the following extracted rubric text, generate a comprehensive structured rubric in JSON format that matches this exact structure:

    {{
        "rubric_info": {{
            "title": "Extract the title from the text (e.g., 'Station 1A - Rash - Psoriasis')",
            "station_info": {{
                "station_number": "Extract station number if present",
                "condition": "Extract medical condition if present",
                "specialty": "Determine medical specialty (e.g., Dermatology, Internal Medicine)"
            }},
            "total_points": "Calculate total possible points",
            "creation_timestamp": "{pd.Timestamp.now().isoformat()}",
            "source_files": 1
        }},
        "assessment_domains": [
            {{
                "name": "History Taking",
                "description": "Gathering patient history and presenting complaint",
                "editable": false,
                "total_points": "Sum of all criteria points in this domain",
                "subcategories": [
                    {{
                        "id": 1,
                        "name": "Extract criterion name from text",
                        "category": "Determine category (CC, HPI, PMH, Med, All, FH, SH)",
                        "points": "Extract point value",
                        "editable": true,
                        "description": "Detailed description of the criterion",
                        "current_points": 0
                    }}
                ]
            }},
            {{
                "name": "Physical Examination", 
                "description": "Conducting appropriate physical examination",
                "editable": false,
                "total_points": "Sum of all criteria points in this domain",
                "subcategories": []
            }},
            {{
                "name": "Diagnostic Accuracy/Reasoning/Justification",
                "description": "Demonstrating diagnostic reasoning and accuracy", 
                "editable": false,
                "total_points": "Sum of all criteria points in this domain",
                "subcategories": []
            }},
            {{
                "name": "Management",
                "description": "Providing appropriate management recommendations",
                "editable": false, 
                "total_points": "Sum of all criteria points in this domain",
                "subcategories": []
            }}
        ]
    }}

    IMPORTANT INSTRUCTIONS:
    1. Extract ALL individual criteria from the text and categorize them into the 4 domains above
    2. For each criterion, determine the appropriate category code (CC, HPI, PMH, Med, All, FH, SH, PE, DA, DR, M)
    3. Extract point values for each criterion (look for numbers in parentheses or after criteria)
    4. Assign sequential ID numbers starting from 1
    5. Look for medical specialty indicators (rash/psoriasis = Dermatology, etc.)
    6. Calculate accurate total points for each domain and overall
    7. Make criterion names descriptive and clear
    8. Set current_points to 0 for all criteria (scoring will be done in the interface)
    9. Return ONLY valid JSON, no additional text or formatting

    Rubric Text:
    {combined_text}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert medical education assistant. Return only valid JSON without any markdown formatting or additional text."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Clean up the response to ensure it's valid JSON
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        # Parse to validate JSON
        import json
        parsed_json = json.loads(response_text)
        return parsed_json
        
    except Exception as e:
        print(f"Error in LLM processing: {e}")
        # Return a fallback structure
        return {
            "rubric_info": {
                "title": "Medical Assessment Rubric",
                "station_info": {
                    "station_number": "Unknown",
                    "condition": "General Assessment", 
                    "specialty": "General Medicine"
                },
                "total_points": 0,
                "creation_timestamp": pd.Timestamp.now().isoformat(),
                "source_files": 1
            },
            "assessment_domains": [
                {
                    "name": "History Taking",
                    "description": "Gathering patient history and presenting complaint",
                    "editable": False,
                    "total_points": 0,
                    "subcategories": []
                },
                {
                    "name": "Physical Examination",
                    "description": "Conducting appropriate physical examination", 
                    "editable": False,
                    "total_points": 0,
                    "subcategories": []
                },
                {
                    "name": "Diagnostic Accuracy/Reasoning/Justification",
                    "description": "Demonstrating diagnostic reasoning and accuracy",
                    "editable": False, 
                    "total_points": 0,
                    "subcategories": []
                },
                {
                    "name": "Management",
                    "description": "Providing appropriate management recommendations",
                    "editable": False,
                    "total_points": 0, 
                    "subcategories": []
                }
            ]
        }


def main():
    print(upload_file("Station 1B - Skin Concern - Tinea.docx"))


if __name__ == "__main__":
    main()
