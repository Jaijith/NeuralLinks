/**
 * Voice Service - API client for voice endpoints
 * Handles voice session creation and management
 */

import api from './apiClient';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

/**
 * Create a new voice session
 * @param {Object} options - Session options
 * @param {string} options.avatarId - Avatar ID (optional)
 * @param {string} options.settingPreset - Voice setting preset
 * @param {Object} options.userPreferences - User preferences
 * @returns {Promise<Object>} Session configuration with ephemeral token
 */
export const createVoiceSession = async (options = {}) => {
  try {
    const response = await api.post('/api/voice/session', {
      avatar_id: options.avatarId,
      setting_preset: options.settingPreset || 'default',
      user_preferences: options.userPreferences
    });
    return response.data;
  } catch (error) {
    console.error('Error creating voice session:', error);
    throw error;
  }
};

/**
 * Get current voice prompt (for debugging)
 * @param {string} avatarId - Avatar ID
 * @returns {Promise<Object>} Prompt and state summary
 */
export const getVoicePrompt = async (avatarId) => {
  try {
    const response = await api.get(`/api/voice/prompt/${avatarId}`);
    return response.data;
  } catch (error) {
    console.error('Error getting voice prompt:', error);
    throw error;
  }
};

/**
 * Record a voice event
 * @param {string} eventType - Event type
 * @param {Object} context - Event context
 * @returns {Promise<Object>} Event result
 */
export const recordVoiceEvent = async (eventType, context = {}) => {
  try {
    const response = await api.post('/api/voice/event', {
      event_type: eventType,
      context
    });
    return response.data;
  } catch (error) {
    console.error('Error recording voice event:', error);
    throw error;
  }
};

/**
 * Get voice settings
 * @returns {Promise<Object>} User voice settings and presets
 */
export const getVoiceSettings = async () => {
  try {
    const response = await api.get('/api/voice/settings');
    return response.data;
  } catch (error) {
    console.error('Error getting voice settings:', error);
    throw error;
  }
};

/**
 * Update voice settings
 * @param {Object} settings - Settings to update
 * @returns {Promise<Object>} Updated settings
 */
export const updateVoiceSettings = async (settings) => {
  try {
    const response = await api.post('/api/voice/settings', {
      setting_preset: settings.preset,
      custom_settings: settings.custom
    });
    return response.data;
  } catch (error) {
    console.error('Error updating voice settings:', error);
    throw error;
  }
};

export default {
  createVoiceSession,
  getVoicePrompt,
  recordVoiceEvent,
  getVoiceSettings,
  updateVoiceSettings
};
