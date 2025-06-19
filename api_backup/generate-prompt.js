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
    const { extracted_text, filename, dashboard_criteria } = req.body;
    
    if (!extracted_text && !dashboard_criteria) {
      return res.status(400).json({ error: 'Missing extracted_text or dashboard_criteria in request body' });
    }

    console.log('Processing request for YAML generation...');
    
    let criteria = [];
    let examsList = [];

    // If dashboard criteria is provided, use it (for YAML downloads)
    if (dashboard_criteria && dashboard_criteria.length > 0) {
      console.log('Using dashboard criteria for YAML generation');
      criteria = dashboard_criteria.map(criterion => ({
        examId: criterion.examId || criterion.name.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_'),
        name: criterion.name,
        max_points: parseInt(criterion.max_points) || 1,
        examples: Array.isArray(criterion.examples) ? criterion.examples : []
      }));
      examsList = criteria.map(c => c.examId);
    } else {
      // Use AI analyzer for initial processing
      console.log('Using AI analyzer for criteria extraction');
      
      try {
        // Call the adaptive OCR analyzer first
        const adaptiveResponse = await fetch('http://localhost:3000/api/adaptive-ocr-analyzer', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            fileContent: extracted_text,
            fileName: filename
          })
        });

        if (adaptiveResponse.ok) {
          const adaptiveData = await adaptiveResponse.json();
          criteria = adaptiveData.criteria || [];
          examsList = criteria.map(c => c.examId);
          console.log(`Adaptive OCR extracted ${criteria.length} criteria`);
        } else {
          // Fallback to regular AI analyzer
          const aiResponse = await fetch('http://localhost:3000/api/ai-rubric-analyzer', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              extracted_text: extracted_text,
              filename: filename
            })
          });

          if (aiResponse.ok) {
            const aiData = await aiResponse.json();
            criteria = aiData.criteria || [];
            examsList = criteria.map(c => c.examId);
            console.log(`Fallback AI extracted ${criteria.length} criteria`);
          } else {
            throw new Error('Both adaptive OCR and AI analyzer failed');
          }
        }
      } catch (aiError) {
        console.warn('Advanced analyzers unavailable, using basic parsing:', aiError.message);
        
        // Fallback to basic parsing
        const fallbackCriteria = await basicCriteriaExtraction(extracted_text, filename);
        criteria = fallbackCriteria;
        examsList = criteria.map(c => c.examId);
      }
    }

    if (criteria.length === 0) {
      return res.status(400).json({ error: 'No criteria could be extracted from the document' });
    }

    console.log(`Generating YAML for ${criteria.length} criteria:`, criteria.map(c => c.name));

    // Generate the YAML content in the exact format of your training examples
    const yamlContent = generateYAMLContent(criteria, examsList);

    // Create parsed structure for the dashboard
    const parsedYaml = {
      system_message: "You are a helpful assistant tasked with analyzing and scoring a recorded medical examination between a medical student and a patient. Provide your response in JSON format.",
      user_message: `Your task is to identify the start and end times of specific medical assessments...`,
      criteria: criteria,
      exams_list: examsList,
      response_config: {
        structured_output: true
      }
    };

    console.log('YAML generation complete');

    res.status(200).json({
      message: 'Prompt generated successfully',
      yaml_content: yamlContent,
      parsed_yaml: parsedYaml,
      validation_success: true,
      criteria_count: criteria.length,
      generated_from: dashboard_criteria ? 'dashboard' : 'ai_extraction'
    });

  } catch (error) {
    console.error('Prompt generation failed:', error);
    res.status(500).json({ 
      error: `Failed to generate prompt: ${error.message}` 
    });
  }
}

async function basicCriteriaExtraction(extracted_text, filename) {
  console.log('Using enhanced Excel criteria extraction');
  
  const criteria = [];
  const lines = extracted_text.split('\n').filter(line => line.trim());
  
  // Parse the new Excel extraction format
  const extractedCriteria = parseExcelTableData(extracted_text);
  
  if (extractedCriteria.length > 0) {
    console.log(`Extracted ${extractedCriteria.length} criteria from Excel table structure`);
    return extractedCriteria;
  }
  
  // Fallback to pattern matching if extraction fails
  console.log('Falling back to pattern matching');
  return fallbackPatternExtraction(extracted_text, filename);
}

