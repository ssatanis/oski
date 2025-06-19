import formidable from 'formidable';
import { Buffer } from 'buffer';
import vision from '@google-cloud/vision';
import pdfParse from 'pdf-parse';
import mammoth from 'mammoth';
import XLSX from 'xlsx';
import { parse } from 'csv-parse/sync';
import sharp from 'sharp';

export const config = {
  api: {
    bodyParser: false,
    maxDuration: 60,
  },
};

// Initialize Google Vision client
const visionClient = new vision.ImageAnnotatorClient({
  apiKey: process.env.GOOGLE_VISION_API_KEY
});

// Convert Excel to image for visual analysis
async function excelToImage(buffer) {
  try {
    const workbook = XLSX.read(buffer, { type: 'buffer' });
    const worksheet = workbook.Sheets[workbook.SheetNames[0]];
    
    // Convert to HTML first
    const html = XLSX.utils.sheet_to_html(worksheet, {
      header: '<html><body style="font-family: Arial; font-size: 14px;">',
      footer: '</body></html>'
    });
    
    // Use puppeteer-core or playwright to render HTML to image
    // For now, we'll extract structured data
    return { html, worksheet };
  } catch (error) {
    console.error('Excel to image conversion error:', error);
    throw error;
  }
}

// Use Google Vision to understand document structure
async function analyzeDocumentWithVision(buffer, fileType) {
  try {
    let imageBuffer = buffer;
    
    // Convert non-image files to images for Vision API
    if (['xlsx', 'xls', 'docx', 'pdf'].includes(fileType)) {
      // For Excel/Word/PDF, we need to convert to image
      // This is a simplified version - in production, use puppeteer or similar
      console.log('Converting document to image for Vision analysis...');
      
      if (fileType === 'pdf') {
        // For PDFs, extract first page as image
        const { pdf2pic } = await import('pdf2pic');
        const converter = pdf2pic({
          density: 300,
          savename: 'temp',
          savedir: '/tmp',
          format: 'png'
        });
        const result = await converter.convert(buffer, 1);
        imageBuffer = result.buffer;
      }
    }
    
    // Use Google Vision for document understanding
    const [result] = await visionClient.documentTextDetection({
      image: { content: imageBuffer.toString('base64') }
    });
    
    const fullTextAnnotation = result.fullTextAnnotation;
    
    if (!fullTextAnnotation) {
      throw new Error('No text detected in document');
    }
    
    // Extract structured information
    const structuredData = {
      rawText: fullTextAnnotation.text,
      pages: fullTextAnnotation.pages,
      blocks: [],
      tables: []
    };
    
    // Analyze document structure
    fullTextAnnotation.pages.forEach(page => {
      page.blocks.forEach(block => {
        const blockText = block.paragraphs
          .map(p => p.words.map(w => w.symbols.map(s => s.text).join('')).join(' '))
          .join('\n');
        
        structuredData.blocks.push({
          text: blockText,
          confidence: block.confidence,
          bounds: block.boundingBox
        });
      });
    });
    
    return structuredData;
  } catch (error) {
    console.error('Vision API error:', error);
    throw error;
  }
}

