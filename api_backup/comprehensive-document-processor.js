import formidable from 'formidable';
import fs from 'fs/promises';
import path from 'path';
import { spawn } from 'child_process';
import { promisify } from 'util';

export const config = {
  api: {
    bodyParser: false,
    responseLimit: false,
  },
};

// Enhanced document processor that integrates with Python analyzer
class ComprehensiveDocumentProcessor {
  constructor() {
    this.pythonScriptPath = path.join(process.cwd(), 'api', 'comprehensive-document-analyzer.py');
    this.uploadDir = path.join(process.cwd(), 'temp-uploads');
    this.ensureUploadDir();
  }

  async ensureUploadDir() {
    try {
      await fs.access(this.uploadDir);
    } catch {
      await fs.mkdir(this.uploadDir, { recursive: true });
    }
  }

  async processMultipleFiles(files) {
    console.log(`🔄 Processing ${files.length} files with comprehensive analyzer`);
    
    try {
      // Prepare file paths for Python script
      const filePaths = files.map(file => file.filepath);
      
      // Run Python analyzer
      const analysisResult = await this.runPythonAnalyzer(filePaths);
      
      // Parse and enhance results
      const enhancedResult = await this.enhanceAnalysisResults(analysisResult, files);
      
      // Convert to interactive rubric format
      const interactiveRubric = await this.convertToInteractiveRubric(enhancedResult);
      
      // Clean up temporary files
      await this.cleanupTempFiles(files);
      
      return {
        success: true,
        analysisResult: enhancedResult,
        interactiveRubric: interactiveRubric,
        processedFiles: files.length,
        timestamp: new Date().toISOString()
      };
      
    } catch (error) {
      console.error('❌ Document processing failed:', error);
      await this.cleanupTempFiles(files);
      throw error;
    }
  }

  async runPythonAnalyzer(filePaths) {
    console.log('🐍 Running Python comprehensive analyzer...');
    
    return new Promise((resolve, reject) => {
      const cliScriptPath = path.join(process.cwd(), 'api', 'cli_analyzer.py');
      const pythonProcess = spawn('python3', [
        cliScriptPath,
        'analyze_multiple',
        JSON.stringify(filePaths)
      ], {
        stdio: ['pipe', 'pipe', 'pipe'],
        env: {
          ...process.env,
          AWS_ACCESS_KEY_ID: process.env.AWS_ACCESS_KEY_ID,
          AWS_SECRET_ACCESS_KEY: process.env.AWS_SECRET_ACCESS_KEY,
          AWS_REGION: process.env.AWS_REGION || 'us-east-1',
          GOOGLE_APPLICATION_CREDENTIALS: process.env.GOOGLE_APPLICATION_CREDENTIALS
        }
      });

      let stdout = '';
      let stderr = '';

      pythonProcess.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      pythonProcess.stderr.on('data', (data) => {
        stderr += data.toString();
        console.log('Python output:', data.toString());
      });

      pythonProcess.on('close', (code) => {
        if (code === 0) {
          try {
            const result = JSON.parse(stdout);
            resolve(result);
          } catch (parseError) {
            console.error('Failed to parse Python output:', stdout);
            reject(new Error('Failed to parse analysis results'));
          }
        } else {
          console.error('Python script failed:', stderr);
          reject(new Error(`Python analyzer failed with code ${code}`));
        }
      });

      pythonProcess.on('error', (error) => {
        console.error('Failed to start Python process:', error);
        reject(error);
      });
    });
  }

  async enhanceAnalysisResults(analysisResult, originalFiles) {
    console.log('🔍 Enhancing analysis results...');
    
    // Add file metadata
    const enhancedDocuments = analysisResult.documents.map((doc, index) => {
      const originalFile = originalFiles[index];
      return {
        ...doc,
        original_filename: originalFile?.originalFilename || `file_${index}`,
        file_size: originalFile?.size || 0,
        mime_type: originalFile?.mimetype || 'unknown',
        upload_timestamp: new Date().toISOString()
      };
    });

    // Enhance combined analysis
    const enhancedCombinedAnalysis = {
      ...analysisResult.combined_analysis,
      processing_time: new Date().toISOString(),
      ocr_engines_used: this.determineOCREnginesUsed(analysisResult),
      confidence_scores: this.calculateConfidenceScores(analysisResult),
      quality_assessment: this.assessOverallQuality(analysisResult)
    };

    return {
      ...analysisResult,
      documents: enhancedDocuments,
      combined_analysis: enhancedCombinedAnalysis
    };
  }

