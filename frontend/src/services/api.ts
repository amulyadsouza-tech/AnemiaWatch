const API_BASE = '/api';

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
  try {
    res = await fetch(`${API_BASE}${endpoint}`, options);
  } catch (err: any) {
    throw new Error(
      'Unable to connect to backend server. Please verify backend service is running on port 8000.'
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
      if (res.status === 502 || res.status === 503 || res.status === 504) {
        errorMsg = 'Backend service currently unavailable (502/504). Please ensure backend server is running on port 8000.';
      } else if (res.status === 404) {
        errorMsg = 'API endpoint not found (404).';
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
    return token
      ? `${API_BASE}/screening/${id}/pdf?token=${encodeURIComponent(token)}`
      : `${API_BASE}/screening/${id}/pdf`;
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
