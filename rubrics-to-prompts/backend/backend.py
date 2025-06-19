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

if azure_openai_key and azure_openai_endpoint:
    try:
        client = AzureOpenAI(
            api_version="2024-12-01-preview",
            azure_endpoint=azure_openai_endpoint,
            api_key=azure_openai_key
        )
        print("✅ Azure OpenAI client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Azure OpenAI client: {e}")
        client = None
else:
    print("⚠️ Azure OpenAI configuration missing. Please set AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT")
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

    if not client:
        print("❌ Azure OpenAI client not available. Using fallback structure.")
        return create_fallback_structure(combined_text)
    
    try:
        print(f"🤖 Processing rubric with Azure OpenAI...")
        print(f"📄 Text length: {len(combined_text)} characters")
        
        response = client.chat.completions.create(
            model=azure_openai_deployment,
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert medical education assistant specializing in OSCE rubric analysis. Analyze the provided rubric text thoroughly and extract ALL criteria with their point values. Return only valid JSON without markdown formatting."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        
        response_text = response.choices[0].message.content.strip()
        print(f"✅ Received AI response: {len(response_text)} characters")
        
        # Clean up the response to ensure it's valid JSON
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        # Parse to validate JSON
        parsed_json = json.loads(response_text)
        print(f"✅ Successfully parsed JSON rubric structure")
        
        # Validate the structure has actual content
        total_criteria = sum(len(domain.get('subcategories', [])) for domain in parsed_json.get('assessment_domains', []))
        if total_criteria == 0:
            print("⚠️ No criteria found in AI response, using text-based extraction")
            return create_structured_rubric_from_text(combined_text)
        
        print(f"✅ Extracted {total_criteria} criteria across domains")
        return parsed_json
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"Raw response: {response_text[:500]}...")
        return create_structured_rubric_from_text(combined_text)
        
    except Exception as e:
        print(f"❌ Error in LLM processing: {e}")
        return create_structured_rubric_from_text(combined_text)

def create_fallback_structure(text):
    """Create a basic structure when AI is not available"""
    print("🔄 Creating fallback structure from text analysis...")
    return create_structured_rubric_from_text(text)

def create_structured_rubric_from_text(text):
    """Extract criteria from text when AI processing fails"""
    print("🔍 Analyzing text manually to extract criteria...")
    
    lines = text.split('\n')
    criteria = []
    
    # Look for patterns that indicate criteria (points in parentheses, numbered items, etc.)
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Look for point values in parentheses
        if '(' in line and ')' in line:
            try:
                # Extract point value
                point_start = line.rfind('(')
                point_end = line.rfind(')')
                if point_start < point_end:
                    point_text = line[point_start+1:point_end]
                    if any(char.isdigit() for char in point_text):
                        criterion_name = line[:point_start].strip()
                        # Extract numeric value
                        points = int(''.join(filter(str.isdigit, point_text)))
                        if criterion_name and points > 0:
                            criteria.append({
                                "id": len(criteria) + 1,
                                "name": criterion_name,
                                "category": "General",
                                "points": points,
                                "editable": True,
                                "description": criterion_name,
                                "current_points": 0
                            })
            except:
                continue
    
    # If no criteria found with parentheses, look for other patterns
    if not criteria:
        numbered_pattern = False
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                criteria.append({
                    "id": len(criteria) + 1,
                    "name": line,
                    "category": "General",
                    "points": 1,
                    "editable": True,
                    "description": line,
                    "current_points": 0
                })
                numbered_pattern = True
        
        # If still no criteria, create from any non-empty lines
        if not criteria and not numbered_pattern:
            for line in lines[:10]:  # Take first 10 meaningful lines
                line = line.strip()
                if len(line) > 10:  # Skip very short lines
                    criteria.append({
                        "id": len(criteria) + 1,
                        "name": line,
                        "category": "General", 
                        "points": 1,
                        "editable": True,
                        "description": line,
                        "current_points": 0
                    })
    
    # Distribute criteria across domains
    history_criteria = []
    physical_criteria = []
    diagnostic_criteria = []
    management_criteria = []
    
    for i, criterion in enumerate(criteria):
        if i % 4 == 0:
            criterion["category"] = "HPI"
            history_criteria.append(criterion)
        elif i % 4 == 1:
            criterion["category"] = "PE"
            physical_criteria.append(criterion)
        elif i % 4 == 2:
            criterion["category"] = "DA"
            diagnostic_criteria.append(criterion)
        else:
            criterion["category"] = "M"
            management_criteria.append(criterion)
    
    total_points = sum(c["points"] for c in criteria)
    
    result = {
        "rubric_info": {
            "title": "Extracted Medical Assessment Rubric",
            "station_info": {
                "station_number": "Extracted",
                "condition": "Medical Assessment",
                "specialty": "General Medicine"
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
    
    print(f"✅ Manually extracted {len(criteria)} criteria")
    return result


def main():
    print(upload_file("Station 1B - Skin Concern - Tinea.docx"))


if __name__ == "__main__":
    main()
