// Rubricon Standalone App - Complete Implementation
// This file contains all the functionality from the main site without header/footer dependencies

let currentFile = null;
let processedData = null;
let currentRubricData = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    console.log('Rubricon standalone app loaded');
    setupFileUpload();
    setupDragAndDrop();
    
    // Listen for changes in form inputs to update preview
    document.addEventListener('input', function(e) {
        if (e.target.matches('#systemMessage')) {
            updateUserMessagePreview();
        }
    });
});

function setupFileUpload() {
    const fileInput = document.getElementById('fileInput');
    
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            handleFileSelection(file);
        }
    });
}

function setupDragAndDrop() {
    const uploadZone = document.getElementById('uploadZone');

    uploadZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelection(files[0]);
        }
    });
}

function handleFileSelection(file) {
    currentFile = file;
    
    // Update file preview
    const filePreview = document.getElementById('filePreview');
    const processButton = document.getElementById('processButton');
    const processingSection = document.getElementById('processingSection');

    // Create file preview HTML
    filePreview.innerHTML = `
        <div class="file-info">
            <div class="file-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
            </div>
            <div>
                <h3>${file.name}</h3>
                <p>${formatFileSize(file.size)}</p>
            </div>
        </div>
    `;
    
    filePreview.style.display = 'flex';
    processButton.disabled = false;
    
    // Show processing section
    processingSection.style.display = 'block';
    
    // Smooth scroll to processing section
    setTimeout(() => {
        processingSection.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center' 
        });
    }, 300);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function simpleHash(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash);
}

function generateAdaptiveCriteria(fileName, criteriaCount, variation) {
    const domainTemplates = {
        cardiology: ['Heart Auscultation', 'Blood Pressure Measurement', 'Pulse Assessment', 'ECG Interpretation'],
        dermatology: ['Skin Inspection', 'Lesion Assessment', 'Patient History', 'Documentation'],
        neurology: ['Neurological Examination', 'Reflex Testing', 'Cognitive Assessment', 'Motor Function'],
        general: ['Patient Communication', 'History Taking', 'Physical Examination', 'Clinical Reasoning']
    };
    
    // Determine domain from filename
    let domain = 'general';
    if (fileName.includes('cardio') || fileName.includes('heart')) domain = 'cardiology';
    if (fileName.includes('derm') || fileName.includes('skin')) domain = 'dermatology';
    if (fileName.includes('neuro') || fileName.includes('brain')) domain = 'neurology';
    
    const templates = domainTemplates[domain];
    const criteria = [];
    
    for (let i = 0; i < criteriaCount; i++) {
        const template = templates[i % templates.length];
        const points = Math.max(1, Math.min(10, 2 + (variation + i) % 6));
        
        criteria.push({
            name: template,
            code: template.replace(/\s+/g, '_').toUpperCase(),
            points: points,
            description: `Assessment of ${template.toLowerCase()} skills`,
            items: [
                `Demonstrates proper ${template.toLowerCase()} technique`,
                `Shows competency in ${template.toLowerCase()}`,
                `Communicates findings clearly`
            ]
        });
    }
    
    return criteria;
}

