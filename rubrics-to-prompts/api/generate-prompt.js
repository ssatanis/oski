import { LearningRubricAnalyzer } from './lib/learning-rubric-analyzer.js';
import fetch from 'node-fetch';

export const config = {
  api: {
    maxDuration: 60,
  },
};

// Initialize the learning analyzer
const rubricAnalyzer = new LearningRubricAnalyzer();

// Azure OpenAI configuration
const AZURE_OPENAI_ENDPOINT = process.env.AZURE_OPENAI_ENDPOINT;
const AZURE_OPENAI_KEY = process.env.AZURE_OPENAI_KEY;
const AZURE_OPENAI_DEPLOYMENT_NAME = process.env.AZURE_OPENAI_DEPLOYMENT_NAME;

async function callAzureOpenAI(prompt, maxTokens = 4000) {
  if (!AZURE_OPENAI_KEY || !AZURE_OPENAI_ENDPOINT) {
    console.log('Azure OpenAI not configured, using pattern-based analysis only');
    return null;
  }
  
  const url = `${AZURE_OPENAI_ENDPOINT}/openai/deployments/${AZURE_OPENAI_DEPLOYMENT_NAME}/chat/completions?api-version=2024-02-01`;
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'api-key': AZURE_OPENAI_KEY
      },
      body: JSON.stringify({
        messages: [
          {
            role: 'system',
            content: 'You are an expert at understanding and analyzing assessment rubrics from various fields. You excel at extracting structured information from unstructured documents.'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        max_tokens: maxTokens,
        temperature: 0.1,
        response_format: { type: "json_object" }
      })
    });
    
    if (!response.ok) {
      const error = await response.text();
      console.error('Azure OpenAI error:', error);
      return null;
    }
    
    const data = await response.json();
    return data.choices[0].message.content;
  } catch (error) {
    console.error('Azure OpenAI call failed:', error);
    return null;
  }
}

async function enhanceWithAzureAI(rubricAnalysis, originalText, structuredContent) {
  const prompt = `Analyze this rubric and extract ALL sections, criteria, and scoring information.

${structuredContent ? 'Structured Content:\n' + JSON.stringify(structuredContent, null, 2).substring(0, 3000) : ''}

Original Text (first 3000 chars):
${originalText.substring(0, 3000)}

Current Analysis:
${JSON.stringify(rubricAnalysis, null, 2)}

IMPORTANT: 
1. Extract EVERY section and subsection exactly as they appear in the rubric
2. Preserve ALL point values accurately
3. Maintain the exact hierarchy and structure
4. Do NOT assume standard sections - extract what's actually there
5. Include all evaluation criteria and sub-items

Return a JSON object with this EXACT structure:
{
  "sections": [
    {
      "name": "Exact section name from rubric",
      "maxPoints": 0,
      "items": [
        {
          "description": "Exact item description",
          "points": 0,
          "examples": ["Relevant example 1", "Example 2"],
          "criteria": ["Specific evaluation criterion"]
        }
      ]
    }
  ],
  "totalPoints": 0,
  "metadata": {
    "rubricType": "Type of assessment",
    "additionalInfo": "Any other relevant information"
  }
}`;

  const aiResponse = await callAzureOpenAI(prompt);
  
  if (aiResponse) {
    try {
      const enhanced = JSON.parse(aiResponse);
      // Merge AI insights with pattern-based analysis
      return mergeAnalyses(rubricAnalysis, enhanced);
    } catch (error) {
      console.error('Failed to parse AI response:', error);
    }
  }
  
  return rubricAnalysis;
}

