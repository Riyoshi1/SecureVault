"use client"

import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import OutgoingRequests from '../sharing/OutgoingRequests';

export default function SharedWithMePage() {
  const [outgoing, setOutgoing] = useState<any[]>([]);
  const [error, setError] = useState('');

  const load = async () => {
    try { setOutgoing(await api.outgoingRequests()); } catch (e: any) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">📨 Shared With Me / Access Requests</h1>
        <p className="text-slate-400 text-sm">
          Paste the RSA-encrypted key you received via WhatsApp / Email. Your private key (unwrapped with your session
          Master Key) decrypts it to recover the Shared Symmetric Key, which then decrypts the owner&apos;s data.
        </p>
      </div>
      {error && <div className="p-3 rounded text-sm bg-red-500/10 border border-red-500/30 text-red-400">{error}</div>}
      <div className="bg-dark-800 border border-slate-700 rounded-xl p-6">
        <OutgoingRequests requests={outgoing} onRefresh={load} />
      </div>
    </div>
  );
}
