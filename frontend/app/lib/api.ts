const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const getHeaders = (isFormData = false) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const headers: HeadersInit = {};
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }
  
  return headers;
};

const handleResponse = async (res: Response) => {
  if (!res.ok) {
    let errMessage = 'An error occurred';
    try {
      const errData = await res.json();
      if (Array.isArray(errData.detail)) {
        errMessage = errData.detail
          .map((d: any) => String(d.msg).replace(/^Value error, /, ''))
          .join('; ');
      } else {
        errMessage = errData.detail || errMessage;
      }
    } catch (e) {
      errMessage = res.statusText;
    }
    throw new Error(errMessage);
  }
  return res.json();
};

export const api = {
  register: async (data: any) => {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },
  
  login: async (data: any) => {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },
  
  getMe: async () => {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
      headers: getHeaders(),
    });
    return handleResponse(res);
  },
  
  getPrivateData: async () => {
    const res = await fetch(`${API_BASE}/api/data/private`, {
      headers: getHeaders(),
    });
    return handleResponse(res);
  },
  
  updatePrivateData: async (data: any) => {
    const res = await fetch(`${API_BASE}/api/data/private`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },
  
  uploadFile: async (file: File, algorithm: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('algorithm', algorithm);
    
    const res = await fetch(`${API_BASE}/api/files/upload`, {
      method: 'POST',
      headers: getHeaders(true), // true for FormData
      body: formData,
    });
    return handleResponse(res);
  },
  
  listFiles: async () => {
    const res = await fetch(`${API_BASE}/api/files/list`, {
      headers: getHeaders(),
    });
    return handleResponse(res);
  },
  
  downloadFile: async (id: string, filename: string) => {
    const res = await fetch(`${API_BASE}/api/files/download/${id}`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Download failed');
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },
  
  deleteFile: async (id: string) => {
    const res = await fetch(`${API_BASE}/api/files/${id}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    return handleResponse(res);
  },
  
  runBenchmark: async (data: any) => {
    const res = await fetch(`${API_BASE}/api/benchmark/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  inspectCiphers: async (plaintext: string) => {
    const res = await fetch(`${API_BASE}/api/benchmark/inspect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plaintext }),
    });
    return handleResponse(res);
  },

  // ===== Assignment 2: Key Management & Sharing =====
  getMyKeys: async () => {
    const res = await fetch(`${API_BASE}/api/sharing/my-keys`, { headers: getHeaders() });
    return handleResponse(res);
  },

  listUsers: async () => {
    const res = await fetch(`${API_BASE}/api/sharing/users`, { headers: getHeaders() });
    return handleResponse(res);
  },

  requestAccess: async (owner_id: string, reason?: string) => {
    const res = await fetch(`${API_BASE}/api/sharing/request`, {
      method: 'POST', headers: getHeaders(), body: JSON.stringify({ owner_id, reason }),
    });
    return handleResponse(res);
  },

  incomingRequests: async () => {
    const res = await fetch(`${API_BASE}/api/sharing/incoming`, { headers: getHeaders() });
    return handleResponse(res);
  },

  outgoingRequests: async () => {
    const res = await fetch(`${API_BASE}/api/sharing/outgoing`, { headers: getHeaders() });
    return handleResponse(res);
  },

  approveRequest: async (id: string) => {
    const res = await fetch(`${API_BASE}/api/sharing/approve/${id}`, { method: 'POST', headers: getHeaders() });
    return handleResponse(res);
  },

  denyRequest: async (id: string) => {
    const res = await fetch(`${API_BASE}/api/sharing/deny/${id}`, { method: 'POST', headers: getHeaders() });
    return handleResponse(res);
  },

  revokeRequest: async (id: string) => {
    const res = await fetch(`${API_BASE}/api/sharing/revoke/${id}`, { method: 'POST', headers: getHeaders() });
    return handleResponse(res);
  },

  accessSharedData: async (request_id: string, encrypted_key: string) => {
    const res = await fetch(`${API_BASE}/api/sharing/access-shared-data`, {
      method: 'POST', headers: getHeaders(), body: JSON.stringify({ request_id, encrypted_key }),
    });
    return handleResponse(res);
  },

  /** Returns the decrypted shared file as a Blob (caller decides preview vs download). */
  fetchSharedFile: async (request_id: string, file_id: string, encrypted_key: string): Promise<Blob> => {
    const res = await fetch(`${API_BASE}/api/sharing/shared-file/${file_id}`, {
      method: 'POST', headers: getHeaders(), body: JSON.stringify({ request_id, encrypted_key }),
    });
    if (!res.ok) await handleResponse(res);
    return res.blob();
  }
};
