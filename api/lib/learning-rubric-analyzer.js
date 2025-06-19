import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import XLSX from 'xlsx';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export class LearningRubricAnalyzer {
  constructor() {
    this.trainingPatterns = [];
    this.rubricExamples = [];
    this.yamlExamples = [];
    this.initialized = false;
  }

  async initialize() {
    if (this.initialized) return;
    
    try {
      // Load training data from the rubrics and yaml_prompts folders
      await this.loadTrainingData();
      this.initialized = true;
    } catch (error) {
      console.error('Failed to initialize training data:', error);
      // Continue anyway - we'll use dynamic analysis
      this.initialized = true;
    }
  }

  async loadTrainingData() {
    // Try multiple possible paths for the training data
    const possiblePaths = [
      path.join(process.cwd(), '..', '..', 'rubrics'),
      path.join(process.cwd(), 'rubrics'),
      '/Users/sahajsatani/Documents/Oski/rubrics-to-prompts/rubrics'
    ];

    let rubricsPath = null;
    let yamlPath = null;

    // Find the correct paths
    for (const basePath of possiblePaths) {
      try {
        await fs.access(basePath);
        rubricsPath = basePath;
        yamlPath = basePath.replace('/rubrics', '/yaml_prompts');
        break;
      } catch (e) {
        continue;
      }
    }

    if (!rubricsPath) {
      console.log('Training data folders not found, using dynamic analysis only');
      return;
    }

    // Load rubric examples
    try {
      const rubricFiles = await fs.readdir(rubricsPath);
      
      for (const file of rubricFiles) {
        if (file.endsWith('.xlsx') || file.endsWith('.xls')) {
          const filePath = path.join(rubricsPath, file);
          const data = await fs.readFile(filePath);
          const workbook = XLSX.read(data, { type: 'buffer' });
          
          // Extract patterns from the workbook
          const patterns = this.extractPatternsFromWorkbook(workbook, file);
          this.trainingPatterns.push(...patterns);
        }
      }
    } catch (error) {
      console.error('Error loading rubrics:', error);
    }

    // Load YAML examples
    try {
      const yamlFiles = await fs.readdir(yamlPath);
      
      for (const file of yamlFiles) {
        if (file.endsWith('.yaml') || file.endsWith('.yml')) {
          const filePath = path.join(yamlPath, file);
          const content = await fs.readFile(filePath, 'utf8');
          this.yamlExamples.push({
            filename: file,
            content: content
          });
        }
      }
    } catch (error) {
      console.error('Error loading YAML examples:', error);
    }

    console.log(`Loaded ${this.trainingPatterns.length} patterns from ${rubricFiles.length} rubrics`);
    console.log(`Loaded ${this.yamlExamples.length} YAML examples`);
  }

  extractPatternsFromWorkbook(workbook, filename) {
    const patterns = [];
    
    workbook.SheetNames.forEach(sheetName => {
      const sheet = workbook.Sheets[sheetName];
      const data = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' });
      
      // Analyze the structure
      let currentSection = null;
      let sectionPattern = null;
      
      data.forEach((row, rowIndex) => {
        const rowText = row.filter(cell => cell).join(' ').trim();
        if (!rowText) return;
        
        // Detect section headers
        if (this.looksLikeSectionHeader(rowText, row)) {
          patterns.push({
            type: 'section_header',
            pattern: rowText,
            structure: row,
            filename: filename,
            sheetName: sheetName
          });
          currentSection = rowText;
        } else if (currentSection && this.looksLikeItem(rowText, row)) {
          patterns.push({
            type: 'item',
            pattern: rowText,
            structure: row,
            section: currentSection,
            filename: filename,
            sheetName: sheetName
          });
        }
      });
    });
    
    return patterns;
  }

  looksLikeSectionHeader(text, row) {
    // Check if it's a header based on various criteria
    const headerIndicators = [
      /^[A-Z][A-Z\s]+$/,  // All caps
      /^\d+\.\s*[A-Z]/,   // Numbered with capital
      /^[A-Z].*:$/,       // Ends with colon
      text.length < 50 && row.length <= 3  // Short text in few columns
    ];
    
    return headerIndicators.some(indicator => 
      indicator instanceof RegExp ? indicator.test(text) : indicator
    );
  }

  looksLikeItem(text, row) {
    // Check if it's an item/criterion
    const itemIndicators = [
      /^[•·▪▫◦‣⁃-]\s*/,  // Bullet points
      /^\d+\.\s*/,        // Numbered
      /^\w+.*\d+\s*(?:points?|pts?)/i,  // Has points
      row.some(cell => /^\d+$/.test(String(cell)))  // Has number in separate column
    ];
    
    return itemIndicators.some(indicator => 
      indicator instanceof RegExp ? indicator.test(text) : indicator
    );
  }

  async analyzeWithPatterns(structuredContent) {
    await this.initialize();
    
    const analysis = {
      sections: [],
      totalPoints: 0,
      confidence: 0,
      metadata: {
        matchedPatterns: 0,
        usedTraining: this.trainingPatterns.length > 0
      }
    };
    
    // Extract content based on file type
    if (structuredContent.structure?.sheets) {
      this.analyzeSpreadsheetWithLearning(structuredContent, analysis);
    } else if (structuredContent.visionAnalysis) {
      this.analyzeVisionWithLearning(structuredContent.visionAnalysis, analysis);
    } else {
      this.analyzeTextWithLearning(structuredContent.rawText, analysis);
    }
    
    return analysis;
  }

  analyzeSpreadsheetWithLearning(content, analysis) {
    Object.entries(content.structure.sheets).forEach(([sheetName, sheetData]) => {
      const rows = sheetData.rows;
      let currentSection = null;
      let sectionItems = [];
      
      rows.forEach((row, rowIndex) => {
        const rowData = row.map(cell => cell.value || '');
        const rowText = rowData.join(' ').trim();
        
        if (!rowText) return;
        
        // Check against learned patterns
        const matchedPattern = this.findBestPatternMatch(rowText, rowData);
        
        if (matchedPattern && matchedPattern.type === 'section_header') {
          // Save previous section
          if (currentSection) {
            currentSection.items = sectionItems;
            analysis.sections.push(currentSection);
          }
          
          // Start new section
          currentSection = this.createSectionFromPattern(rowText, rowData, matchedPattern);
          sectionItems = [];
          analysis.metadata.matchedPatterns++;
        } else if (currentSection) {
          // Try to extract item
          const item = this.extractItemFromRow(rowData, rowText, matchedPattern);
          if (item.description) {
            sectionItems.push(item);
            if (matchedPattern) analysis.metadata.matchedPatterns++;
          }
        }
      });
      
      // Don't forget last section
      if (currentSection) {
        currentSection.items = sectionItems;
        analysis.sections.push(currentSection);
      }
    });
    
    // Calculate total points
    this.calculateTotalPoints(analysis);
  }

  findBestPatternMatch(text, structure) {
    if (this.trainingPatterns.length === 0) return null;
    
    let bestMatch = null;
    let bestScore = 0;
    
    this.trainingPatterns.forEach(pattern => {
      const score = this.calculatePatternSimilarity(text, structure, pattern);
      if (score > bestScore && score > 0.5) {  // Threshold
        bestScore = score;
        bestMatch = pattern;
      }
    });
    
    return bestMatch;
  }

  calculatePatternSimilarity(text, structure, pattern) {
    // Simple similarity calculation
    let score = 0;
    
    // Text similarity
    const textLower = text.toLowerCase();
    const patternLower = pattern.pattern.toLowerCase();
    
    if (textLower === patternLower) {
      score = 1;
    } else if (textLower.includes(patternLower) || patternLower.includes(textLower)) {
      score = 0.7;
    } else {
      // Check word overlap
      const textWords = textLower.split(/\s+/);
      const patternWords = patternLower.split(/\s+/);
      const overlap = textWords.filter(w => patternWords.includes(w)).length;
      score = overlap / Math.max(textWords.length, patternWords.length);
    }
    
    // Structure similarity (number of columns, etc.)
    if (structure.length === pattern.structure.length) {
      score += 0.2;
    }
    
    return Math.min(score, 1);
  }

  createSectionFromPattern(text, rowData, pattern) {
    const section = {
      name: this.cleanSectionName(text),
      maxPoints: 0,
      items: [],
      metadata: {
        pattern: pattern ? pattern.pattern : null,
        confidence: pattern ? 'high' : 'low'
      }
    };
    
    // Extract points if present
    const pointsMatch = text.match(/(\d+)\s*(?:points?|pts?)/i);
    if (pointsMatch) {
      section.maxPoints = parseInt(pointsMatch[1]);
    } else {
      // Check other columns for points
      rowData.forEach(cell => {
        if (/^\d+$/.test(String(cell))) {
          section.maxPoints = Math.max(section.maxPoints, parseInt(cell));
        }
      });
    }
    
    return section;
  }

  cleanSectionName(text) {
    // Remove common prefixes/suffixes
    return text
      .replace(/^\d+\.\s*/, '')  // Remove numbering
      .replace(/\s*[:|-]\s*$/, '')  // Remove trailing punctuation
      .replace(/\s*\d+\s*(?:points?|pts?)?\s*$/i, '')  // Remove points
      .trim();
  }

  extractItemFromRow(rowData, rowText, pattern) {
    const item = {
      description: '',
      points: 0,
      examples: [],
      criteria: []
    };
    
    // Find the main description (usually first non-empty cell)
    let mainText = '';
    let pointsFound = false;
    
    rowData.forEach((cell, index) => {
      const cellStr = String(cell).trim();
      
      if (!cellStr) return;
      
      // Check if it's a number (likely points)
      if (/^\d+$/.test(cellStr) && !pointsFound) {
        item.points = parseInt(cellStr);
        pointsFound = true;
      } else if (!mainText && cellStr.length > 2) {
        mainText = cellStr;
      }
    });
    
    // Clean up the description
    item.description = mainText
      .replace(/^[•·▪▫◦‣⁃-]\s*/, '')  // Remove bullets
      .replace(/^\d+\.\s*/, '')  // Remove numbering
      .replace(/\s*\d+\s*(?:points?|pts?)?\s*$/i, '')  // Remove trailing points
      .trim();
    
    // Try to extract points from text if not found in separate column
    if (!item.points && mainText) {
      const pointsMatch = mainText.match(/(\d+)\s*(?:points?|pts?)/i);
      if (pointsMatch) {
        item.points = parseInt(pointsMatch[1]);
      }
    }
    
    return item;
  }

  calculateTotalPoints(analysis) {
    analysis.totalPoints = analysis.sections.reduce((total, section) => {
      if (section.maxPoints) {
        return total + section.maxPoints;
      } else {
        // Sum individual item points
        const itemTotal = section.items.reduce((sum, item) => sum + (item.points || 0), 0);
        section.maxPoints = itemTotal;  // Set section max points
        return total + itemTotal;
      }
    }, 0);
  }

  generateExamplesFromTraining(sectionName) {
    // Look for similar sections in training data
    const similarSections = this.yamlExamples
      .map(yaml => {
        // Simple YAML parsing to find criteria
        const criteriaMatch = yaml.content.match(/criteria:\s*\n([\s\S]*?)(?:\n\w+:|$)/);
        if (!criteriaMatch) return [];
        
        const criteriaText = criteriaMatch[1];
        const examples = [];
        
        // Extract examples for similar sections
        const sectionRegex = new RegExp(`name:\\s*"?${sectionName}`, 'i');
        if (sectionRegex.test(criteriaText)) {
          const exampleMatches = criteriaText.match(/examples:\s*\n((?:\s+-[^\n]+\n?)+)/g);
          if (exampleMatches) {
            exampleMatches.forEach(match => {
              const items = match.match(/-\s*"?([^"\n]+)"?/g);
              if (items) {
                examples.push(...items.map(item => 
                  item.replace(/^-\s*"?/, '').replace(/"?\s*$/, '')
                ));
              }
            });
          }
        }
        
        return examples;
      })
      .flat();
    
    // Return unique examples or generate generic ones
    if (similarSections.length > 0) {
      return [...new Set(similarSections)].slice(0, 5);
    }
    
    // Fallback to generic examples
    return [
      `Perform ${sectionName.toLowerCase()} assessment`,
      `Document findings related to ${sectionName.toLowerCase()}`,
      `Complete ${sectionName.toLowerCase()} evaluation`
    ];
  }
}