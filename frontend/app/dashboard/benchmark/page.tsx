"use client"

import { useState } from 'react';
import { api } from '../../lib/api';

interface BenchmarkResult {
  algorithm: string;
  encrypt_avg_ms: number;
  decrypt_avg_ms: number;
  ciphertext_size_bytes: number;
  data_size_bytes: number;
}

interface InspectItem {
  algorithm: string;
  mode: string;
  block_size_bits: number;
  key_size_bits: number;
  plaintext_size_bytes: number;
  total_output_bytes: number;
  iv_or_nonce_hex: string;
  iv_or_nonce_bytes: number;
  ciphertext_hex: string;
  ciphertext_bytes: number;
  padding_bytes: number;
  hmac_hex: string;
  hmac_bytes: number;
  encrypt_time_ms: number;
  decrypt_time_ms: number;
}

interface InspectResponse {
  plaintext: string;
  plaintext_hex: string;
  items: InspectItem[];
}

export default function Benchmark() {
  const [dataSize, setDataSize] = useState('100');
  const [iterations, setIterations] = useState('10');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<BenchmarkResult[] | null>(null);
  const [error, setError] = useState('');

  const [sampleText, setSampleText] = useState('Rahasia Negara - Kuliah Keamanan Informasi 2026');
  const [inspectLoading, setInspectLoading] = useState(false);
  const [inspectData, setInspectData] = useState<InspectResponse | null>(null);

  const handleInspect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sampleText.trim()) return;
    setInspectLoading(true);
    setError('');
    try {
      const data = await api.inspectCiphers(sampleText);
      setInspectData(data);
    } catch (err: any) {
      setError(err.message || 'Cipher inspection failed');
    } finally {
      setInspectLoading(false);
    }
  };

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResults(null);
    
    try {
      const data = await api.runBenchmark({
        data_size_kb: parseInt(dataSize),
        iterations: parseInt(iterations)
      });
      setResults(data.results);
    } catch (err: any) {
      setError(err.message || 'Benchmark failed');
    } finally {
      setLoading(false);
    }
  };

  const getAlgoColor = (algo: string) => {
    if (algo === 'AES-CBC') return 'bg-green-500';
    if (algo === 'DES-CBC') return 'bg-yellow-500';
    if (algo === 'RC4') return 'bg-orange-500';
    return 'bg-blue-500';
  };

  const formatTime = (ms: number) => {
    if (ms < 0.1) return '< 0.1 ms';
    return ms.toFixed(2) + ' ms';
  };

  const formatSize = (bytes: number) => {
    return (bytes / 1024).toFixed(2) + ' KB';
  };

  // Calculate max values for bar charts
  const maxEncrypt = results ? Math.max(...results.map(r => r.encrypt_avg_ms)) : 1;
  const maxDecrypt = results ? Math.max(...results.map(r => r.decrypt_avg_ms)) : 1;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Cryptography Benchmark</h1>
        <p className="text-slate-400">Compare performance metrics of different encryption algorithms.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-6">
          <form onSubmit={handleRun} className="bg-dark-800 border border-slate-700 rounded-xl p-6 space-y-4">
            <h3 className="font-semibold text-lg border-b border-slate-700 pb-2">Configuration</h3>
            
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-300">Data Size (KB)</label>
              <select 
                value={dataSize}
                onChange={(e) => setDataSize(e.target.value)}
                className="w-full px-4 py-2 bg-dark-900 border border-slate-700 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none text-foreground appearance-none"
              >
                <option value="1">1 KB (Tiny text)</option>
                <option value="10">10 KB (Small document)</option>
                <option value="100">100 KB (Image/PDF)</option>
                <option value="500">500 KB (Medium file)</option>
                <option value="1000">1000 KB (1 MB file)</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-300">Iterations (Loops)</label>
              <select 
                value={iterations}
                onChange={(e) => setIterations(e.target.value)}
                className="w-full px-4 py-2 bg-dark-900 border border-slate-700 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none text-foreground appearance-none"
              >
                <option value="5">5 Iterations (Faster)</option>
                <option value="10">10 Iterations (Standard)</option>
                <option value="20">20 Iterations (More accurate)</option>
                <option value="50">50 Iterations (Stress test)</option>
              </select>
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="w-full pt-4 mt-2 py-2.5 bg-primary-600 hover:bg-primary-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              {loading ? 'Running Benchmark...' : 'Run Benchmark ⚡'}
            </button>
          </form>

          <div className="bg-dark-800/50 border border-slate-700 rounded-xl p-5 text-sm text-slate-300 space-y-3">
            <h4 className="font-semibold text-foreground flex items-center gap-2">ℹ️ How it works</h4>
            <p>The backend generates random binary data of the specified size and runs encryption and decryption operations repeatedly.</p>
            <p>The average time taken across all iterations is measured to provide a reliable performance metric.</p>
            <p><strong>Note:</strong> Block ciphers (AES/DES) use padding, so ciphertext will be slightly larger than plaintext.</p>
          </div>
        </div>

        <div className="lg:col-span-2">
          {error && (
            <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/50 text-red-400">
              {error}
            </div>
          )}

          {loading ? (
            <div className="h-full min-h-[400px] flex flex-col items-center justify-center bg-dark-800 border border-slate-700 rounded-xl">
              <div className="animate-spin text-5xl mb-4">⚙️</div>
              <p className="text-slate-400 animate-pulse">Running intense calculations on the server...</p>
            </div>
          ) : results ? (
            <div className="space-y-6">
              {/* Table */}
              <div className="bg-dark-800 border border-slate-700 rounded-xl overflow-hidden">
                <table className="w-full text-left text-sm">
                  <thead className="bg-dark-900 border-b border-slate-700 text-slate-400">
                    <tr>
                      <th className="px-6 py-4 font-medium">Algorithm</th>
                      <th className="px-6 py-4 font-medium">Encrypt Avg</th>
                      <th className="px-6 py-4 font-medium">Decrypt Avg</th>
                      <th className="px-6 py-4 font-medium">Output Size</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700/50">
                    {results.map((r, i) => (
                      <tr key={i} className="hover:bg-dark-900/50">
                        <td className="px-6 py-4 font-medium">
                          <span className={`inline-block w-2 h-2 rounded-full mr-2 ${getAlgoColor(r.algorithm)}`}></span>
                          {r.algorithm}
                        </td>
                        <td className="px-6 py-4 text-slate-300">{formatTime(r.encrypt_avg_ms)}</td>
                        <td className="px-6 py-4 text-slate-300">{formatTime(r.decrypt_avg_ms)}</td>
                        <td className="px-6 py-4 text-slate-300">
                          {formatSize(r.ciphertext_size_bytes)} 
                          {r.ciphertext_size_bytes > r.data_size_bytes && <span className="text-xs text-slate-500 ml-1">(+{r.ciphertext_size_bytes - r.data_size_bytes}B overhead)</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Charts */}
              <div className="bg-dark-800 border border-slate-700 rounded-xl p-6 space-y-8">
                <div>
                  <h3 className="text-sm font-semibold text-slate-400 mb-4 uppercase tracking-wider">Encryption Time (Lower is better)</h3>
                  <div className="space-y-3">
                    {results.map((r, i) => (
                      <div key={i} className="flex items-center gap-4">
                        <div className="w-24 text-sm font-medium">{r.algorithm}</div>
                        <div className="flex-1 bg-dark-900 rounded-full h-4 overflow-hidden relative">
                          <div 
                            className={`h-full ${getAlgoColor(r.algorithm)} rounded-full transition-all duration-1000`}
                            style={{ width: `${Math.max((r.encrypt_avg_ms / maxEncrypt) * 100, 1)}%` }}
                          ></div>
                        </div>
                        <div className="w-20 text-right text-sm text-slate-400">{formatTime(r.encrypt_avg_ms)}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-slate-400 mb-4 uppercase tracking-wider">Decryption Time (Lower is better)</h3>
                  <div className="space-y-3">
                    {results.map((r, i) => (
                      <div key={i} className="flex items-center gap-4">
                        <div className="w-24 text-sm font-medium">{r.algorithm}</div>
                        <div className="flex-1 bg-dark-900 rounded-full h-4 overflow-hidden relative">
                          <div 
                            className={`h-full ${getAlgoColor(r.algorithm)} rounded-full transition-all duration-1000`}
                            style={{ width: `${Math.max((r.decrypt_avg_ms / maxDecrypt) * 100, 1)}%` }}
                          ></div>
                        </div>
                        <div className="w-20 text-right text-sm text-slate-400">{formatTime(r.decrypt_avg_ms)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full min-h-[400px] flex flex-col items-center justify-center bg-dark-800 border border-slate-700 rounded-xl text-slate-400 p-8 text-center">
              <div className="text-5xl mb-4">📊</div>
              <h3 className="text-xl font-medium mb-2 text-foreground">Ready to Benchmark</h3>
              <p>Select your data size and iteration count, then run the benchmark to compare AES, DES, and RC4 performance.</p>
            </div>
          )}
        </div>
      </div>

      {/* Live Ciphertext Structure & Hex Inspector (Modules 01-05) */}
      <div className="bg-dark-800 border border-slate-700 rounded-xl p-6 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-700 pb-4">
          <div>
            <h2 className="text-xl font-bold text-foreground">🔬 Live Ciphertext Structure & Hex Inspector</h2>
            <p className="text-sm text-slate-400">
              Compare how Block Ciphers (AES-256-CBC, DES-CBC) and Stream Ciphers (RC4) transform plaintext into binary ciphertext.
            </p>
          </div>
        </div>

        <form onSubmit={handleInspect} className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={sampleText}
            onChange={(e) => setSampleText(e.target.value)}
            placeholder="Enter plaintext to inspect across AES, DES, and RC4..."
            className="flex-1 px-4 py-2.5 bg-dark-900 border border-slate-700 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none text-foreground font-mono text-sm"
          />
          <button
            type="submit"
            disabled={inspectLoading}
            className="px-6 py-2.5 bg-primary-600 hover:bg-primary-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50 whitespace-nowrap"
          >
            {inspectLoading ? 'Encrypting...' : 'Inspect Ciphertext 🔍'}
          </button>
        </form>

        {inspectData && (
          <div className="space-y-4">
            <div className="p-3 rounded-lg bg-dark-900 border border-slate-700/80 text-xs font-mono text-slate-300">
              <span className="text-slate-400">Plaintext UTF-8 ({inspectData.items[0]?.plaintext_size_bytes} bytes): </span>
              <span className="text-emerald-400 break-all">{inspectData.plaintext_hex}</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {inspectData.items.map((item) => (
                <div key={item.algorithm} className="bg-dark-900 border border-slate-700 rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span className="font-bold text-foreground">{item.algorithm}</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      Key: {item.key_size_bits}-bit | Block: {item.block_size_bits}-bit
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">{item.mode}</p>

                  <div className="text-xs space-y-2 font-mono">
                    <div>
                      <span className="text-blue-400 block font-sans font-semibold">
                        1. {item.algorithm === 'RC4' ? 'Random Nonce' : 'Initialization Vector (IV)'} ({item.iv_or_nonce_bytes} B):
                      </span>
                      <div className="p-1.5 bg-blue-500/10 border border-blue-500/20 rounded text-blue-300 break-all">
                        {item.iv_or_nonce_hex}
                      </div>
                    </div>

                    <div>
                      <span className="text-emerald-400 block font-sans font-semibold">
                        2. Ciphertext Body ({item.ciphertext_bytes} B, Padding: +{item.padding_bytes} B):
                      </span>
                      <div className="p-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded text-emerald-300 break-all max-h-24 overflow-y-auto">
                        {item.ciphertext_hex}
                      </div>
                    </div>

                    <div>
                      <span className="text-purple-400 block font-sans font-semibold">
                        3. HMAC-SHA256 Tag ({item.hmac_bytes} B - Encrypt-then-MAC):
                      </span>
                      <div className="p-1.5 bg-purple-500/10 border border-purple-500/20 rounded text-purple-300 break-all">
                        {item.hmac_hex}
                      </div>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-800 flex justify-between text-xs text-slate-400">
                    <span>Total: <strong className="text-slate-200">{item.total_output_bytes} B</strong></span>
                    <span>Enc: {item.encrypt_time_ms} ms | Dec: {item.decrypt_time_ms} ms</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