function mergeAnalyses(patternAnalysis, aiAnalysis) {
  // Combine the best of both analyses
  const merged = {
    sections: [],
    totalPoints: 0,
    metadata: {
      ...patternAnalysis.metadata,
      ...aiAnalysis.metadata,
      enhanced: true
    }
  };
  
  // Create a map of sections from both analyses
  const sectionMap = new Map();
  
  // Add pattern-based sections
  patternAnalysis.sections.forEach(section => {
    sectionMap.set(section.name.toLowerCase(), section);
  });
  
  // Merge or add AI sections
  if (aiAnalysis.sections) {
    aiAnalysis.sections.forEach(aiSection => {
      const key = aiSection.name.toLowerCase();
      if (sectionMap.has(key)) {
        // Merge items
        const existing = sectionMap.get(key);
        existing.items = mergeItems(existing.items, aiSection.items);
        existing.maxPoints = Math.max(existing.maxPoints, aiSection.maxPoints || 0);
      } else {
        // Add new section
        sectionMap.set(key, aiSection);
      }
    });
  }
  
  merged.sections = Array.from(sectionMap.values());
  merged.totalPoints = Math.max(patternAnalysis.totalPoints, aiAnalysis.totalPoints || 0);
  
  return merged;
}

function mergeItems(patternItems, aiItems) {
  const itemMap = new Map();
  
  // Add pattern items
  patternItems.forEach(item => {
    itemMap.set(item.description.toLowerCase(), item);
  });
  
  // Merge AI items
  aiItems.forEach(aiItem => {
    const key = aiItem.description.toLowerCase();
    if (itemMap.has(key)) {
      // Update with AI enhancements
      const existing = itemMap.get(key);
      if (aiItem.examples && aiItem.examples.length > existing.examples.length) {
        existing.examples = aiItem.examples;
      }
      if (aiItem.points && !existing.points) {
        existing.points = aiItem.points;
      }
    } else {
      // Add new item
      itemMap.set(key, aiItem);
    }
  });
  
  return Array.from(itemMap.values());
}

function convertToYAMLStructure(analysis, filename = '') {
  const criteria = [];
  
  // Convert sections to criteria
  analysis.sections.forEach(section => {
    const sectionId = section.name.replace(/[^\w]/g, '_').replace(/_+/g, '_');
    
    if (!section.items || section.items.length === 0) {
      // Section without items
      criteria.push({
        id: sectionId,
        name: section.name,
        description: `Assessment of ${section.name}`,
        max_points: section.maxPoints || 1,
        examples: rubricAnalyzer.generateExamplesFromTraining(section.name)
      });
    } else {
      // Create criteria for each item
      section.items.forEach((item, index) => {
        const itemId = `${sectionId}_${index + 1}`;
        criteria.push({
          id: itemId,
          name: `${section.name}: ${item.description}`,
          description: item.description,
          max_points: item.points || 1,
          examples: item.examples.length > 0 ? 
            item.examples : 
            rubricAnalyzer.generateExamplesFromTraining(section.name),
          section: section.name
        });
      });
    }
  });
  
  // Build comprehensive user message preamble
  const sectionSummary = analysis.sections.map(s => 
    `- ${s.name}: ${s.maxPoints || 'Variable'} points`
  ).join('\n');
  
  return {
    system_message: `You are a helpful assistant tasked with analyzing and scoring a recorded examination or assessment. This evaluation covers multiple criteria across different sections. Provide your response in JSON format with specific timestamps and rationales for each score.`,
    
    user_message_preamble: `Your task is to evaluate performance based on the following rubric with ${analysis.totalPoints} total possible points.

Assessment Sections:
${sectionSummary}

For each criterion below, identify specific moments in the transcript where it is demonstrated, provide timestamps, and score according to the rubric's point values.`,
    
    criteria: criteria,
    
    formatting_instructions: `- Ensure strict adherence to JSON formatting
- Identify specific timestamps where each criterion is demonstrated
- Provide clear rationale for each score based on the rubric
- Score according to the exact point values specified
- If a criterion is not demonstrated, score 0 with explanation
- Return ONLY the JSON response without any additional text`,
    
    response_schema: generateResponseSchema(criteria)
  };
}