function parseExcelTableData(extracted_text) {
  const criteria = [];
  const lines = extracted_text.split('\n');
  
  // Look for the "ASSESSMENT CRITERIA EXTRACTED" section
  let criteriaSection = false;
  let verbalizationSection = false;
  let extractedVerbalizations = [];
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // Check for verbalization examples section
    if (line.includes('EXTRACTED VERBALIZATION EXAMPLES')) {
      verbalizationSection = true;
      continue;
    }
    
    if (verbalizationSection && line.startsWith('•')) {
      extractedVerbalizations.push(line.substring(1).trim());
      continue;
    }
    
    if (line.includes('SCORING INFORMATION') || line.includes('EXCEL STRUCTURE')) {
      verbalizationSection = false;
    }
    
    // Check for criteria section
    if (line.includes('ASSESSMENT CRITERIA EXTRACTED')) {
      criteriaSection = true;
      continue;
    }
    
    if (line.includes('Domain,Code,Max Points,Description,Specific Assessment Items')) {
      continue; // Skip header
    }
    
    // Parse CSV-style criteria data
    if (criteriaSection && line.includes('"') && line.includes(',')) {
      try {
        // Parse CSV line: "Physical Exam Elements","PE",2,"Description","item1; item2"
        const csvMatch = line.match(/"([^"]+)","([^"]+)",(\d+),"([^"]+)","([^"]+)"/);
        
        if (csvMatch) {
          const [, name, code, points, description, itemsString] = csvMatch;
          const items = itemsString.split(';').map(item => item.trim());
          
          // Generate relevant verbalization examples based on the specific items
          const examples = generateVerbalizationsFromItems(items, extractedVerbalizations);
          
          const examId = name.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_');
          
          criteria.push({
            examId: examId,
            name: name,
            max_points: parseInt(points),
            examples: examples
          });
        }
      } catch (error) {
        console.warn('Error parsing criteria line:', line, error.message);
      }
    }
    
    // Stop parsing if we hit the verbalization section
    if (line.includes('=== EXTRACTED VERBALIZATION EXAMPLES ===')) {
      criteriaSection = false;
    }
  }
  
  return criteria;
}

function generateVerbalizationsFromItems(items, extractedVerbalizations) {
  const examples = [];
  
  // Use extracted verbalizations if available
  if (extractedVerbalizations.length > 0) {
    examples.push(...extractedVerbalizations.slice(0, 3)); // Take first 3
  }
  
  // Add specific examples based on the assessment items
  items.forEach(item => {
    if (item.toLowerCase().includes('wash') && item.toLowerCase().includes('hands')) {
      examples.push("I'm going to wash my hands before the examination");
    }
    if (item.toLowerCase().includes('inspect') && item.toLowerCase().includes('skin')) {
      examples.push("I'm going to inspect your skin carefully");
      examples.push("Let me examine the affected area");
    }
    if (item.toLowerCase().includes('introduce')) {
      examples.push("Hello, I'm Dr. Smith and I'll be examining you today");
    }
    if (item.toLowerCase().includes('consent') || item.toLowerCase().includes('explain')) {
      examples.push("Is it okay if I proceed with the examination?");
    }
    if (item.toLowerCase().includes('palpat') || item.toLowerCase().includes('feel')) {
      examples.push("I'm going to feel this area with my hands");
    }
    if (item.toLowerCase().includes('listen') || item.toLowerCase().includes('auscult')) {
      examples.push("I'm going to listen to your heart and lungs");
    }
  });
  
  // Remove duplicates and ensure we have at least 2 examples
  const uniqueExamples = [...new Set(examples)];
  
  if (uniqueExamples.length === 0) {
    uniqueExamples.push("I'm going to perform this examination now");
    uniqueExamples.push("Please let me know if you feel any discomfort");
  } else if (uniqueExamples.length === 1) {
    uniqueExamples.push("Please let me know if you feel any discomfort");
  }
  
  return uniqueExamples.slice(0, 4); // Limit to 4 examples max
}

