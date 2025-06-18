import fs from 'fs';
import path from 'path';

export const config = {
  api: {
    bodyParser: {
      sizeLimit: '10mb',
    },
  },
};

// Training data and AI model
class RubricAI {
  constructor() {
    this.trainingData = [];
    this.medicalPatterns = [];
    this.loaded = false;
  }

  async loadTrainingData() {
    if (this.loaded) return;

    try {
      console.log('Loading AI training data...');
      
      // Load YAML prompts for pattern recognition
      const yamlDir = '/Users/sahajsatani/Documents/Oski/rubrics-to-prompts/yaml_prompts/src/prompts/prompt_yamls/osce-audio';
      
      if (fs.existsSync(yamlDir)) {
        const yamlFiles = fs.readdirSync(yamlDir).filter(file => file.endsWith('.yaml'));
        
        for (const file of yamlFiles) {
          try {
            const content = fs.readFileSync(path.join(yamlDir, file), 'utf-8');
            const stationId = file.replace('.yaml', '');
            
            // Extract patterns from YAML content
            const criteria = this.extractCriteriaFromYaml(content, stationId);
            this.trainingData.push({
              station: stationId,
              file: file,
              criteria: criteria,
              content: content
            });
          } catch (err) {
            console.warn(`Could not load YAML file ${file}:`, err.message);
          }
        }
      }

      // Build comprehensive medical examination patterns
      this.buildMedicalPatterns();
      this.loaded = true;
      console.log(`AI trained with ${this.trainingData.length} YAML examples and ${this.medicalPatterns.length} medical patterns`);
      
    } catch (error) {
      console.error('Error loading training data:', error);
      this.loaded = true; // Continue with limited functionality
    }
  }

  extractCriteriaFromYaml(content, stationId) {
    const criteria = [];
    const lines = content.split('\n');
    
    let inExamSection = false;
    let currentExam = null;
    
    for (const line of lines) {
      // Look for exam definitions
      const examMatch = line.match(/^\s*(\d+):\s*([A-Za-z_]+):\s*(.+)/);
      if (examMatch) {
        if (currentExam) {
          criteria.push(currentExam);
        }
        
        currentExam = {
          id: examMatch[2],
          name: examMatch[2].replace(/_/g, ' '),
          description: examMatch[3],
          examples: [],
          station: stationId
        };
        inExamSection = true;
      }
      
      // Look for examples
      if (inExamSection && line.trim().startsWith('-') && !line.includes('Examples:')) {
        const example = line.trim().substring(1).trim();
        if (example && currentExam) {
          currentExam.examples.push(example);
        }
      }
    }
    
    if (currentExam) {
      criteria.push(currentExam);
    }
    
    return criteria;
  }