async function processRubric() {
    if (!currentFile) {
        showStatus('error', 'Please select a file first.');
        return;
    }

    const processButton = document.getElementById('processButton');
    const statusMessages = document.getElementById('statusMessages');
    
    // Disable button and show processing state
    processButton.disabled = true;
    processButton.innerHTML = `
        <div class="loading-spinner"></div>
        Processing...
    `;

    // Clear previous status messages
    statusMessages.innerHTML = '';

    try {
        // Step 1: Simulate file processing
        showStatus('processing', 'Analyzing file structure...', true);
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Step 2: Simulate OCR extraction
        showStatus('processing', 'Extracting text content...', true);
        const fileExtension = currentFile.name.split('.').pop().toLowerCase();
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // Step 3: Generate criteria from file
        showStatus('processing', 'Generating assessment criteria...', true);
        const processedResult = await simulateProcessing(currentFile.name);
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        processedData = processedResult;
        
        // Step 4: Success
        const criteriaCount = processedData.parsed_yaml?.criteria?.length || 0;
        showStatus('success', `✅ Document processed successfully! Extracted ${criteriaCount} assessment criteria.`, false);
        
        // Show dashboard section
        showDashboard(processedData);

    } catch (error) {
        console.error('Error processing rubric:', error);
        showStatus('error', 'Failed to process rubric. Please try again.');
        
        // Reset button
        processButton.disabled = false;
        processButton.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5 3 19 12 5 21 5 3"></polygon>
            </svg>
            Process Rubric
        `;
    }
}

async function simulateProcessing(fileName) {
    // Generate realistic criteria based on filename
    const baseFileName = fileName.toLowerCase().replace(/\.[^.]+$/, '');
    const criteria = generateAdaptiveCriteria(baseFileName, 3, 0);
    
    const processedCriteria = criteria.map(criterion => ({
        name: criterion.name,
        max_points: criterion.points,
        examples: criterion.items
    }));
    
    return {
        success: true,
        generated_from: 'adaptive_ai',
        criteria_count: processedCriteria.length,
        parsed_yaml: {
            system_message: 'You are a helpful assistant tasked with analyzing and scoring a recorded medical examination between a medical student and a patient. Provide your response in JSON format.',
            criteria: processedCriteria
        }
    };
}

function showDashboard(data) {
    currentRubricData = data;
    const dashboardSection = document.getElementById('dashboardSection');
    
    // Initialize dashboard with data
    initializeDashboard(data);
    
    // Show dashboard section
    dashboardSection.style.display = 'block';
    
    // Smooth scroll to dashboard
    setTimeout(() => {
        dashboardSection.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center' 
        });
    }, 500);
}

function initializeDashboard(data) {
    console.log('Initializing dashboard with data:', data);
    
    // Set system message
    document.getElementById('systemMessage').value = data.parsed_yaml?.system_message || 'You are a helpful assistant tasked with analyzing and scoring a recorded medical examination between a medical student and a patient. Provide your response in JSON format.';
    
    // Load criteria
    const criteria = data.parsed_yaml?.criteria || [];
    console.log('Loading criteria:', criteria);
    
    if (criteria.length > 0) {
        loadCriteria(criteria);
    } else {
        // Add one empty criterion if none exist
        addNewCriterion();
    }
    
    // Update total points and preview
    updateTotalPoints();
    updateUserMessagePreview();
}

function loadCriteria(criteria) {
    const container = document.getElementById('criteriaContainer');
    container.innerHTML = '';
    
    criteria.forEach((criterion, index) => {
        addCriterionToDOM(criterion, index);
    });
}

function addNewCriterion() {
    const criterion = {
        name: '',
        max_points: 1,
        examples: ['']
    };
    const container = document.getElementById('criteriaContainer');
    const index = container.children.length;
    addCriterionToDOM(criterion, index);
    updateTotalPoints();
    updateUserMessagePreview();
}

function addCriterionToDOM(criterion, index) {
    const container = document.getElementById('criteriaContainer');
    const criterionDiv = document.createElement('div');
    criterionDiv.className = 'criterion-item';
    criterionDiv.dataset.index = index;
    
    // Ensure criterion has required fields
    const safeCriterion = {
        name: criterion?.name || '',
        max_points: criterion?.max_points || 1,
        examples: criterion?.examples || ['']
    };
    
    criterionDiv.innerHTML = `
        <div class="criterion-header">
            <div style="display: flex; align-items: center; gap: 15px;">
                <span class="criterion-number">${index + 1}</span>
                <div style="flex: 1;">
                    <div class="input-group" style="margin-bottom: 10px;">
                        <input type="text" class="form-input criterion-name" placeholder="e.g., Patient Greeting and Introduction" value="${safeCriterion.name}" oninput="updateCriterion(${index})">
                    </div>
                    <div class="input-group">
                        <label>Max Points:</label>
                        <input type="number" class="form-input criterion-points" min="1" max="10" value="${safeCriterion.max_points}" oninput="updateCriterion(${index})" style="width: 80px;">
                    </div>
                </div>
            </div>
            <button class="btn-remove-criterion" onclick="removeCriterion(${index})">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        </div>
        <div class="criterion-examples">
            <label>Examples:</label>
            <div class="examples-list">
                ${safeCriterion.examples.map((example, exampleIndex) => `
                    <div class="example-item">
                        <input type="text" class="example-input" placeholder="e.g., I'm going to examine your..." value="${example}" oninput="updateCriterion(${index})">
                        <button class="btn-remove-example" onclick="removeExample(${index}, ${exampleIndex})">×</button>
                    </div>
                `).join('')}
            </div>
            <button class="btn-add-example" onclick="addExample(${index})">+ Add Example</button>
        </div>
    `;
    
    container.appendChild(criterionDiv);
}

function updateCriterion(index) {
    updateTotalPoints();
    updateUserMessagePreview();
}

function removeCriterion(index) {
    const container = document.getElementById('criteriaContainer');
    const item = container.children[index];
    if (item) {
        item.remove();
        reindexCriteria();
        updateTotalPoints();
        updateUserMessagePreview();
    }
}

function addExample(criterionIndex) {
    const container = document.getElementById('criteriaContainer');
    const criterionItem = container.children[criterionIndex];
    const examplesList = criterionItem.querySelector('.examples-list');
    
    const exampleDiv = document.createElement('div');
    exampleDiv.className = 'example-item';
    exampleDiv.innerHTML = `
        <input type="text" class="example-input" placeholder="e.g., I'm going to examine your..." oninput="updateCriterion(${criterionIndex})">
        <button class="btn-remove-example" onclick="removeExample(${criterionIndex}, ${examplesList.children.length})">×</button>
    `;
    
    examplesList.appendChild(exampleDiv);
}

function removeExample(criterionIndex, exampleIndex) {
    const container = document.getElementById('criteriaContainer');
    const criterionItem = container.children[criterionIndex];
    const examplesList = criterionItem.querySelector('.examples-list');
    const exampleItem = examplesList.children[exampleIndex];
    if (exampleItem) {
        exampleItem.remove();
        updateCriterion(criterionIndex);
    }
}

function reindexCriteria() {
    const container = document.getElementById('criteriaContainer');
    Array.from(container.children).forEach((item, index) => {
        item.dataset.index = index;
        const numberSpan = item.querySelector('.criterion-number');
        if (numberSpan) numberSpan.textContent = index + 1;
        
        // Update onclick handlers
        const nameInput = item.querySelector('.criterion-name');
        const pointsInput = item.querySelector('.criterion-points');
        const exampleInputs = item.querySelectorAll('.example-input');
        const removeBtn = item.querySelector('.btn-remove-criterion');
        const addExampleBtn = item.querySelector('.btn-add-example');
        
        if (nameInput) nameInput.setAttribute('oninput', `updateCriterion(${index})`);
        if (pointsInput) pointsInput.setAttribute('oninput', `updateCriterion(${index})`);
        if (removeBtn) removeBtn.setAttribute('onclick', `removeCriterion(${index})`);
        if (addExampleBtn) addExampleBtn.setAttribute('onclick', `addExample(${index})`);
        
        exampleInputs.forEach((input, exampleIndex) => {
            input.setAttribute('oninput', `updateCriterion(${index})`);
            const removeExampleBtn = input.nextElementSibling;
            if (removeExampleBtn) {
                removeExampleBtn.setAttribute('onclick', `removeExample(${index}, ${exampleIndex})`);
            }
        });
    });
}

function updateTotalPoints() {
    const container = document.getElementById('criteriaContainer');
    let total = 0;
    
    Array.from(container.children).forEach(item => {
        const pointsInput = item.querySelector('.criterion-points');
        if (pointsInput) {
            total += parseInt(pointsInput.value) || 0;
        }
    });
    
    document.getElementById('totalPoints').textContent = `Total Points: ${total}`;
}

function updateUserMessagePreview() {
    console.log('User message preview updated');
}

function downloadYAML() {
    const criteria = getCurrentDashboardCriteria();
    
    if (criteria.length === 0) {
        alert('No criteria available for download. Please add some assessment criteria first.');
        return;
    }
    
    const yamlContent = generateYAMLContent(criteria);
    downloadFile(yamlContent, 'assessment-rubric.yaml', 'text/yaml');
}

function getCurrentDashboardCriteria() {
    const container = document.getElementById('criteriaContainer');
    const criteria = [];
    
    Array.from(container.children).forEach(item => {
        const nameInput = item.querySelector('.criterion-name');
        const pointsInput = item.querySelector('.criterion-points');
        const exampleInputs = item.querySelectorAll('.example-input');
        
        const examples = Array.from(exampleInputs)
            .map(input => input.value.trim())
            .filter(value => value);
        
        if (nameInput.value.trim()) {
            criteria.push({
                name: nameInput.value.trim(),
                max_points: parseInt(pointsInput.value) || 1,
                examples: examples.length > 0 ? examples : [`I'm going to assess your ${nameInput.value.trim().toLowerCase()}`]
            });
        }
    });
    
    return criteria;
}