function fallbackPatternExtraction(extracted_text, filename) {
  const criteria = [];
  
  // Look for common medical examination patterns
  const medicalPatterns = [
    { pattern: /physical.{0,20}exam/i, name: 'Physical Examination', points: 2 },
    { pattern: /history.{0,20}taking/i, name: 'History Taking', points: 3 },
    { pattern: /diagnostic.{0,20}accuracy/i, name: 'Diagnostic Accuracy', points: 2 },
    { pattern: /communication|rapport/i, name: 'Patient Communication', points: 1 },
    { pattern: /hands|hygiene|wash/i, name: 'Hand Hygiene', points: 1 },
    { pattern: /skin|inspect/i, name: 'Skin Inspection', points: 1 }
  ];
  
  const textContent = extracted_text.toLowerCase();
  
  for (const pattern of medicalPatterns) {
    if (pattern.pattern.test(textContent)) {
      const examId = pattern.name.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_');
      
      let examples = [];
      if (pattern.name.toLowerCase().includes('physical')) {
        examples = [
          "I'm going to examine you now",
          "Let me check this area"
        ];
      } else if (pattern.name.toLowerCase().includes('history')) {
        examples = [
          "Can you tell me about your symptoms?",
          "When did this start?"
        ];
      } else if (pattern.name.toLowerCase().includes('hygiene')) {
        examples = [
          "I'm going to wash my hands before the examination"
        ];
      } else if (pattern.name.toLowerCase().includes('skin')) {
        examples = [
          "I'm going to inspect your skin carefully"
        ];
      } else {
        examples = [`I'm going to assess your ${pattern.name.toLowerCase()}`];
      }
      
      criteria.push({
        examId: examId,
        name: pattern.name,
        max_points: pattern.points,
        examples: examples
      });
      
      break; // Only take the first match to avoid duplicates
    }
  }
  
  // If no patterns found, create a default physical exam criterion
  if (criteria.length === 0) {
    criteria.push({
      examId: 'Physical_Exam_Elements',
      name: 'Physical Exam Elements',
      max_points: 2,
      examples: [
        "I'm going to wash my hands before the examination",
        "I'm going to inspect your skin carefully"
      ]
    });
  }
  
  return criteria;
}

function generateYAMLContent(criteria, examsList) {
  // Generate YAML in the exact format of your training examples
  const yamlContent = `system_message: |
   You are a helpful assistant tasked with analyzing and scoring a recorded medical examination between a medical student and a patient. Provide your response in JSON format.
   
user_message: |
   
   Your task is to identify the start and end times of specific medical assessments within the conversation and provide the reasoning behind your choices. Whenever the medical student asks about pain or mentions checking a specific part of the body (e.g., "any pain when I do this?" or "let me check your..."), assume that a medical assessment is being conducted at that moment. You will be provided with a description and example for each assessment. This station consists of the following medical assessments: ${examsList.join(', ')}
   
   Important Instructions:
   - When determining the start and end times of each assessment, focus on the moments where the doctor instructs the patient to perform an action or asks specific questions. Give these phrases priority for setting the \`start_time\` and \`end_time\` over phrases where the doctor states their own actions.
   - Whenever the medical student asks about pain, takes history, performs examination, makes diagnostic statements, or discusses management, assume that the relevant assessment is being conducted at that moment.
   - Always pay close attention to surrounding context and related medical assessments mentioned.
      
   You need to identify the following medical assessments from this transcript: 
${criteria.map((criterion, index) => `   	 ${index + 1}. ${criterion.examId}: Did the doctor perform ${criterion.name.toLowerCase()}? 
   	 - Verbalization examples: ${criterion.examples.join(', ')}`).join('\n\n')}
   
   
   If no assessment is detected, you can say "no assessment was performed", start_time: "nan", end_time: "nan", score: 0.
   
   ### Formatting Instructions
   
   - Ensure strict adherence to JSON formatting.
   - Do not use double quotes for multiple statements within a single field.
   - Use commas, single quotes, or other appropriate delimiters for multiple statements.
   - Do not include any text before or after the JSON output. Provide ONLY the json response.
   
   Please provide a response in the following format with keys: ${examsList.join(', ')}
   
   and the schema: 
   {
        "statement": "statement extracted from the transcript that supports this specific assessment",
        "start_time": "timepoint for start of the assessment (MM:SS only)",
        "end_time": "timepoint for end of the assessment (MM:SS only)",
        "rationale": "reasoning behind scoring the medical assessment",
        "score": "score of the assessment (0 or 1)"
   }
response_config:
  structured_output: True`;

  return yamlContent;
} 