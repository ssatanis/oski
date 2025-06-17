'use client';

import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDropzone } from 'react-dropzone';
import { 
  Upload, 
  FileText, 
  Download, 
  Edit3, 
  CheckCircle, 
  AlertCircle, 
  RefreshCw,
  Eye,
  Zap,
  Settings
} from 'lucide-react';
import axios from 'axios';
import toast, { Toaster } from 'react-hot-toast';
import dynamic from 'next/dynamic';

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
  parsed_yaml: any;
  filename: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function RubricsToPrompts() {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus | null>(null);
  const [result, setResult] = useState<ProcessingResult | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedYaml, setEditedYaml] = useState('');
  const [showPreview, setShowPreview] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      setUploadedFile(file);
      setResult(null);
      setTaskId(null);
      setProcessingStatus(null);
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
      
      toast.success('File uploaded successfully! Processing started...');
      
      // Start polling for status
      pollStatus(task_id);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Upload failed');
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
        toast.success('Processing completed successfully!');
      } else if (data.status === 'error') {
        toast.error(data.error || 'Processing failed');
        setProcessingStatus(null);
      } else {
        // Continue polling
        setTimeout(() => pollStatus(id), 2000);
      }
    } catch (error) {
      toast.error('Failed to get processing status');
    }
  };

  const downloadYaml = async () => {
    if (!taskId) return;
    
    try {
      const response = await axios.get(`${API_BASE_URL}/download-yaml/${taskId}`, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/x-yaml' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${uploadedFile?.name?.split('.')[0] || 'rubric'}_prompt.yaml`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      toast.success('YAML file downloaded successfully!');
    } catch (error) {
      toast.error('Download failed');
    }
  };

  const saveEditedYaml = async () => {
    if (!taskId) return;
    
    try {
      await axios.post(`${API_BASE_URL}/update-yaml/${taskId}`, {
        yaml_content: editedYaml
      });
      
      toast.success('YAML updated successfully!');
      setIsEditing(false);
      
      // Update local result
      if (result) {
        setResult({
          ...result,
          yaml_content: editedYaml
        });
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to save changes');
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
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-white to-gray-50">
      <Toaster position="top-right" />
      
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-white via-gray-50 to-blue-50">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-blue-100 via-white to-gray-50 opacity-70"></div>
        
        {/* Rotating Shape */}
        <div className="absolute top-1/2 right-20 transform -translate-y-1/2">
          <motion.img
            src="/images/683d91777124b040c4a5b5db-683f0aa9ed4f9367dd6c8ff1_shape-2.webp"
            alt="Rotating shape"
            className="w-96 h-96 opacity-20"
            animate={{ rotate: 360 }}
            transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
          />
        </div>
        
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center">
            <motion.h1 
              className="text-5xl font-bold text-gray-900 mb-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
            >
              Rubrics to Prompts
            </motion.h1>
            <motion.p 
              className="text-xl text-gray-600 max-w-3xl mx-auto mb-8"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              Transform OSCE rubrics into AI-ready prompts with intelligent OCR processing and automated YAML generation
            </motion.p>
            <motion.div
              className="flex justify-center space-x-4"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.4 }}
            >
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                <Zap className="w-4 h-4 mr-1" />
                AI-Powered
              </span>
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                <FileText className="w-4 h-4 mr-1" />
                OCR Processing
              </span>
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-800">
                <Settings className="w-4 h-4 mr-1" />
                YAML Generation
              </span>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Main Application */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            
            {/* Left Panel - Upload & Configuration */}
            <motion.div 
              className="bg-gradient-to-br from-indigo-600 to-purple-700 rounded-2xl p-8 text-white shadow-2xl"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8 }}
            >
              <h2 className="text-2xl font-bold mb-6">Upload Rubric</h2>
              
              {/* File Upload Area */}
              <div 
                {...getRootProps()} 
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-300 ${
                  isDragActive 
                    ? 'border-white bg-white/20' 
                    : 'border-white/50 hover:border-white hover:bg-white/10'
                }`}
              >
                <input {...getInputProps()} />
                <Upload className="w-12 h-12 mx-auto mb-4 opacity-80" />
                {uploadedFile ? (
                  <div>
                    <p className="text-lg font-semibold">{uploadedFile.name}</p>
                    <p className="text-sm opacity-80">
                      {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-lg">Drop your rubric file here</p>
                    <p className="text-sm opacity-80 mt-2">
                      Supports PDF, DOC, DOCX, XLS, XLSX, TXT, CSV, and images
                    </p>
                  </div>
                )}
              </div>

              {/* Process Button */}
              <motion.button
                onClick={uploadAndProcess}
                disabled={!uploadedFile || !!processingStatus}
                className="w-full mt-6 py-4 px-6 bg-gradient-to-r from-green-500 to-emerald-600 rounded-xl font-semibold text-white shadow-lg hover:shadow-xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {processingStatus ? (
                  <div className="flex items-center justify-center">
                    <RefreshCw className="w-5 h-5 mr-2 animate-spin" />
                    Processing...
                  </div>
                ) : (
                  'Process Rubric'
                )}
              </motion.button>

              {/* Reset Button */}
              {(uploadedFile || result) && (
                <motion.button
                  onClick={resetProcess}
                  className="w-full mt-3 py-3 px-6 bg-white/20 rounded-xl font-semibold text-white hover:bg-white/30 transition-all duration-300"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Start Over
                </motion.button>
              )}
            </motion.div>

            {/* Right Panel - Workflow & Results */}
            <motion.div 
              className="bg-white rounded-2xl p-8 shadow-xl"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8 }}
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Processing Workflow</h2>
              
              {/* Workflow Steps */}
              <div className="space-y-4">
                {[
                  { id: 'upload', name: 'File Upload', desc: 'Upload your rubric document' },
                  { id: 'file_processing', name: 'File Processing', desc: 'Analyzing document structure' },
                  { id: 'ocr_processing', name: 'OCR Extraction', desc: 'Extracting text content' },
                  { id: 'ai_generation', name: 'AI Generation', desc: 'Converting to YAML format' },
                  { id: 'validation', name: 'Validation', desc: 'Ensuring YAML structure' },
                  { id: 'completed', name: 'Completed', desc: 'Ready for download' }
                ].map((step, index) => {
                  const isActive = processingStatus?.step === step.id;
                  const isCompleted = processingStatus?.completed || (result && step.id === 'completed');
                  const isPending = !processingStatus || (processingStatus && !isActive && !isCompleted);
                  
                  return (
                    <motion.div
                      key={step.id}
                      className={`p-4 rounded-xl border-2 transition-all duration-300 ${
                        isCompleted 
                          ? 'border-green-500 bg-green-50' 
                          : isActive 
                          ? 'border-blue-500 bg-blue-50' 
                          : 'border-gray-200 bg-gray-50'
                      }`}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                    >
                      <div className="flex items-center">
                        {isCompleted ? (
                          <CheckCircle className="w-6 h-6 text-green-500 mr-3" />
                        ) : isActive ? (
                          <RefreshCw className="w-6 h-6 text-blue-500 mr-3 animate-spin" />
                        ) : (
                          <div className="w-6 h-6 rounded-full border-2 border-gray-300 mr-3"></div>
                        )}
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900">{step.name}</h3>
                          <p className="text-sm text-gray-600">{step.desc}</p>
                        </div>
                      </div>
                      
                      {isActive && processingStatus && (
                        <div className="mt-3">
                          <div className="flex justify-between text-sm text-gray-600 mb-1">
                            <span>{processingStatus.message}</span>
                            <span>{Math.round(processingStatus.progress)}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <motion.div 
                              className="bg-blue-500 h-2 rounded-full" 
                              initial={{ width: 0 }}
                              animate={{ width: `${processingStatus.progress}%` }}
                              transition={{ duration: 0.5 }}
                            />
                          </div>
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </div>
            </motion.div>
          </div>

          {/* Results Section */}
          <AnimatePresence>
            {result && (
              <motion.div
                className="mt-16"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.8 }}
              >
                <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
                  <div className="bg-gradient-to-r from-green-500 to-emerald-600 p-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <CheckCircle className="w-8 h-8 text-white mr-3" />
                        <div>
                          <h2 className="text-2xl font-bold text-white">Processing Complete!</h2>
                          <p className="text-green-100">Your YAML prompt has been generated</p>
                        </div>
                      </div>
                      <div className="flex space-x-3">
                        <motion.button
                          onClick={() => setShowPreview(!showPreview)}
                          className="flex items-center px-4 py-2 bg-white/20 rounded-lg text-white hover:bg-white/30 transition-colors"
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                        >
                          <Eye className="w-4 h-4 mr-2" />
                          {showPreview ? 'Hide' : 'Preview'}
                        </motion.button>
                        <motion.button
                          onClick={() => setIsEditing(!isEditing)}
                          className="flex items-center px-4 py-2 bg-white/20 rounded-lg text-white hover:bg-white/30 transition-colors"
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                        >
                          <Edit3 className="w-4 h-4 mr-2" />
                          Edit
                        </motion.button>
                        <motion.button
                          onClick={downloadYaml}
                          className="flex items-center px-6 py-2 bg-white text-green-600 rounded-lg font-semibold hover:bg-gray-100 transition-colors"
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                        >
                          <Download className="w-4 h-4 mr-2" />
                          Download YAML
                        </motion.button>
                      </div>
                    </div>
                  </div>

                  {/* YAML Preview/Editor */}
                  <AnimatePresence>
                    {(showPreview || isEditing) && (
                      <motion.div
                        className="p-6 border-t border-gray-200"
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.3 }}
                      >
                        {isEditing ? (
                          <div>
                            <div className="flex justify-between items-center mb-4">
                              <h3 className="text-lg font-semibold text-gray-900">Edit YAML</h3>
                              <div className="space-x-3">
                                <button
                                  onClick={() => setIsEditing(false)}
                                  className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
                                >
                                  Cancel
                                </button>
                                <button
                                  onClick={saveEditedYaml}
                                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                                >
                                  Save Changes
                                </button>
                              </div>
                            </div>
                            <div className="border rounded-lg overflow-hidden">
                              <MonacoEditor
                                height="400px"
                                language="yaml"
                                value={editedYaml}
                                onChange={(value) => setEditedYaml(value || '')}
                                theme="vs-light"
                                options={{
                                  minimap: { enabled: false },
                                  lineNumbers: 'on',
                                  wordWrap: 'on',
                                  automaticLayout: true
                                }}
                              />
                            </div>
                          </div>
                        ) : (
                          <div>
                            <h3 className="text-lg font-semibold text-gray-900 mb-4">Generated YAML Preview</h3>
                            <div className="border rounded-lg overflow-hidden">
                              <MonacoEditor
                                height="400px"
                                language="yaml"
                                value={result.yaml_content}
                                theme="vs-light"
                                options={{
                                  readOnly: true,
                                  minimap: { enabled: false },
                                  lineNumbers: 'on',
                                  wordWrap: 'on',
                                  automaticLayout: true
                                }}
                              />
                            </div>
                          </div>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 text-center text-gray-600">
        <p className="text-sm italic">
          Created by Sahaj Satani & Aarash Zakeri
        </p>
      </footer>
    </div>
  );
}
