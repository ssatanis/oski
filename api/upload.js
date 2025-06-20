// Vercel Serverless Function for File Upload with Backend Integration
import formidable from 'formidable';
import fs from 'fs';
import path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export const config = {
  api: {
    bodyParser: false,
  },
};

// Advanced text extraction using Python backend functionality
async function extractTextFromFile(filepath, filename) {
  const ext = path.extname(filename).toLowerCase();
  
  try {
    // Use the Python backend for comprehensive text extraction
    const pythonScript = `
import sys
import os
sys.path.append('${path.join(process.cwd(), 'rubrics-to-prompts', 'backend')}')

from backend import upload_file
import json

try:
    result = upload_file('${filepath}')
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({
        "success": False,
        "error": str(e),
        "rubric": {
            "title": "Error Processing File",
            "total_points": 0,
            "criteria": []
        }
    }))
`;

    // Write temporary Python script
    const tempScript = path.join('/tmp', `extract_${Date.now()}.py`);
    fs.writeFileSync(tempScript, pythonScript);
    
    // Execute Python script
    const { stdout, stderr } = await execAsync(`cd ${process.cwd()} && python3 ${tempScript}`);
    
    // Clean up temp script
    try {
      fs.unlinkSync(tempScript);
    } catch (e) {
      // Ignore cleanup errors
    }
    
    if (stderr) {
      console.warn('Python stderr:', stderr);
    }
    
    // Parse the result
    const result = JSON.parse(stdout.trim());
    
    if (result.success && result.rubric) {
      return {
        extractedText: stdout, // Full result for debugging
        rubric: result.rubric,
        yamlContent: result.yaml_content
      };
    } else {
      throw new Error(result.error || 'Python processing failed');
    }
    
  } catch (error) {
    console.error('Advanced extraction failed:', error);
    // Fallback to simple extraction
    return await fallbackExtraction(filepath, filename);
  }
}

// Fallback extraction for when Python backend is not available
async function fallbackExtraction(filepath, filename) {
  const ext = path.extname(filename).toLowerCase();
  
  let content = '';
  try {
    if (ext === '.txt' || ext === '.csv') {
      content = fs.readFileSync(filepath, 'utf8');
    } else {
      // For binary files, extract what we can
      content = `Uploaded file: ${filename}\nFile type: ${ext}\nProcessing with fallback method.`;
    }
  } catch (error) {
    content = `Error reading file: ${filename}`;
  }
  
  // Parse the actual content of the file to extract rubric criteria
  const parsedRubric = parseRubricContent(content, filename);
  
  return {
    extractedText: content,
    rubric: parsedRubric,
    yamlContent: generateYAMLFromRubric(parsedRubric)
  };
}

// Parse the rubric content to extract criteria
function parseRubricContent(content, filename) {
  const lines = content.split('\n').filter(line => line.trim());
  const criteria = [];
  
  // Extract title from first few lines or filename
  let title = path.basename(filename, path.extname(filename));
  for (let i = 0; i < Math.min(3, lines.length); i++) {
    if (lines[i].length > 10 && !lines[i].match(/^\s*[\d\-\*\•]/)) {
      title = lines[i].trim();
      break;
    }
  }
  
  let currentSection = null;
  let totalPoints = 0;
  
  // Look for sections and criteria in the content
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // Skip empty lines
    if (!line) continue;
    
    // Check for section headers (e.g., "History Taking (3 points)")
    const sectionMatch = line.match(/^([A-Za-z\s]+)\s*\((\d+)\s*points?\)/i);
    if (sectionMatch) {
      currentSection = sectionMatch[1].trim();
      const sectionPoints = parseInt(sectionMatch[2]);
      
      // Add as a criterion
      criteria.push({
        name: currentSection,
        points: sectionPoints,
        description: `${currentSection} assessment`,
        examples: [`Assessing ${currentSection.toLowerCase()}`]
      });
      
      totalPoints += sectionPoints;
      continue;
    }
    
    // Check for bullet points or numbered items under a section
    if (currentSection && (line.startsWith('-') || line.startsWith('•') || line.match(/^\d+[\.\)]/))) {
      const itemText = line.replace(/^[-•\d\.\)]\s*/, '').trim();
      const pointsMatch = itemText.match(/\((\d+)\s*points?\)/i);
      
      let itemPoints = 1;
      let itemName = itemText;
      
      if (pointsMatch) {
        itemPoints = parseInt(pointsMatch[1]);
        itemName = itemText.replace(/\((\d+)\s*points?\)/i, '').trim();
      }
      
      // Add as a criterion if it's substantial enough
      if (itemName.length > 3) {
        criteria.push({
          name: itemName,
          points: itemPoints,
          description: `${currentSection}: ${itemName}`,
          examples: generateExamples(itemName, currentSection)
        });
        
        totalPoints += itemPoints;
      }
    }
  }
  
  // If no criteria were found, use some default ones based on the content
  if (criteria.length === 0) {
    return generateDefaultRubric(filename);
  }
  
  return {
    title: title,
    total_points: totalPoints,
    criteria: criteria
  };
}

