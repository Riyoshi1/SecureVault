"use client"

import { useState, useEffect } from 'react';
import { api } from '../../lib/api';

export default function Profile() {
  const [formData, setFormData] = useState({
    full_name: '',
    nik: '',
    date_of_birth: '',
    address: ''
  });
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [message, setMessage] = useState({ text: '', type: '' });

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const data = await api.getPrivateData();
      if (data) {
        setFormData({
          full_name: data.full_name || '',
          nik: data.nik || '',
          date_of_birth: data.date_of_birth || '',
          address: data.address || ''
        });
      }
    } catch (err) {
      console.error("Failed to load profile", err);
    } finally {
      setInitialLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ text: '', type: '' });
    
    try {
      await api.updatePrivateData(formData);
      setMessage({ text: 'Profile successfully encrypted and saved.', type: 'success' });
    } catch (err: any) {
      setMessage({ text: err.message || 'Failed to update profile', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  if (initialLoading) {
    return <div className="animate-pulse space-y-4">
      <div className="h-10 w-1/4 bg-dark-800 rounded"></div>
      <div className="h-64 bg-dark-800 rounded-xl"></div>
    </div>;
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Personal Identifiable Information (PII)</h1>
        <p className="text-slate-400">Securely store your sensitive personal data.</p>
      </div>

      <div className="bg-blue-900/20 border border-blue-500/30 rounded-xl p-4 flex gap-4 items-start">
        <div className="text-2xl">🛡️</div>
        <div>
          <h3 className="font-semibold text-blue-400">Data Privacy & Compliance</h3>
          <p className="text-sm text-slate-300 mt-1">
            In compliance with GDPR and UU PDP, all sensitive data entered here is automatically encrypted using 
            <strong className="text-green-400 ml-1">AES-256-CBC</strong> before being stored in the database. 
            The backend only sees ciphertext.
          </p>
        </div>
      </div>

      {message.text && (
        <div className={`p-4 rounded-lg border ${
          message.type === 'success' 
            ? 'bg-green-500/10 border-green-500/50 text-green-400' 
            : 'bg-red-500/10 border-red-500/50 text-red-400'
        }`}>
          {message.text}
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-dark-800 border border-slate-700 rounded-xl p-6 space-y-5">
        <div className="flex justify-between items-center mb-6 pb-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold">Secure Profile Data</h2>
          <span className="px-3 py-1 bg-green-500/10 border border-green-500/30 text-green-400 rounded-full text-xs font-medium flex items-center gap-1">
            🔒 AES-256-CBC Encrypted
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-300">Full Name</label>
            <input 
              type="text" 
              name="full_name"
              value={formData.full_name}
              onChange={handleChange}
              placeholder="e.g. John Doe"
              className="w-full px-4 py-2 bg-dark-900 border border-slate-700 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
            />
          </div>
          
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-300">NIK (National ID)</label>
            <input 
              type="text" 
              name="nik"
              value={formData.nik}
              onChange={handleChange}
              placeholder="16-digit ID number"
              className="w-full px-4 py-2 bg-dark-900 border border-slate-700 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none font-mono"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-300">Date of Birth</label>
          <input 
            type="date" 
            name="date_of_birth"
            value={formData.date_of_birth}
            onChange={handleChange}
            className="w-full md:w-1/2 px-4 py-2 bg-dark-900 border border-slate-700 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none [color-scheme:dark]"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-300">Residential Address</label>
          <textarea 
            name="address"
            value={formData.address}
            onChange={handleChange}
            rows={3}
            placeholder="Full street address..."
            className="w-full px-4 py-2 bg-dark-900 border border-slate-700 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none resize-none"
          />
        </div>

        <div className="pt-4 flex justify-end">
          <button 
            type="submit" 
            disabled={loading}
            className="px-6 py-2.5 bg-primary-600 hover:bg-primary-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? 'Encrypting & Saving...' : 'Encrypt & Save'}
          </button>
        </div>
      </form>
    </div>
  );
}
