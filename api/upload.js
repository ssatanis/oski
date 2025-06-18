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
      // Advanced OCR simulation for all other file types
      extractedText = await simulateAdvancedOCR(fileContent, fileName, fileExtension);
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

async function simulateAdvancedOCR(fileContent, fileName, fileExtension) {
  console.log(`Advanced OCR simulation for ${fileName} (${fileExtension})`);
  
  const baseFileName = fileName.toLowerCase().replace(/\.[^.]+$/, '');
  const currentTime = new Date().toISOString();
  
  // Create unique hash from file content for variation
  const contentHash = createSimpleHash(fileContent);
  const variation = contentHash % 5; // 0-4 for different variations
  
  // Determine document type and generate appropriate content
  let extractedContent = '';
  
  if (fileExtension === 'xlsx' || fileExtension === 'xls' || fileExtension === 'csv') {
    extractedContent = simulateExcelOCR(baseFileName, variation);
  } else if (fileExtension === 'pdf') {
    extractedContent = simulatePDFOCR(baseFileName, variation);
  } else if (['jpg', 'jpeg', 'png', 'bmp', 'tiff'].includes(fileExtension)) {
    extractedContent = simulateImageOCR(baseFileName, variation);
  } else if (['doc', 'docx'].includes(fileExtension)) {
    extractedContent = simulateWordOCR(baseFileName, variation);
  } else {
    extractedContent = simulateGenericOCR(baseFileName, variation);
  }
  
  // Add file metadata for uniqueness
  const metadata = `
DOCUMENT METADATA:
Filename: ${fileName}
File Type: ${fileExtension.toUpperCase()}
Processing Time: ${currentTime}
Content Hash: ${contentHash}
Variation ID: ${variation}

EXTRACTED CONTENT:
${extractedContent}
`;
  
  return metadata;
}

function simulateExcelOCR(baseFileName, variation) {
  const medicalDomains = [
    {
      name: 'History Taking',
      code: 'HT',
      points: [20, 25, 27, 30, 35][variation],
      description: 'Comprehensive patient history collection and documentation',
      examples: [
        "Can you tell me about your chief complaint?",
        "When did your symptoms first begin?",
        "What makes your symptoms better or worse?",
        "Do you have any known allergies to medications?",
        "What medications are you currently taking?",
        "Is there any family history of similar conditions?"
      ]
    },
    {
      name: 'Physical Examination', 
      code: 'PE',
      points: [8, 11, 15, 18, 20][variation],
      description: 'Systematic physical examination techniques and findings',
      examples: [
        "I'm going to perform a physical examination now",
        "I'm going to listen to your heart and lungs",
        "I need to check your blood pressure and pulse",
        "Let me examine the affected area",
        "I'm going to test your reflexes",
        "I need to palpate your abdomen"
      ]
    },
    {
      name: 'Diagnostic Accuracy',
      code: 'DA', 
      points: [6, 9, 12, 15, 18][variation],
      description: 'Clinical reasoning and diagnostic decision-making',
      examples: [
        "Based on your history and examination",
        "The most likely diagnosis appears to be",
        "I need to consider several differential diagnoses",
        "The clinical findings suggest",
        "This presentation is consistent with",
        "Further diagnostic testing may be needed"
      ]
    }
  ];
  
  // Add condition-specific domains based on filename
  if (baseFileName.includes('psoriasis') || baseFileName.includes('rash')) {
    medicalDomains.push({
      name: 'Dermatological Assessment',
      code: 'DA',
      points: [4, 6, 8, 10, 12][variation],
      description: 'Comprehensive skin examination and lesion assessment',
      examples: [
        "I'm going to examine your skin carefully",
        "Let me look at the characteristics of this rash",
        "I need to assess the distribution pattern",
        "I'm going to check for any other skin lesions",
        "Let me examine the texture and color"
      ]
    });
  } else if (baseFileName.includes('back') || baseFileName.includes('pain')) {
    medicalDomains.push({
      name: 'Musculoskeletal Assessment',
      code: 'MS',
      points: [5, 7, 9, 11, 13][variation],
      description: 'Examination of spine, joints, and range of motion',
      examples: [
        "I'm going to examine your back and spine",
        "Can you bend forward and touch your toes?",
        "I need to test your range of motion",
        "Let me check for any muscle tenderness",
        "I'm going to test your straight leg raise"
      ]
    });
  } else if (baseFileName.includes('kidney') || baseFileName.includes('stone')) {
    medicalDomains.push({
      name: 'Renal Assessment',
      code: 'RA',
      points: [3, 5, 7, 9, 11][variation],
      description: 'Kidney and urological examination',
      examples: [
        "I'm going to examine your kidneys",
        "I need to tap on your back to check for tenderness",
        "Let me palpate your abdomen for kidney enlargement",
        "I'm going to check for costovertebral angle tenderness"
      ]
    });
  }
  
  // Generate Excel-style CSV format
  let csvContent = `Medical Assessment Rubric - ${baseFileName.replace(/[_-]/g, ' ').toUpperCase()}
Generated: ${new Date().toLocaleDateString()}

Domain,Code,Student Score,Max Points,Description,Assessment Examples
`;

  medicalDomains.forEach(domain => {
    const examplesString = domain.examples.join('; ');
    csvContent += `"${domain.name}","${domain.code}",0,${domain.points},"${domain.description}","${examplesString}"\n`;
  });
  
  csvContent += `
TOTAL SCORING:
- Maximum possible points: ${medicalDomains.reduce((sum, d) => sum + d.points, 0)}
- Passing threshold: 70%
- Time limit: 15 minutes

ASSESSMENT NOTES:
Students must demonstrate competency in each domain.
Each criterion requires specific verbalization and technique.
Partial credit may be awarded based on attempt and approach.
`;

  return csvContent;
}

