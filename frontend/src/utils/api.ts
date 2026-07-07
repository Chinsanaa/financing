import axios from 'axios';
import { createClient } from './supabase';

/**
 * Single axios client for the FastAPI backend.
 *
 * A request interceptor attaches the CURRENT Supabase access token on every
 * request (getSession() transparently refreshes expired tokens), so:
 * - components never pass tokens or Authorization headers around,
 * - no token is ever written into shared axios defaults (the old singleton
 *   kept a stale token globally and never cleared it on logout).
 */

function getBaseUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_URL;
  if (url) return url;
  if (process.env.NODE_ENV === 'production') {
    // Silently falling back to localhost in production made every request
    // fail with an opaque network error. Fail loudly instead.
    throw new Error('NEXT_PUBLIC_API_URL is not configured');
  }
  return 'http://localhost:8000';
}

// Create a single supabase client instance so session is properly persisted
const supabaseClient = createClient();

export const apiClient = axios.create();

apiClient.interceptors.request.use(async (config) => {
  config.baseURL = getBaseUrl();
  try {
    const {
      data: { session },
    } = await supabaseClient.auth.getSession();
    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`;
    } else {
      console.warn('No Supabase session found - request may fail with 401');
    }
  } catch (err) {
    console.error('Failed to get Supabase session:', err);
  }
  return config;
});

// A 401 means the session is gone (expired refresh token, revoked user) —
// bounce to the login page instead of leaving every tab in an error state.
apiClient.interceptors.response.use(undefined, (error) => {
  if (typeof window !== 'undefined' && error?.response?.status === 401) {
    window.location.href = '/auth';
  }
  return Promise.reject(error);
});

export const api = {
  get: (url: string, config?: any) => apiClient.get(url, config),
  post: (url: string, data?: any, config?: any) => apiClient.post(url, data, config),
  put: (url: string, data?: any, config?: any) => apiClient.put(url, data, config),
  patch: (url: string, data?: any, config?: any) => apiClient.patch(url, data, config),
  delete: (url: string, config?: any) => apiClient.delete(url, config),

  // Typed helpers for the real backend routes
  uploads: {
    upload: (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiClient.post('/uploads/', formData);
    },
  },

  training: {
    retrain: () => apiClient.post('/training/retrain'),
    getStatus: (modelRunId: string) => apiClient.get(`/training/${modelRunId}`),
    list: () => apiClient.get('/training/'),
  },

  classifyTx: {
    label: (transactionId: string, categoryId: string) =>
      apiClient.post(`/classify/${transactionId}/label`, { category_id: categoryId }),
    accept: (transactionId: string) =>
      apiClient.post(`/classify/${transactionId}/accept`, {}),
  },

  categories: {
    list: () => apiClient.get('/categories/'),
    create: (name: string) => apiClient.post('/categories/', { name }),
    delete: (id: string) => apiClient.delete(`/categories/${id}`),
  },
};
