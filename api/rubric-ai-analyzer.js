export class RubricAI {
    constructor() {
      this.medicalPatterns = this.buildMedicalPatterns();
    }
  
    buildMedicalPatterns() {
      return [
        {
          name: 'Physical Examination',
          keywords: ['physical', 'exam', 'examination', 'inspect', 'palpate', 'skin', 'observe'],
          examples: [
            "I'm going to perform this examination now",
            "Let me examine this area",
            "I'll check your skin",
            "Please let me know if you feel any discomfort"
          ]
        },
        {
          name: 'Respiratory Evaluation',
          keywords: ['respiratory', 'breathing', 'lungs', 'chest', 'auscultation', 'breath'],
          examples: [
            "I'm going to listen to your heart and lungs",
            "Please take a deep breath",
            "Let me check your breathing",
            "Any shortness of breath?"
          ]
        },
        {
          name: 'Musculoskeletal Assessment',
          keywords: ['musculoskeletal', 'muscle', 'joint', 'movement', 'range', 'motion', 'strength'],
          examples: [
            "I'm going to check your range of motion",
            "Can you move your arm like this?",
            "Let me test your muscle strength",
            "Any joint pain or stiffness?"
          ]
        },
        {
          name: 'Abdominal Examination',
          keywords: ['abdominal', 'abdomen', 'stomach', 'belly', 'digestive', 'palpation'],
          examples: [
            "I'm going to examine your abdomen",
            "Let me feel this area",
            "Any pain or tenderness here?",
            "I'll check for any abnormalities"
          ]
        },
        {
          name: 'Cardiovascular Assessment',
          keywords: ['cardiovascular', 'heart', 'cardiac', 'pulse', 'blood pressure', 'circulation'],
          examples: [
            "Let me check your pulse",
            "I'll listen to your heart",
            "Any chest pain or palpitations?",
            "I'm going to check your blood pressure"
          ]
        },
        {
          name: 'Neurological Examination',
          keywords: ['neurological', 'neuro', 'reflex', 'sensation', 'coordination', 'mental'],
          examples: [
            "I'm going to test your reflexes",
            "Can you follow my finger with your eyes?",
            "Let me check your coordination",
            "Any numbness or tingling?"
          ]
        }
      ];
    }
  
    async analyzeDocument(text) {
      const result = {
        criteria: [],
        system_message: '',
        user_message_preamble: '',
        formatting_instructions: ''
      };
  
      try {
        // Extract criteria using multiple strategies
        const patternCriteria = this.extractByPatterns(text);
        const structuredCriteria = this.extractStructuredCriteria(text);
        const tableCriteria = this.extractFromTableFormat(text);
        
        // Merge and deduplicate criteria
        const allCriteria = [...patternCriteria, ...structuredCriteria, ...tableCriteria];
        const uniqueCriteria = this.deduplicateCriteria(allCriteria);
        
        result.criteria = uniqueCriteria.length > 0 ? uniqueCriteria : this.generateDefaultCriteria(text);
        
        // Set system and user messages
        result.system_message = "You are a helpful assistant tasked with analyzing and scoring a recorded medical examination between a medical student and a patient. Provide your response in JSON format.";
        
        result.user_message_preamble = `Your task is to identify the start and end times of specific physical exams within the conversation and provide the reasoning behind your choices. Whenever the medical student asks about pain or mentions checking a specific part of the body (e.g., "any pain when I do this?" or "let me check your..."), assume that a physical exam is being conducted at that moment.`;
        
        result.formatting_instructions = `- Ensure strict adherence to JSON formatting.
  - Do not use double quotes for multiple statements within a single field.
  - Use commas, single quotes, or other appropriate delimiters for multiple statements.
  - Do not include any text before or after the JSON output.
  - Provide ONLY the json response.`;
        
      } catch (error) {
        console.error('Document analysis error:', error);
        result.criteria = this.generateDefaultCriteria(text);
      }
      
      return result;
    }
  
    extractByPatterns(text) {
      const criteria = [];
      const normalizedText = text.toLowerCase();
      
      this.medicalPatterns.forEach(pattern => {
        // Check if any keywords are present
        const hasKeyword = pattern.keywords.some(keyword => 
          normalizedText.includes(keyword.toLowerCase())
        );
        
        if (hasKeyword) {
          criteria.push({
            name: pattern.name,
            max_points: this.extractPoints(text, pattern.name) || 1,
            examples: pattern.examples,
            description: `Clinical assessment of ${pattern.name.toLowerCase()}`
          });
        }
      });
      
      return criteria;
    }
  
    extractStructuredCriteria(text) {
      const criteria = [];
      const lines = text.split('\n').map(line => line.trim()).filter(line => line);
      
      // Look for structured patterns like "1. Physical Examination - 5 points"
      const structuredPattern = /^(?:\d+\.?\s*)?([A-Za-z\s]+(?:Examination|Assessment|Evaluation|Test|Check))\s*[-:|\s]+\s*(\d+)\s*(?:points?|pts?)?/i;
      
      lines.forEach(line => {
        const match = line.match(structuredPattern);
        if (match) {
          const name = match[1].trim();
          const points = parseInt(match[2]) || 1;
          
          // Find matching pattern for examples
          const pattern = this.medicalPatterns.find(p => 
            p.name.toLowerCase() === name.toLowerCase() ||
            p.keywords.some(k => name.toLowerCase().includes(k))
          );
          
          criteria.push({
            name: name,
            max_points: points,
            examples: pattern ? pattern.examples : this.generateGenericExamples(name),
            description: `Clinical assessment of ${name.toLowerCase()}`
          });
        }
      });
      
      return criteria;
    }
  
    extractFromTableFormat(text) {
      const criteria = [];
      const lines = text.split('\n');
      
      // Look for Excel/table patterns
      lines.forEach((line, index) => {
        // Pattern for "Row X: Name | Value | Points"
        if (line.includes('|') || line.includes('\t')) {
          const parts = line.split(/[|\t]/).map(p => p.trim()).filter(p => p);
          
          if (parts.length >= 2) {
            // Look for examination names
            const examPattern = /(?:Examination|Assessment|Evaluation|Test)/i;
            const examPart = parts.find(p => examPattern.test(p));
            
            if (examPart) {
              // Extract points if available
              const pointsPart = parts.find(p => /\d+/.test(p));
              const points = pointsPart ? parseInt(pointsPart.match(/\d+/)[0]) : 1;
              
              criteria.push({
                name: examPart,
                max_points: points,
                examples: this.generateGenericExamples(examPart),
                description: `Clinical assessment of ${examPart.toLowerCase()}`
              });
            }
          }
        }
      });
      
      return criteria;
    }
  
    extractPoints(text, criterionName) {
      // Look for points near the criterion name
      const searchRadius = 100; // characters to search around the criterion
      const lowerText = text.toLowerCase();
      const lowerCriterion = criterionName.toLowerCase();
      
      const index = lowerText.indexOf(lowerCriterion);
      if (index === -1) return 1;
      
      const start = Math.max(0, index - searchRadius);
      const end = Math.min(text.length, index + criterionName.length + searchRadius);
      const nearbyText = text.substring(start, end);
      
      // Look for point patterns
      const pointPatterns = [
        /(\d+)\s*(?:points?|pts?)/i,
        /(?:points?|pts?)\s*[:=]\s*(\d+)/i,
        /(?:max|maximum)\s*[:=]?\s*(\d+)/i
      ];
      
      for (const pattern of pointPatterns) {
        const match = nearbyText.match(pattern);
        if (match) {
          return parseInt(match[1]);
        }
      }
      
      return 1; // Default to 1 point
    }
  
    deduplicateCriteria(criteria) {
      const seen = new Set();
      return criteria.filter(criterion => {
        const key = criterion.name.toLowerCase();
        if (seen.has(key)) {
          return false;
        }
        seen.add(key);
        return true;
      });
    }
  
    generateDefaultCriteria(text) {
      // Generate reasonable defaults based on common OSCE patterns
      return [
        {
          name: 'History Taking',
          max_points: 3,
          examples: [
            "Can you tell me about your symptoms?",
            "When did this start?",
            "Any relevant medical history?",
            "Are you taking any medications?"
          ],
          description: 'Assessment of history taking skills'
        },
        {
          name: 'Physical Examination',
          max_points: 5,
          examples: [
            "I'm going to examine you now",
            "Let me check this area",
            "Please let me know if you feel any discomfort",
            "I'll perform a physical examination"
          ],
          description: 'Assessment of physical examination technique'
        },
        {
          name: 'Communication Skills',
          max_points: 2,
          examples: [
            "I understand your concerns",
            "Let me explain what I'm doing",
            "Do you have any questions?",
            "Thank you for your cooperation"
          ],
          description: 'Assessment of doctor-patient communication'
        }
      ];
    }
  
    generateGenericExamples(criterionName) {
      const name = criterionName.toLowerCase();
      return [
        `I'm going to perform ${name} now`,
        `Let me check your ${name.split(' ')[0]}`,
        "Please let me know if you feel any discomfort",
        `This is part of the ${name}`
      ];
    }
  }