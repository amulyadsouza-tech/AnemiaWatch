// Resolve backend base URL cleanly:
// 1. If VITE_API_URL is configured, use it.
// 2. If in production (Vercel) and VITE_API_URL was omitted at build time,
//    fallback to the deployed Render backend so requests never hit Vercel static hosting (which returns 405).
// 3. In local dev (localhost), leave empty so Vite dev proxy handles /api → localhost:8000.
const envBackend = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '');
const isVercelHost = typeof window !== 'undefined' && (
  window.location.hostname.endsWith('.vercel.app') ||
  window.location.hostname.includes('vercel')
);

const DEFAULT_RENDER_BACKEND = 'https://anemiawatch-backend.onrender.com';

let normalizedBackend = envBackend;
if (!normalizedBackend && (isVercelHost || import.meta.env.PROD)) {
  normalizedBackend = DEFAULT_RENDER_BACKEND;
}

if (normalizedBackend.endsWith('/api')) {
  normalizedBackend = normalizedBackend.slice(0, -4);
}

export const BACKEND_BASE = normalizedBackend;
export const API_BASE = BACKEND_BASE ? `${BACKEND_BASE}/api` : '/api';

/**
 * Converts a relative image URL returned by the backend (/api/screening/file/...)
 * into an absolute URL using the same BACKEND_BASE.
 * If the URL is already absolute (starts with http), it is returned as-is.
 */
export function getImageUrl(relativeUrl: string | null | undefined): string {
  if (!relativeUrl) return '';
  if (relativeUrl.startsWith('http')) return relativeUrl;
  return `${BACKEND_BASE}${relativeUrl}`;
}

export async function ensureAuthToken(): Promise<string> {
  let token = localStorage.getItem('anemiawatch_token');
  if (!token) {
    try {
      const res = await fetch(`${API_BASE}/auth/guest`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.access_token) {
          localStorage.setItem('anemiawatch_token', data.access_token);
          token = data.access_token;
        }
      }
    } catch {
      // ignore network errors during preflight
    }
  }
  return token || '';
}

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('anemiawatch_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T = any>(
  endpoint: string,
  options: RequestInit = {},
  fallbackError = 'System error occurred'
): Promise<T> {
  let res: Response;
  const targetUrl = `${API_BASE}${endpoint}`;
  try {
    res = await fetch(targetUrl, options);
  } catch (err: any) {
    throw new Error(
      'Unable to connect to the backend service. If using Render free tier, the server may take 30-60 seconds to spin up from sleep. Please try again shortly.'
    );
  }

  let json: any = null;
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      json = await res.json();
    } catch {
      json = null;
    }
  }

  if (!res.ok) {
    let errorMsg = fallbackError;
    if (json) {
      if (typeof json.detail === 'string') {
        errorMsg = json.detail;
      } else if (Array.isArray(json.detail)) {
        // FastAPI 422 validation array
        errorMsg = json.detail
          .map((d: any) => `${d.loc?.slice(-1)[0] || 'input'}: ${d.msg}`)
          .join(', ');
      } else if (json.message) {
        errorMsg = json.message;
      }
    } else {
      if (res.status === 405) {
        errorMsg = 'Method not allowed (405). The request was rejected by the server or routed to the frontend host instead of the API backend. Please ensure VITE_API_URL points to the backend.';
      } else if (res.status === 500) {
        errorMsg = 'Internal server or database error (500). Please check backend database logs.';
      } else if (res.status === 502 || res.status === 503 || res.status === 504) {
        errorMsg = 'Backend service is currently unavailable or starting up (Render free tier may take ~30s to wake up). Please try again shortly.';
      } else if (res.status === 404) {
        errorMsg = 'API endpoint not found (404). Please verify backend service URL.';
      } else if (res.status === 401) {
        errorMsg = 'Session expired or invalid email/password.';
      } else {
        errorMsg = `Server returned HTTP status ${res.status}`;
      }
    }
    throw new Error(errorMsg);
  }

  if (json !== null) {
    return json as T;
  }

  return {} as T;
}

export const api = {
  // Health
  async getHealth() {
    return request('/health', {}, 'Backend health check failed');
  },

  // Auth
  async register(data: any) {
    return request('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }, 'Registration failed');
  },

  async login(data: any) {
    return request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }, 'Login failed');
  },

  async guestLogin() {
    return request('/auth/guest', {
      method: 'POST',
    }, 'Guest login failed');
  },

  async getMe() {
    return request('/auth/me', {
      headers: { ...getAuthHeader() },
    }, 'Session expired');
  },

  async updateProfile(data: any) {
    return request('/auth/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify(data),
    }, 'Failed to update profile');
  },

  // Screening
  async screenNail(file: File) {
    await ensureAuthToken();
    const formData = new FormData();
    formData.append('file', file);
    return request('/screening/nail', {
      method: 'POST',
      headers: { ...getAuthHeader() },
      body: formData,
    }, 'Failed to process fingernail screening');
  },

  async screenConjunctiva(file: File) {
    await ensureAuthToken();
    const formData = new FormData();
    formData.append('file', file);
    return request('/screening/conjunctiva', {
      method: 'POST',
      headers: { ...getAuthHeader() },
      body: formData,
    }, 'Failed to process conjunctiva screening');
  },

  async getHistory() {
    return request('/screening/history', {
      headers: { ...getAuthHeader() },
    }, 'Failed to load screening history');
  },

  async getScreeningDetail(id: number | string) {
    return request(`/screening/detail/${id}`, {
      headers: { ...getAuthHeader() },
    }, 'Failed to load screening details');
  },

  async getArticles() {
    return request('/screening/articles', {}, 'Failed to load articles');
  },

  getPdfUrl(id: number | string) {
    const token = localStorage.getItem('anemiawatch_token');
    const base = `${BACKEND_BASE}/api`;
    return token
      ? `${base}/screening/${id}/pdf?token=${encodeURIComponent(token)}`
      : `${base}/screening/${id}/pdf`;
  },

  // Doctor
  async getDoctorDashboard() {
    return request('/doctor/dashboard', {
      headers: { ...getAuthHeader() },
    }, 'Failed to load doctor dashboard');
  },

  async getDoctorPatients(search?: string) {
    const endpoint = search
      ? `/doctor/patients?search=${encodeURIComponent(search)}`
      : '/doctor/patients';
    return request(endpoint, {
      headers: { ...getAuthHeader() },
    }, 'Failed to load patient list');
  },

  async getDoctorPatientDetail(id: number) {
    return request(`/doctor/patient/${id}`, {
      headers: { ...getAuthHeader() },
    }, 'Failed to load patient history');
  },
};
