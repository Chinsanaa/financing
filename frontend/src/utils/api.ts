import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

let apiClient: AxiosInstance | null = null;

export function getApiClient(token?: string): AxiosInstance {
  if (!apiClient) {
    apiClient = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  // Add token to headers if provided
  if (token) {
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }

  return apiClient;
}

// API endpoints
export const api = {
  // Auth
  auth: {
    signup: async (email: string, password: string) => {
      return getApiClient().post('/auth/signup', { email, password });
    },
    login: async (email: string, password: string) => {
      return getApiClient().post('/auth/login', { email, password });
    },
    logout: async (token: string) => {
      return getApiClient(token).post('/auth/logout');
    },
  },

  // Categories
  categories: {
    list: async (token: string) => {
      return getApiClient(token).get('/categories/');
    },
    create: async (token: string, name: string, icon?: string, color?: string) => {
      return getApiClient(token).post('/categories/', { name, icon, color });
    },
    update: async (token: string, id: string, data: any) => {
      return getApiClient(token).put(`/categories/${id}`, data);
    },
    delete: async (token: string, id: string) => {
      return getApiClient(token).delete(`/categories/${id}`);
    },
  },

  // Uploads
  uploads: {
    list: async (token: string) => {
      return getApiClient(token).get('/uploads/');
    },
    upload: async (token: string, file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return getApiClient(token).post('/uploads/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    getStatus: async (token: string, uploadId: string) => {
      return getApiClient(token).get(`/uploads/${uploadId}`);
    },
  },

  // Training
  training: {
    retrain: async (token: string) => {
      return getApiClient(token).post('/training/retrain');
    },
    getStatus: async (token: string, modelRunId: string) => {
      return getApiClient(token).get(`/training/${modelRunId}`);
    },
    list: async (token: string) => {
      return getApiClient(token).get('/training/');
    },
  },

  // Classification
  classify: {
    predict: async (token: string, limit?: number) => {
      return getApiClient(token).post('/classify/', { limit });
    },
    accept: async (token: string, transactionId: string) => {
      return getApiClient(token).put(`/classify/${transactionId}`);
    },
    override: async (token: string, transactionId: string, category: string) => {
      return getApiClient(token).post(`/classify/${transactionId}/override`, { category });
    },
  },

  // Dashboard
  dashboard: {
    summary: async (token: string) => {
      return getApiClient(token).get('/dashboard/summary');
    },
    byCategory: async (token: string) => {
      return getApiClient(token).get('/dashboard/by-category');
    },
    trends: async (token: string, days?: number) => {
      return getApiClient(token).get(`/dashboard/trends?days=${days || 30}`);
    },
    reviewQueue: async (token: string) => {
      return getApiClient(token).get('/dashboard/review-queue');
    },
    onboardingStatus: async (token: string) => {
      return getApiClient(token).get('/dashboard/onboarding-status');
    },
    completeOnboarding: async (token: string) => {
      return getApiClient(token).post('/dashboard/onboarding-complete');
    },
  },
};
