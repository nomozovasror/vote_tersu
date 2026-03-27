import axios from 'axios';

// Smart API URL detection for production
function getApiBaseUrl(): string {
  // 1. Use environment variable if set
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }

  // 2. In production, use the same host and port (proxied by Nginx)
  if (import.meta.env.PROD) {
    return window.location.origin;
  }

  // 3. Default for development
  return 'http://localhost:2014';
}

const API_BASE_URL = getApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;

export const WS_BASE_URL = API_BASE_URL.replace('http', 'ws');