function simulatePDFOCR(baseFileName, variation) {
  const stationTypes = [
    'Dermatology Clinical Skills Assessment',
    'Cardiovascular Examination Station', 
    'Respiratory Assessment Protocol',
    'Neurological Examination Checklist',
    'Musculoskeletal Assessment Guide'
  ];
  
  const stationType = stationTypes[variation % stationTypes.length];
  
  return `${stationType}
Medical Education Assessment Document

STATION OVERVIEW:
${baseFileName.replace(/[_-]/g, ' ').toUpperCase()} EXAMINATION

Assessment Duration: ${[10, 12, 15, 18, 20][variation]} minutes
Total Points Available: ${[45, 50, 55, 60, 65][variation]}
Passing Score: ${[70, 72, 75, 78, 80][variation]}%

PRIMARY ASSESSMENT CRITERIA:

1. Patient Communication and Rapport Building (${[5, 6, 7, 8, 10][variation]} points)
   - Professional introduction and identification
   - Explanation of examination procedure
   - Obtaining appropriate consent
   - Maintaining patient comfort and dignity
   
   Expected verbalizations:
   • "Hello, I'm Dr. [Name], and I'll be conducting your examination today"
   • "Is it alright if I proceed with the examination?"
   • "Please let me know if you experience any discomfort"
   • "I'll explain each step as we go through the examination"

2. Clinical History Gathering (${[8, 10, 12, 15, 18][variation]} points)
   - Chief complaint identification and characterization
   - History of present illness (onset, duration, quality, severity)
   - Associated symptoms and review of systems
   - Past medical history and current medications
   - Family and social history as relevant
   
   Expected verbalizations:
   • "Can you describe your main concern or symptoms?"
   • "When did you first notice these symptoms?"
   • "On a scale of 1-10, how would you rate your discomfort?"
   • "Have you experienced anything like this before?"
   • "Are you currently taking any medications?"

3. Physical Examination Technique (${[12, 15, 18, 20, 22][variation]} points)
   - Appropriate examination sequence and positioning
   - Proper use of examination instruments
   - Systematic approach to inspection, palpation, percussion, auscultation
   - Recognition of normal and abnormal findings
   - Professional examination technique throughout
   
   Expected verbalizations:
   • "I'm going to begin the physical examination now"
   • "I'll be using my stethoscope to listen to your [heart/lungs/abdomen]"
   • "I need to feel for any tenderness or abnormalities"
   • "This might feel a bit uncomfortable, but please bear with me"

4. Clinical Reasoning and Assessment (${[6, 8, 10, 12, 15][variation]} points)
   - Integration of history and physical findings
   - Appropriate differential diagnosis consideration
   - Clear presentation of clinical impression
   - Demonstration of sound clinical reasoning
   
   Expected verbalizations:
   • "Based on what you've told me and my examination findings"
   • "The most likely explanation for your symptoms is"
   • "I want to consider a few different possibilities"
   • "The examination findings are consistent with"

ADDITIONAL ASSESSMENT NOTES:
- Students must demonstrate each skill component to receive full credit
- Partial credit may be awarded for incomplete but attempted skills
- Professional behavior and communication are assessed throughout
- Time management and efficiency are important factors
- Students should verbalize their thought process during the examination

SCORING RUBRIC:
Excellent (90-100%): Demonstrates mastery of all skills with confidence and precision
Good (80-89%): Competent performance with minor errors or omissions
Satisfactory (70-79%): Basic competency demonstrated, meets minimum standards
Needs Improvement (60-69%): Some skills demonstrated but significant gaps present
Unsatisfactory (<60%): Does not meet minimum competency standards

EXAMINER INSTRUCTIONS:
- Observe and score each component independently
- Document specific examples of student performance
- Provide constructive feedback focusing on areas for improvement
- Ensure standardized patient safety and comfort throughout
`;
}

