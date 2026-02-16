/**
 * Siddhi Bazaar - Marketplace API Service
 */

import apiClient from './apiClient';

const BASE = '/api/marketplace';

export const marketplaceService = {
  // Catalog
  searchSkills: (params = {}) => apiClient.get(`${BASE}/skills`, { params }),
  getSkill: (skillId) => apiClient.get(`${BASE}/skills/${skillId}`),
  getCategories: () => apiClient.get(`${BASE}/categories`),
  getFeatured: () => apiClient.get(`${BASE}/featured`),
  getPopular: (limit = 10) => apiClient.get(`${BASE}/popular`, { params: { limit } }),
  getRecommended: () => apiClient.get(`${BASE}/recommended`),

  // Installation
  getInstalled: () => apiClient.get(`${BASE}/installed`),
  installSkill: (skillId) => apiClient.post(`${BASE}/install/${skillId}`),
  uninstallSkill: (skillId) => apiClient.delete(`${BASE}/uninstall/${skillId}`),
  toggleSkill: (skillId, enabled) => apiClient.patch(`${BASE}/toggle/${skillId}`, { enabled }),

  // Reviews
  getReviews: (skillId, page = 1) => apiClient.get(`${BASE}/skills/${skillId}/reviews`, { params: { page } }),
  submitReview: (skillId, rating, reviewText = '') =>
    apiClient.post(`${BASE}/skills/${skillId}/review`, { rating, review_text: reviewText }),

  // Gateway
  getGatewayStatus: () => apiClient.get(`${BASE}/gateway/status`),

  // Admin
  seedCatalog: () => apiClient.post(`${BASE}/admin/seed`),
  getStats: () => apiClient.get(`${BASE}/admin/stats`),
};

export default marketplaceService;
