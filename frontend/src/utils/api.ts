import axios from 'axios';
import { createClient } from './supabase';
import { clearApiCache } from './apiCache';
import type {
  BudgetResponse,
  CashflowResponse,
  CurrencyCode,
  FxCurrenciesResponse,
  ProfileResponse,
  ProfileUpdate,
  ReportsQuery,
  ReportsResponse,
  SummaryResponse,
  TransactionKindResponse,
  TransactionKindUpdate,
  TrendsResponse,
  UploadRecord,
  UploadResult,
  UploadsListResponse,
} from '@/types/v5';

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

// Cached API responses (apiCache.ts) belong to the signed-in user — drop them
// on every sign-out path (header button, Settings, session expiry).
if (typeof window !== 'undefined') {
  supabaseClient.auth.onAuthStateChange((event) => {
    if (event === 'SIGNED_OUT') clearApiCache();
  });
}

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
    clearApiCache();
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
    upload: (file: File, opts?: { onUploadProgress?: (e: any) => void }) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiClient.post('/uploads/', formData, opts);
    },
    delete: (uploadId: string) =>
      apiClient.delete(`/uploads/${uploadId}`),
    getStatus: (uploadId: string) =>
      apiClient.get(`/uploads/${uploadId}`),
  },

  transactions: {
    create: (data: {
      timestamp: string;
      merchant: string;
      description: string;
      amount: number;
      category_id: string;
    }) => apiClient.post('/transactions/', data),
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
    bulkLabel: (transactionIds: string[], categoryId: string) =>
      apiClient.post('/classify/bulk-label', { transaction_ids: transactionIds, category_id: categoryId }),
    split: (transactionId: string, splits: { category_id: string; amount: number }[]) =>
      apiClient.post(`/classify/${transactionId}/split`, { splits }),
    unsplit: (transactionId: string) =>
      apiClient.delete(`/classify/${transactionId}/split`),
  },

  categories: {
    list: () => apiClient.get('/categories/'),
    create: (name: string) => apiClient.post('/categories/', { name }),
    update: (id: string, data: { name?: string; color?: string | null }) =>
      apiClient.put(`/categories/${id}`, data),
    delete: (id: string) => apiClient.delete(`/categories/${id}`),
  },

  export: {
    xlsx: () => apiClient.get('/dashboard/export', { responseType: 'blob' }),
  },

  subscriptions: {
    list: () => apiClient.get('/subscriptions/'),
    confirm: (id: string) => apiClient.post(`/subscriptions/${id}/confirm`, {}),
    dismiss: (id: string) => apiClient.post(`/subscriptions/${id}/dismiss`, {}),
  },

  // ── v5 typed helpers (docs/contracts/API_V5.md) ──────────────────────────
  // Additive only: the untyped helpers above keep working unchanged.

  /** Typed v5 upload (response adds `reimported`, `rows_by_kind`). */
  uploadsV5: {
    upload: (file: File, opts?: { onUploadProgress?: (e: any) => void }) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiClient.post<UploadResult>('/uploads/', formData, opts);
    },
    list: () => apiClient.get<UploadsListResponse>('/uploads/'),
    getStatus: (uploadId: string) => apiClient.get<UploadRecord>(`/uploads/${uploadId}`),
  },

  dashboard: {
    summary: () => apiClient.get<SummaryResponse>('/dashboard/summary'),
    trends: (params: { granularity?: 'day' | 'month'; days?: number; months?: number } = {}) =>
      apiClient.get<TrendsResponse>(`/dashboard/trends${qs(params)}`),
    cashflow: (months = 12) => apiClient.get<CashflowResponse>(`/dashboard/cashflow${qs({ months })}`),
    budget: (month?: string) => apiClient.get<BudgetResponse>(`/dashboard/budget${qs({ month })}`),
    reports: (query: ReportsQuery = {}) => apiClient.get<ReportsResponse>(`/dashboard/reports${qs(query)}`),
  },

  /** Path builders for useApi() (shares its cache/invalidation). */
  paths: {
    summary: '/dashboard/summary',
    cashflow: (months = 12) => `/dashboard/cashflow${qs({ months })}`,
    trends: (params: { granularity?: 'day' | 'month'; days?: number; months?: number } = {}) =>
      `/dashboard/trends${qs(params)}`,
    budget: (month?: string) => (month ? `/dashboard/budget${qs({ month })}` : '/dashboard/budget'),
    reports: (query: ReportsQuery = {}) => `/dashboard/reports${qs(query)}`,
    fxCurrencies: '/fx/currencies',
    profile: '/settings/profile',
  },

  fx: {
    currencies: () => apiClient.get<FxCurrenciesResponse>('/fx/currencies'),
  },

  settings: {
    getProfile: () => apiClient.get<ProfileResponse>('/settings/profile'),
    updateProfile: (data: ProfileUpdate) => apiClient.patch<ProfileResponse>('/settings/profile', data),
    setHomeCurrency: (code: CurrencyCode | null) =>
      apiClient.patch<ProfileResponse>('/settings/profile', { home_currency: code } satisfies ProfileUpdate),
  },

  transactionKind: {
    update: (transactionId: string, data: TransactionKindUpdate) =>
      apiClient.patch<TransactionKindResponse>(`/transactions/${transactionId}/kind`, data),
  },
};

/** Query string from defined, non-empty params ("" when none). */
function qs(params: object): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === '' || v === false) continue;
    sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : '';
}
