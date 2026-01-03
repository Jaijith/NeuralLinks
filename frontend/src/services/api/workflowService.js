/**
 * Workflow Service
 * API calls for workflow operations (missions, leads, chat)
 */

import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api/workflow`;

const config = { withCredentials: true };

// ============================================================================
// Chat API
// ============================================================================

export const chatService = {
  /**
   * Create or get active chat session
   */
  async createSession(userId) {
    const response = await axios.post(`${API}/chat/${userId}/session`, {}, config);
    return response.data;
  },

  /**
   * Send a message in a chat session
   */
  async sendMessage(sessionId, content) {
    const response = await axios.post(
      `${API}/chat/session/${sessionId}/message`,
      { content },
      config
    );
    return response.data;
  },

  /**
   * Get chat history for a user
   */
  async getHistory(userId, limit = 50) {
    const response = await axios.get(`${API}/chat/${userId}/history?limit=${limit}`, config);
    return response.data;
  },

  /**
   * Get a specific chat session
   */
  async getSession(sessionId) {
    const response = await axios.get(`${API}/chat/session/${sessionId}`, config);
    return response.data;
  }
};

// ============================================================================
// Mission API
// ============================================================================

export const missionService = {
  /**
   * Create a new mission
   */
  async create(userId, missionData) {
    const response = await axios.post(`${API}/missions/${userId}`, missionData, config);
    return response.data;
  },

  /**
   * List missions for a user
   */
  async list(userId, { status, limit = 20, skip = 0 } = {}) {
    let url = `${API}/missions/${userId}?limit=${limit}&skip=${skip}`;
    if (status) url += `&status=${status}`;
    const response = await axios.get(url, config);
    return response.data;
  },

  /**
   * Get mission details
   */
  async get(missionId) {
    const response = await axios.get(`${API}/missions/detail/${missionId}`, config);
    return response.data;
  },

  /**
   * Get detailed mission status
   */
  async getStatus(missionId) {
    const response = await axios.get(`${API}/missions/detail/${missionId}/status`, config);
    return response.data;
  },

  /**
   * Start a mission
   */
  async start(missionId) {
    const response = await axios.post(`${API}/missions/detail/${missionId}/start`, {}, config);
    return response.data;
  },

  /**
   * Pause a mission
   */
  async pause(missionId) {
    const response = await axios.post(`${API}/missions/detail/${missionId}/pause`, {}, config);
    return response.data;
  },

  /**
   * Resume a mission
   */
  async resume(missionId) {
    const response = await axios.post(`${API}/missions/detail/${missionId}/resume`, {}, config);
    return response.data;
  },

  /**
   * Cancel a mission
   */
  async cancel(missionId) {
    const response = await axios.post(`${API}/missions/detail/${missionId}/cancel`, {}, config);
    return response.data;
  },

  /**
   * Get mission activities
   */
  async getActivities(missionId, limit = 50) {
    const response = await axios.get(
      `${API}/missions/detail/${missionId}/activities?limit=${limit}`,
      config
    );
    return response.data;
  }
};

// ============================================================================
// Lead API
// ============================================================================

export const leadService = {
  /**
   * Get all leads for a user
   */
  async list(userId, { status, limit = 50, skip = 0 } = {}) {
    let url = `${API}/leads/${userId}?limit=${limit}&skip=${skip}`;
    if (status) url += `&status=${status}`;
    const response = await axios.get(url, config);
    return response.data;
  },

  /**
   * Get leads for a specific mission
   */
  async listForMission(missionId, { status, priority, limit = 50, skip = 0 } = {}) {
    let url = `${API}/leads/mission/${missionId}?limit=${limit}&skip=${skip}`;
    if (status) url += `&status=${status}`;
    if (priority) url += `&priority=${priority}`;
    const response = await axios.get(url, config);
    return response.data;
  },

  /**
   * Get lead details
   */
  async get(leadId) {
    const response = await axios.get(`${API}/leads/detail/${leadId}`, config);
    return response.data;
  },

  /**
   * Update a lead
   */
  async update(leadId, { status, notes, rating } = {}) {
    const response = await axios.patch(
      `${API}/leads/detail/${leadId}`,
      { status, notes, rating },
      config
    );
    return response.data;
  },

  /**
   * Mark lead as followed up
   */
  async markFollowedUp(leadId) {
    const response = await axios.post(`${API}/leads/detail/${leadId}/follow-up`, {}, config);
    return response.data;
  },

  /**
   * Dismiss a lead
   */
  async dismiss(leadId, reason = '') {
    const response = await axios.post(`${API}/leads/detail/${leadId}/dismiss`, reason, config);
    return response.data;
  },

  /**
   * Get lead statistics
   */
  async getStats(userId) {
    const response = await axios.get(`${API}/leads/${userId}/stats`, config);
    return response.data;
  },

  /**
   * Get top leads
   */
  async getTop(userId, limit = 10) {
    const response = await axios.get(`${API}/leads/${userId}/top?limit=${limit}`, config);
    return response.data;
  }
};

// ============================================================================
// Workflow Types API
// ============================================================================

export const workflowTypesService = {
  /**
   * Get available workflow types
   */
  async getTypes() {
    const response = await axios.get(`${API}/types`, config);
    return response.data;
  }
};

export default {
  chat: chatService,
  mission: missionService,
  lead: leadService,
  types: workflowTypesService
};

