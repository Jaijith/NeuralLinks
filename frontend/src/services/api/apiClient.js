/**
 * Centralized Axios instance with interceptors
 * Handles authentication, error handling, and request/response transformation
 */

import axios from 'axios';
import config from '@/config/config';

// Create axios instance with default configuration
const apiClient = axios.create({
  baseURL: config.api.baseURL,
  timeout: config.api.timeout,
  withCredentials: config.api.withCredentials,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add any auth tokens here if needed
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }

    // Log request in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, {
        data: config.data,
        params: config.params,
      });
    }

    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    // Log response in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, {
        status: response.status,
        data: response.data,
      });
    }

    return response;
  },
  (error) => {
    // Handle common errors
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;

      switch (status) {
        case 401:
          // Unauthorized - redirect to login
          if (window.location.pathname !== '/') {
            window.location.href = '/';
          }
          break;
        case 403:
          // Forbidden
          console.error('[API Error] Forbidden:', data?.detail || 'Access denied');
          break;
        case 404:
          // Not found
          console.error('[API Error] Not found:', error.config.url);
          break;
        case 500:
          // Server error
          console.error('[API Error] Server error:', data?.detail || 'Internal server error');
          break;
        default:
          console.error('[API Error]', status, data?.detail || error.message);
      }
    } else if (error.request) {
      // Request made but no response received
      console.error('[API Error] No response received:', error.request);
    } else {
      // Error setting up request
      console.error('[API Error] Request setup error:', error.message);
    }

    return Promise.reject(error);
  }
);

export default apiClient;

