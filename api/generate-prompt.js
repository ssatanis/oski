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

    // Parse the extracted text to identify criteria and generate proper YAML
    const lines = extracted_text.split('\n').filter(line => line.trim());
    const criteria = [];
    let stationName = 'OSCE_Assessment';
    let examsList = [];

    // Extract station/title name if present
    const titleLine = lines.find(line => 
      line.toLowerCase().includes('station') || 
      line.toLowerCase().includes('assessment') ||
      line.toLowerCase().includes('osce') ||
      line.toLowerCase().includes('examination') ||
      line.toLowerCase().includes('rubric')
    );
    if (titleLine) {
      stationName = titleLine.trim().replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_');
    }

    // Extract criteria and create exam names
    lines.forEach((line, index) => {
      // Look for criteria patterns
      const criteriaMatch = line.match(/^(?:Criteria?\s*\d+:|^\d+[:.]?\s*)(.*?)(?:\((\d+)-(\d+)\s*points?\)|\((\d+)\s*points?\))?/i);
      if (criteriaMatch) {
        const name = criteriaMatch[1].trim();
        const maxPoints = criteriaMatch[4] || criteriaMatch[3] || 1;
        
        // Look for examples in following lines
        const examples = [];
        for (let i = index + 1; i < Math.min(index + 10, lines.length); i++) {
          const nextLine = lines[i];
          if (nextLine.includes('point') && nextLine.includes(':')) {
            examples.push(nextLine.replace(/^\d+\s*points?:\s*/i, '').trim());
          } else if (nextLine.match(/^(?:Criteria?\s*\d+:|^\d+[:.]?\s*)/i)) {
            break; // Hit next criteria
          } else if (nextLine.trim().startsWith('-') || nextLine.trim().startsWith('•')) {
            examples.push(nextLine.replace(/^[-•]\s*/, '').trim());
          }
        }

        // Create exam ID from criterion name
        const examId = name.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_');
        examsList.push(examId);

        criteria.push({
          examId: examId,
          name: name,
          max_points: parseInt(maxPoints),
          examples: examples.length > 0 ? examples : [
            `I'm going to examine your ${name.toLowerCase()}`,
            `Let me check your ${name.toLowerCase()}`,
            `I'm going to assess your ${name.toLowerCase()}`
          ]
        });
      }
    });

    // If no criteria found, try to extract from different patterns
    if (criteria.length === 0) {
      // Look for bullet points or numbered lists
      lines.forEach((line, index) => {
        const bulletMatch = line.match(/^[-•]\s*(.+)/);
        const numberedMatch = line.match(/^\d+\.\s*(.+)/);
        
        if (bulletMatch || numberedMatch) {
          const name = (bulletMatch?.[1] || numberedMatch?.[1] || '').trim();
          if (name && name.length > 5) { // Reasonable length check
            const examId = name.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_');
            examsList.push(examId);
            
            criteria.push({
              examId: examId,
              name: name,
              max_points: 1,
              examples: [
                `I'm going to examine your ${name.toLowerCase()}`,
                `Let me check your ${name.toLowerCase()}`,
                `I'm going to assess your ${name.toLowerCase()}`
              ]
            });
          }
        }
      });
    }

    // Default criteria if still nothing found
    if (criteria.length === 0) {
      criteria.push(
        {
          examId: "Patient_Greeting",
          name: "Patient Greeting and Introduction",
          max_points: 1,
          examples: [
            "Hello, I'm Dr. Smith",
            "Good morning, I'm a medical student",
            "Hi, I'll be examining you today"
          ]
        },
        {
          examId: "Physical_Examination", 
          name: "Physical Examination",
          max_points: 1,
          examples: [
            "I'm going to examine you now",
            "Let me check your vital signs",
            "I'm going to listen to your heart"
          ]
        }
      );
      examsList = ["Patient_Greeting", "Physical_Examination"];
    }

    // Generate the YAML content in the exact format of abdominal_pain.yaml
    const yamlContent = `system_message: 
   You are a helpful assistant tasked with analyzing and scoring a recorded medical examination between a medical student and a patient. Provide your response in JSON format.
   
user_message: 
  |
   
   Your task is to identify the start and end times of specific physical exams within the conversation and provide the reasoning behind your choices. Whenever the medical student asks about pain or mentions checking a specific part of the body (e.g., "any pain when I do this?" or "let me check your..."), assume that a physical exam is being conducted at that moment. You will be provided with a description and example for each exam. This station consists of the following physical exams: ${examsList.join(', ')}
   
   Important Instructions:
   - When determining the start and end times of each examination, focus on the moments where the doctor instructs the patient to perform an action (e.g., "look up at the ceiling", "look straight ahead"). Give these phrases priority for setting the \`start_time\` and \`end_time\` over phrases where the doctor states their own actions (e.g., "I'm going to look at your nose and eyes").
   - Whenever the medical student asks about pain or mentions checking a specific part of the body (e.g., "any pain when I do this?" or "let me check your..."), assume that a physical exam is being conducted at that moment. You will be provided with a description and example for each exam.
   - Always pay close attention to surrounding context and related physical examinations mentioned.
      
   You need to identify the following physical exams from this transcript: 
${criteria.map((criterion, index) => `   	 ${index + 1}. ${criterion.examId}: Did the doctor ${criterion.name.toLowerCase().includes('did') ? criterion.name.toLowerCase() : `perform ${criterion.name.toLowerCase()}`}? 
   	 - Verbalization examples: ${criterion.examples.join(', ')}`).join('\n\n')}
   
   
   If no exam is detected, you can say "no exam was performed", start_time: "nan", end_time: "nan", score: 0.
   
   ### Formatting Instructions
   
   - Ensure strict adherence to JSON formatting.
   - Do not use double quotes for multiple statements within a single field.
   - Use commas, single quotes, or other appropriate delimiters for multiple statements.
   - Do not include any text before or after the JSON output. Provide ONLY the json response.
   
   Please provide a response in the following format with keys: ${examsList.join(', ')}
   
   and the schema: 
   {
        "statement": "statement extracted from the transcript that supports this specific exam",
        "start_time": "timepoint for start of the exam (MM:SS only)",
        "end_time": "timepoint for end of the exam (MM:SS only)",
        "rationale": "reasoning behind scoring the physical exam",
        "score": "score of the exam (0 or 1)"
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