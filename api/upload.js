import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { writeFileSync, unlinkSync, readFileSync } from 'fs';
import { tmpdir } from 'os';

// Set up for ES modules
const require = createRequire(import.meta.url);
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export const config = {
  api: {
    bodyParser: {
      sizeLimit: '10mb',
    },
  },
};

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
    // For Vercel, we'll create a simplified text extraction
    // This is a demo implementation - in production you'd use proper libraries
    
    const { fileContent, fileName } = req.body;
    
    if (!fileContent || !fileName) {
      return res.status(400).json({ 
        error: 'Missing fileContent or fileName in request body' 
      });
    }

    // Simple text extraction based on file type
    const fileExtension = fileName.split('.').pop().toLowerCase();
    let extractedText = '';

    if (fileExtension === 'txt') {
      // For text files, just decode the base64 content
      extractedText = Buffer.from(fileContent, 'base64').toString('utf-8');
    } else {
      // For other file types, return a demo response
      extractedText = `Demo rubric content extracted from ${fileName}:

OSCE Station Assessment Rubric

Criteria 1: Patient Greeting and Introduction (0-2 points)
- 0 points: No greeting or introduction
- 1 point: Basic greeting only
- 2 points: Professional greeting with name and role introduction

Criteria 2: History Taking (0-3 points)
- 0 points: No relevant history obtained
- 1 point: Limited history with major gaps
- 2 points: Adequate history with minor gaps
- 3 points: Comprehensive and systematic history

Criteria 3: Physical Examination (0-3 points)
- 0 points: No examination performed
- 1 point: Limited examination
- 2 points: Adequate examination technique
- 3 points: Thorough and systematic examination

Criteria 4: Communication Skills (0-2 points)
- 0 points: Poor communication
- 1 point: Basic communication
- 2 points: Excellent communication and empathy

Total Points: 10`;
    }

    if (!extractedText.trim()) {
      return res.status(400).json({ 
        error: 'No text could be extracted from the file' 
      });
    }

    res.status(200).json({
      message: 'File processed successfully',
      filename: fileName,
      extracted_text: extractedText,
      text_length: extractedText.length
    });

  } catch (error) {
    console.error('Upload processing failed:', error);
    res.status(500).json({ 
      error: `Failed to process file: ${error.message}` 
    });
  }
} 