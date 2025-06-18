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
  console.log('Using basic criteria extraction as fallback');
  
  const criteria = [];
  const lines = extracted_text.split('\n').filter(line => line.trim());
  
  // Look for common medical examination patterns
  const medicalPatterns = [
    { pattern: /history.{0,20}taking/i, name: 'History Taking', points: 25 },
    { pattern: /physical.{0,20}exam/i, name: 'Physical Examination', points: 15 },
    { pattern: /diagnostic.{0,20}accuracy/i, name: 'Diagnostic Accuracy', points: 10 },
    { pattern: /diagnostic.{0,20}reasoning/i, name: 'Diagnostic Reasoning', points: 8 },
    { pattern: /management/i, name: 'Management', points: 5 },
    { pattern: /abdomen/i, name: 'Abdominal Examination', points: 8 },
    { pattern: /heart|cardiac/i, name: 'Cardiovascular Examination', points: 8 },
    { pattern: /lung|respiratory/i, name: 'Respiratory Examination', points: 8 },
    { pattern: /skin|rash/i, name: 'Skin Examination', points: 6 },
    { pattern: /neuro/i, name: 'Neurological Examination', points: 10 }
  ];
  
  const textContent = extracted_text.toLowerCase();
  
  for (const pattern of medicalPatterns) {
    if (pattern.pattern.test(textContent)) {
      const examId = pattern.name.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_');
      
      let examples = [];
      if (pattern.name.toLowerCase().includes('history')) {
        examples = [
          "Can you tell me about your symptoms?",
          "When did this start?",
          "What makes it better or worse?",
          "Do you have any allergies?"
        ];
      } else if (pattern.name.toLowerCase().includes('physical')) {
        examples = [
          "I'm going to examine you now",
          "I'm going to listen to your heart",
          "I'm going to check your blood pressure"
        ];
      } else if (pattern.name.toLowerCase().includes('diagnostic')) {
        examples = [
          "Based on your symptoms and examination",
          "The most likely diagnosis is",
          "I need to consider several possibilities"
        ];
      } else if (pattern.name.toLowerCase().includes('management')) {
        examples = [
          "I recommend",
          "The treatment includes",
          "We should follow up"
        ];
      } else {
        examples = [`I'm going to examine your ${pattern.name.toLowerCase()}`];
      }
      
      criteria.push({
        examId: examId,
        name: pattern.name,
        max_points: pattern.points,
        examples: examples
      });
    }
  }
  
  // If no patterns found, use generic defaults
  if (criteria.length === 0) {
    criteria.push(
      {
        examId: 'Patient_History',
        name: 'Patient History',
        max_points: 5,
        examples: ["Can you tell me about your symptoms?", "What brings you in today?"]
      },
      {
        examId: 'Physical_Examination',
        name: 'Physical Examination',
        max_points: 4,
        examples: ["I'm going to examine you now", "Let me check your vital signs"]
      }
    );
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