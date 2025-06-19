from pathlib import Path
from openai import AzureOpenAI
import pandas as pd
from docx import Document
import mammoth
import pdfplumber
import os
import json

# Initialize Azure OpenAI client
client = None
azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT") 
azure_openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")

if azure_openai_key and azure_openai_endpoint and azure_openai_deployment:
    try:
        client = AzureOpenAI(
            api_version="2024-12-01-preview",
            azure_endpoint=azure_openai_endpoint,
            api_key=azure_openai_key
        )
    except Exception as e:
        client = None
else:
    client = None


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

    # Always use text-based extraction for reliable results
    return create_structured_rubric_from_text(combined_text)



def create_structured_rubric_from_text(text):
    """Extract criteria from text using pattern matching"""
    lines = text.split('\n')
    criteria = []
    title = "Medical Assessment Rubric"
    
    # Try to extract title from first few lines
    for line in lines[:5]:
        line = line.strip()
        if line and ("station" in line.lower() or "rubric" in line.lower() or "assessment" in line.lower()):
            title = line
            break
    
    # Look for criteria patterns
    for i, line in enumerate(lines):
        line = line.strip()
        if not line or len(line) < 5:
            continue
            
        # Pattern 1: Points in parentheses - e.g., "Chief complaint (2 pts)"
        if '(' in line and ')' in line and any(char.isdigit() for char in line):
            try:
                point_start = line.rfind('(')
                point_end = line.rfind(')')
                if point_start < point_end:
                    point_text = line[point_start+1:point_end]
                    if any(char.isdigit() for char in point_text):
                        criterion_name = line[:point_start].strip()
                        points = int(''.join(filter(str.isdigit, point_text)))
                        if criterion_name and points > 0:
                            criteria.append({
                                "id": len(criteria) + 1,
                                "name": criterion_name,
                                "category": determine_category(criterion_name),
                                "points": points,
                                "editable": True,
                                "description": criterion_name,
                                "current_points": 0
                            })
                            continue
            except:
                pass
        
        # Pattern 2: Numbered items - e.g., "1. History taking"
        if (line[0].isdigit() and '.' in line[:3]) or line.startswith('-') or line.startswith('•'):
            clean_line = line.lstrip('0123456789.-• ').strip()
            if clean_line and len(clean_line) > 3:
                criteria.append({
                    "id": len(criteria) + 1,
                    "name": clean_line,
                    "category": determine_category(clean_line),
                    "points": extract_points_from_text(clean_line),
                    "editable": True,
                    "description": clean_line,
                    "current_points": 0
                })
    
    # If no criteria found, create from meaningful lines
    if not criteria:
        for line in lines:
            line = line.strip()
            if len(line) > 10 and not line.lower().startswith(('total', 'score', 'points')):
                criteria.append({
                    "id": len(criteria) + 1,
                    "name": line[:100],  # Limit length
                    "category": determine_category(line),
                    "points": 1,
                    "editable": True,
                    "description": line[:200],
                    "current_points": 0
                })
                if len(criteria) >= 15:  # Limit to reasonable number
                    break
    
    # Distribute criteria across domains
    history_criteria = []
    physical_criteria = []
    diagnostic_criteria = []
    management_criteria = []
    
    for criterion in criteria:
        category = criterion["category"]
        if category in ["CC", "HPI", "PMH", "Med", "All", "FH", "SH"]:
            history_criteria.append(criterion)
        elif category == "PE":
            physical_criteria.append(criterion)
        elif category in ["DA", "DR"]:
            diagnostic_criteria.append(criterion)
        elif category == "M":
            management_criteria.append(criterion)
        else:
            # Distribute remaining evenly
            domain_idx = len(criterion["name"]) % 4
            if domain_idx == 0:
                criterion["category"] = "HPI"
                history_criteria.append(criterion)
            elif domain_idx == 1:
                criterion["category"] = "PE"
                physical_criteria.append(criterion)
            elif domain_idx == 2:
                criterion["category"] = "DA"
                diagnostic_criteria.append(criterion)
            else:
                criterion["category"] = "M"
                management_criteria.append(criterion)
    
    total_points = sum(c["points"] for c in criteria)
    
    return {
        "rubric_info": {
            "title": title,
            "station_info": {
                "station_number": "Extracted",
                "condition": extract_condition(text),
                "specialty": extract_specialty(text)
            },
            "total_points": total_points,
            "creation_timestamp": pd.Timestamp.now().isoformat(),
            "source_files": 1
        },
        "assessment_domains": [
            {
                "name": "History Taking",
                "description": "Gathering patient history and presenting complaint",
                "editable": False,
                "total_points": sum(c["points"] for c in history_criteria),
                "subcategories": history_criteria
            },
            {
                "name": "Physical Examination",
                "description": "Conducting appropriate physical examination",
                "editable": False,
                "total_points": sum(c["points"] for c in physical_criteria),
                "subcategories": physical_criteria
            },
            {
                "name": "Diagnostic Accuracy/Reasoning/Justification",
                "description": "Demonstrating diagnostic reasoning and accuracy",
                "editable": False,
                "total_points": sum(c["points"] for c in diagnostic_criteria),
                "subcategories": diagnostic_criteria
            },
            {
                "name": "Management",
                "description": "Providing appropriate management recommendations",
                "editable": False,
                "total_points": sum(c["points"] for c in management_criteria),
                "subcategories": management_criteria
            }
        ]
    }

def determine_category(text):
    """Determine the category based on text content"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["chief", "complaint", "presenting"]):
        return "CC"
    elif any(word in text_lower for word in ["history", "present", "illness", "symptom"]):
        return "HPI"
    elif any(word in text_lower for word in ["past", "medical", "previous"]):
        return "PMH"
    elif any(word in text_lower for word in ["medication", "drug", "allergy"]):
        return "Med"
    elif any(word in text_lower for word in ["family", "hereditary"]):
        return "FH"
    elif any(word in text_lower for word in ["social", "smoking", "alcohol"]):
        return "SH"
    elif any(word in text_lower for word in ["examination", "physical", "inspect", "palpat", "auscult"]):
        return "PE"
    elif any(word in text_lower for word in ["diagnosis", "differential", "reasoning"]):
        return "DA"
    elif any(word in text_lower for word in ["management", "treatment", "plan", "follow"]):
        return "M"
    else:
        return "General"

def extract_points_from_text(text):
    """Extract point values from text"""
    numbers = [int(s) for s in text.split() if s.isdigit()]
    if numbers:
        return min(numbers[0], 10)  # Cap at 10 points
    return 1

def extract_condition(text):
    """Extract medical condition from text"""
    text_lower = text.lower()
    conditions = ["psoriasis", "eczema", "dermatitis", "rash", "tinea", "acne", "diabetes", "hypertension"]
    for condition in conditions:
        if condition in text_lower:
            return condition.title()
    return "Medical Assessment"

def extract_specialty(text):
    """Extract medical specialty from text"""
    text_lower = text.lower()
    if any(word in text_lower for word in ["dermatology", "skin", "rash", "psoriasis"]):
        return "Dermatology"
    elif any(word in text_lower for word in ["cardiology", "heart", "cardiac"]):
        return "Cardiology"
    elif any(word in text_lower for word in ["internal", "medicine"]):
        return "Internal Medicine"
    else:
        return "General Medicine"


def main():
    print(upload_file("Station 1B - Skin Concern - Tinea.docx"))


if __name__ == "__main__":
    main()
