"use client"

import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import Link from 'next/link';

interface FileData {
  id: string;
  original_filename: string;
  file_category: string;
  algorithm: string;
  original_size: number;
  created_at: string;
}

export default function Dashboard() {
  const [files, setFiles] = useState<FileData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchFiles = async () => {
    try {
      setLoading(true);
      const data = await api.listFiles();
      setFiles(data.files || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch files');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  const handleDownload = async (id: string, filename: string) => {
    try {
      await api.downloadFile(id, filename);
    } catch (err: any) {
      alert(err.message || 'Download failed');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this file?')) return;
    
    try {
      await api.deleteFile(id);
      fetchFiles();
    } catch (err: any) {
      alert(err.message || 'Delete failed');
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getAlgorithmColor = (algo: string) => {
    if (algo.includes('AES')) return 'text-green-400 bg-green-400/10 border-green-400/20';
    if (algo.includes('DES')) return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20';
    if (algo.includes('RC4')) return 'text-orange-400 bg-orange-400/10 border-orange-400/20';
    return 'text-slate-400 bg-slate-400/10 border-slate-400/20';
  };

  const getFileIcon = (category: string) => {
    switch (category) {
      case 'image': return '🖼️';
      case 'document': return '📄';
      case 'video': return '🎬';
      default: return '📎';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">My Secure Files</h1>
          <p className="text-slate-400">Manage and decrypt your encrypted files.</p>
        </div>
        <Link 
          href="/dashboard/upload" 
          className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
        >
          <span>⬆️</span> Upload File
        </Link>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/50 text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 bg-dark-800 rounded-lg border border-slate-700"></div>
          ))}
        </div>
      ) : files.length === 0 ? (
        <div className="text-center py-16 px-4 border-2 border-dashed border-slate-700 rounded-xl bg-dark-800/50">
          <div className="text-4xl mb-4">📭</div>
          <h3 className="text-xl font-semibold mb-2">No files yet</h3>
          <p className="text-slate-400 mb-6">Your vault is empty. Upload some files to secure them.</p>
          <Link 
            href="/dashboard/upload" 
            className="px-6 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg font-medium transition-colors"
          >
            Upload First File
          </Link>
        </div>
      ) : (
        <div className="bg-dark-800 border border-slate-700 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-dark-900 border-b border-slate-700 text-slate-400">
                <tr>
                  <th className="px-6 py-4 font-medium">Filename</th>
                  <th className="px-6 py-4 font-medium">Algorithm</th>
                  <th className="px-6 py-4 font-medium">Size</th>
                  <th className="px-6 py-4 font-medium">Date</th>
                  <th className="px-6 py-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {files.map((file) => (
                  <tr key={file.id} className="hover:bg-dark-900/50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <span className="text-xl">{getFileIcon(file.file_category)}</span>
                        <span className="font-medium text-slate-200">{file.original_filename}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-medium border ${getAlgorithmColor(file.algorithm)}`}>
                        {file.algorithm}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-400">
                      {formatSize(file.original_size)}
                    </td>
                    <td className="px-6 py-4 text-slate-400">
                      {new Date(file.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right space-x-3">
                      <button 
                        onClick={() => handleDownload(file.id, file.original_filename)}
                        className="text-primary-400 hover:text-primary-300 font-medium"
                      >
                        Download
                      </button>
                      <button 
                        onClick={() => handleDelete(file.id)}
                        className="text-red-400 hover:text-red-300 font-medium"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
