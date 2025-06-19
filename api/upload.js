import Tesseract from 'tesseract.js';
import mammoth from 'mammoth';
import pdfParse from 'pdf-parse';
import XLSX from 'xlsx';
import sharp from 'sharp';

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
    const { fileContent, fileName } = req.body;
    
    if (!fileContent || !fileName) {
      return res.status(400).json({ 
        error: 'Missing fileContent or fileName in request body' 
      });
    }

    console.log(`Processing file: ${fileName} (${fileContent.length} chars base64)`);
    
    // Enhanced text extraction based on file type
    const fileExtension = fileName.split('.').pop().toLowerCase();
    let extractedText = '';

    if (fileExtension === 'txt') {
      // For text files, decode the base64 content
      extractedText = Buffer.from(fileContent, 'base64').toString('utf-8');
    } else {
      // Real OCR processing for all file types
      extractedText = await processFileWithOCR(fileContent, fileName, fileExtension);
    }

    if (!extractedText.trim()) {
      return res.status(400).json({ 
        error: 'No text could be extracted from the file' 
      });
    }

    console.log(`Extracted ${extractedText.length} characters from ${fileName}`);

    res.status(200).json({
      message: 'File processed successfully',
      filename: fileName,
      extracted_text: extractedText,
      text_length: extractedText.length,
      file_type: fileExtension
    });

  } catch (error) {
    console.error('Upload processing failed:', error);
    res.status(500).json({ 
      error: `Failed to process file: ${error.message}` 
    });
  }
}

async function processFileWithOCR(fileContent, fileName, fileExtension) {
  console.log(`Processing file with OCR: ${fileName} (${fileExtension})`);
  
  const buffer = Buffer.from(fileContent, 'base64');
  let extractedText = '';
  
  try {
    if (fileExtension === 'xlsx' || fileExtension === 'xls' || fileExtension === 'csv') {
      // Process Excel/CSV files
      extractedText = await processExcelFile(buffer, fileExtension);
    } else if (fileExtension === 'pdf') {
      // Process PDF files
      extractedText = await processPDFFile(buffer);
    } else if (['jpg', 'jpeg', 'png', 'bmp', 'tiff'].includes(fileExtension)) {
      // Process image files with OCR
      extractedText = await processImageWithOCR(buffer);
    } else if (['doc', 'docx'].includes(fileExtension)) {
      // Process Word documents
      extractedText = await processWordDocument(buffer);
    } else {
      throw new Error(`Unsupported file type: ${fileExtension}`);
    }
    
    if (!extractedText.trim()) {
      throw new Error('No text could be extracted from the file');
    }
    
    return extractedText;
    
  } catch (error) {
    console.error(`OCR processing failed for ${fileName}:`, error);
    throw new Error(`Failed to process ${fileExtension.toUpperCase()} file: ${error.message}`);
  }
}

async function processExcelFile(buffer, fileExtension) {
  const workbook = XLSX.read(buffer, { type: 'buffer' });
  let allText = '';
  
  workbook.SheetNames.forEach(sheetName => {
    const worksheet = workbook.Sheets[sheetName];
    const csvData = XLSX.utils.sheet_to_csv(worksheet);
    allText += `\n=== SHEET: ${sheetName} ===\n${csvData}\n`;
  });
  
  return allText;
}

async function processPDFFile(buffer) {
  const data = await pdfParse(buffer);
  return data.text;
}

async function processImageWithOCR(buffer) {
  // Convert image to a format Tesseract can handle
  const processedImage = await sharp(buffer)
    .greyscale()
    .normalize()
    .png()
    .toBuffer();
  
  const { data: { text } } = await Tesseract.recognize(processedImage, 'eng', {
    logger: m => console.log(m)
  });
  
  return text;
}

async function processWordDocument(buffer) {
  const result = await mammoth.extractRawText({ buffer });
  return result.value;
} 