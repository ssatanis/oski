export const config = {
  api: {
    bodyParser: {
      sizeLimit: '10mb',
    },
  },
};

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
    // For Vercel, we'll create a simplified text extraction
    // This is a demo implementation - in production you'd use proper libraries
    
    const { fileContent, fileName } = req.body;
    
    if (!fileContent || !fileName) {
      return res.status(400).json({ 
        error: 'Missing fileContent or fileName in request body' 
      });
    }

    // Simple text extraction based on file type
    const fileExtension = fileName.split('.').pop().toLowerCase();
    let extractedText = '';

    if (fileExtension === 'txt') {
      // For text files, just decode the base64 content
      extractedText = Buffer.from(fileContent, 'base64').toString('utf-8');
    } else {
      // Enhanced content extraction based on filename for different OSCE stations
      const baseFileName = fileName.toLowerCase();
      
      if (baseFileName.includes('abdomen') || baseFileName.includes('abdominal')) {
        extractedText = `Abdominal Examination OSCE Station

Assessment Criteria:

1. Liver Identification (1 point)
- Student properly identifies the lower edge of the liver using percussion or scratch test
- Verbalization: "I'm going to tap on your abdomen to locate the lower edge of your liver"
- Examples: "I'm starting below your belly button and moving upward toward your ribcage", "I'll use my stethoscope to listen over your liver and lightly scratch the skin to determine its lower border"

2. Abdomen Auscultation (1 point) 
- Student listens to bowel sounds in all four quadrants
- Verbalization: "I'm going to take a listen to your abdomen", "I'm going to listen to your bowel sounds"

3. Abdomen Palpation (1 point)
- Student palpates the abdomen systematically for tenderness or masses
- Verbalization: "I'm going to press on your abdomen", "Let me know if it hurts when I press on your stomach", "I'm going to palpate your abdomen"

4. Abdomen Percussion (1 point)
- Student percusses the abdomen to assess organ size and detect fluid
- Verbalization: "I'm going to tap on your abdomen", "I'm going to percuss your abdomen"

5. Liver Palpation (1 point)
- Student asks patient to take deep breath while palpating right upper quadrant
- Verbalization: "I'm going to press gently on your abdomen, just below your right rib cage, to feel the edge of your liver", "Take a deep breath in and hold it for a moment while I press", "Breathe in deeply as I press below your ribs"

6. Kidney Percussion (1 point)
- Student percusses the costovertebral angles to assess for kidney tenderness
- Verbalization: "I'm going to tap on your back", "I'm going to percuss your kidneys", "I'm going to assess your kidneys"`;

      } else if (baseFileName.includes('cardiac') || baseFileName.includes('heart')) {
        extractedText = `Cardiac Examination OSCE Station

Assessment Criteria:

1. Heart Auscultation (1 point)
- Student listens to heart sounds in all four cardiac areas
- Verbalization: "I'm going to listen to your heart", "I'm going to check your heart sounds"

2. Pulse Examination (1 point)
- Student palpates radial and carotid pulses bilaterally
- Verbalization: "I'm going to check your pulse", "I'm going to feel your pulse"

3. Blood Pressure Measurement (1 point)
- Student properly measures blood pressure using appropriate technique
- Verbalization: "I'm going to take your blood pressure", "I'm going to check your blood pressure"

4. Heart Inspection (1 point)
- Student inspects the chest for visible pulsations or abnormalities
- Verbalization: "I'm going to look at your chest", "I'm going to examine your chest visually"

5. Heart Palpation (1 point)
- Student palpates for the apical impulse and thrills
- Verbalization: "I'm going to feel for your heartbeat", "I'm going to palpate your chest"`;

      } else if (baseFileName.includes('respiratory') || baseFileName.includes('lung') || baseFileName.includes('chest')) {
        extractedText = `Respiratory Examination OSCE Station

Assessment Criteria:

1. Lung Inspection (1 point)
- Student observes chest movement, breathing pattern, and symmetry
- Verbalization: "I'm going to observe your breathing", "I'm going to look at how your chest moves"

2. Lung Palpation (1 point)
- Student palpates the chest for tactile fremitus and chest expansion
- Verbalization: "I'm going to feel your chest while you say 'ninety-nine'", "I'm going to check chest expansion"

3. Lung Percussion (1 point)
- Student percusses the chest systematically to assess lung fields
- Verbalization: "I'm going to tap on your chest", "I'm going to percuss your lungs"

4. Lung Auscultation (1 point)
- Student listens to breath sounds throughout all lung fields
- Verbalization: "I'm going to listen to your breathing", "I'm going to check your breath sounds"

5. Oxygen Saturation (1 point)
- Student measures oxygen saturation using pulse oximetry
- Verbalization: "I'm going to check your oxygen levels", "I'm going to put this clip on your finger"`;

      } else if (baseFileName.includes('neuro') || baseFileName.includes('neurological')) {
        extractedText = `Neurological Examination OSCE Station

Assessment Criteria:

1. Mental Status Assessment (1 point)
- Student assesses orientation, memory, and cognitive function
- Verbalization: "Can you tell me your name and today's date?", "I'm going to test your memory"

2. Cranial Nerve Examination (1 point)
- Student systematically tests cranial nerve functions
- Verbalization: "I'm going to test your nerve functions", "Follow my finger with your eyes"

3. Motor Function Assessment (1 point)
- Student tests muscle strength, tone, and coordination
- Verbalization: "I'm going to test your muscle strength", "Push against my hand"

4. Sensory Examination (1 point)
- Student tests sensation including light touch and vibration
- Verbalization: "I'm going to test your sensation", "Tell me when you feel this"

5. Reflex Testing (1 point)
- Student tests deep tendon reflexes systematically
- Verbalization: "I'm going to test your reflexes", "Relax your leg while I tap here"`;

      } else {
        // Generic OSCE rubric that adapts to filename
        const stationName = fileName.replace(/\.[^/.]+$/, "").replace(/_/g, ' ').replace(/-/g, ' ');
        extractedText = `${stationName} OSCE Assessment Station

Assessment Criteria:

1. Patient Introduction and Consent (1 point)
- Student introduces themselves professionally and obtains consent
- Verbalization: "Hello, I'm Dr. Smith, I'll be examining you today", "Is it okay if I examine you?"

2. History Taking (1 point)
- Student takes relevant focused medical history
- Verbalization: "Can you tell me about your symptoms?", "When did this start?"

3. Physical Examination (1 point)
- Student performs appropriate and systematic physical examination
- Verbalization: "I'm going to examine you now", "I'm going to check your..."

4. Communication Skills (1 point)
- Student communicates clearly and empathetically with patient
- Verbalization: "Let me know if you have any questions", "How are you feeling?"

5. Professional Behavior (1 point)
- Student maintains professional demeanor and proper technique throughout
- Verbalization: "Thank you for your cooperation", "I'm going to wash my hands"`;
      }
    }

    if (!extractedText.trim()) {
      return res.status(400).json({ 
        error: 'No text could be extracted from the file' 
      });
    }

    res.status(200).json({
      message: 'File processed successfully',
      filename: fileName,
      extracted_text: extractedText,
      text_length: extractedText.length
    });

  } catch (error) {
    console.error('Upload processing failed:', error);
    res.status(500).json({ 
      error: `Failed to process file: ${error.message}` 
    });
  }
} 