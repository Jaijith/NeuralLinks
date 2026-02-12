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

/**
 * Get social context for voice session (on-demand)
 * Called when AI uses the recall_social_context function
 * @param {Object} options - Context options
 * @param {string} options.avatarId - Avatar ID
 * @param {string} options.contextType - Type of context to fetch
 * @param {string} options.friendName - Friend name (optional)
 * @param {string} options.timeRange - Time range (optional)
 * @returns {Promise<Object>} Context data
 */
export const getVoiceContext = async (options) => {
  try {
    const response = await api.post('/api/voice/context', {
      avatar_id: options.avatarId,
      context_type: options.contextType,
      friend_name: options.friendName,
      time_range: options.timeRange || 'recent'
    });
    return response.data;
  } catch (error) {
    console.error('Error getting voice context:', error);
    // Return fallback response so AI can continue gracefully
    return {
      success: false,
      summary: "I'm having trouble remembering the details right now."
    };
  }
};

/**
 * Pre-warm context cache (call on hover over voice orb)
 * This reduces latency when the session actually starts
 * @param {string} avatarId - Avatar ID
 * @returns {Promise<Object>} Pre-warmed context
 */
export const prewarmContext = async (avatarId) => {
  try {
    const response = await api.get(`/api/voice/context/tier1/${avatarId}`);
    return response.data;
  } catch (error) {
    // Silently fail - this is just optimization
    console.debug('Pre-warm context failed:', error);
    return null;
  }
};

/**
 * Save voice transcript (called on session end)
 * This is fire-and-forget - doesn't wait for response
 * 
 * @param {Object} transcript - Transcript data
 * @param {string} transcript.sessionId - Session ID
 * @param {string} transcript.avatarId - Avatar ID
 * @param {Array} transcript.messages - Array of {role, content, timestamp}
 * @param {string} transcript.startedAt - ISO timestamp
 * @param {string} transcript.endedAt - ISO timestamp
 * @param {number} transcript.durationSeconds - Duration in seconds
 */
export const saveTranscript = (transcript) => {
  // Fire-and-forget: use fetch with keepalive so it survives page navigation
  // Don't await this - we want to return immediately
  try {
    fetch(`${BACKEND_URL}/api/voice/transcript`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Include auth cookie
      },
      credentials: 'include',
      body: JSON.stringify({
        session_id: transcript.sessionId,
        avatar_id: transcript.avatarId,
        messages: transcript.messages,
        started_at: transcript.startedAt,
        ended_at: transcript.endedAt,
        duration_seconds: transcript.durationSeconds
      }),
      keepalive: true  // Survives page navigation
    }).catch(err => {
      // Silently fail - this is background processing
      console.debug('Transcript save failed:', err);
    });
  } catch (error) {
    // Silently fail
    console.debug('Transcript save error:', error);
  }
};

/**
 * Get user's voice memory (connections, interests, facts)
 * Called at session start to enrich the conversation
 * @param {string} avatarId - Avatar ID
 * @returns {Promise<Object>} Memory data
 */
export const getVoiceMemory = async (avatarId) => {
  try {
    const response = await api.get(`/api/voice/memory/${avatarId}`);
    return response.data;
  } catch (error) {
    console.debug('Voice memory fetch failed:', error);
    return { success: false, memory: {} };
  }
};

/**
 * Trigger a workflow mission from voice command
 * Called when AI uses the trigger_workflow function
 * @param {Object} options - Workflow options
 * @param {string} options.avatarId - Avatar ID
 * @param {string} options.missionType - Type of mission
 * @param {string} options.missionName - Name for the mission
 * @param {string} options.description - Mission description
 * @param {Array} options.interests - Interests to filter by
 * @param {Array} options.keywords - Keywords to search
 * @param {string} options.approach - Approach style
 * @param {number} options.maxTargets - Max targets
 * @returns {Promise<Object>} Trigger result
 */
/**
 * Recall past voice conversations
 * Called when AI uses the recall_past_conversations function
 * @param {Object} options - Recall options
 * @param {string} options.avatarId - Avatar ID
 * @param {string} options.query - What to search for in past conversations
 * @param {boolean} options.includeFullTranscript - Whether to fetch full S3 transcript
 * @returns {Promise<Object>} Recall results with summary
 */
export const recallPastConversations = async (options) => {
  try {
    const response = await api.post('/api/voice/recall', {
      avatar_id: options.avatarId,
      query: options.query,
      include_full_transcript: options.includeFullTranscript || false
    });
    return response.data;
  } catch (error) {
    console.error('Error recalling past conversations:', error);
    return {
      success: false,
      summary: "I'm having trouble searching my memory right now. Let me try to remember on my own..."
    };
  }
};

export const triggerWorkflow = async (options) => {
  try {
    const response = await api.post('/api/voice/workflow', {
      avatar_id: options.avatarId,
      mission_type: options.missionType,
      mission_name: options.missionName,
      description: options.description,
      interests: options.interests || [],
      keywords: options.keywords || [],
      approach: options.approach || 'friendly',
      max_targets: options.maxTargets || 10
    });
    return response.data;
  } catch (error) {
    console.error('Error triggering workflow:', error);
    return {
      success: false,
      message: "I wasn't able to start that mission right now. Please try again or check the Missions page."
    };
  }
};

export default {
  createVoiceSession,
  getVoicePrompt,
  recordVoiceEvent,
  getVoiceSettings,
  updateVoiceSettings,
  getVoiceContext,
  prewarmContext,
  saveTranscript,
  getVoiceMemory,
  recallPastConversations,
  triggerWorkflow
};
