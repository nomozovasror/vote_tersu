import axios from 'axios';

// Smart API URL detection for production
function getApiBaseUrl(): string {
  // 1. In production, always use the same host and port (proxied by Nginx)
  if (import.meta.env.PROD) {
    return window.location.origin.replace(/\/$/, '');
  }

  // 2. Use environment variable if set (mostly for development)
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL.replace(/\/$/, '');
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

// Interceptor to clean up URLs: ensure no leading slash in request URL
// and ensure baseURL doesn't have a trailing slash.
// This prevents Axios from treating the URL as absolute and dropping the port.
api.interceptors.request.use((config) => {
  if (config.url && config.url.startsWith('/')) {
    config.url = config.url.substring(1);
  }
  
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;

export const WS_BASE_URL = API_BASE_URL.replace('http', 'ws');
