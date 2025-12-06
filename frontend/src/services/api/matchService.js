/**
 * Match service
 * Handles all match-related API calls
 */

import apiClient from './apiClient';
import endpoints from './endpoints';

export const matchService = {
  /**
   * Get user's matches
   */
  getMatches: async () => {
    const response = await apiClient.get(endpoints.matches.list);
    return response.data;
  },

  /**
   * Discover new matches
   */
  discoverMatches: async () => {
    const response = await apiClient.post(endpoints.matches.discover, {});
    return response.data;
  },

  /**
   * Get match conversation
   */
  getMatchConversation: async (matchId) => {
    const response = await apiClient.get(endpoints.matches.getConversation(matchId));
    return response.data;
  },
};

export default matchService;

