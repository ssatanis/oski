// Vercel Serverless Function for File Upload
import formidable from 'formidable';
import fs from 'fs';
import path from 'path';

export const config = {
  api: {
    bodyParser: false,
  },
};

// Simple text extraction based on file type
function extractTextFromFile(filepath, filename) {
  const ext = path.extname(filename).toLowerCase();
  
  // For demo purposes, return simulated extraction
  const content = fs.readFileSync(filepath, 'utf8').slice(0, 1000); // First 1000 chars
  
  // Simulate different content based on file extension
  const templates = {
    '.pdf': 'OSCE Assessment Rubric\n\nStation: Clinical Examination\n\n1. Patient Introduction (2 points)\n2. History Taking (5 points)\n3. Physical Examination (7 points)\n4. Communication Skills (3 points)\n5. Professionalism (3 points)',
    '.docx': 'Medical Student Assessment\n\nCriteria:\n- Introduces self appropriately\n- Takes comprehensive history\n- Performs systematic examination\n- Communicates findings clearly\n- Maintains professional demeanor',
    '.xlsx': 'Criterion,Points\nPatient Greeting,2\nChief Complaint,3\nHistory of Present Illness,5\nPhysical Exam,7\nPatient Education,3',
    '.txt': content
  };
  
  return templates[ext] || content;
}

// Generate criteria from extracted text
function generateCriteriaFromText(text, filename) {
  // Simple parsing logic - in production, use AI
  const criteria = [];
  
  // Check for common medical assessment keywords
  const keywords = {
    'introduction': { name: 'Patient Introduction', points: 2 },
    'greeting': { name: 'Patient Greeting', points: 2 },
    'history': { name: 'History Taking', points: 5 },
    'examination': { name: 'Physical Examination', points: 7 },
    'physical exam': { name: 'Physical Examination', points: 7 },
    'communication': { name: 'Communication Skills', points: 3 },
    'professionalism': { name: 'Professional Behavior', points: 3 },
    'diagnosis': { name: 'Clinical Reasoning', points: 4 },
    'education': { name: 'Patient Education', points: 3 }
  };
  
  const lowerText = text.toLowerCase();
  const foundCriteria = new Set();
  
  for (const [keyword, criterion] of Object.entries(keywords)) {
    if (lowerText.includes(keyword) && !foundCriteria.has(criterion.name)) {
      criteria.push({
        name: criterion.name,
        points: criterion.points,
        examples: [`I will now perform ${criterion.name.toLowerCase()}`, `Let me assess your ${keyword}`]
      });
      foundCriteria.add(criterion.name);
    }
  }
  
  // If no criteria found, add defaults
  if (criteria.length === 0) {
    criteria.push(
      { name: 'History Taking', points: 5, examples: ['Tell me about your symptoms', 'When did this start?'] },
      { name: 'Physical Examination', points: 7, examples: ['I will examine you now', 'Let me check this area'] },
      { name: 'Communication', points: 3, examples: ['Do you have any questions?', 'Let me explain'] }
    );
  }
  
  return criteria;
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
    
    // Extract text from file
    const extractedText = extractTextFromFile(file.filepath, file.originalFilename || file.name);
    
    // Generate criteria
    const criteria = generateCriteriaFromText(extractedText, file.originalFilename || file.name);
    
    // Clean up uploaded file
    fs.unlinkSync(file.filepath);
    
    // Return response
    res.status(200).json({
      success: true,
      filename: file.originalFilename || file.name,
      extracted_text: extractedText.slice(0, 500) + '...', // First 500 chars
      criteria: criteria,
      message: 'File processed successfully'
    });
    
  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ 
      error: 'Failed to process file',
      details: error.message 
    });
  }
}