function generateResponseSchema(criteria) {
  const properties = {};
  const required = [];
  
  criteria.forEach(criterion => {
    properties[criterion.id] = {
      type: "object",
      properties: {
        statement: { 
          type: "string", 
          description: "Direct quote or specific action from the transcript/recording" 
        },
        start_time: { 
          type: "string", 
          pattern: "^\\d{2}:\\d{2}$", 
          description: "Start timestamp (MM:SS)" 
        },
        end_time: { 
          type: "string", 
          pattern: "^\\d{2}:\\d{2}$", 
          description: "End timestamp (MM:SS)" 
        },
        rationale: { 
          type: "string", 
          description: "Detailed explanation for the score given" 
        },
        score: { 
          type: "integer", 
          minimum: 0, 
          maximum: criterion.max_points,
          description: `Score out of ${criterion.max_points} points` 
        }
      },
      required: ["statement", "start_time", "end_time", "rationale", "score"]
    };
    required.push(criterion.id);
  });
  
  return {
    type: "object",
    properties: properties,
    required: required,
    additionalProperties: false
  };
}

function formatYAMLContent(yamlStructure) {
  const { system_message, user_message_preamble, criteria, formatting_instructions, response_schema } = yamlStructure;
  
  // Group criteria by section for better organization
  const sections = {};
  criteria.forEach(c => {
    const section = c.section || 'General';
    if (!sections[section]) sections[section] = [];
    sections[section].push(c);
  });
  
  // Build criteria YAML with section organization
  let criteriaYAML = 'criteria:\n';
  Object.entries(sections).forEach(([sectionName, sectionCriteria]) => {
    criteriaYAML += `  # ${sectionName}\n`;
    sectionCriteria.forEach(c => {
      const examplesYAML = c.examples.map(ex => `      - "${ex}"`).join('\n');
      criteriaYAML += `  - id: "${c.id}"
    name: "${c.name}"
    description: "${c.description}"
    max_points: ${c.max_points}
    examples:
${examplesYAML}
`;
    });
  });
  
  return `system_message: |
  ${system_message.split('\n').map(line => '  ' + line).join('\n')}

user_message_preamble: |
  ${user_message_preamble.split('\n').map(line => '  ' + line).join('\n')}

${criteriaYAML}
formatting_instructions: |
  ${formatting_instructions.split('\n').map(line => '  ' + line).join('\n')}

response_schema: ${JSON.stringify(response_schema, null, 2)}`;
}

