"use client"

import { useState } from 'react';
import { useAuth } from '../lib/auth';
import { api } from '../lib/api';
import Link from 'next/link';

export default function Register() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (!/^[A-Za-z0-9_]{3,30}$/.test(username)) {
      setError("Username 3-30 karakter: huruf, angka, atau underscore");
      return;
    }
    if (password.length < 6) {
      setError("Password minimal 6 karakter");
      return;
    }
    if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      setError("Password harus mengandung huruf dan angka");
      return;
    }

    setLoading(true);
    
    try {
      const data = await api.register({ username, password });
      register(data.access_token);
    } catch (err: any) {
      setError(err.message || 'Failed to register');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md p-8 rounded-2xl bg-dark-800 border border-slate-700 shadow-xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-foreground flex justify-center items-center gap-2">
            🛡️ SecureVault
          </h1>
          <p className="text-slate-400 mt-2">Create a new secure account.</p>
        </div>
        
        {error && (
          <div className="mb-4 p-3 rounded bg-red-500/10 border border-red-500/50 text-red-400 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Username</label>
            <input 
              type="text" 
              required
              minLength={3}
              maxLength={30}
              className="w-full px-4 py-2 bg-dark-900 border border-slate-700 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none text-foreground"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Password</label>
            <input 
              type="password" 
              required
              minLength={6}
              maxLength={72}
              className="w-full px-4 py-2 bg-dark-900 border border-slate-700 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none text-foreground"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <p className="text-xs text-slate-500 mt-1">Minimal 6 karakter, kombinasi huruf dan angka.</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Confirm Password</label>
            <input 
              type="password" 
              required
              className="w-full px-4 py-2 bg-dark-900 border border-slate-700 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none text-foreground"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>
          <button 
            type="submit" 
            disabled={loading}
            className="w-full py-2 px-4 bg-primary-600 hover:bg-primary-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
          >
            {loading ? 'Creating account...' : 'Register'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-400">
          Already have an account? <Link href="/login" className="text-blue-400 hover:text-blue-300 hover:underline font-medium">Login here</Link>
        </p>
      </div>
    </div>
  );
}
