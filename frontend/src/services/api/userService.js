/**
 * User service
 * Handles all user and profile-related API calls
 */

import apiClient from './apiClient';
import endpoints from './endpoints';

export const userService = {
  /**
   * Get user profile by ID
   */
  getUserProfile: async (userId, worldMode = 'real') => {
    const response = await apiClient.get(endpoints.users.profile(userId), {
      params: { world_mode: worldMode },
    });
    return response.data;
  },

  /**
   * Update user's real profile
   */
  updateProfile: async (profileData) => {
    const response = await apiClient.put(endpoints.users.updateProfile, profileData);
    return response.data;
  },

  /**
   * Update user's avatar profile
   */
  updateAvatarProfile: async (avatarData) => {
    const response = await apiClient.put(endpoints.users.updateAvatarProfile, avatarData);
    return response.data;
  },

  /**
   * Get user's avatar profile
   */
  getAvatarProfile: async () => {
    const response = await apiClient.get(endpoints.users.getAvatarProfile);
    return response.data;
  },

  /**
   * Upload profile picture
   */
  uploadProfilePicture: async (file, worldMode = 'real') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('world_mode', worldMode);

    const response = await apiClient.post(endpoints.users.uploadPicture, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Upload cover photo
   */
  uploadCoverPhoto: async (file, worldMode = 'real') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('world_mode', worldMode);

    const response = await apiClient.post(endpoints.users.uploadCover, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

export default userService;