// Vercel Serverless Function for YAML Generation
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
        examples: Array.isArray(criterion.examples) ? criterion.examples : [criterion.examples || ''].filter(Boolean)
      }));
      examsList = criteria.map(c => c.examId);
    } else {
      // Generate criteria from extracted text (initial processing)
      console.log('Generating criteria from extracted text');
      
      // Simple keyword-based extraction
      const keywords = {
        'history': { name: 'History Taking', points: 5 },
        'examination': { name: 'Physical Examination', points: 7 },
        'communication': { name: 'Communication Skills', points: 3 },
        'diagnosis': { name: 'Clinical Reasoning', points: 4 },
        'safety': { name: 'Patient Safety', points: 2 }
      };
      
      const lowerText = extracted_text.toLowerCase();
      const foundCriteria = new Set();
      
      for (const [keyword, criterion] of Object.entries(keywords)) {
        if (lowerText.includes(keyword) && !foundCriteria.has(criterion.name)) {
          const examId = criterion.name.replace(/\s+/g, '_');
          criteria.push({
            examId: examId,
            name: criterion.name,
            max_points: criterion.points,
            examples: [`I will now perform ${criterion.name.toLowerCase()}`]
          });
          examsList.push(examId);
          foundCriteria.add(criterion.name);
        }
      }
      
      // Default criteria if none found
      if (criteria.length === 0) {
        criteria = [
          { examId: 'History_Taking', name: 'History Taking', max_points: 5, examples: ['Tell me about your symptoms'] },
          { examId: 'Physical_Examination', name: 'Physical Examination', max_points: 7, examples: ['I will examine you now'] },
          { examId: 'Communication', name: 'Communication', max_points: 3, examples: ['Do you have questions?'] }
        ];
        examsList = criteria.map(c => c.examId);
      }
    }

    // Generate YAML content
    let yamlContent = `# OSCE Assessment Rubric
# Generated from: ${filename || 'manual_input'}
# Date: ${new Date().toISOString()}

system_message: |
  You are a helpful assistant tasked with analyzing and scoring a recorded medical examination between a medical student and a patient. Provide your response in JSON format.

user_message: |
  Your task is to identify the start and end times of specific physical exams within the conversation and provide the reasoning behind your choices.
  This station consists of the following physical exams: ${examsList.join(', ')}
  
  You need to identify the following physical exams from this transcript:
${criteria.map((c, i) => `    ${i + 1}. ${c.examId}: Did the doctor perform ${c.name.toLowerCase()}?
       - Verbalization examples: ${c.examples.join(', ')}`).join('\n')}

response_config:
  structured_output: true
  format: json
  schema:
    type: object
    properties:
${criteria.map(c => `      ${c.examId}:
        type: object
        properties:
          performed: 
            type: boolean
          start_time: 
            type: string
          end_time: 
            type: string
          score: 
            type: integer
            minimum: 0
            maximum: ${c.max_points}
          reasoning: 
            type: string`).join('\n')}

assessment_config:
  type: "medical_osce_assessment"
  version: "2.0"
  generated_at: "${new Date().toISOString()}"
  source_file: "${filename || 'manual_input'}"
  criteria_count: ${criteria.length}
  total_points: ${criteria.reduce((sum, c) => sum + c.max_points, 0)}

assessment_criteria:
${criteria.map((c, i) => `  - id: "criterion_${i + 1}"
    name: "${c.name}"
    code: "${c.examId.toUpperCase()}"
    description: "Comprehensive assessment of ${c.name.toLowerCase()} skills and techniques"
    max_points: ${c.max_points}
    assessment_items:
      - "Performed ${c.name.toLowerCase()} systematically and thoroughly"
      - "Used appropriate techniques and tools"
      - "Maintained patient comfort and dignity"
      - "Communicated findings clearly"
    scoring:
      excellent: ${c.max_points}
      good: ${Math.floor(c.max_points * 0.8)}
      satisfactory: ${Math.floor(c.max_points * 0.6)}
      needs_improvement: ${Math.floor(c.max_points * 0.3)}
      unsatisfactory: 0
    time_limit: "${c.max_points * 2} minutes"
    format: "performance_based"
    verbalization_examples:
${c.examples.map(ex => `      - "${ex}"`).join('\n')}`).join('\n')}

verbalization_examples:
  introduction:
    - "Hello, I'm Dr. [Name], a medical student"
    - "I'll be conducting your examination today"
    - "Please let me know if you feel any discomfort"
  
  general_examination:
${criteria.flatMap(c => c.examples.map(ex => `    - "${ex}"`)).join('\n')}
  
  closing:
    - "Thank you for your cooperation"
    - "Do you have any questions for me?"
    - "I'll discuss my findings with my supervisor"

assessment_instructions: |
  1. Review the transcript carefully for evidence of each assessment criterion
  2. Identify specific timestamps where each exam component begins and ends
  3. Score based on completeness, technique, and communication
  4. Provide clear reasoning for each score assigned
  5. Consider patient safety and comfort in your evaluation

output_format: |
  Return a JSON object with the following structure:
  {
    "assessment_results": {
      "[exam_id]": {
        "performed": boolean,
        "start_time": "MM:SS",
        "end_time": "MM:SS", 
        "score": integer (0-max_points),
        "reasoning": "Detailed explanation of score"
      }
    },
    "total_score": integer,
    "general_feedback": "Overall performance summary"
  }

quality_criteria:
  - accuracy: "Timestamps must be precise to the second"
  - completeness: "All criteria must be evaluated"
  - objectivity: "Scores based on observable behaviors only"
  - clarity: "Reasoning must be specific and evidence-based"`;

    // Return the YAML content
    res.status(200).json({
      yaml_content: yamlContent,
      parsed_yaml: {
        assessment_config: {
          criteria_count: criteria.length,
          total_points: criteria.reduce((sum, c) => sum + c.max_points, 0)
        }
      },
      validation_success: true
    });

  } catch (error) {
    console.error('YAML generation error:', error);
    res.status(500).json({ 
      error: 'Failed to generate YAML',
      details: error.message 
    });
  }
}