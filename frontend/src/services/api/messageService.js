/**
 * Message service
 * Handles all messaging-related API calls
 */

import apiClient from './apiClient';
import endpoints from './endpoints';

export const messageService = {
  /**
   * Send a direct message
   */
  sendMessage: async (recipientId, message, worldMode = 'real') => {
    const response = await apiClient.post(endpoints.messages.send, {
      recipient_id: recipientId,
      message,
      world_mode: worldMode,
    });
    return response.data;
  },

  /**
   * Get avatar conversations
   */
  getAvatarConversations: async () => {
    const response = await apiClient.get(endpoints.messages.getConversations);
    return response.data;
  },

  /**
   * Get conversation with a specific user
   */
  getConversation: async (userId) => {
    const response = await apiClient.get(endpoints.messages.getConversation(userId));
    return response.data;
  },
};

export default messageService;