// Enhanced text extraction that preserves structure
async function extractStructuredText(buffer, fileName) {
  const extension = fileName.split('.').pop().toLowerCase();
  
  try {
    let structuredContent = {
      rawText: '',
      structure: {},
      tables: [],
      metadata: { fileName, fileType: extension }
    };
    
    switch (extension) {
      case 'xlsx':
      case 'xls':
        const workbook = XLSX.read(buffer, { type: 'buffer', cellStyles: true });
        structuredContent.structure.sheets = {};
        
        workbook.SheetNames.forEach(sheetName => {
          const sheet = workbook.Sheets[sheetName];
          
          // Get range
          const range = XLSX.utils.decode_range(sheet['!ref']);
          const sheetData = {
            name: sheetName,
            rows: [],
            mergedCells: sheet['!merges'] || []
          };
          
          // Extract cell by cell to preserve structure
          for (let row = range.s.r; row <= range.e.r; row++) {
            const rowData = [];
            for (let col = range.s.c; col <= range.e.c; col++) {
              const cellAddress = XLSX.utils.encode_cell({ r: row, c: col });
              const cell = sheet[cellAddress];
              
              rowData.push({
                value: cell ? cell.v : '',
                formula: cell ? cell.f : undefined,
                type: cell ? cell.t : undefined,
                style: cell ? cell.s : undefined,
                address: cellAddress
              });
            }
            sheetData.rows.push(rowData);
          }
          
          structuredContent.structure.sheets[sheetName] = sheetData;
          
          // Also create a text representation
          const textRepresentation = XLSX.utils.sheet_to_txt(sheet, { FS: '\t', RS: '\n' });
          structuredContent.rawText += `\n=== Sheet: ${sheetName} ===\n${textRepresentation}\n`;
        });
        
        // Use Vision API for visual understanding if available
        if (process.env.GOOGLE_VISION_API_KEY) {
          try {
            const visionAnalysis = await analyzeDocumentWithVision(buffer, extension);
            structuredContent.visionAnalysis = visionAnalysis;
          } catch (visionError) {
            console.log('Vision API analysis failed, continuing with structured extraction:', visionError.message);
          }
        }
        
        break;
        
      case 'pdf':
        const pdfData = await pdfParse(buffer);
        structuredContent.rawText = pdfData.text;
        structuredContent.structure.pages = pdfData.numpages;
        structuredContent.structure.info = pdfData.info;
        
        // If PDF has minimal text, use Vision API
        if (pdfData.text.trim().length < 100 && process.env.GOOGLE_VISION_API_KEY) {
          const visionAnalysis = await analyzeDocumentWithVision(buffer, extension);
          structuredContent.visionAnalysis = visionAnalysis;
          structuredContent.rawText = visionAnalysis.rawText;
        }
        break;
        
      case 'docx':
        const docResult = await mammoth.extractRawText({ buffer });
        structuredContent.rawText = docResult.value;
        
        // Also extract with formatting
        const htmlResult = await mammoth.convertToHtml({ buffer });
        structuredContent.structure.html = htmlResult.value;
        break;
        
      case 'csv':
        const csvText = buffer.toString('utf-8');
        const records = parse(csvText, {
          columns: true,
          skip_empty_lines: true,
          relaxed_quotes: true,
          delimiter: [',', '\t', '|', ';']
        });
        
        structuredContent.structure.headers = Object.keys(records[0] || {});
        structuredContent.structure.rows = records;
        structuredContent.rawText = csvText;
        break;
        
      case 'txt':
        structuredContent.rawText = buffer.toString('utf-8');
        break;
        
      case 'png':
      case 'jpg':
      case 'jpeg':
      case 'gif':
        // Use Vision API for images
        if (process.env.GOOGLE_VISION_API_KEY) {
          const visionAnalysis = await analyzeDocumentWithVision(buffer, extension);
          structuredContent = {
            ...structuredContent,
            ...visionAnalysis
          };
        } else {
          // Fallback to Tesseract
          const Tesseract = await import('tesseract.js');
          const result = await Tesseract.recognize(buffer, 'eng');
          structuredContent.rawText = result.data.text;
        }
        break;
        
      default:
        throw new Error(`Unsupported file type: ${extension}`);
    }
    
    return structuredContent;
  } catch (error) {
    console.error(`Error extracting structured text from ${fileName}:`, error);
    throw error;
  }
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const form = formidable();
    const [fields, files] = await form.parse(req);
    
    const fileContent = fields.fileContent?.[0];
    const fileName = fields.fileName?.[0];
    
    if (!fileContent || !fileName) {
      return res.status(400).json({ error: 'Missing file content or filename' });
    }
    
    const buffer = Buffer.from(fileContent, 'base64');
    
    console.log(`Processing file: ${fileName} with structured extraction...`);
    const structuredContent = await extractStructuredText(buffer, fileName);
    
    if (!structuredContent.rawText && !structuredContent.visionAnalysis) {
      return res.status(400).json({ 
        error: 'No content could be extracted from the file',
        details: 'The file might be corrupted or contain no readable content'
      });
    }
    
    console.log(`Successfully extracted structured content from ${fileName}`);
    
    res.status(200).json({ 
      extracted_text: structuredContent.rawText,
      structured_content: structuredContent,
      file_name: fileName,
      has_vision_analysis: !!structuredContent.visionAnalysis
    });
    
  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ 
      error: 'Failed to process file',
      details: error.message 
    });
  }
}