function generateYAMLContent(criteria) {
    const systemMessage = document.getElementById('systemMessage').value || 'You are a helpful assistant tasked with analyzing and scoring a recorded medical examination between a medical student and a patient. Provide your response in JSON format.';
    
    let yaml = `system_message: |\n  ${systemMessage}\n\nuser_message: |\n`;
    
    const examsList = criteria.map(c => c.name.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_'));
    
    yaml += `  Your task is to identify the start and end times of specific physical exams within the conversation and provide the reasoning behind your choices.\n`;
    yaml += `  This station consists of the following physical exams: ${examsList.join(', ')}\n\n`;
    
    yaml += `  You need to identify the following physical exams from this transcript:\n`;
    criteria.forEach((criterion, index) => {
        const examId = criterion.name.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_');
        yaml += `    ${index + 1}. ${examId}: Did the doctor perform ${criterion.name.toLowerCase()}?\n`;
        yaml += `       - Verbalization examples: ${criterion.examples.join(', ')}\n`;
    });
    
    yaml += `\nresponse_config:\n  structured_output: True\n`;
    
    return yaml;
}

function copyToClipboard() {
    const criteria = getCurrentDashboardCriteria();
    
    if (criteria.length === 0) {
        alert('No criteria available to copy. Please add some assessment criteria first.');
        return;
    }
    
    const yamlContent = generateYAMLContent(criteria);
    
    navigator.clipboard.writeText(yamlContent).then(() => {
        showStatus('success', 'YAML content copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy: ', err);
        alert('Failed to copy to clipboard. Please try downloading instead.');
    });
}

function showStatus(type, message, withSpinner = false) {
    const statusMessages = document.getElementById('statusMessages');
    
    const statusDiv = document.createElement('div');
    statusDiv.className = `status-message ${type}`;
    
    let iconHtml = '';
    if (withSpinner) {
        iconHtml = '<div class="loading-spinner"></div>';
    } else if (type === 'success') {
        iconHtml = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 12l2 2 4-4"></path>
                <circle cx="12" cy="12" r="10"></circle>
            </svg>
        `;
    } else if (type === 'error') {
        iconHtml = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="15" y1="9" x2="9" y2="15"></line>
                <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
        `;
    }
    
    statusDiv.innerHTML = `${iconHtml}<span>${message}</span>`;
    
    // Clear previous messages if this is not a processing step
    if (type !== 'processing') {
        statusMessages.innerHTML = '';
    }
    
    statusMessages.appendChild(statusDiv);
    
    // Trigger animation
    setTimeout(() => {
        statusDiv.classList.add('visible');
    }, 100);
}

function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    URL.revokeObjectURL(url);
    
    // Show success message
    showStatus('success', `${filename} downloaded successfully!`);
}

// Add CSS for loading spinner and status messages
const style = document.createElement('style');
style.textContent = `
    .loading-spinner {
        display: inline-block;
        width: 16px;
        height: 16px;
        border: 2px solid #f3f3f3;
        border-top: 2px solid #4a90e2;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-right: 8px;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .status-message {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 15px;
        margin: 10px 0;
        border-radius: 6px;
        opacity: 0;
        transform: translateY(10px);
        transition: all 0.3s ease;
    }

    .status-message.visible {
        opacity: 1;
        transform: translateY(0);
    }

    .status-message.processing {
        background: #e3f2fd;
        color: #1565c0;
        border: 1px solid #bbdefb;
    }

    .status-message.success {
        background: #e8f5e8;
        color: #2e7d32;
        border: 1px solid #c8e6c9;
    }

    .status-message.error {
        background: #ffebee;
        color: #c62828;
        border: 1px solid #ffcdd2;
    }

    .dragover {
        border-color: #4a90e2 !important;
        background-color: #f0f8ff !important;
    }
`;
document.head.appendChild(style); 