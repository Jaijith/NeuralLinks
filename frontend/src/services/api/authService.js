/**
 * Authentication service
 * Handles all authentication-related API calls
 */

import apiClient from './apiClient';
import endpoints from './endpoints';

export const authService = {
  /**
   * Get current authenticated user
   */
  getCurrentUser: async () => {
    const response = await apiClient.get(endpoints.auth.me);
    return response.data;
  },

  /**
   * Logout current user
   */
  logout: async () => {
    try {
      await apiClient.post(endpoints.auth.logout, {});
      return { success: true };
    } catch (error) {
      // Non-critical - still return success for UI
      console.error('Logout API error (non-critical):', error);
      return { success: true };
    }
  },

  /**
   * Delete user account
   */
  deleteAccount: async () => {
    const response = await apiClient.delete(endpoints.auth.account);
    return response.data;
  },
};

export default authService;