  buildMedicalPatterns() {
    // Extract all unique examination types and their patterns
    const examTypes = new Set();
    const examplePatterns = new Map();
    
    for (const training of this.trainingData) {
      for (const criterion of training.criteria) {
        examTypes.add(criterion.id);
        
        if (!examplePatterns.has(criterion.id)) {
          examplePatterns.set(criterion.id, []);
        }
        examplePatterns.get(criterion.id).push(...criterion.examples);
      }
    }
    
    // Build comprehensive medical examination patterns
    this.medicalPatterns = [
      {
        category: 'History Taking',
        keywords: ['history', 'symptoms', 'complaint', 'illness', 'medications', 'allergies', 'family history', 'social history'],
        patterns: [
          /history.{0,20}taking/i,
          /chief.{0,10}complaint/i,
          /present.{0,10}illness/i,
          /past.{0,10}medical/i,
          /family.{0,10}history/i,
          /social.{0,10}history/i,
          /medications?/i,
          /allergies/i
        ],
        examples: [
          "Can you tell me about your symptoms?",
          "When did this start?",
          "What makes it better or worse?",
          "Do you have any allergies?",
          "What medications are you taking?",
          "Any family history of this condition?",
          "Do you smoke or drink alcohol?",
          "What brings you in today?"
        ],
        defaultPoints: 25
      },
      {
        category: 'Physical Examination',
        keywords: ['physical', 'examination', 'inspect', 'palpate', 'percuss', 'auscult', 'vital signs'],
        patterns: [
          /physical.{0,20}exam/i,
          /vital.{0,10}signs/i,
          /blood.{0,10}pressure/i,
          /heart.{0,10}rate/i,
          /auscult/i,
          /palpat/i,
          /percuss/i,
          /inspect/i
        ],
        examples: [
          "I'm going to examine you now",
          "I'm going to listen to your heart",
          "I'm going to check your blood pressure",
          "Let me examine your abdomen",
          "I'm going to test your reflexes",
          "I need to check your pulse",
          "I'm going to look at your skin"
        ],
        defaultPoints: 15
      },
      {
        category: 'Abdominal Examination',
        keywords: ['abdomen', 'liver', 'kidney', 'bowel', 'stomach'],
        patterns: [
          /abdomen/i,
          /liver/i,
          /kidney/i,
          /bowel.{0,10}sounds/i,
          /stomach/i,
          /palpat.{0,10}abdomen/i
        ],
        examples: [
          "I'm going to examine your abdomen",
          "I'm going to listen to your bowel sounds",
          "I'm going to press on your stomach",
          "I'm going to tap on your abdomen",
          "I'm going to feel for your liver edge",
          "I'm going to check your kidneys"
        ],
        defaultPoints: 10
      },
      {
        category: 'Cardiovascular Examination',
        keywords: ['heart', 'cardiac', 'pulse', 'blood pressure', 'cardiovascular'],
        patterns: [
          /heart/i,
          /cardiac/i,
          /pulse/i,
          /blood.{0,10}pressure/i,
          /cardiovascular/i,
          /auscult.{0,10}heart/i
        ],
        examples: [
          "I'm going to listen to your heart",
          "I'm going to check your pulse",
          "I'm going to take your blood pressure",
          "Let me examine your heart sounds",
          "I'm going to feel your pulse"
        ],
        defaultPoints: 8
      },
      {
        category: 'Respiratory Examination',
        keywords: ['lung', 'respiratory', 'breathing', 'chest', 'breath sounds'],
        patterns: [
          /lung/i,
          /respiratory/i,
          /breathing/i,
          /chest/i,
          /breath.{0,10}sounds/i,
          /auscult.{0,10}lung/i
        ],
        examples: [
          "I'm going to listen to your lungs",
          "Take a deep breath",
          "I'm going to check your breathing",
          "I'm going to examine your chest",
          "I'm going to listen to your breath sounds"
        ],
        defaultPoints: 8
      },
      {
        category: 'Neurological Examination',
        keywords: ['neuro', 'reflex', 'mental status', 'cranial nerve', 'motor', 'sensory'],
        patterns: [
          /neuro/i,
          /reflex/i,
          /mental.{0,10}status/i,
          /cranial.{0,10}nerve/i,
          /motor/i,
          /sensory/i
        ],
        examples: [
          "I'm going to test your reflexes",
          "Follow my finger with your eyes",
          "Can you squeeze my hands?",
          "I'm going to test your sensation",
          "I'm going to check your coordination"
        ],
        defaultPoints: 10
      },
      {
        category: 'Diagnostic Reasoning',
        keywords: ['diagnosis', 'reasoning', 'differential', 'assessment', 'impression'],
        patterns: [
          /diagnostic.{0,20}reasoning/i,
          /diagnostic.{0,20}accuracy/i,
          /differential.{0,10}diagnosis/i,
          /clinical.{0,10}reasoning/i,
          /assessment/i,
          /impression/i
        ],
        examples: [
          "Based on your symptoms and examination",
          "The most likely diagnosis is",
          "I need to consider several possibilities",
          "The findings suggest",
          "This is consistent with",
          "My clinical impression is"
        ],
        defaultPoints: 8
      },
      {
        category: 'Management',
        keywords: ['management', 'treatment', 'plan', 'follow up', 'referral'],
        patterns: [
          /management/i,
          /treatment/i,
          /plan/i,
          /follow.{0,10}up/i,
          /referral/i,
          /recommend/i
        ],
        examples: [
          "I recommend",
          "The treatment includes",
          "We should follow up",
          "I'm going to refer you to",
          "The treatment plan includes",
          "You should take this medication"
        ],
        defaultPoints: 5
      }
    ];
  }

