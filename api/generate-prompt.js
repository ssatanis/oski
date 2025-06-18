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
    let rubricTitle = 'OSCE Assessment Rubric';
    let totalPoints = 0;

    // Extract rubric title if present
    const titleLine = lines.find(line => 
      line.toLowerCase().includes('rubric') || 
      line.toLowerCase().includes('assessment') ||
      line.toLowerCase().includes('osce')
    );
    if (titleLine) {
      rubricTitle = titleLine.trim();
    }

    // Extract criteria from the text
    lines.forEach((line, index) => {
      const criteriaMatch = line.match(/^(?:Criteria?\s*\d+:|^\d+[:.]?\s*)(.*?)(?:\((\d+)-(\d+)\s*points?\)|\((\d+)\s*points?\))?/i);
      if (criteriaMatch) {
        const name = criteriaMatch[1].trim();
        const maxPoints = criteriaMatch[4] || criteriaMatch[3] || 2; // Default to 2 points
        totalPoints += parseInt(maxPoints);
        
        // Look for examples in following lines
        const examples = [];
        for (let i = index + 1; i < Math.min(index + 5, lines.length); i++) {
          const nextLine = lines[i];
          if (nextLine.includes('point') && nextLine.includes(':')) {
            examples.push(nextLine.trim());
          } else if (nextLine.match(/^(?:Criteria?\s*\d+:|^\d+[:.]?\s*)/i)) {
            break; // Hit next criteria
          }
        }

        criteria.push({
          name: name,
          max_points: parseInt(maxPoints),
          examples: examples
        });
      }
    });

    // If no criteria found, create default ones
    if (criteria.length === 0) {
      criteria.push(
        {
          name: "Patient Greeting and Introduction",
          max_points: 2,
          examples: [
            "0 points: No greeting or introduction",
            "1 point: Basic greeting only", 
            "2 points: Professional greeting with name and role introduction"
          ]
        },
        {
          name: "Clinical Assessment",
          max_points: 3,
          examples: [
            "0 points: No assessment performed",
            "1 point: Limited assessment with major gaps",
            "2 points: Adequate assessment with minor gaps",
            "3 points: Comprehensive and systematic assessment"
          ]
        }
      );
      totalPoints = 5;
    }

    // Generate the YAML content in the format of 1A.yaml
    const yamlContent = `key: 
  ${rubricTitle.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase()}
system_message: 
  |
   You are a helpful assistant tasked with analyzing and scoring a recorded medical examination between a medical student and a patient. Provide your response in JSON format.
   
user_message: 
  |   
   Important Instruction:
   When determining the start and end times of each examination, focus on the moments where the doctor instructs the patient to perform an action (e.g., "look up at the ceiling", "look straight ahead"). Give these phrases priority for setting the \`start_time\` and \`end_time\` over phrases where the doctor states their own actions (e.g., "I'm going to examine your...").
      
   You need to identify the following examinations from this conversation: 
${criteria.map((criterion, index) => `   ${index + 1}: ${criterion.name.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_')}: Did the doctor perform ${criterion.name.toLowerCase()}? 
    - Examples: 
${criterion.examples.map(example => `    	 - ${example.replace(/^\d+\s*points?:\s*/i, '')}`).join('\n')}
`).join('\n')}   
   
   If there is any part in the conversation where the medical student is performing an examination but you cannot tell what specific type it is, look at the conversation before and after to find what type of exam that was. Pay close attention to surrounding context and related examinations mentioned.
   
   If no exam is detected, you can say "No exam was performed", start_time: "nan", end_time: "nan", score: 0.
        
   # Formatting instructions
   
   - Ensure strict adherence to JSON formatting.
   - Do not use double quotes for multiple statements within a single field.
   - Use commas, single quotes, or other appropriate delimiters for multiple statements.
   - Do not include any text before or after the JSON output. Provide ONLY the json response.
   
   Please provide a response in the following format with keys: ${criteria.map(criterion => criterion.name.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_')).join(', ')}
   
   and the schema: 
   {
        "statement": "statement extracted from the conversation that supports this specific exam",
        "start_time": "timepoint for start of the exam (ONLY 1 decimal pt)",
        "end_time": "timepoint for end of the exam (ONLY 1 decimal pt)",
        "rationale": "reasoning behind scoring the examination",
        "score": "score of the exam (0-${Math.max(...criteria.map(c => c.max_points))})"
   }
response_config:
  structured_output: True`;

    // Create parsed structure for the dashboard
    const parsedYaml = {
      key: rubricTitle.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase(),
      system_message: "You are a helpful assistant tasked with analyzing and scoring a recorded medical examination between a medical student and a patient. Provide your response in JSON format.",
      user_message: "Analysis instructions for medical examination assessment",
      criteria: criteria,
      total_points: totalPoints,
      response_config: {
        structured_output: true
      }
    };

    const jsonContent = JSON.stringify(parsedYaml, null, 2);

    res.status(200).json({
      message: 'Prompt generated successfully',
      yaml_content: yamlContent,
      json_content: jsonContent,
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