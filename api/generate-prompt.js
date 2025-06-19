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

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { extracted_text, structured_content, dashboard_criteria } = req.body;
    
    if (dashboard_criteria) {
      // Generate YAML from dashboard edits
      const yamlContent = formatYAMLContent(dashboard_criteria);
      return res.status(200).json({
        yaml_content: yamlContent,
        parsed_yaml: dashboard_criteria,
        success: true
      });
    }
    
    if (!structured_content && !extracted_text) {
      return res.status(400).json({ error: 'No content provided for analysis' });
    }
    
    console.log('Starting dynamic rubric analysis with learning...');
    
    // Use structured content if available
    const contentToAnalyze = structured_content || { rawText: extracted_text };
    
    // Perform pattern-based analysis with learning
    let rubricAnalysis = await rubricAnalyzer.analyzeWithPatterns(contentToAnalyze);
    
    // Enhance with Azure OpenAI if available
    const enhancedAnalysis = await enhanceWithAzureAI(
      rubricAnalysis, 
      extracted_text || contentToAnalyze.rawText,
      structured_content
    );
    
    // Convert to YAML structure
    const yamlStructure = convertToYAMLStructure(
      enhancedAnalysis, 
      contentToAnalyze.metadata?.fileName
    );
    
    // Generate formatted YAML
    const yamlContent = formatYAMLContent(yamlStructure);
    
    res.status(200).json({
      yaml_content: yamlContent,
      parsed_yaml: yamlStructure,
      rubric_analysis: enhancedAnalysis,
      success: true
    });
    
  } catch (error) {
    console.error('Generate prompt error:', error);
    res.status(500).json({ 
      error: 'Failed to generate prompt',
      details: error.message 
    });
  }
}