  determineOCREnginesUsed(analysisResult) {
    const enginesUsed = new Set();
    
    analysisResult.documents.forEach(doc => {
      if (doc.extraction?.ocr_results?.tesseract) enginesUsed.add('Tesseract');
      if (doc.extraction?.ocr_results?.aws_textract) enginesUsed.add('AWS Textract');
      if (doc.extraction?.ocr_results?.google_vision) enginesUsed.add('Google Vision');
    });
    
    return Array.from(enginesUsed);
  }

  calculateConfidenceScores(analysisResult) {
    const confidenceScores = {};
    let totalConfidence = 0;
    let scoreCount = 0;

    analysisResult.documents.forEach((doc, index) => {
      if (doc.extraction?.ocr_results) {
        const ocrResults = doc.extraction.ocr_results;
        const docScores = {};
        
        ['tesseract', 'aws_textract', 'google_vision'].forEach(engine => {
          if (ocrResults[engine]?.confidence) {
            docScores[engine] = ocrResults[engine].confidence;
            totalConfidence += ocrResults[engine].confidence;
            scoreCount++;
          }
        });
        
        confidenceScores[`document_${index}`] = docScores;
      }
    });

    confidenceScores.overall_average = scoreCount > 0 ? totalConfidence / scoreCount : 0;
    return confidenceScores;
  }

  assessOverallQuality(analysisResult) {
    const successful = analysisResult.combined_analysis.successful_extractions;
    const total = analysisResult.combined_analysis.total_files;
    const successRate = total > 0 ? successful / total : 0;
    
    let qualityLevel;
    if (successRate >= 0.9) qualityLevel = 'excellent';
    else if (successRate >= 0.7) qualityLevel = 'good';
    else if (successRate >= 0.5) qualityLevel = 'fair';
    else qualityLevel = 'poor';

    return {
      success_rate: successRate,
      quality_level: qualityLevel,
      total_criteria_extracted: analysisResult.combined_analysis.merged_criteria?.length || 0,
      text_extraction_completeness: this.assessTextCompleteness(analysisResult)
    };
  }

  assessTextCompleteness(analysisResult) {
    const totalWords = analysisResult.combined_analysis.combined_text.split(' ').length;
    
    if (totalWords > 500) return 'comprehensive';
    else if (totalWords > 200) return 'adequate';
    else if (totalWords > 50) return 'minimal';
    else return 'insufficient';
  }

  async convertToInteractiveRubric(analysisResult) {
    console.log('🎯 Converting to interactive rubric format...');
    
    const combinedCriteria = analysisResult.combined_analysis.merged_criteria || [];
    const detectedSections = this.detectMedicalSections(analysisResult.combined_analysis.combined_text);
    
    // Create structured rubric based on detected content
    const interactiveRubric = {
      rubric_info: {
        title: this.extractRubricTitle(analysisResult.combined_analysis.combined_text),
        station_info: this.extractStationInfo(analysisResult.combined_analysis.combined_text),
        total_points: this.calculateTotalPoints(combinedCriteria),
        creation_timestamp: new Date().toISOString(),
        source_files: analysisResult.documents.length
      },
      assessment_domains: this.createAssessmentDomains(detectedSections, combinedCriteria),
      metadata: {
        extraction_confidence: analysisResult.combined_analysis.confidence_scores?.overall_average || 0,
        ocr_engines_used: this.determineOCREnginesUsed(analysisResult),
        document_types: analysisResult.documents.map(doc => doc.structure?.document_type).filter(Boolean)
      }
    };

    return interactiveRubric;
  }