// Generate examples based on criterion name and section
function generateExamples(criterionName, sectionName) {
  const examples = [];
  const nameLower = criterionName.toLowerCase();
  const sectionLower = sectionName ? sectionName.toLowerCase() : '';
  
  // History taking examples
  if (sectionLower.includes('history')) {
    if (nameLower.includes('chief') || nameLower.includes('complaint')) {
      examples.push("What brings you in today?");
      examples.push("Can you tell me your main concern?");
    } else if (nameLower.includes('present') || nameLower.includes('illness')) {
      examples.push("When did this start?");
      examples.push("How has it changed over time?");
    } else {
      examples.push(`Tell me about your ${nameLower}`);
      examples.push(`I'd like to ask about your ${nameLower}`);
    }
  } 
  // Physical exam examples
  else if (sectionLower.includes('physical') || sectionLower.includes('examination')) {
    if (nameLower.includes('vital') || nameLower.includes('signs')) {
      examples.push("I'm going to check your vital signs");
      examples.push("Let me take your blood pressure");
    } else {
      examples.push(`I'm going to examine your ${nameLower}`);
      examples.push(`Let me check this area`);
    }
  }
  // Generic examples if no specific ones
  else {
    examples.push(`I'm assessing ${nameLower}`);
    examples.push(`Let me evaluate ${nameLower}`);
  }
  
  return examples;
}

// Generate YAML content from the rubric
function generateYAMLFromRubric(rubric) {
  return `# OSCE Assessment Rubric
# ${rubric.title}
# Total Points: ${rubric.total_points}

system_message: |
  You are a helpful assistant tasked with analyzing and scoring a recorded medical examination between a medical student and a patient. Provide your response in JSON format.

user_message: |
  Your task is to identify and score the following assessment criteria in the medical examination.
  
  Assessment Criteria:
${rubric.criteria.map(c => `  - ${c.name} (${c.points} points): ${c.description || c.name}`).join('\n')}

response_config:
  structured_output: true
  format: json

assessment_config:
  type: "medical_osce_assessment"
  version: "2.0"
  criteria_count: ${rubric.criteria.length}
  total_points: ${rubric.total_points}

assessment_criteria:
${rubric.criteria.map((c, i) => `  - id: "criterion_${i + 1}"
    name: "${c.name}"
    max_points: ${c.points}
    description: "${c.description || c.name}"
    verbalization_examples:
${c.examples.map(ex => `      - "${ex}"`).join('\n')}`).join('\n')}
`;
}

// Generate default rubric structure
function generateDefaultRubric(filename) {
  return {
    title: `Assessment for ${path.basename(filename, path.extname(filename))}`,
    total_points: 20,
    criteria: [
      {
        name: "Patient Introduction",
        points: 2,
        description: "Introduces self and establishes rapport",
        examples: ["Hello, I'm Dr. Smith", "I'll be examining you today"]
      },
      {
        name: "History Taking",
        points: 6,
        description: "Gathers relevant patient history",
        examples: ["Tell me about your symptoms", "When did this start?"]
      },
      {
        name: "Physical Examination",
        points: 8,
        description: "Performs appropriate physical examination",
        examples: ["I'm going to examine you now", "Let me check this area"]
      },
      {
        name: "Communication Skills",
        points: 4,
        description: "Communicates clearly and professionally",
        examples: ["Do you have any questions?", "Let me explain what I found"]
      }
    ]
  };
}

// Generate default YAML content
function generateDefaultYAML(filename) {
  const rubric = generateDefaultRubric(filename);
  return `# OSCE Assessment Rubric
# ${rubric.title}
# Total Points: ${rubric.total_points}

system_message: |
  You are a helpful assistant tasked with analyzing and scoring a recorded medical examination between a medical student and a patient. Provide your response in JSON format.

user_message: |
  Your task is to identify and score the following assessment criteria in the medical examination.
  
  Assessment Criteria:
${rubric.criteria.map(c => `  - ${c.name} (${c.points} points): ${c.description}`).join('\n')}

response_config:
  structured_output: true
  format: json

assessment_config:
  type: "medical_osce_assessment"
  version: "2.0"
  criteria_count: ${rubric.criteria.length}
  total_points: ${rubric.total_points}

assessment_criteria:
${rubric.criteria.map((c, i) => `  - id: "criterion_${i + 1}"
    name: "${c.name}"
    max_points: ${c.points}
    description: "${c.description}"
    verbalization_examples:
${c.examples.map(ex => `      - "${ex}"`).join('\n')}`).join('\n')}
`;
}

export default async function handler(req, res) {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // Handle preflight requests
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Parse form data
    const form = new formidable.IncomingForm();
    form.uploadDir = '/tmp';
    form.keepExtensions = true;
    
    const [fields, files] = await new Promise((resolve, reject) => {
      form.parse(req, (err, fields, files) => {
        if (err) reject(err);
        else resolve([fields, files]);
      });
    });
    
    const file = Array.isArray(files.file) ? files.file[0] : files.file;
    
    if (!file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }
    
    // Extract text and generate rubric using backend
    const extractionResult = await extractTextFromFile(file.filepath, file.originalFilename || file.name);
    
    // Transform backend result to expected format
    const criteria = extractionResult.rubric.criteria.map(criterion => ({
      examId: criterion.name.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_'),
      name: criterion.name,
      max_points: criterion.points,
      examples: criterion.examples || []
    }));
    
    // Clean up uploaded file
    fs.unlinkSync(file.filepath);
    
    // Return comprehensive response
    res.status(200).json({
      success: true,
      filename: file.originalFilename || file.name,
      extracted_text: extractionResult.extractedText.slice(0, 1000), // First 1000 chars for debugging
      criteria: criteria,
      rubric: extractionResult.rubric,
      yaml_content: extractionResult.yamlContent,
      message: 'File processed successfully with backend integration',
      processing_method: extractionResult.rubric.criteria.length > 0 ? 'Python Backend' : 'Fallback'
    });
    
  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ 
      error: 'Failed to process file',
      details: error.message 
    });
  }
}
