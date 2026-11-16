"use client"

import { useState } from 'react';
import { api } from '../../lib/api';

/**
 * Section D — Outgoing Requests / Shared With Me (Requester view).
 * The requester pastes the RSA-OAEP encrypted key received via WhatsApp/Email;
 * the backend unwraps their private key, recovers the Shared DEK and decrypts
 * the owner's PII snapshot + files.
 */
export default function OutgoingRequests({ requests, onRefresh }: { requests: any[]; onRefresh?: () => void }) {
  const [keys, setKeys] = useState<Record<string, string>>({});
  const [unlocked, setUnlocked] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ url: string; mime: string; name: string } | null>(null);

  const loadKeyFile = async (id: string, file?: File) => {
    if (!file) return;
    const text = (await file.text()).trim();
    setKeys(k => ({ ...k, [id]: text }));
  };

  const unlock = async (id: string) => {
    setBusy(id);
    setErrors(e => ({ ...e, [id]: '' }));
    try {
      const data = await api.accessSharedData(id, keys[id] || '');
      setUnlocked(u => ({ ...u, [id]: data }));
    } catch (err: any) {
      setUnlocked(u => { const c = { ...u }; delete c[id]; return c; });
      setErrors(e => ({ ...e, [id]: err.message }));
    } finally {
      setBusy(null);
    }
  };

  const getFile = async (reqId: string, f: any, mode: 'preview' | 'download') => {
    setBusy(`${reqId}:${f.id}`);
    try {
      const blob = await api.fetchSharedFile(reqId, f.id, keys[reqId]);
      const url = URL.createObjectURL(new Blob([blob], { type: f.mime_type }));
      if (mode === 'preview') {
        setPreview({ url, mime: f.mime_type, name: f.original_filename });
      } else {
        const a = document.createElement('a');
        a.href = url; a.download = f.original_filename;
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
    } catch (err: any) {
      setErrors(e => ({ ...e, [reqId]: err.message }));
    } finally {
      setBusy(null);
    }
  };

  const badge = (s: string) => ({
    PENDING: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
    APPROVED: 'bg-green-500/10 text-green-400 border-green-500/30',
    DENIED: 'bg-red-500/10 text-red-400 border-red-500/30',
    REVOKED: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
  } as any)[s] || '';

  const previewable = (m: string) => m.startsWith('image/') || m.startsWith('video/') || m === 'application/pdf';

  if (!requests.length) return <p className="text-slate-500 text-sm">You have not sent any access requests yet.</p>;

  return (
    <div className="space-y-4">
      {requests.map(r => (
        <div key={r.id} className="p-4 rounded-lg bg-dark-900 border border-slate-700 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <span className="font-semibold">To: {r.owner_username}</span>
              {r.reason && <span className="text-slate-400 text-sm"> — “{r.reason}”</span>}
              <div className="text-xs text-slate-500">{new Date(r.created_at + 'Z').toLocaleString()}</div>
            </div>
            <span className={`text-xs px-2 py-1 rounded border ${badge(r.status)}`}>{r.status}</span>
          </div>

          {r.status === 'APPROVED' && (
            <div className="space-y-2">
              <label className="text-sm text-slate-300">Paste RSA-Encrypted Symmetric Key (from WA/Email)</label>
              <textarea
                rows={3}
                value={keys[r.id] || ''}
                onChange={e => setKeys(k => ({ ...k, [r.id]: e.target.value }))}
                placeholder="Base64 RSA-OAEP ciphertext…"
                className="w-full font-mono text-xs p-2 rounded bg-dark-800 border border-slate-700 focus:border-primary-500 outline-none"
              />
              <div className="flex flex-wrap gap-2 items-center">
                <button
                  onClick={() => unlock(r.id)}
                  disabled={busy === r.id || !(keys[r.id] || '').trim()}
                  className="px-4 py-2 rounded bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-sm font-medium"
                >
                  {busy === r.id ? 'Decrypting…' : '🔓 Unlock Private Data & Files'}
                </button>
                <label className="text-xs text-slate-400 cursor-pointer hover:text-slate-200">
                  or load .key file
                  <input type="file" accept=".key,.txt" className="hidden" onChange={e => loadKeyFile(r.id, e.target.files?.[0])} />
                </label>
              </div>
              {errors[r.id] && (
                <div className="p-2 rounded text-sm bg-red-500/10 border border-red-500/30 text-red-400">❌ {errors[r.id]}</div>
              )}
            </div>
          )}

          {unlocked[r.id] && (
            <div className="space-y-3 pt-2 border-t border-slate-700">
              <div className="text-xs text-green-400">
                ✅ RSA-OAEP decrypted → Shared DEK fingerprint <code>{unlocked[r.id].key_fingerprint}</code> → AES-256-CBC + HMAC verified
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                {[['Full Name', 'full_name'], ['NIK', 'nik'], ['Date of Birth', 'date_of_birth'], ['Address', 'address']].map(([label, k]) => (
                  <div key={k} className="p-3 rounded bg-dark-800 border border-slate-700">
                    <div className="text-xs text-slate-500">{label}</div>
                    <div className="font-medium break-words">{unlocked[r.id].pii[k] || <span className="text-slate-600">—</span>}</div>
                  </div>
                ))}
              </div>
              <table className="w-full text-sm">
                <thead className="text-slate-400 text-left">
                  <tr><th className="py-1">File</th><th>Type</th><th>Orig. Alg.</th><th>Size</th><th></th></tr>
                </thead>
                <tbody>
                  {unlocked[r.id].files.length === 0 && (
                    <tr><td colSpan={5} className="py-2 text-slate-500">No files shared.</td></tr>
                  )}
                  {unlocked[r.id].files.map((f: any) => (
                    <tr key={f.id} className="border-t border-slate-800">
                      <td className="py-2 break-all">{f.original_filename}</td>
                      <td>{f.file_category}</td>
                      <td>{f.source_algorithm}</td>
                      <td>{(f.original_size / 1024).toFixed(1)} KB</td>
                      <td className="text-right space-x-2 whitespace-nowrap">
                        {previewable(f.mime_type) && (
                          <button onClick={() => getFile(r.id, f, 'preview')} disabled={!!busy}
                            className="px-2 py-1 text-xs rounded border border-slate-600 hover:bg-dark-800">Preview</button>
                        )}
                        <button onClick={() => getFile(r.id, f, 'download')} disabled={!!busy}
                          className="px-2 py-1 text-xs rounded bg-primary-600 hover:bg-primary-500 text-white">
                          {busy === `${r.id}:${f.id}` ? '…' : 'Decrypt & Download'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ))}

      {onRefresh && (
        <button onClick={onRefresh} className="text-xs text-slate-400 hover:text-slate-200">↻ Refresh</button>
      )}

      {preview && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
          onClick={() => { URL.revokeObjectURL(preview.url); setPreview(null); }}>
          <div className="bg-dark-800 rounded-xl p-4 max-w-4xl w-full max-h-[90vh] overflow-auto" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between mb-3">
              <span className="font-semibold break-all">{preview.name}</span>
              <button onClick={() => { URL.revokeObjectURL(preview.url); setPreview(null); }} className="text-slate-400 hover:text-white">✕</button>
            </div>
            {preview.mime.startsWith('image/') && <img src={preview.url} alt={preview.name} className="max-w-full mx-auto" />}
            {preview.mime.startsWith('video/') && <video src={preview.url} controls className="w-full" />}
            {preview.mime === 'application/pdf' && <iframe src={preview.url} className="w-full h-[75vh]" />}
          </div>
        </div>
      )}
    </div>
  );
}