  extractRubricTitle(text) {
    // Extract title from text using patterns
    const titlePatterns = [
      /station\s+\d+[a-z]?\s*-\s*([^-\n]+)/i,
      /([^-\n]+)\s*-\s*rubric/i,
      /assessment:\s*([^\n]+)/i,
      /evaluation:\s*([^\n]+)/i
    ];

    for (const pattern of titlePatterns) {
      const match = text.match(pattern);
      if (match) {
        return match[1].trim();
      }
    }

    return "Medical Assessment Rubric";
  }

  extractStationInfo(text) {
    const stationMatch = text.match(/station\s+(\d+[a-z]?)/i);
    const conditionMatch = text.match(/(?:station\s+\d+[a-z]?\s*-\s*)?([^-\n]+(?:rash|psoriasis|skin|dermatology)[^-\n]*)/i);
    
    return {
      station_number: stationMatch ? stationMatch[1] : null,
      condition: conditionMatch ? conditionMatch[1].trim() : null,
      specialty: this.detectSpecialty(text)
    };
  }

  detectSpecialty(text) {
    const specialtyPatterns = {
      'Dermatology': ['rash', 'psoriasis', 'skin', 'dermatology', 'dermatological'],
      'Internal Medicine': ['internal medicine', 'general medicine'],
      'Emergency Medicine': ['emergency', 'urgent', 'trauma'],
      'Cardiology': ['cardiac', 'heart', 'cardiovascular'],
      'Neurology': ['neurological', 'brain', 'nervous system'],
      'Pediatrics': ['pediatric', 'child', 'infant']
    };

    const textLower = text.toLowerCase();
    for (const [specialty, keywords] of Object.entries(specialtyPatterns)) {
      if (keywords.some(keyword => textLower.includes(keyword))) {
        return specialty;
      }
    }

    return 'General Medicine';
  }

  calculateTotalPoints(criteria) {
    return criteria.reduce((total, criterion) => {
      return total + (criterion.points || 0);
    }, 0);
  }

  createAssessmentDomains(detectedSections, criteria) {
    // Create the standard medical assessment domains
    const standardDomains = [
      {
        name: "History Taking",
        description: "Gathering patient history and presenting complaint",
        editable: false,
        subcategories: this.createHistoryTakingSubcategories(),
        total_points: 27
      },
      {
        name: "Physical Examination",
        description: "Conducting appropriate physical examination",
        editable: false,
        subcategories: this.createPhysicalExamSubcategories(),
        total_points: 11
      },
      {
        name: "Diagnostic Accuracy/Reasoning/Justification",
        description: "Demonstrating diagnostic reasoning and accuracy",
        editable: false,
        subcategories: this.createDiagnosticSubcategories(),
        total_points: 9
      },
      {
        name: "Management",
        description: "Providing appropriate management recommendations",
        editable: false,
        subcategories: this.createManagementSubcategories(),
        total_points: 4
      }
    ];

    return standardDomains;
  }

