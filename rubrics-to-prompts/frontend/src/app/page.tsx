'use client';

import React, { useState, useCallback } from 'react';
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
  Settings
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
        : 'Upload failed';
      toast.error(errorMessage);
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
    } catch {
      toast.error('Failed to get processing status');
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
        // Convert YAML to JSON for download
        content = JSON.stringify(parsedRubric, null, 2);
        filename = `${uploadedFile?.name?.split('.')[0] || 'rubric'}_prompt.json`;
        mimeType = 'application/json';
        content = new Blob([content], { type: mimeType });
      }
      
      const url = URL.createObjectURL(content);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      toast.success(`${format.toUpperCase()} file downloaded successfully!`);
    } catch {
      toast.error('Download failed');
    }
  };

  const saveEditedYaml = async () => {
    if (!taskId) return;
    
    try {
      await axios.post(`${API_BASE_URL}/update-yaml/${taskId}`, {
        yaml_content: editedYaml
      });
      
      toast.success('Changes saved successfully!');
      setIsEditing(false);
      
      // Update local result
      if (result) {
        setResult({
          ...result,
          yaml_content: editedYaml
        });
      }
    } catch (error) {
      const errorMessage = axios.isAxiosError(error) && error.response?.data?.detail 
        ? error.response.data.detail 
        : 'Failed to save changes';
      toast.error(errorMessage);
    }
  };

  const resetProcess = () => {
    setUploadedFile(null);
    setTaskId(null);
    setProcessingStatus(null);
    setResult(null);
    setIsEditing(false);
    setEditedYaml('');
    setShowPreview(false);
    setParsedRubric(null);
    setCurrentView('upload');
  };

  const updateRubricItem = (sectionIndex: number, itemIndex: number, field: string, value: string | number) => {
    if (!parsedRubric) return;
    
    const updated = { ...parsedRubric };
    if (field === 'description' || field === 'criteria') {
      updated.sections[sectionIndex].items[itemIndex][field] = value as string;
    } else if (field === 'points') {
      updated.sections[sectionIndex].items[itemIndex][field] = value as number;
    }
    
    setParsedRubric(updated);
    
    // Update the YAML content
    const yamlContent = `rubric_info:
  title: "${updated.rubric_info.title}"
  total_points: ${updated.rubric_info.total_points}
  description: "${updated.rubric_info.description}"

sections:
${updated.sections.map(section => `  - section_name: "${section.section_name}"
    section_id: "${section.section_id}"
    description: "${section.description}"
    items:
${section.items.map(item => `      - item_id: "${item.item_id}"
        description: "${item.description}"
        points: ${item.points}
        criteria: "${item.criteria}"`).join('\n')}`).join('\n')}`;
    
    setEditedYaml(yamlContent);
  };

  return (
    <div className="min-h-screen bg-white">
      <Toaster position="top-right" />
      
      {/* Header */}
      <header className="bg-white border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="oski-heading text-3xl text-gray-900">PromptGen</h1>
              <p className="text-gray-600 mt-1">OSCE Rubric Converter</p>
            </div>
            {currentView === 'dashboard' && (
              <button
                onClick={resetProcess}
                className="oski-button-secondary"
              >
                <RotateCcw className="w-4 h-4" />
                New Rubric
              </button>
            )}
          </div>
        </div>
      </header>

      <AnimatePresence mode="wait">
        {currentView === 'upload' ? (
          <motion.div
            key="upload"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
          >
            {/* Hero Section */}
            <section className="py-20 bg-gradient-to-br from-gray-50 to-white">
              <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                <h2 className="oski-heading text-5xl text-gray-900 mb-6">
                  Upload your OSCE Rubric
                </h2>
                <p className="text-xl text-gray-600 mb-12 max-w-2xl mx-auto">
                  Transform traditional rubrics into structured assessment prompts with intelligent processing
                </p>

                {/* Upload Area */}
                <div className="max-w-lg mx-auto">
                  <div 
                    {...getRootProps()} 
                    className={`oski-upload-area p-12 text-center cursor-pointer ${
                      isDragActive ? 'drag-active' : ''
                    }`}
                  >
                    <input {...getInputProps()} />
                    <Upload className="w-16 h-16 mx-auto mb-6 text-gray-400" />
                    {uploadedFile ? (
                      <div className="space-y-2">
                        <p className="text-lg font-semibold text-gray-900">{uploadedFile.name}</p>
                        <p className="text-sm text-gray-500">
                          {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                        <p className="text-xs text-gray-400">Click to change file</p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <p className="text-lg font-semibold text-gray-900">
                          Drag or drop your files here or click to upload
                        </p>
                        <p className="text-sm text-gray-500">
                          Supports PDF, Word, Excel, text files, and images
                        </p>
                      </div>
                    )}
                  </div>

                  {uploadedFile && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="mt-8"
                    >
                      <button
                        onClick={uploadAndProcess}
                        disabled={!!processingStatus}
                        className="oski-button-primary w-full text-lg py-4"
                      >
                        {processingStatus ? (
                          <>
                            <RefreshCw className="w-5 h-5 animate-spin" />
                            Processing Rubric...
                          </>
                        ) : (
                          <>
                            <Settings className="w-5 h-5" />
                            Process Rubric
                          </>
                        )}
                      </button>
                    </motion.div>
                  )}
                </div>

                {/* Processing Status */}
                {processingStatus && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-12 max-w-2xl mx-auto"
                  >
                    <div className="oski-card">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold text-gray-900">Processing Status</h3>
                        <span className="text-sm text-gray-500">
                          {Math.round(processingStatus.progress)}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
                        <div 
                          className="bg-black h-2 rounded-full transition-all duration-500" 
                          style={{ width: `${processingStatus.progress}%` }}
                        />
                      </div>
                      <p className="text-gray-600">{processingStatus.message}</p>
                    </div>
                  </motion.div>
                )}
              </div>
            </section>
          </motion.div>
        ) : (
          <motion.div
            key="dashboard"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
          >
            {/* Dashboard */}
            <section className="py-8">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                {/* Dashboard Header */}
                <div className="oski-card mb-8">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                        <CheckCircle className="w-6 h-6 text-green-600" />
                      </div>
                      <div>
                        <h2 className="oski-heading text-2xl text-gray-900">Rubric Ready</h2>
                        <p className="text-gray-600">
                          {parsedRubric?.rubric_info?.title || 'OSCE Assessment Rubric'}
                        </p>
                      </div>
                    </div>
                    <div className="flex space-x-3">
                      <button
                        onClick={() => setShowPreview(!showPreview)}
                        className="oski-button-secondary"
                      >
                        {showPreview ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        {showPreview ? 'Hide Code' : 'View Code'}
                      </button>
                      <button
                        onClick={() => downloadFile('yaml')}
                        className="oski-button-secondary"
                      >
                        <FileDown className="w-4 h-4" />
                        Export YAML
                      </button>
                      <button
                        onClick={() => downloadFile('json')}
                        className="oski-button-primary"
                      >
                        <Download className="w-4 h-4" />
                        Export JSON
                      </button>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                  {/* Rubric Editor */}
                  <div className="lg:col-span-2">
                    <div className="oski-card">
                      <h3 className="text-xl font-semibold text-gray-900 mb-6">Assessment Sections</h3>
                      <div className="space-y-6">
                        {parsedRubric?.sections.map((section, sectionIndex) => (
                          <motion.div
                            key={section.section_id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: sectionIndex * 0.1 }}
                            className="border border-gray-200 rounded-lg p-6"
                          >
                            <h4 className="font-semibold text-gray-900 mb-4">{section.section_name}</h4>
                            <p className="text-gray-600 text-sm mb-4">{section.description}</p>
                            <div className="space-y-4">
                              {section.items.map((item, itemIndex) => (
                                <div key={item.item_id} className="border-l-4 border-gray-100 pl-4">
                                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    <div className="md:col-span-2">
                                      <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Description
                                      </label>
                                      <textarea
                                        value={item.description}
                                        onChange={(e) => updateRubricItem(sectionIndex, itemIndex, 'description', e.target.value)}
                                        className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent"
                                        rows={2}
                                      />
                                    </div>
                                    <div>
                                      <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Points
                                      </label>
                                      <input
                                        type="number"
                                        value={item.points}
                                        onChange={(e) => updateRubricItem(sectionIndex, itemIndex, 'points', parseInt(e.target.value) || 0)}
                                        className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent"
                                      />
                                    </div>
                                  </div>
                                  <div className="mt-4">
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                      Assessment Criteria
                                    </label>
                                    <textarea
                                      value={item.criteria}
                                      onChange={(e) => updateRubricItem(sectionIndex, itemIndex, 'criteria', e.target.value)}
                                      className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent"
                                      rows={2}
                                    />
                                  </div>
                                </div>
                              ))}
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Summary & Actions */}
                  <div className="space-y-6">
                    {/* Summary Card */}
                    <div className="oski-card">
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">Assessment Summary</h3>
                      <div className="space-y-3">
                        <div className="flex justify-between">
                          <span className="text-gray-600">Total Sections:</span>
                          <span className="font-semibold">{parsedRubric?.sections.length || 0}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Total Items:</span>
                          <span className="font-semibold">
                            {parsedRubric?.sections.reduce((acc, section) => acc + section.items.length, 0) || 0}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Total Points:</span>
                          <span className="font-semibold">{parsedRubric?.rubric_info?.total_points || 0}</span>
                        </div>
                      </div>
                    </div>

                    {/* Export Options */}
                    <div className="oski-card">
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">Export Options</h3>
                      <div className="space-y-3">
                        <button
                          onClick={() => downloadFile('yaml')}
                          className="w-full oski-button-secondary justify-start"
                        >
                          <FileText className="w-4 h-4" />
                          Download YAML File
                        </button>
                        <button
                          onClick={() => downloadFile('json')}
                          className="w-full oski-button-primary justify-start"
                        >
                          <FileDown className="w-4 h-4" />
                          Download JSON File
                        </button>
                      </div>
                    </div>

                    {/* Save Changes */}
                    {editedYaml !== result?.yaml_content && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="oski-card border-orange-200 bg-orange-50"
                      >
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="text-lg font-semibold text-orange-900">Unsaved Changes</h3>
                          <button
                            onClick={saveEditedYaml}
                            className="oski-button-primary"
                          >
                            <Save className="w-4 h-4" />
                            Save
                          </button>
                        </div>
                        <p className="text-sm text-orange-700">
                          You have unsaved changes to your rubric. Save them before downloading.
                        </p>
                      </motion.div>
                    )}
                  </div>
                </div>

                {/* Code Preview */}
                <AnimatePresence>
                  {showPreview && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mt-8"
                    >
                      <div className="oski-card">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="text-lg font-semibold text-gray-900">Generated Code</h3>
                          <div className="flex space-x-2">
                            <button
                              onClick={() => setIsEditing(!isEditing)}
                              className={`oski-button-secondary ${isEditing ? 'bg-black text-white' : ''}`}
                            >
                              <Edit3 className="w-4 h-4" />
                              {isEditing ? 'View Only' : 'Edit Code'}
                            </button>
                          </div>
                        </div>
                        <div className="border rounded-lg overflow-hidden">
                          <MonacoEditor
                            height="400px"
                            language="yaml"
                            value={isEditing ? editedYaml : result?.yaml_content}
                            onChange={(value) => isEditing && setEditedYaml(value || '')}
                            theme="vs-light"
                            options={{
                              readOnly: !isEditing,
                              minimap: { enabled: false },
                              lineNumbers: 'on',
                              wordWrap: 'on',
                              automaticLayout: true,
                              fontSize: 14,
                              fontFamily: 'var(--font-geist-mono), monospace'
                            }}
                          />
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </section>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
