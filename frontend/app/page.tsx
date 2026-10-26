"use client"

import Link from 'next/link';
import { useAuth } from './lib/auth';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const { token, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (token) {
      router.push('/dashboard');
    }
  }, [token, router]);

  if (isLoading) return <div className="min-h-screen flex items-center justify-center bg-background">Loading...</div>;

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
      <div className="max-w-4xl w-full text-center space-y-8">
        
        <div className="space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <span>⚖️ UU PDP No. 27/2022 & GDPR Compliant</span>
          </div>
          <h1 className="text-5xl font-extrabold text-foreground tracking-tight flex items-center justify-center gap-3">
            🛡️ SecureVault HR e-KYC
          </h1>
          <p className="text-lg text-slate-300 max-w-2xl mx-auto">
            Sistem Brankas Digital Terenkripsi untuk Onboarding Karyawan & Verifikasi e-KYC Institusi Finansial.
          </p>
          <p className="text-sm text-slate-400 max-w-xl mx-auto">
            Melindungi Data Pribadi (PII), Pindaian KTP/Paspor, Dokumen Perkantoran (Kontrak/Slip Gaji), dan Video Verifikasi dengan implementasi <strong>AES-256-CBC</strong>, <strong>DES-CBC</strong>, dan <strong>RC4</strong>.
          </p>
        </div>

        <div className="flex justify-center gap-4 pt-8">
          <Link href="/login" className="px-8 py-3 rounded-lg bg-primary-600 hover:bg-primary-500 text-white font-medium transition-colors">
            Login
          </Link>
          <Link href="/register" className="px-8 py-3 rounded-lg bg-dark-800 hover:bg-slate-700 text-white border border-slate-700 font-medium transition-colors">
            Register
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-16 mt-8 border-t border-slate-800">
          <div className="p-6 rounded-xl bg-dark-800/50 border border-slate-800 text-left">
            <h3 className="text-lg font-semibold text-green-400 mb-2">AES-256-CBC</h3>
            <p className="text-sm text-slate-400">Advanced Encryption Standard. The industry standard for secure data encryption.</p>
          </div>
          <div className="p-6 rounded-xl bg-dark-800/50 border border-slate-800 text-left">
            <h3 className="text-lg font-semibold text-yellow-400 mb-2">DES-CBC</h3>
            <p className="text-sm text-slate-400">Data Encryption Standard. Legacy encryption algorithm for compatibility testing.</p>
          </div>
          <div className="p-6 rounded-xl bg-dark-800/50 border border-slate-800 text-left">
            <h3 className="text-lg font-semibold text-orange-400 mb-2">RC4</h3>
            <p className="text-sm text-slate-400">Rivest Cipher 4. Stream cipher known for its speed in software implementations.</p>
          </div>
        </div>

      </div>
    </div>
  );
}