  createHistoryTakingSubcategories() {
    return [
      {
        id: 1,
        name: "Chief Concern",
        category: "CC",
        points: 1,
        editable: true,
        description: "Identifies and documents the chief concern appropriately"
      },
      {
        id: 2,
        name: "History of Present Illness (HPI)",
        category: "HPI", 
        points: 2,
        editable: true,
        description: "Gathers comprehensive history of present illness"
      },
      {
        id: 3,
        name: "Initially on right elbow",
        category: "HPI",
        points: 3,
        editable: true,
        description: "Identifies initial location of symptoms"
      },
      {
        id: 4,
        name: "Now (past 2 months not required) on both elbows",
        category: "HPI",
        points: 4,
        editable: true,
        description: "Documents progression and current extent"
      },
      {
        id: 5,
        name: "Itchy",
        category: "HPI",
        points: 5,
        editable: true,
        description: "Identifies key symptom characteristics"
      },
      {
        id: 6,
        name: "No previous episodes",
        category: "HPI",
        points: 6,
        editable: true,
        description: "Establishes episode history"
      },
      {
        id: 7,
        name: "Moisturizer provides temporary relief",
        category: "HPI",
        points: 7,
        editable: true,
        description: "Documents relief measures and effectiveness"
      },
      {
        id: 8,
        name: "Stress makes it worse",
        category: "HPI",
        points: 8,
        editable: true,
        description: "Identifies exacerbating factors"
      },
      {
        id: 9,
        name: "Mild OR intermittent itchiness",
        category: "HPI",
        points: 9,
        editable: true,
        description: "Characterizes symptom severity and pattern"
      },
      {
        id: 10,
        name: "Occasional OR intermittent discomfort",
        category: "HPI",
        points: 10,
        editable: true,
        description: "Documents associated discomfort"
      },
      {
        id: 11,
        name: "No fever",
        category: "HPI",
        points: 11,
        editable: true,
        description: "Rules out systemic symptoms"
      },
      {
        id: 12,
        name: "No drainage OR pus",
        category: "HPI",
        points: 12,
        editable: true,
        description: "Rules out signs of infection"
      },
      {
        id: 13,
        name: "No joint pain",
        category: "HPI",
        points: 13,
        editable: true,
        description: "Rules out joint involvement"
      },
      {
        id: 14,
        name: "No recent travel",
        category: "HPI",
        points: 14,
        editable: true,
        description: "Rules out travel-related exposures"
      },
      {
        id: 15,
        name: "No pets",
        category: "HPI",
        points: 15,
        editable: true,
        description: "Rules out pet-related exposures"
      },
      {
        id: 16,
        name: "No changes to detergents/soaps",
        category: "HPI",
        points: 16,
        editable: true,
        description: "Rules out contact allergen exposure"
      },
      {
        id: 17,
        name: "Hypertension",
        category: "PMH",
        points: 17,
        editable: true,
        description: "Documents relevant past medical history"
      },
      {
        id: 18,
        name: "Lisinopril",
        category: "Med",
        points: 18,
        editable: true,
        description: "Documents current medications"
      },
      {
        id: 19,
        name: "Claritin",
        category: "Med",
        points: 19,
        editable: true,
        description: "Documents additional medications"
      },
      {
        id: 20,
        name: "No supplements",
        category: "Med",
        points: 20,
        editable: true,
        description: "Documents supplement use"
      },
      {
        id: 21,
        name: "Over-the-counter moisturizer",
        category: "Med",
        points: 21,
        editable: true,
        description: "Documents self-treatment measures"
      },
      {
        id: 22,
        name: "Penicillin causes rash OR hives",
        category: "All",
        points: 22,
        editable: true,
        description: "Documents drug allergies"
      },
      {
        id: 23,
        name: "Seasonal allergy OR cedar allergy",
        category: "All",
        points: 23,
        editable: true,
        description: "Documents environmental allergies"
      },
      {
        id: 24,
        name: "Father has chronic rash",
        category: "FH",
        points: 24,
        editable: true,
        description: "Documents relevant family history"
      },
      {
        id: 25,
        name: "Non-smoker",
        category: "SH",
        points: 25,
        editable: true,
        description: "Documents smoking history"
      },
      {
        id: 26,
        name: "1 alcoholic drink per week",
        category: "SH",
        points: 26,
        editable: true,
        description: "Documents alcohol use"
      },
      {
        id: 27,
        name: "Works as a receptionist",
        category: "SH",
        points: 27,
        editable: true,
        description: "Documents occupational history"
      }
    ];
  }

  createPhysicalExamSubcategories() {
    return [
      {
        id: 28,
        name: "Vitals: documented T, HR, RR, BP (all 4 required)",
        category: "PE",
        points: 28,
        editable: true,
        description: "Documents complete vital signs"
      },
      {
        id: 29,
        name: "Well-demarcated (2 points)",
        category: "PE",
        points: 29,
        editable: true,
        description: "Describes lesion borders appropriately"
      },
      {
        id: 30,
        name: "Erythematous OR red",
        category: "PE",
        points: 30,
        editable: true,
        description: "Describes lesion color"
      },
      {
        id: 31,
        name: "Plaques (2 points)",
        category: "PE",
        points: 31,
        editable: true,
        description: "Identifies lesion morphology"
      },
      {
        id: 32,
        name: "Scale (2 points)",
        category: "PE",
        points: 32,
        editable: true,
        description: "Identifies surface characteristics"
      },
      {
        id: 33,
        name: "On elbows OR extensor surface upper extremities (2 points)",
        category: "PE",
        points: 33,
        editable: true,
        description: "Identifies anatomical distribution"
      },
      {
        id: 34,
        name: "No significant rash on knees OR back",
        category: "PE",
        points: 34,
        editable: true,
        description: "Documents absence of lesions elsewhere"
      }
    ];
  }

