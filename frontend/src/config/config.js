/**
 * Centralized configuration management
 * Handles environment variables and app-wide configuration
 */

const config = {
  // API Configuration
  api: {
    baseURL: process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001',
    timeout: 30000, // 30 seconds
    withCredentials: true,
  },

  // App Configuration
  app: {
    name: 'NeuralLinks',
    version: '1.0.0',
    environment: process.env.NODE_ENV || 'development',
  },

  // Feature Flags
  features: {
    enableVisualEdits: process.env.REACT_APP_ENABLE_VISUAL_EDITS === 'true',
    enableHealthCheck: process.env.ENABLE_HEALTH_CHECK === 'true',
  },

  // Pagination defaults
  pagination: {
    defaultLimit: 20,
    maxLimit: 100,
  },

  // File upload limits
  upload: {
    maxImageSize: 5 * 1024 * 1024, // 5MB
    allowedImageTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'],
  },
};

export default config;