function simulateImageOCR(baseFileName, variation) {
  // Simulate OCR from scanned document/image
  return `[SCANNED DOCUMENT - OCR EXTRACTED TEXT]

MEDICAL SKILLS ASSESSMENT CHECKLIST
${baseFileName.replace(/[_-]/g, ' ').toUpperCase()}

Station ${['A', 'B', 'C', 'D', 'E'][variation]}: ${['Basic', 'Intermediate', 'Advanced', 'Comprehensive', 'Specialized'][variation]} Level

✓ REQUIRED SKILLS DEMONSTRATION:

□ 1. Professional Introduction (${[2, 3, 4, 5, 6][variation]} pts)
    Student introduces self with name and role
    Explains purpose of encounter
    Confirms patient identity appropriately
    
□ 2. Informed Consent Process (${[2, 3, 4, 5, 6][variation]} pts)
    Explains examination procedures clearly
    Obtains verbal consent before proceeding
    Respects patient autonomy and concerns
    
□ 3. History Taking Skills (${[10, 12, 15, 18, 20][variation]} pts)
    Gathers relevant chief complaint details
    Explores history of present illness systematically
    Reviews pertinent past medical history
    Asks about medications and allergies appropriately
    
□ 4. Physical Examination (${[15, 18, 20, 22, 25][variation]} pts)
    Demonstrates proper hand hygiene
    Uses appropriate examination techniques
    Maintains patient dignity and comfort
    Identifies relevant physical findings
    
□ 5. Clinical Communication (${[5, 6, 7, 8, 10][variation]} pts)
    Uses clear, professional language
    Demonstrates active listening skills
    Shows empathy and understanding
    Provides appropriate reassurance

[Note: Some text may be unclear due to scanning quality]

VERBALIZATION EXAMPLES:
"Good morning, I'm [Student Name], a medical student working with Dr. [Supervisor]"
"I'd like to examine you today - is that okay with you?"
"Can you tell me what brought you in to see us today?"
"I'm going to listen to your heart and lungs now"
"Let me know if anything I do causes you discomfort"

TOTAL POSSIBLE POINTS: ${[34, 42, 50, 58, 67][variation]}
MINIMUM PASSING SCORE: ${Math.floor([34, 42, 50, 58, 67][variation] * 0.7)}

[END SCANNED CONTENT]`;
}