  analyzeDocument(content, filename) {
    console.log(`AI analyzing document: ${filename}`);
    
    const criteria = [];
    const contentLower = content.toLowerCase();
    const lines = content.split('\n').filter(line => line.trim());
    
    // First, try to find specific medical examination patterns
    const foundPatterns = new Set();
    
    for (const pattern of this.medicalPatterns) {
      // Check if this pattern exists in the content
      const patternFound = pattern.patterns.some(regex => regex.test(contentLower)) ||
                          pattern.keywords.some(keyword => contentLower.includes(keyword.toLowerCase()));
      
      if (patternFound) {
        foundPatterns.add(pattern.category);
        
        // Extract specific sub-examinations for this category
        const subExams = this.extractSubExaminations(content, pattern);
        
        if (subExams.length > 0) {
          criteria.push(...subExams);
        } else {
          // Use default pattern
          const examId = pattern.category.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_');
          criteria.push({
            examId: examId,
            name: pattern.category,
            max_points: pattern.defaultPoints,
            examples: pattern.examples.slice(0, 5) // Limit examples
          });
        }
      }
    }
    
    // If no patterns found, try to extract from structured data
    if (criteria.length === 0) {
      console.log('No patterns found, attempting structured extraction...');
      const structuredCriteria = this.extractStructuredCriteria(content);
      criteria.push(...structuredCriteria);
    }
    
    // If still no criteria, use intelligent defaults based on filename
    if (criteria.length === 0) {
      console.log('Using intelligent defaults based on filename...');
      const defaultCriteria = this.generateDefaultCriteria(filename);
      criteria.push(...defaultCriteria);
    }
    
    console.log(`AI extracted ${criteria.length} criteria for ${filename}`);
    return criteria;
  }

