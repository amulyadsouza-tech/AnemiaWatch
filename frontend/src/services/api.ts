// Resolve backend base URL cleanly:
// 1. If user configured a custom URL in localStorage ('anemiawatch_api_url'), use it.
// 2. If VITE_API_URL is configured, use it.
// 3. In local dev (localhost / 127.0.0.1) or same-origin SPA: use relative '' so requests go to /api
//    (proxied by Vite to localhost:8000 in dev/preview, or served directly by FastAPI).
// 4. In production on external hosts (e.g. Vercel), if no VITE_API_URL is given, use relative ''
//    so vercel.json rewrites /api/* to the deployed backend without CORS issues.
const customBackend = typeof window !== 'undefined'
  ? (localStorage.getItem('anemiawatch_api_url') || '').trim().replace(/\/+$/, '')
  : '';

const envBackend = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '');

const isLocalhost = typeof window !== 'undefined' && (
  window.location.hostname === 'localhost' ||
  window.location.hostname === '127.0.0.1' ||
  window.location.hostname === '0.0.0.0' ||
  window.location.hostname.endsWith('.local')
);

const isVercelHost = typeof window !== 'undefined' && (
  window.location.hostname.endsWith('.vercel.app') ||
  window.location.hostname.includes('vercel')
);

let normalizedBackend = customBackend || envBackend;

if (!normalizedBackend) {
  if (isLocalhost) {
    if (typeof window !== 'undefined' && (window.location.port === '5173' || window.location.port === '4173' || window.location.port === '8000')) {
      normalizedBackend = ''; // Use relative /api (handled by Vite proxy or FastAPI)
    } else {
      normalizedBackend = 'http://localhost:8000';
    }
  } else if (isVercelHost) {
    // On Vercel: use relative /api (handled by vercel.json rewrites)
    normalizedBackend = '';
  } else {
    normalizedBackend = '';
  }
}

if (normalizedBackend.endsWith('/api')) {
  normalizedBackend = normalizedBackend.slice(0, -4);
}

export const BACKEND_BASE = normalizedBackend;
export const API_BASE = BACKEND_BASE ? `${BACKEND_BASE}/api` : '/api';

export function getCustomApiUrl(): string {
  return typeof window !== 'undefined' ? (localStorage.getItem('anemiawatch_api_url') || '') : '';
}

export function setCustomApiUrl(url: string) {
  if (typeof window === 'undefined') return;
  if (url && url.trim()) {
    localStorage.setItem('anemiawatch_api_url', url.trim().replace(/\/+$/, ''));
  } else {
    localStorage.removeItem('anemiawatch_api_url');
  }
  window.location.reload();
}

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

  async registerDoctor(data: any) {
    return request('/auth/register/doctor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }, 'Doctor registration failed');
  },

  async login(data: any) {
    return request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }, 'Login failed');
  },

  async refreshToken(refreshToken: string) {
    return request('/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }, 'Token refresh failed');
  },

  async logoutBackend(refreshToken?: string) {
    try {
      await request('/auth/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
        body: JSON.stringify({ refresh_token: refreshToken || '' }),
      });
    } catch {
      // Ignore network errors on logout
    }
  },

  async changePassword(data: { current_password: string; new_password: string }) {
    return request('/auth/change-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify(data),
    }, 'Password change failed');
  },

  async forgotPassword(email: string) {
    return request('/auth/forgot-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    }, 'Password reset request failed');
  },

  async resetPassword(token: string, newPassword: string) {
    return request('/auth/reset-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, new_password: newPassword }),
    }, 'Password reset failed');
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

  // Consents & Patient Access
  async getMyConsents() {
    return request('/patients/me/consents', {
      headers: { ...getAuthHeader() },
    }, 'Failed to load consents');
  },

  async grantConsent(data: { doctor_id: string; purpose?: string; expires_in_days?: number }) {
    return request('/patients/me/consents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify(data),
    }, 'Failed to grant consent');
  },

  async revokeConsent(consentId: string) {
    return request(`/patients/me/consents/${consentId}`, {
      method: 'DELETE',
      headers: { ...getAuthHeader() },
    }, 'Failed to revoke consent');
  },

  async getApprovedDoctors() {
    return request('/patients/doctors/available', {
      headers: { ...getAuthHeader() },
    }, 'Failed to load doctors list');
  },

  // Admin
  async getAdminStats() {
    return request('/admin/stats', {
      headers: { ...getAuthHeader() },
    }, 'Failed to load admin stats');
  },

  async getPendingDoctors() {
    return request('/admin/doctors/pending', {
      headers: { ...getAuthHeader() },
    }, 'Failed to load pending doctor applications');
  },

  async reviewDoctor(doctorId: string, approved: boolean, notes?: string) {
    return request(`/admin/doctors/${doctorId}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify({ approved, verification_notes: notes }),
    }, 'Failed to verify doctor');
  },

  async getAuditLogs(limit = 100, skip = 0) {
    return request(`/admin/audit-logs?limit=${limit}&skip=${skip}`, {
      headers: { ...getAuthHeader() },
    }, 'Failed to load audit logs');
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

  async getDoctorPatientDetail(id: number | string) {
    return request(`/doctor/patient/${id}`, {
      headers: { ...getAuthHeader() },
    }, 'Failed to load patient history');
  },
};
