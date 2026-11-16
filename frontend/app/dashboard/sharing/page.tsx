"use client"

import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import OutgoingRequests from './OutgoingRequests';

const card = "bg-dark-800 border border-slate-700 rounded-xl p-6 space-y-4";
const btn = "px-3 py-1.5 text-sm rounded font-medium transition-colors disabled:opacity-50";

function HexBox({ hex, max = 192 }: { hex: string; max?: number }) {
  const [full, setFull] = useState(false);
  return (
    <div>
      <pre className="font-mono text-xs p-2 rounded bg-dark-900 border border-slate-700 whitespace-pre-wrap break-all text-amber-300">
        {full || hex.length <= max ? hex : hex.slice(0, max) + '…'}
      </pre>
      {hex.length > max && (
        <button onClick={() => setFull(!full)} className="text-xs text-slate-400 hover:text-slate-200">
          {full ? 'Collapse' : `Show all ${hex.length / 2} bytes`}
        </button>
      )}
    </div>
  );
}

export default function SharingPage() {
  const [vault, setVault] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [incoming, setIncoming] = useState<any[]>([]);
  const [outgoing, setOutgoing] = useState<any[]>([]);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState({ text: '', type: '' });
  const [issued, setIssued] = useState<any>(null);
  const [copied, setCopied] = useState(false);

  const load = async () => {
    try {
      const [v, u, i, o] = await Promise.all([
        api.getMyKeys(), api.listUsers(), api.incomingRequests(), api.outgoingRequests(),
      ]);
      setVault(v); setUsers(u); setIncoming(i); setOutgoing(o);
    } catch (err: any) {
      setMsg({ text: err.message, type: 'error' });
    }
  };

  useEffect(() => { load(); }, []);

  const act = async (key: string, fn: () => Promise<any>, ok?: string) => {
    setBusy(key); setMsg({ text: '', type: '' });
    try {
      const res = await fn();
      if (ok) setMsg({ text: ok, type: 'success' });
      await load();
      return res;
    } catch (err: any) {
      setMsg({ text: err.message, type: 'error' });
    } finally {
      setBusy(null);
    }
  };

  const approve = async (r: any) => {
    const res = await act(r.id, () => api.approveRequest(r.id));
    if (res) { setIssued({ ...res, requester: r.requester_username, owner: r.owner_username }); setCopied(false); }
  };

  const showToken = (r: any) => {
    setIssued({
      rsa_encrypted_key_b64: r.rsa_encrypted_key_b64, key_fingerprint: r.key_fingerprint,
      requester: r.requester_username, owner: r.owner_username,
      wrapped_key_hex: vault?.wrapped_keys?.find((w: any) => w.access_request_id === r.id)?.wrapped_key_hex,
    });
    setCopied(false);
  };

  const shareText = (i: any) =>
    `🔐 SecureVault — Encrypted Access Key\n` +
    `From: ${i.owner} → To: ${i.requester}\n` +
    `This key is RSA-2048-OAEP encrypted with YOUR public key. Only you can decrypt it.\n` +
    `Paste it in SecureVault › Shared With Me:\n\n${i.rsa_encrypted_key_b64}`;

  const downloadKey = (i: any) => {
    const blob = new Blob([i.rsa_encrypted_key_b64], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `securevault_${i.owner}_to_${i.requester}.key`;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  };

  const pending = incoming.filter(r => r.status === 'PENDING');
  const history = incoming.filter(r => r.status !== 'PENDING');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">🔑 Key Management & Sharing</h1>
        <p className="text-slate-400 text-sm">
          RSA-2048-OAEP key distribution + envelope encryption (KEK → DEK). Stallings Ch. 9.1 & 10.1 · OWASP Key Management.
        </p>
      </div>

      {msg.text && (
        <div className={`p-3 rounded text-sm border ${msg.type === 'error'
          ? 'bg-red-500/10 border-red-500/30 text-red-400' : 'bg-green-500/10 border-green-500/30 text-green-400'}`}>
          {msg.text}
        </div>
      )}

      {/* ---------- Section A ---------- */}
      <section className={card}>
        <h2 className="text-lg font-semibold">A · My Cryptographic Key Vault</h2>
        {!vault ? <p className="text-slate-500 text-sm">Loading…</p> : (
          <>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-slate-300 mb-1">
                  RSA-{vault.rsa_key_bits} Public Key (PEM, stored in plaintext)
                </div>
                <pre className="font-mono text-[11px] p-2 rounded bg-dark-900 border border-slate-700 whitespace-pre-wrap break-all text-green-300 max-h-56 overflow-auto">
                  {vault.rsa_public_key}
                </pre>
                <div className="text-xs text-slate-500 mt-1">SHA-256 fingerprint: <code>{vault.rsa_public_key_fingerprint}</code></div>
              </div>
              <div>
                <div className="text-sm text-slate-300 mb-1">
                  Encrypted RSA Private Key in DB ({vault.rsa_private_key_encrypted_bytes} bytes, hex)
                </div>
                <HexBox hex={vault.rsa_private_key_encrypted_hex} max={480} />
                <div className="text-xs text-slate-500 mt-1">Wrap: {vault.rsa_private_key_wrap} · Padding: {vault.rsa_padding}</div>
              </div>
            </div>

            <div>
              <div className="text-sm text-slate-300 mb-2">Wrapped Symmetric Keys (DEKs) stored in <code>stored_symmetric_keys</code></div>
              {vault.wrapped_keys.length === 0 ? (
                <p className="text-slate-500 text-sm">No shared DEKs yet — approve a request to generate one.</p>
              ) : (
                <div className="space-y-2">
                  {vault.wrapped_keys.map((w: any) => (
                    <div key={w.id} className="p-3 rounded bg-dark-900 border border-slate-700 text-sm space-y-1">
                      <div className="flex flex-wrap justify-between gap-2">
                        <span className="font-medium">{w.purpose}</span>
                        <span className="text-xs text-slate-500">{new Date(w.created_at + 'Z').toLocaleString()}</span>
                      </div>
                      <div className="text-xs text-slate-400">
                        DEK: {w.algorithm} · Wrapped with: {w.wrap_algorithm} · {w.wrapped_key_bytes} bytes
                        (IV 16 ‖ C 48 ‖ HMAC 32) · fingerprint <code>{w.key_fingerprint}</code>
                      </div>
                      <HexBox hex={w.wrapped_key_hex} max={160} />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </section>

      {/* ---------- Section B ---------- */}
      <section className={card}>
        <h2 className="text-lg font-semibold">B · Directory & Request Access</h2>
        {users.length === 0 ? <p className="text-slate-500 text-sm">No other users registered.</p> : (
          <div className="space-y-2">
            {users.map(u => (
              <div key={u.id} className="flex flex-wrap items-center gap-3 p-3 rounded bg-dark-900 border border-slate-700">
                <div className="min-w-[140px]">
                  <div className="font-medium">👤 {u.username}</div>
                  <div className="text-xs text-slate-500">{u.has_rsa_key ? '🔑 RSA key ready' : '⚠️ no RSA key (must log in once)'}</div>
                </div>
                <input
                  value={reasons[u.id] || ''}
                  onChange={e => setReasons(r => ({ ...r, [u.id]: e.target.value }))}
                  placeholder="Reason (e.g. HR Background Check Verification)"
                  maxLength={500}
                  className="flex-1 min-w-[200px] px-3 py-1.5 text-sm rounded bg-dark-800 border border-slate-700 focus:border-primary-500 outline-none"
                />
                <button
                  disabled={busy === `req:${u.id}`}
                  onClick={() => act(`req:${u.id}`, () => api.requestAccess(u.id, reasons[u.id]),
                    `Access request sent to ${u.username}.`)}
                  className={`${btn} bg-primary-600 hover:bg-primary-500 text-white`}
                >
                  Request Private Data Access
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ---------- Section C ---------- */}
      <section className={card}>
        <h2 className="text-lg font-semibold">C · Incoming Requests (Data Owner)</h2>
        {pending.length === 0 && <p className="text-slate-500 text-sm">No pending requests.</p>}
        {pending.map(r => (
          <div key={r.id} className="flex flex-wrap items-center justify-between gap-3 p-3 rounded bg-dark-900 border border-yellow-500/30">
            <div>
              <div className="font-medium">{r.requester_username} wants to see your private data</div>
              {r.reason && <div className="text-sm text-slate-400">“{r.reason}”</div>}
            </div>
            <div className="flex gap-2">
              <button disabled={busy === r.id} onClick={() => approve(r)}
                className={`${btn} bg-green-600 hover:bg-green-500 text-white`}>
                {busy === r.id ? 'Generating & encrypting…' : '✅ Approve & Generate Key'}
              </button>
              <button disabled={busy === r.id} onClick={() => act(r.id, () => api.denyRequest(r.id), 'Request denied.')}
                className={`${btn} border border-red-500/40 text-red-400 hover:bg-red-500/10`}>
                Deny
              </button>
            </div>
          </div>
        ))}

        {history.length > 0 && (
          <div className="pt-2">
            <div className="text-sm text-slate-400 mb-2">History</div>
            <table className="w-full text-sm">
              <tbody>
                {history.map(r => (
                  <tr key={r.id} className="border-t border-slate-800">
                    <td className="py-2">{r.requester_username}</td>
                    <td className="text-slate-400">{r.reason || '—'}</td>
                    <td>{r.status}</td>
                    <td className="text-right space-x-2 whitespace-nowrap">
                      {r.status === 'APPROVED' && (
                        <>
                          <button onClick={() => showToken(r)} className={`${btn} border border-slate-600 hover:bg-dark-800`}>Re-share key</button>
                          <button disabled={busy === r.id}
                            onClick={() => confirm('Revoke access and crypto-shred the shared copy?') &&
                              act(r.id, () => api.revokeRequest(r.id), 'Access revoked; shared ciphertexts and wrapped DEK deleted.')}
                            className={`${btn} border border-red-500/40 text-red-400 hover:bg-red-500/10`}>Revoke</button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ---------- Section D ---------- */}
      <section className={card}>
        <h2 className="text-lg font-semibold">D · Outgoing Requests / Shared With Me</h2>
        <OutgoingRequests requests={outgoing} onRefresh={load} />
      </section>

      {/* ---------- Issued key modal ---------- */}
      {issued && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4" onClick={() => setIssued(null)}>
          <div className="bg-dark-800 border border-slate-700 rounded-xl p-6 max-w-2xl w-full space-y-4 max-h-[90vh] overflow-auto"
            onClick={e => e.stopPropagation()}>
            <div className="flex justify-between">
              <h3 className="text-lg font-semibold">🔐 Encrypted Key Token for {issued.requester}</h3>
              <button onClick={() => setIssued(null)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            <p className="text-sm text-slate-400">
              A fresh 256-bit Shared Symmetric Key was generated, your PII & files were re-encrypted with it
              (AES-256-CBC + HMAC-SHA256), and it was encrypted with <b>{issued.requester}</b>&apos;s RSA-2048 public key (OAEP-SHA256).
              Send this token through any channel — it is useless without their private key.
            </p>
            {issued.shared_file_count !== undefined && (
              <div className="text-xs text-slate-400">
                Shared: PII fields [{(issued.shared_pii_fields || []).join(', ') || 'none'}] · {issued.shared_file_count} file(s)
              </div>
            )}
            <div>
              <div className="text-sm text-slate-300 mb-1">RSA-Encrypted Key (Base64, 256-byte ciphertext)</div>
              <textarea readOnly rows={5} value={issued.rsa_encrypted_key_b64}
                className="w-full font-mono text-xs p-2 rounded bg-dark-900 border border-slate-700" />
            </div>
            <div className="flex flex-wrap gap-2">
              <button onClick={async () => { await navigator.clipboard.writeText(issued.rsa_encrypted_key_b64); setCopied(true); }}
                className={`${btn} bg-slate-600 hover:bg-slate-500 text-white`}>{copied ? '✔ Copied' : '📋 Copy Encrypted Key (Base64)'}</button>
              <a target="_blank" rel="noreferrer"
                href={`https://wa.me/?text=${encodeURIComponent(shareText(issued))}`}
                className={`${btn} bg-green-600 hover:bg-green-500 text-white`}>💬 Send via WhatsApp</a>
              <a href={`mailto:?subject=${encodeURIComponent('SecureVault – RSA-Encrypted Access Key')}&body=${encodeURIComponent(shareText(issued))}`}
                className={`${btn} bg-blue-600 hover:bg-blue-500 text-white`}>✉️ Send via Email</a>
              <button onClick={() => downloadKey(issued)}
                className={`${btn} border border-slate-600 hover:bg-dark-900`}>⬇️ Download .key File</button>
            </div>
            {issued.wrapped_key_hex && (
              <div>
                <div className="text-sm text-slate-300 mb-1">Same DEK as stored in DB (wrapped by your KEK, hex)</div>
                <HexBox hex={issued.wrapped_key_hex} max={400} />
              </div>
            )}
            <div className="text-xs text-slate-500">DEK fingerprint: <code>{issued.key_fingerprint}</code></div>
          </div>
        </div>
      )}
    </div>
  );
}