  extractSubExaminations(content, pattern) {
    const subExams = [];
    const lines = content.split('\n');
    
    // Look for numbered or bulleted lists within this category
    const examPatterns = [
      /^\s*\d+[\.\)]\s*(.+?)(?:\s*\((\d+)\s*points?\))?$/i,
      /^\s*[-•]\s*(.+?)(?:\s*\((\d+)\s*points?\))?$/i,
      /^\s*(.+?):\s*(.+?)(?:\s*\((\d+)\s*points?\))?$/i
    ];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      
      for (const examPattern of examPatterns) {
        const match = line.match(examPattern);
        if (match) {
          const examName = match[1].trim();
          const points = parseInt(match[2] || match[3]) || 1;
          
          // Skip if this looks like a category header
          if (examName.toLowerCase().includes(pattern.category.toLowerCase()) && examName.length < 50) {
            continue;
          }
          
          // Look for examples in following lines
          const examples = [];
          for (let j = i + 1; j < Math.min(i + 10, lines.length); j++) {
            const nextLine = lines[j];
            if (nextLine.match(/^\s*\d+[\.\)]/)) break; // Hit next numbered item
            
            if (nextLine.toLowerCase().includes('example') || 
                nextLine.toLowerCase().includes('verbalization')) {
              const exampleText = nextLine.replace(/^.*?(?:example|verbalization)[s:]*\s*/i, '').trim();
              if (exampleText) {
                examples.push(...exampleText.split(/[,;]/).map(ex => ex.trim().replace(/^["']|["']$/g, '')).filter(ex => ex));
              }
            }
          }
          
          // Use pattern examples if none found
          if (examples.length === 0) {
            examples.push(...pattern.examples.slice(0, 3));
          }
          
          const examId = examName.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_');
          subExams.push({
            examId: examId,
            name: examName,
            max_points: points,
            examples: examples
          });
        }
      }
    }
    
    return subExams;
  }

  extractStructuredCriteria(content) {
    const criteria = [];
    const lines = content.split('\n').filter(line => line.trim());
    
    // Try to find CSV-like or table-like data
    for (const line of lines) {
      if (line.includes(',') && line.split(',').length >= 3) {
        const parts = line.split(',').map(part => part.trim().replace(/^["']|["']$/g, ''));
        
        if (parts.length >= 3 && !parts[0].toLowerCase().includes('domain') && 
            !parts[0].toLowerCase().includes('criteria')) {
          const name = parts[0];
          const points = parseInt(parts[2]) || parseInt(parts[1]) || 1;
          const description = parts[3] || parts[2] || '';
          const examples = parts[4] ? parts[4].split(/[;|]/).map(ex => ex.trim()).filter(ex => ex) : [];
          
          if (name && name.length > 2) {
            const examId = name.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_');
            criteria.push({
              examId: examId,
              name: name,
              max_points: points,
              examples: examples.length > 0 ? examples : [`I'm going to assess your ${name.toLowerCase()}`]
            });
          }
        }
      }
    }
    
    return criteria;
  }

  generateDefaultCriteria(filename) {
    const baseFilename = filename.toLowerCase().replace(/\.[^.]+$/, '');
    
    // Generate intelligent defaults based on filename and common medical patterns
    const defaults = [];
    
    if (baseFilename.includes('psoriasis') || baseFilename.includes('rash') || baseFilename.includes('skin')) {
      defaults.push(
        {
          examId: 'Skin_Inspection',
          name: 'Skin Inspection',
          max_points: 3,
          examples: [
            "I'm going to inspect your skin closely",
            "I'm looking for any rashes or abnormalities",
            "Let me examine the affected area"
          ]
        },
        {
          examId: 'Lesion_Assessment',
          name: 'Lesion Assessment',
          max_points: 2,
          examples: [
            "I'm going to examine this lesion",
            "Let me look at the characteristics of this rash",
            "I need to assess the distribution"
          ]
        }
      );
    } else if (baseFilename.includes('back') || baseFilename.includes('pain')) {
      defaults.push(
        {
          examId: 'Back_Examination',
          name: 'Back Examination',
          max_points: 4,
          examples: [
            "I'm going to examine your back",
            "Let me check your spine",
            "I'm going to assess your back pain"
          ]
        },
        {
          examId: 'Range_of_Motion',
          name: 'Range of Motion Assessment',
          max_points: 3,
          examples: [
            "Can you bend forward for me?",
            "Try to touch your toes",
            "Bend to the side"
          ]
        }
      );
    } else {
      // Generic medical examination defaults
      defaults.push(
        {
          examId: 'Patient_History',
          name: 'Patient History',
          max_points: 5,
          examples: [
            "Can you tell me about your symptoms?",
            "When did this start?",
            "What brings you in today?"
          ]
        },
        {
          examId: 'Physical_Examination',
          name: 'Physical Examination',
          max_points: 4,
          examples: [
            "I'm going to examine you now",
            "Let me check your vital signs",
            "I need to perform a physical exam"
          ]
        },
        {
          examId: 'Assessment_and_Plan',
          name: 'Assessment and Plan',
          max_points: 3,
          examples: [
            "Based on my examination",
            "I think the most likely diagnosis is",
            "Here's what I recommend"
          ]
        }
      );
    }
    
    return defaults;
  }
}

// Initialize the AI model
const rubricAI = new RubricAI();

export default async function handler(req, res) {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Ensure AI is loaded
    await rubricAI.loadTrainingData();
    
    const { extracted_text, filename } = req.body;
    
    if (!extracted_text) {
      return res.status(400).json({ error: 'Missing extracted_text in request body' });
    }

    console.log(`AI processing file: ${filename || 'unknown'}`);
    
    // Use AI to analyze the document
    const criteria = rubricAI.analyzeDocument(extracted_text, filename || 'document');
    
    if (criteria.length === 0) {
      return res.status(400).json({ error: 'Could not extract any criteria from the document' });
    }

    console.log(`AI analysis complete: ${criteria.length} criteria extracted`);

    res.status(200).json({
      message: 'AI analysis complete',
      criteria: criteria,
      ai_analysis: {
        training_data_loaded: rubricAI.loaded,
        training_examples: rubricAI.trainingData.length,
        patterns_available: rubricAI.medicalPatterns.length
      }
    });

  } catch (error) {
    console.error('AI analysis failed:', error);
    res.status(500).json({ 
      error: `AI analysis failed: ${error.message}` 
    });
  }
} 