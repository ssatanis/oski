export class DynamicRubricAnalyzer {
    constructor() {
      this.sectionPatterns = [
        // Patterns for identifying rubric sections
        /^([\w\s]+(?:Taking|Exam|Examination|Assessment|Evaluation|Accuracy|Reasoning|Management|Skills?))\s*[:|-]?\s*(\d+)?\s*(?:points?|pts?)?/i,
        /^(?:\d+\.?\s*)?([\w\s]+)\s*\((\d+)\s*(?:points?|pts?)?\)/i,
        /^([\w\s]+)\s*-\s*(?:Max\s*)?(\d+)\s*(?:points?|pts?)?/i
      ];
      
      this.subItemPatterns = [
        /^(?:[•·▪▫◦‣⁃]\s*|[-*]\s*|\d+\.\s*)(.*?)(?:\s*\((\d+)\s*(?:points?|pts?)?\))?$/,
        /^(?:\s{2,}|\t+)(.*?)(?:\s*[:|-]\s*(\d+)\s*(?:points?|pts?)?)?$/
      ];
    }
  
    analyzeRubricStructure(structuredContent) {
      const analysis = {
        sections: [],
        totalPoints: 0,
        rubricType: 'unknown',
        metadata: {}
      };
      
      // Analyze based on file type
      if (structuredContent.structure?.sheets) {
        // Excel file - analyze sheet structure
        analysis.rubricType = 'spreadsheet';
        this.analyzeSpreadsheet(structuredContent, analysis);
      } else if (structuredContent.visionAnalysis) {
        // Use vision analysis for scanned/image documents
        analysis.rubricType = 'vision-analyzed';
        this.analyzeVisionOutput(structuredContent.visionAnalysis, analysis);
      } else {
        // Text-based analysis
        analysis.rubricType = 'text';
        this.analyzeText(structuredContent.rawText, analysis);
      }
      
      return analysis;
    }
  
    analyzeSpreadsheet(content, analysis) {
      Object.entries(content.structure.sheets).forEach(([sheetName, sheetData]) => {
        const rows = sheetData.rows;
        
        // Find header rows and section starts
        let currentSection = null;
        let sectionStartRow = -1;
        
        rows.forEach((row, rowIndex) => {
          const rowText = row.map(cell => cell.value?.toString() || '').join(' ').trim();
          
          if (!rowText) return;
          
          // Check if this row is a section header
          const sectionMatch = this.detectSectionHeader(rowText);
          if (sectionMatch) {
            // Save previous section if exists
            if (currentSection) {
              this.extractSectionItems(rows, sectionStartRow, rowIndex, currentSection);
              analysis.sections.push(currentSection);
            }
            
            currentSection = {
              name: sectionMatch.name,
              maxPoints: sectionMatch.points || 0,
              items: [],
              metadata: { sheet: sheetName, startRow: rowIndex }
            };
            sectionStartRow = rowIndex + 1;
          }
        });
        
        // Don't forget the last section
        if (currentSection) {
          this.extractSectionItems(rows, sectionStartRow, rows.length, currentSection);
          analysis.sections.push(currentSection);
        }
      });
      
      // Calculate total points
      analysis.totalPoints = analysis.sections.reduce((sum, section) => {
        const sectionTotal = section.items.reduce((itemSum, item) => itemSum + (item.points || 0), 0);
        return sum + (section.maxPoints || sectionTotal);
      }, 0);
    }
  
    detectSectionHeader(text) {
      // Common section headers in medical rubrics
      const knownSections = [
        'History Taking',
        'Physical Exam',
        'Physical Examination',
        'Diagnostic Accuracy',
        'Diagnostic Reasoning',
        'Diagnostic Accuracy/Reasoning/Justification',
        'Management',
        'Patient Management',
        'Communication Skills',
        'Professional Behavior',
        'Documentation'
      ];
      
      // Check against known sections first
      for (const section of knownSections) {
        if (text.toLowerCase().includes(section.toLowerCase())) {
          // Extract points if present
          const pointsMatch = text.match(/(\d+)\s*(?:points?|pts?)?/i);
          return {
            name: section,
            points: pointsMatch ? parseInt(pointsMatch[1]) : null
          };
        }
      }
      
      // Try pattern matching
      for (const pattern of this.sectionPatterns) {
        const match = text.match(pattern);
        if (match) {
          return {
            name: match[1].trim(),
            points: match[2] ? parseInt(match[2]) : null
          };
        }
      }
      
      return null;
    }
  
    extractSectionItems(rows, startRow, endRow, section) {
      for (let i = startRow; i < endRow; i++) {
        const row = rows[i];
        if (!row) continue;
        
        const rowText = row.map(cell => cell.value?.toString() || '').join(' ').trim();
        if (!rowText) continue;
        
        // Skip if this is another section header
        if (this.detectSectionHeader(rowText)) break;
        
        // Extract item details
        const item = this.extractItemDetails(rowText, row);
        if (item.description) {
          section.items.push(item);
        }
      }
    }
  
    extractItemDetails(text, row = null) {
      const item = {
        description: '',
        points: 0,
        examples: [],
        criteria: []
      };
      
      // Clean the text
      text = text.trim();
      
      // Try to extract points
      const pointsPatterns = [
        /\((\d+)\s*(?:points?|pts?)?\)/i,
        /(\d+)\s*(?:points?|pts?)/i,
        /:\s*(\d+)$/i
      ];
      
      for (const pattern of pointsPatterns) {
        const match = text.match(pattern);
        if (match) {
          item.points = parseInt(match[1]);
          // Remove the points from the description
          text = text.replace(match[0], '').trim();
          break;
        }
      }
      
      // Set description
      item.description = text;
      
      // If we have row data, check for points in separate columns
      if (row && Array.isArray(row)) {
        row.forEach(cell => {
          const cellValue = cell.value?.toString() || '';
          if (/^\d+$/.test(cellValue) && !item.points) {
            item.points = parseInt(cellValue);
          }
        });
      }
      
      return item;
    }
  
    analyzeVisionOutput(visionAnalysis, analysis) {
      // Process Google Vision API output
      const blocks = visionAnalysis.blocks || [];
      let currentSection = null;
      
      blocks.forEach(block => {
        const text = block.text.trim();
        if (!text) return;
        
        // Check if this is a section header
        const sectionMatch = this.detectSectionHeader(text);
        if (sectionMatch) {
          if (currentSection) {
            analysis.sections.push(currentSection);
          }
          
          currentSection = {
            name: sectionMatch.name,
            maxPoints: sectionMatch.points || 0,
            items: [],
            confidence: block.confidence
          };
        } else if (currentSection) {
          // This might be an item under the current section
          const item = this.extractItemDetails(text);
          if (item.description) {
            currentSection.items.push(item);
          }
        }
      });
      
      // Add the last section
      if (currentSection) {
        analysis.sections.push(currentSection);
      }
    }
  
    analyzeText(text, analysis) {
      const lines = text.split('\n').map(line => line.trim()).filter(line => line);
      let currentSection = null;
      let currentIndentLevel = 0;
      
      lines.forEach(line => {
        // Check if this is a section header
        const sectionMatch = this.detectSectionHeader(line);
        if (sectionMatch) {
          if (currentSection) {
            analysis.sections.push(currentSection);
          }
          
          currentSection = {
            name: sectionMatch.name,
            maxPoints: sectionMatch.points || 0,
            items: []
          };
          currentIndentLevel = 0;
        } else if (currentSection) {
          // Check if this is a sub-item
          const indent = line.match(/^(\s*)/)[1].length;
          if (indent > currentIndentLevel || this.isListItem(line)) {
            const item = this.extractItemDetails(line);
            if (item.description) {
              currentSection.items.push(item);
            }
          }
        }
      });
      
      // Add the last section
      if (currentSection) {
        analysis.sections.push(currentSection);
      }
      
      // Calculate total points
      analysis.totalPoints = analysis.sections.reduce((sum, section) => {
        const sectionTotal = section.items.reduce((itemSum, item) => itemSum + (item.points || 0), 0);
        return sum + (section.maxPoints || sectionTotal);
      }, 0);
    }
  
    isListItem(text) {
      return /^(?:[•·▪▫◦‣⁃]\s*|[-*]\s*|\d+\.\s*)/.test(text);
    }
  
    generateExamplesForSection(sectionName) {
      const exampleMap = {
        'History Taking': [
          "Can you tell me what brings you in today?",
          "When did these symptoms first start?",
          "Have you experienced anything like this before?",
          "Are you currently taking any medications?",
          "Do you have any allergies?",
          "Any relevant family medical history?"
        ],
        'Physical Exam': [
          "I'm going to examine you now",
          "Please let me know if you feel any discomfort",
          "Can you take a deep breath for me?",
          "I'm going to check your vital signs",
          "Let me listen to your heart and lungs",
          "I'll examine the affected area"
        ],
        'Diagnostic Accuracy': [
          "Based on the findings, the most likely diagnosis is...",
          "The differential diagnoses include...",
          "This is consistent with...",
          "We should rule out...",
          "The key findings that support this diagnosis are..."
        ],
        'Management': [
          "I recommend starting treatment with...",
          "We should order the following tests...",
          "Follow up in 2 weeks to assess response",
          "If symptoms worsen, please return immediately",
          "The treatment plan includes..."
        ]
      };
      
      // Find the best match
      for (const [key, examples] of Object.entries(exampleMap)) {
        if (sectionName.toLowerCase().includes(key.toLowerCase())) {
          return examples;
        }
      }
      
      // Generic examples if no match
      return [
        `Perform ${sectionName.toLowerCase()} assessment`,
        `Document ${sectionName.toLowerCase()} findings`,
        `Complete ${sectionName.toLowerCase()} evaluation`
      ];
    }
  }