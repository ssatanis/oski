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
    const { extracted_text } = req.body;
    
    if (!extracted_text) {
      return res.status(400).json({ error: 'Missing extracted_text in request body' });
    }

    console.log('Processing extracted text for prompt generation...');
    
    // Enhanced parsing to handle comprehensive medical rubrics
    const lines = extracted_text.split('\n').filter(line => line.trim());
    const criteria = [];
    let examsList = [];
    let stationName = 'Medical_Assessment';

    // Extract station/title name if present
    const titleLine = lines.find(line => 
      line.toLowerCase().includes('osce') || 
      line.toLowerCase().includes('assessment') ||
      line.toLowerCase().includes('medical') ||
      line.toLowerCase().includes('examination') ||
      line.toLowerCase().includes('rubric')
    );
    if (titleLine) {
      stationName = titleLine.trim().replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_');
    }

    // Parse domain-based medical rubrics (Excel-style format)
    const domainPattern = /^(.+?)\s*\(([A-Z]{1,3})\),\s*\d+,\s*(\d+),\s*(.+?),"(.+?)"$/;
    const domainMatches = lines.filter(line => domainPattern.test(line));
    
    if (domainMatches.length > 0) {
      console.log('Found domain-based medical rubric format');
      
      domainMatches.forEach(line => {
        const match = line.match(domainPattern);
        if (match) {
          const [, domainName, domainCode, points, description, examples] = match;
          
          // Split examples by common delimiters
          const exampleList = examples.split(/[,;]/).map(ex => ex.trim().replace(/^"|"$/g, '')).filter(ex => ex);
          
          const examId = domainName.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_');
          examsList.push(examId);
          
          criteria.push({
            examId: examId,
            name: domainName,
            max_points: parseInt(points),
            examples: exampleList
          });
        }
      });
    } else {
      // Parse detailed criteria format (structured format)
      console.log('Parsing detailed criteria format');
      
      let currentDomain = null;
      let domainPoints = 0;
      
      lines.forEach((line, index) => {
        // Look for domain headers
        const domainMatch = line.match(/^\d+\.\s*(.+?)\s*\(Total:\s*(\d+)\s*points?\)/i);
        if (domainMatch) {
          currentDomain = domainMatch[1].trim();
          domainPoints = parseInt(domainMatch[2]);
          
          const examId = currentDomain.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_');
          examsList.push(examId);
          
          // Look for sub-criteria under this domain
          const subCriteria = [];
          const subExamples = [];
          
          for (let i = index + 1; i < lines.length; i++) {
            const nextLine = lines[i];
            
            // Stop if we hit another domain
            if (nextLine.match(/^\d+\.\s*(.+?)\s*\(Total:\s*\d+\s*points?\)/i)) {
              break;
            }
            
            // Look for sub-criteria
            const subCriteriaMatch = nextLine.match(/^\s*-\s*(.+?)\s*\((\d+)\s*points?\)/);
            if (subCriteriaMatch) {
              subCriteria.push(subCriteriaMatch[1].trim());
            }
            
            // Look for examples
            const exampleMatch = nextLine.match(/Examples:\s*(.+)/i);
            if (exampleMatch) {
              const examples = exampleMatch[1].split(/[,;]/).map(ex => ex.trim().replace(/^"|"$/g, '')).filter(ex => ex);
              subExamples.push(...examples);
            }
          }
          
          // Create criteria for this domain
          criteria.push({
            examId: examId,
            name: currentDomain,
            max_points: domainPoints,
            examples: subExamples.length > 0 ? subExamples : [
              `I'm going to assess your ${currentDomain.toLowerCase()}`,
              `Let me evaluate your ${currentDomain.toLowerCase()}`,
              `I need to examine your ${currentDomain.toLowerCase()}`
            ]
          });
        }
      });
      
      // If no structured format found, try to extract from pattern-based text
      if (criteria.length === 0) {
        console.log('Trying pattern-based extraction');
        
        // Look for "History Taking", "Physical Examination", "Diagnostic Accuracy", etc.
        const medicalDomains = [
          { pattern: /history.{0,20}taking/i, name: 'History Taking', points: 27 },
          { pattern: /physical.{0,20}exam/i, name: 'Physical Examination', points: 11 },
          { pattern: /diagnostic.{0,20}accuracy/i, name: 'Diagnostic Accuracy', points: 9 },
          { pattern: /diagnostic.{0,20}reasoning/i, name: 'Diagnostic Reasoning', points: 5 },
          { pattern: /management/i, name: 'Management', points: 4 }
        ];
        
        const textContent = extracted_text.toLowerCase();
        
        medicalDomains.forEach(domain => {
          if (domain.pattern.test(textContent)) {
            const examId = domain.name.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_');
            examsList.push(examId);
            
            // Extract examples for this domain
            let examples = [];
            if (domain.name.toLowerCase().includes('history')) {
              examples = [
                "Can you tell me about your symptoms?",
                "When did this start?",
                "What makes it better or worse?",
                "Do you have any allergies?",
                "What medications are you taking?",
                "Any family history of this condition?"
              ];
            } else if (domain.name.toLowerCase().includes('physical')) {
              examples = [
                "I'm going to examine you now",
                "I'm going to listen to your heart",
                "I'm going to check your blood pressure",
                "Let me examine your abdomen",
                "I'm going to test your reflexes"
              ];
            } else if (domain.name.toLowerCase().includes('diagnostic')) {
              examples = [
                "Based on your symptoms and examination",
                "The most likely diagnosis is",
                "I need to consider several possibilities",
                "The findings suggest",
                "This is consistent with"
              ];
            } else if (domain.name.toLowerCase().includes('management')) {
              examples = [
                "I recommend",
                "We should follow up",
                "You should take",
                "I'm going to refer you to",
                "The treatment plan includes"
              ];
            }
            
            criteria.push({
              examId: examId,
              name: domain.name,
              max_points: domain.points,
              examples: examples
            });
          }
        });
      }
    }

    // Default criteria if still nothing found
    if (criteria.length === 0) {
      console.log('No criteria found, using comprehensive medical defaults');
      const defaultCriteria = [
        {
          name: "History Taking",
          points: 27,
          examples: [
            "Can you tell me about your symptoms?",
            "When did this start?",
            "What makes it better or worse?",
            "Do you have any allergies?",
            "What medications are you taking?"
          ]
        },
        {
          name: "Physical Examination", 
          points: 11,
          examples: [
            "I'm going to examine you now",
            "I'm going to listen to your heart",
            "I'm going to check your blood pressure",
            "Let me examine your abdomen"
          ]
        },
        {
          name: "Diagnostic Accuracy",
          points: 9,
          examples: [
            "Based on your symptoms and examination",
            "The most likely diagnosis is",
            "I need to consider several possibilities"
          ]
        },
        {
          name: "Diagnostic Reasoning",
          points: 5,
          examples: [
            "The reason I think this is",
            "This diagnosis fits because",
            "The evidence includes"
          ]
        },
        {
          name: "Management",
          points: 4,
          examples: [
            "I recommend",
            "The treatment includes",
            "We should follow up"
          ]
        }
      ];
      
      defaultCriteria.forEach(criterion => {
        const examId = criterion.name.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_');
        examsList.push(examId);
        criteria.push({
          examId: examId,
          name: criterion.name,
          max_points: criterion.points,
          examples: criterion.examples
        });
      });
    }

    console.log(`Generated ${criteria.length} criteria:`, criteria.map(c => c.name));

    // Generate the YAML content in the exact format of abdominal_pain.yaml
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

    // Create parsed structure for the dashboard
    const parsedYaml = {
      system_message: "You are a helpful assistant tasked with analyzing and scoring a recorded medical examination between a medical student and a patient. Provide your response in JSON format.",
      user_message: `Your task is to identify the start and end times of specific physical exams within the conversation...`,
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
      validation_success: true
    });

  } catch (error) {
    console.error('Prompt generation failed:', error);
    res.status(500).json({ 
      error: `Failed to generate prompt: ${error.message}` 
    });
  }
} 