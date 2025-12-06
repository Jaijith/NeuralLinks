/**
 * Friend service
 * Handles all friend-related API calls
 */

import apiClient from './apiClient';
import endpoints from './endpoints';

export const friendService = {
  /**
   * Get user's friends list
   */
  getFriends: async (userId = null) => {
    const params = userId ? { user_id: userId } : {};
    const response = await apiClient.get(endpoints.friends.list, { params });
    return response.data;
  },

  /**
   * Get pending friend requests
   */
  getFriendRequests: async () => {
    const response = await apiClient.get(endpoints.friends.requests);
    return response.data;
  },

  /**
   * Send a friend request
   */
  sendFriendRequest: async (friendId) => {
    const response = await apiClient.post(endpoints.friends.sendRequest(friendId), {});
    return response.data;
  },

  /**
   * Accept a friend request
   */
  acceptFriendRequest: async (friendshipId) => {
    const response = await apiClient.post(endpoints.friends.acceptRequest(friendshipId), {});
    return response.data;
  },

  /**
   * Decline a friend request
   */
  declineFriendRequest: async (friendshipId) => {
    const response = await apiClient.post(endpoints.friends.declineRequest(friendshipId), {});
    return response.data;
  },

  /**
   * Remove a friend
   */
  removeFriend: async (friendId) => {
    const response = await apiClient.delete(endpoints.friends.remove(friendId));
    return response.data;
  },

  /**
   * Get suggested users
   */
  getSuggestions: async (limit = 5, worldMode = 'real') => {
    const response = await apiClient.get(endpoints.friends.suggestions, {
      params: { limit, world_mode: worldMode },
    });
    return response.data;
  },
};

export default friendService;