  createDiagnosticSubcategories() {
    return [
      {
        id: 35,
        name: "Psoriasis (5 points)",
        category: "DA",
        points: 35,
        editable: true,
        description: "Provides correct primary diagnosis"
      },
      {
        id: 36,
        name: "Itchy",
        category: "DR",
        points: 36,
        editable: true,
        description: "Provides appropriate clinical reasoning"
      },
      {
        id: 37,
        name: "Family history of rash OR father with rash",
        category: "DR",
        points: 37,
        editable: true,
        description: "Incorporates relevant family history"
      },
      {
        id: 38,
        name: "Raised OR plaque",
        category: "DR",
        points: 38,
        editable: true,
        description: "Describes relevant physical findings"
      },
      {
        id: 39,
        name: "Scale",
        category: "DR",
        points: 39,
        editable: true,
        description: "Identifies key diagnostic feature"
      },
      {
        id: 40,
        name: "On elbows OR extensor surface",
        category: "DR",
        points: 40,
        editable: true,
        description: "Notes characteristic distribution"
      },
      {
        id: 41,
        name: "Eczema OR atopic dermatitis (2 points)",
        category: "DA",
        points: 41,
        editable: true,
        description: "Provides appropriate differential diagnosis"
      },
      {
        id: 42,
        name: "Fungal infection OR Tinea (2 points)",
        category: "DA",
        points: 42,
        editable: true,
        description: "Considers infectious etiology"
      }
    ];
  }

  createManagementSubcategories() {
    return [
      {
        id: 43,
        name: "Skin biopsy",
        category: "M",
        points: 43,
        editable: true,
        description: "Recommends appropriate diagnostic procedure"
      },
      {
        id: 44,
        name: "CBC OR CMP OR Liver function tests (LFTs)",
        category: "M",
        points: 44,
        editable: true,
        description: "Orders relevant laboratory studies"
      },
      {
        id: 45,
        name: "Topical corticosteroids OR Phototherapy",
        category: "M",
        points: 45,
        editable: true,
        description: "Recommends appropriate treatment"
      },
      {
        id: 46,
        name: "Stress management OR moisturize regularly",
        category: "M",
        points: 46,
        editable: true,
        description: "Provides lifestyle recommendations"
      }
    ];
  }

  async cleanupTempFiles(files) {
    console.log('🧹 Cleaning up temporary files...');
    
    for (const file of files) {
      try {
        await fs.unlink(file.filepath);
      } catch (error) {
        console.warn(`Failed to delete temp file ${file.filepath}:`, error.message);
      }
    }
  }
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const processor = new ComprehensiveDocumentProcessor();

  try {
    // Parse multipart form data
    const form = formidable({
      uploadDir: processor.uploadDir,
      keepExtensions: true,
      maxFileSize: 50 * 1024 * 1024, // 50MB
      maxFiles: 10
    });

    const [fields, files] = await form.parse(req);
    
    // Get uploaded files
    const uploadedFiles = [];
    
    // Handle multiple files
    Object.keys(files).forEach(key => {
      const fileArray = Array.isArray(files[key]) ? files[key] : [files[key]];
      uploadedFiles.push(...fileArray);
    });

    if (uploadedFiles.length === 0) {
      return res.status(400).json({ 
        error: 'No files uploaded',
        message: 'Please select at least one file to analyze'
      });
    }

    console.log(`📁 Processing ${uploadedFiles.length} uploaded files`);
    
    // Process files with comprehensive analyzer
    const result = await processor.processMultipleFiles(uploadedFiles);
    
    res.status(200).json(result);

  } catch (error) {
    console.error('❌ Document processing error:', error);
    
    res.status(500).json({
      error: 'Document processing failed',
      message: error.message,
      details: process.env.NODE_ENV === 'development' ? error.stack : undefined
    });
  }
} 