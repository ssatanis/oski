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

    // Demo AI processing - generates structured YAML from rubric text
    // In production, this would call Azure OpenAI API
    const demoYamlContent = `rubric_info:
  title: "OSCE Assessment Rubric"
  description: "Structured rubric for clinical assessment"
  total_points: 10
  format: "structured_assessment"

criteria:
  - criterion_id: "greeting_introduction"
    name: "Patient Greeting and Introduction"
    description: "Assessment of professional greeting and self-introduction"
    max_points: 2
    scale:
      - score: 0
        description: "No greeting or introduction"
        indicators:
          - "Student does not acknowledge patient"
          - "No verbal greeting provided"
      - score: 1
        description: "Basic greeting only"
        indicators:
          - "Simple hello or similar greeting"
          - "Minimal interaction"
      - score: 2
        description: "Professional greeting with name and role introduction"
        indicators:
          - "Clear introduction with name"
          - "States role (medical student, etc.)"
          - "Professional demeanor"

  - criterion_id: "history_taking"
    name: "History Taking"
    description: "Systematic gathering of patient history"
    max_points: 3
    scale:
      - score: 0
        description: "No relevant history obtained"
        indicators:
          - "No questions asked"
          - "Does not gather patient information"
      - score: 1
        description: "Limited history with major gaps"
        indicators:
          - "Few relevant questions"
          - "Important details missed"
      - score: 2
        description: "Adequate history with minor gaps"
        indicators:
          - "Covers main presenting complaint"
          - "Some systematic approach"
      - score: 3
        description: "Comprehensive and systematic history"
        indicators:
          - "Systematic questioning"
          - "Covers all relevant areas"
          - "Appropriate follow-up questions"

assessment_guidelines:
  - "Observe actual behavior and communication"
  - "Look for specific indicators of each score level"
  - "Consider context and patient interaction quality"
  - "Document specific examples when possible"`;

    const parsedYaml = {
      rubric_info: {
        title: "OSCE Assessment Rubric",
        description: "Structured rubric for clinical assessment",
        total_points: 10,
        format: "structured_assessment"
      },
      criteria: [
        {
          criterion_id: "greeting_introduction",
          name: "Patient Greeting and Introduction",
          description: "Assessment of professional greeting and self-introduction",
          max_points: 2
        },
        {
          criterion_id: "history_taking",
          name: "History Taking",
          description: "Systematic gathering of patient history", 
          max_points: 3
        }
      ]
    };

    const jsonContent = JSON.stringify(parsedYaml, null, 2);

    res.status(200).json({
      message: 'Prompt generated successfully',
      yaml_content: demoYamlContent,
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