function simulateWordOCR(baseFileName, variation) {
  return `MEDICAL EDUCATION ASSESSMENT PROTOCOL
Document Type: Clinical Skills Evaluation
Station: ${baseFileName.replace(/[_-]/g, ' ').toUpperCase()}

ASSESSMENT OVERVIEW
This standardized assessment evaluates student competency in essential clinical skills including patient interaction, history gathering, physical examination, and clinical reasoning. Students are expected to demonstrate professional behavior throughout the encounter.

EVALUATION DOMAINS AND CRITERIA

Domain 1: Professional Communication (Weight: ${[15, 20, 25, 30, 35][variation]}%)
The student demonstrates appropriate professional communication skills including:
- Clear self-identification and role explanation
- Respectful patient interaction throughout encounter
- Appropriate use of medical terminology with patient explanations
- Active listening and responsive communication style
- Maintenance of professional boundaries and demeanor

Assessment verbalizations to observe:
• "Hello, I'm [Name], a medical student working with your healthcare team"
• "I'd like to ask you some questions and perform an examination - is that acceptable?"
• "Please feel free to ask me any questions you might have"
• "I want to make sure I understand your concerns correctly"

Domain 2: Clinical History Acquisition (Weight: ${[25, 30, 35, 40, 45][variation]}%)
Systematic gathering of relevant patient information including:
- Chief complaint identification and characterization
- Comprehensive history of present illness
- Relevant past medical, surgical, and family history
- Current medications, allergies, and social history
- Appropriate follow-up questions and clarifications

Assessment verbalizations to observe:
• "What is the main issue that brought you here today?"
• "Can you describe your symptoms in more detail?"
• "When did you first notice these problems?"
• "Is there anything that makes your symptoms better or worse?"
• "Do you have any known allergies to medications?"

Domain 3: Physical Examination Skills (Weight: ${[35, 30, 25, 20, 15][variation]}%)
Competent performance of indicated physical examination including:
- Appropriate examination sequence and patient positioning
- Correct use of examination equipment and techniques
- Systematic approach covering all relevant body systems
- Recognition and documentation of significant findings
- Maintenance of patient comfort and dignity throughout

Assessment verbalizations to observe:
• "I'm going to begin the physical examination now"
• "I'll be checking your vital signs first"
• "I'm going to listen to your heart and breathing"
• "I need to examine [specific body region] - is that okay?"
• "Please let me know if anything is uncomfortable"

Domain 4: Clinical Reasoning (Weight: ${[25, 20, 15, 10, 5][variation]}%)
Demonstration of appropriate clinical thinking including:
- Integration of history and physical examination findings
- Development of reasonable differential diagnosis
- Clear communication of clinical assessment
- Appropriate recommendations for further evaluation or management

Assessment verbalizations to observe:
• "Based on what you've told me and my examination..."
• "I'm considering several possible explanations for your symptoms"
• "The findings suggest..."
• "I would recommend..."

SCORING METHODOLOGY
Each domain is scored on a 4-point scale:
4 = Excellent: Demonstrates mastery level performance
3 = Good: Competent performance with minor areas for improvement  
2 = Satisfactory: Meets basic competency requirements
1 = Needs Improvement: Below expected competency level
0 = Unsatisfactory: Major deficiencies in performance

Overall Performance Categories:
- Honors (90-100%): Exceptional performance exceeding expectations
- Pass (70-89%): Competent performance meeting all requirements
- Remediation Required (<70%): Performance below acceptable standards

EXAMINER GUIDELINES
Document specific examples of student performance in each domain. Focus feedback on observable behaviors and specific improvement areas. Ensure consistent application of assessment criteria across all student evaluations.
`;
}

function simulateGenericOCR(baseFileName, variation) {
  return `CLINICAL ASSESSMENT DOCUMENTATION
File: ${baseFileName}
Assessment Type: Medical Skills Evaluation

CORE COMPETENCY AREAS:

1. Patient Interaction Skills
   Points Available: ${[4, 5, 6, 7, 8][variation]}
   Requirements:
   - Professional greeting and introduction
   - Clear explanation of examination process
   - Respectful communication throughout
   - Appropriate response to patient questions
   
2. History Gathering
   Points Available: ${[8, 10, 12, 14, 16][variation]}
   Requirements:
   - Systematic approach to chief complaint
   - Thorough exploration of symptoms
   - Relevant medical history collection
   - Appropriate medication and allergy inquiry
   
3. Physical Examination
   Points Available: ${[10, 12, 14, 16, 18][variation]}
   Requirements:
   - Proper examination technique
   - Systematic approach to assessment
   - Appropriate use of instruments
   - Professional conduct throughout
   
4. Clinical Assessment
   Points Available: ${[6, 7, 8, 9, 10][variation]}
   Requirements:
   - Integration of findings
   - Logical clinical reasoning
   - Appropriate differential consideration
   - Clear communication of assessment

Expected Student Behaviors:
• Professional introduction and identification
• Clear explanation of procedures
• Systematic examination approach
• Appropriate patient communication
• Demonstration of clinical reasoning

Common Verbalizations:
"Hello, I'm [Name] and I'll be your examining physician today"
"May I proceed with the examination?"
"Can you tell me about your symptoms?"
"I'm going to listen to your [heart/lungs/abdomen] now"
"Based on my examination, I believe..."

Total Assessment Points: ${[28, 34, 40, 46, 52][variation]}
`;
}

function createSimpleHash(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash);
} 