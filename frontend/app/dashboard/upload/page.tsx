"use client"

import { useState, useRef } from 'react';
import { api } from '../../lib/api';
import { useRouter } from 'next/navigation';

export default function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [algorithm, setAlgorithm] = useState('AES-CBC');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      processFile(selected);
    }
  };

  const processFile = (selectedFile: File) => {
    // Check extensions (optional client validation based on requirements)
    const validTypes = ['image/jpeg', 'image/png', 'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'video/mp4'];
    
    setFile(selectedFile);
    setError('');

    // Create preview for images
    if (selectedFile.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onloadend = () => setPreview(reader.result as string);
      reader.readAsDataURL(selectedFile);
    } else {
      setPreview(null);
    }
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    
    setLoading(true);
    setError('');
    
    try {
      await api.uploadFile(file, algorithm);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Upload & Encrypt</h1>
        <p className="text-slate-400">Select a file and an encryption algorithm to secure it.</p>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/50 text-red-400">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          {/* Dropzone */}
          <div 
            className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors cursor-pointer
              ${isDragging ? 'border-primary-500 bg-primary-500/10' : 'border-slate-700 bg-dark-800 hover:border-slate-500'}
              ${file ? 'border-green-500/50 bg-green-500/5' : ''}
            `}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileChange} 
              className="hidden" 
              accept=".jpg,.jpeg,.png,.pdf,.doc,.docx,.xls,.xlsx,.mp4"
            />
            
            {preview ? (
              <div className="flex flex-col items-center">
                <img src={preview} alt="Preview" className="max-h-48 rounded-lg mb-4 shadow-lg" />
                <p className="font-medium text-green-400">{file?.name}</p>
                <p className="text-sm text-slate-400 mt-1">{(file?.size! / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            ) : file ? (
              <div className="flex flex-col items-center">
                <div className="text-5xl mb-4">📄</div>
                <p className="font-medium text-green-400">{file.name}</p>
                <p className="text-sm text-slate-400 mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            ) : (
              <div className="flex flex-col items-center pointer-events-none">
                <div className="text-5xl mb-4 text-slate-500">📁</div>
                <h3 className="text-lg font-semibold mb-2">Drag & Drop your file here</h3>
                <p className="text-slate-400 text-sm mb-4">or click to browse from your computer</p>
                <p className="text-xs text-slate-500">
                  Accepted formats: JPG, PNG, PDF, DOC, DOCX, XLS, XLSX, MP4
                </p>
              </div>
            )}
          </div>

          <button 
            onClick={handleUpload}
            disabled={!file || loading}
            className="w-full py-3 bg-primary-600 hover:bg-primary-500 text-white rounded-lg font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-2"
          >
            {loading ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Encrypting & Uploading...
              </>
            ) : (
              <>🔒 Encrypt & Upload</>
            )}
          </button>
        </div>

        {/* Algorithm Selection */}
        <div className="space-y-4">
          <h3 className="font-semibold text-lg border-b border-slate-700 pb-2">Encryption Algorithm</h3>
          
          <div className="space-y-3">
            <label className={`block cursor-pointer rounded-xl border p-4 transition-colors ${
              algorithm === 'AES-CBC' ? 'border-green-500 bg-green-500/10' : 'border-slate-700 bg-dark-800 hover:border-slate-600'
            }`}>
              <div className="flex items-center gap-3 mb-2">
                <input 
                  type="radio" 
                  name="algorithm" 
                  value="AES-CBC" 
                  checked={algorithm === 'AES-CBC'} 
                  onChange={(e) => setAlgorithm(e.target.value)}
                  className="w-4 h-4 text-green-500 bg-dark-900 border-slate-600 focus:ring-green-500 focus:ring-2"
                />
                <span className="font-semibold text-green-400">AES-256-CBC</span>
              </div>
              <p className="text-xs text-slate-400 pl-7">Highly secure, standard symmetric encryption. Best for all types of files.</p>
            </label>

            <label className={`block cursor-pointer rounded-xl border p-4 transition-colors ${
              algorithm === 'DES-CBC' ? 'border-yellow-500 bg-yellow-500/10' : 'border-slate-700 bg-dark-800 hover:border-slate-600'
            }`}>
              <div className="flex items-center gap-3 mb-2">
                <input 
                  type="radio" 
                  name="algorithm" 
                  value="DES-CBC" 
                  checked={algorithm === 'DES-CBC'} 
                  onChange={(e) => setAlgorithm(e.target.value)}
                  className="w-4 h-4 text-yellow-500 bg-dark-900 border-slate-600 focus:ring-yellow-500 focus:ring-2"
                />
                <span className="font-semibold text-yellow-400">DES-CBC</span>
              </div>
              <p className="text-xs text-slate-400 pl-7">Legacy 56-bit encryption. Included for academic and benchmark purposes.</p>
            </label>

            <label className={`block cursor-pointer rounded-xl border p-4 transition-colors ${
              algorithm === 'RC4' ? 'border-orange-500 bg-orange-500/10' : 'border-slate-700 bg-dark-800 hover:border-slate-600'
            }`}>
              <div className="flex items-center gap-3 mb-2">
                <input 
                  type="radio" 
                  name="algorithm" 
                  value="RC4" 
                  checked={algorithm === 'RC4'} 
                  onChange={(e) => setAlgorithm(e.target.value)}
                  className="w-4 h-4 text-orange-500 bg-dark-900 border-slate-600 focus:ring-orange-500 focus:ring-2"
                />
                <span className="font-semibold text-orange-400">RC4</span>
              </div>
              <p className="text-xs text-slate-400 pl-7">Fast stream cipher. Known vulnerabilities exist, use only for testing.</p>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
