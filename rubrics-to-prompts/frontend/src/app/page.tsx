'use client';

import React, { useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { 
  Upload, 
  FileText, 
  Download, 
  Edit3, 
  CheckCircle, 
  RefreshCw,
  Eye,
  EyeOff,
  Save,
  RotateCcw,
  FileDown,
  Settings,
  ArrowDown,
  Plus,
  X,
  Home
} from 'lucide-react';
import axios from 'axios';
import toast, { Toaster } from 'react-hot-toast';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'framer-motion';

// Dynamically import Monaco Editor to avoid SSR issues
const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false });

interface ProcessingStatus {
  step: string;
  message: string;
  progress: number;
  completed?: boolean;
}

interface ProcessingResult {
  original_text: string;
  yaml_content: string;
  parsed_yaml: Record<string, unknown>;
  filename: string;
}

interface RubricSection {
  section_name: string;
  section_id: string;
  description: string;
  items: RubricItem[];
}

interface RubricItem {
  item_id: string;
  description: string;
  points: number;
  criteria: string;
}

interface ParsedRubric {
  rubric_info: {
    title: string;
    total_points: number;
    description: string;
  };
  sections: RubricSection[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function PromptGen() {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus | null>(null);
  const [result, setResult] = useState<ProcessingResult | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedYaml, setEditedYaml] = useState('');
  const [showPreview, setShowPreview] = useState(false);
  const [parsedRubric, setParsedRubric] = useState<ParsedRubric | null>(null);
  const [currentView, setCurrentView] = useState<'upload' | 'dashboard'>('upload');

  // Ref for smooth scrolling
  const uploadSectionRef = useRef<HTMLElement>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      setUploadedFile(file);
      setResult(null);
      setTaskId(null);
      setProcessingStatus(null);
      setParsedRubric(null);
      setCurrentView('upload');
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'text/plain': ['.txt'],
      'text/csv': ['.csv'],
      'image/*': ['.png', '.jpg', '.jpeg']
    },
    multiple: false,
    maxSize: 50 * 1024 * 1024 // 50MB
  });

  const uploadAndProcess = async () => {
    if (!uploadedFile) {
      toast.error('Please select a file first');
      return;
    }

    const formData = new FormData();
    formData.append('file', uploadedFile);

    try {
      const response = await axios.post(`${API_BASE_URL}/upload-rubric`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      const { task_id } = response.data;
      setTaskId(task_id);
      
      toast.success('File uploaded successfully! Processing...');
      
      // Start polling for status
      pollStatus(task_id);
    } catch (error) {
      const errorMessage = axios.isAxiosError(error) && error.response?.data?.detail 
        ? error.response.data.detail 
        : 'Upload failed - please ensure the backend server is running';
      toast.error(errorMessage);
      console.error('Upload error:', error);
    }
  };

  const pollStatus = async (id: string) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/status/${id}`);
      const data = response.data;
      
      setProcessingStatus({
        step: data.step,
        message: data.message,
        progress: data.progress,
        completed: data.status === 'completed'
      });

      if (data.status === 'completed' && data.result) {
        setResult(data.result);
        setEditedYaml(data.result.yaml_content);
        
        // Parse the YAML for dashboard view
        try {
          const parsed = data.result.parsed_yaml as ParsedRubric;
          setParsedRubric(parsed);
          setCurrentView('dashboard');
        } catch (error) {
          console.error('Failed to parse rubric:', error);
        }
        
        toast.success('Rubric processed successfully!');
      } else if (data.status === 'error') {
        toast.error(data.error || data.message || 'Processing failed');
        setProcessingStatus(null);
      } else if (data.status === 'processing') {
        // Continue polling
        setTimeout(() => pollStatus(id), 2000);
      } else {
        toast.error('Unknown processing status');
        setProcessingStatus(null);
      }
    } catch (error) {
      console.error('Status polling error:', error);
      toast.error('Failed to get processing status - please check backend connection');
    }
  };

  const downloadFile = async (format: 'yaml' | 'json') => {
    if (!taskId) return;
    
    try {
      let content, filename, mimeType;
      
      if (format === 'yaml') {
        const response = await axios.get(`${API_BASE_URL}/download-yaml/${taskId}`, {
          responseType: 'blob'
        });
        content = response.data;
        filename = `${uploadedFile?.name?.split('.')[0] || 'rubric'}_prompt.yaml`;
        mimeType = 'application/x-yaml';
      } else {
        const response = await axios.get(`${API_BASE_URL}/download-json/${taskId}`, {
          responseType: 'blob'
        });
        content = response.data;
        filename = `${uploadedFile?.name?.split('.')[0] || 'rubric'}_prompt.json`;
        mimeType = 'application/json';
      }

      const blob = new Blob([content], { type: mimeType });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success(`${format.toUpperCase()} file downloaded successfully!`);
    } catch (error) {
      toast.error(`Failed to download ${format.toUpperCase()} file`);
      console.error('Download error:', error);
    }
  };

  const saveEditedYaml = async () => {
    if (!taskId || !editedYaml) return;
    
    try {
      await axios.post(`${API_BASE_URL}/update-yaml/${taskId}`, {
        yaml_content: editedYaml
      });
      
      toast.success('Changes saved successfully!');
      setIsEditing(false);
    } catch (error) {
      toast.error('Failed to save changes');
      console.error('Save error:', error);
    }
  };

  const resetProcess = () => {
    setUploadedFile(null);
    setResult(null);
    setTaskId(null);
    setProcessingStatus(null);
    setIsEditing(false);
    setEditedYaml('');
    setShowPreview(false);
    setParsedRubric(null);
    setCurrentView('upload');
  };

  const updateRubricItem = (sectionIndex: number, itemIndex: number, field: string, value: string | number) => {
    if (!parsedRubric) return;
    
    const updated = { ...parsedRubric };
    if (field === 'description') {
      updated.sections[sectionIndex].items[itemIndex].description = value as string;
    } else if (field === 'points') {
      updated.sections[sectionIndex].items[itemIndex].points = value as number;
    } else if (field === 'criteria') {
      updated.sections[sectionIndex].items[itemIndex].criteria = value as string;
    }
    
    setParsedRubric(updated);
  };

  const addRubricItem = (sectionIndex: number) => {
    if (!parsedRubric) return;
    
    const updated = { ...parsedRubric };
    const newItem: RubricItem = {
      item_id: `item_${Date.now()}`,
      description: 'New rubric item',
      points: 1,
      criteria: 'Add criteria here'
    };
    updated.sections[sectionIndex].items.push(newItem);
    setParsedRubric(updated);
  };

  const removeRubricItem = (sectionIndex: number, itemIndex: number) => {
    if (!parsedRubric) return;
    
    const updated = { ...parsedRubric };
    updated.sections[sectionIndex].items.splice(itemIndex, 1);
    setParsedRubric(updated);
  };

  const NavigationHeader = () => (
    <motion.header 
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white/95 backdrop-blur-sm border-b border-gray-100 sticky top-0 z-50"
    >
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <motion.a 
              href="/" 
              className="oski-button-secondary flex items-center gap-2 text-sm"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Home size={16} />
              Back to Oski
            </motion.a>
            <div className="h-6 w-px bg-gray-300" />
            <h1 className="oski-heading text-2xl font-semibold text-gray-900">PromptGen</h1>
          </div>
          
          {currentView === 'dashboard' && (
            <motion.button
              onClick={resetProcess}
              className="oski-button-secondary flex items-center gap-2 text-sm"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Plus size={16} />
              New Upload
            </motion.button>
          )}
        </div>
      </div>
    </motion.header>
  );

  const FileUploadSection = () => (
    <motion.section 
      ref={uploadSectionRef}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="min-h-screen flex items-center justify-center px-6 py-12"
    >
      <div className="max-w-2xl w-full">
        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-center mb-12"
        >
          <h2 className="oski-heading text-4xl font-semibold text-gray-900 mb-4">
            Transform Your OSCE Rubric
          </h2>
          <p className="text-lg text-gray-600 max-w-xl mx-auto">
            Upload your OSCE rubric and let our AI convert it into structured, ready-to-use prompts for assessment automation.
          </p>
        </motion.div>

        <div
          {...getRootProps()}
          className={`oski-upload-area p-12 text-center cursor-pointer transition-all duration-300 ${
            isDragActive ? 'drag-active scale-105' : ''
          }`}
        >
          <motion.div
            whileHover={{ scale: 1.02 }}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.4 }}
            className="w-full h-full"
          >
          <input {...getInputProps()} />
          
          <motion.div
            animate={{ 
              rotateY: isDragActive ? 180 : 0,
              scale: isDragActive ? 1.1 : 1 
            }}
            transition={{ duration: 0.3 }}
            className="mb-6"
          >
            <div className="w-20 h-20 mx-auto bg-gradient-to-br from-gray-100 to-gray-200 rounded-2xl flex items-center justify-center mb-4">
              <Upload className="w-10 h-10 text-gray-600" />
            </div>
          </motion.div>

          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            {isDragActive ? 'Drop your rubric here' : 'Upload your OSCE Rubric'}
          </h3>
          
          <p className="text-gray-600 mb-6">
            Drag and drop your files here or click to upload
          </p>

          {uploadedFile ? (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-gray-50 rounded-xl p-4 mb-6 inline-flex items-center gap-3"
            >
              <FileText className="w-5 h-5 text-gray-600" />
              <span className="font-medium text-gray-900">{uploadedFile.name}</span>
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  setUploadedFile(null);
                }}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X size={16} />
              </button>
            </motion.div>
          ) : (
            <div className="text-sm text-gray-500 mb-6">
              Supports PDF, Word, Excel, images, and text files
            </div>
          )}

          {uploadedFile && !processingStatus && (
            <motion.button
              onClick={(e) => {
                e.stopPropagation();
                uploadAndProcess();
              }}
              className="oski-button-primary"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              Process Rubric
                         </motion.button>
           )}
           </motion.div>
         </div>

         {processingStatus && (
           <ProcessingIndicator status={processingStatus} />
         )}
       </div>
     </motion.section>
   );

  const ProcessingIndicator = ({ status }: { status: ProcessingStatus }) => (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-8 oski-card max-w-md mx-auto"
    >
      <div className="flex items-center gap-4 mb-4">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          className="w-8 h-8 border-2 border-gray-300 border-t-black rounded-full"
        />
        <div>
          <h4 className="font-semibold text-gray-900">{status.step}</h4>
          <p className="text-sm text-gray-600">{status.message}</p>
        </div>
      </div>
      
      <div className="w-full bg-gray-200 rounded-full h-2">
        <motion.div 
          className="bg-black h-2 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${status.progress}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>
      
      <div className="mt-2 text-xs text-gray-500 text-right">
        {Math.round(status.progress)}% complete
      </div>
    </motion.div>
  );

  const RubricDashboard = () => {
    if (!parsedRubric) return null;

    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6 }}
        className="min-h-screen py-12 px-6"
      >
        <div className="max-w-6xl mx-auto">
          {/* Dashboard Header */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-center mb-12"
          >
            <h2 className="oski-heading text-3xl font-semibold text-gray-900 mb-4">
              Rubric Dashboard
            </h2>
            <p className="text-lg text-gray-600">
              Review and edit your processed rubric content before exporting
            </p>
          </motion.div>

          {/* Rubric Info Card */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="oski-card mb-8"
          >
            <div className="flex items-start justify-between mb-6">
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {parsedRubric.rubric_info.title}
                </h3>
                <p className="text-gray-600 mb-4">
                  {parsedRubric.rubric_info.description}
                </p>
                <div className="inline-flex items-center gap-2 bg-gray-100 rounded-full px-4 py-2">
                  <span className="text-sm font-medium text-gray-900">
                    Total Points: {parsedRubric.rubric_info.total_points}
                  </span>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Rubric Sections */}
          <div className="space-y-6 mb-8">
            {parsedRubric.sections.map((section, sectionIndex) => (
              <motion.div
                key={section.section_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + sectionIndex * 0.1 }}
                className="oski-section-divider p-6"
              >
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-lg font-semibold text-gray-900">
                    {section.section_name}
                  </h4>
                  <motion.button
                    onClick={() => addRubricItem(sectionIndex)}
                    className="oski-button-secondary flex items-center gap-2 text-sm"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <Plus size={14} />
                    Add Item
                  </motion.button>
                </div>
                
                <p className="text-gray-600 mb-6">{section.description}</p>
                
                <div className="space-y-4">
                  {section.items.map((item, itemIndex) => (
                    <motion.div
                      key={item.item_id}
                      layout
                      className="bg-white border border-gray-200 rounded-xl p-4"
                    >
                      <div className="flex items-start gap-4">
                        <div className="flex-1 space-y-3">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Description
                            </label>
                            <input
                              type="text"
                              value={item.description}
                              onChange={(e) => updateRubricItem(sectionIndex, itemIndex, 'description', e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-all"
                            />
                          </div>
                          
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                Points
                              </label>
                              <input
                                type="number"
                                value={item.points}
                                onChange={(e) => updateRubricItem(sectionIndex, itemIndex, 'points', parseInt(e.target.value) || 0)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-all"
                                min="0"
                              />
                            </div>
                            
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                Criteria
                              </label>
                              <input
                                type="text"
                                value={item.criteria}
                                onChange={(e) => updateRubricItem(sectionIndex, itemIndex, 'criteria', e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-all"
                              />
                            </div>
                          </div>
                        </div>
                        
                        <motion.button
                          onClick={() => removeRubricItem(sectionIndex, itemIndex)}
                          className="text-gray-400 hover:text-red-500 transition-colors p-1"
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                        >
                          <X size={18} />
                        </motion.button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>

          {/* Export Section */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="oski-card text-center"
          >
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              Export Your Rubric
            </h3>
            <p className="text-gray-600 mb-6">
              Download your processed rubric in the format you need
            </p>
            
            <div className="flex flex-wrap gap-4 justify-center">
              <motion.button
                onClick={() => downloadFile('yaml')}
                className="oski-button-primary flex items-center gap-2"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <FileDown size={18} />
                Download YAML File
              </motion.button>
              
              <motion.button
                onClick={() => downloadFile('json')}
                className="oski-button-secondary flex items-center gap-2"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <FileDown size={18} />
                Download JSON File
              </motion.button>
            </div>
          </motion.div>
        </div>
      </motion.div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-white via-gray-50 to-white">
      <NavigationHeader />
      
      <AnimatePresence mode="wait">
        {currentView === 'upload' ? (
          <FileUploadSection key="upload" />
        ) : (
          <RubricDashboard key="dashboard" />
        )}
      </AnimatePresence>

      <Toaster
        position="bottom-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#ffffff',
            color: '#000000',
            border: '1px solid #e5e7eb',
            borderRadius: '12px',
            boxShadow: '0 10px 40px rgba(0, 0, 0, 0.1)',
          },
        }}
      />
    </div>
  );
}
