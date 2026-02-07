/**
 * Centralized API endpoint definitions
 * All API endpoints should be defined here for maintainability
 */

const API_BASE = '/api';

export const endpoints = {
  // Authentication
  auth: {
    login: `${API_BASE}/auth/google/login`,
    callback: `${API_BASE}/auth/google/callback`,
    me: `${API_BASE}/auth/me`,
    logout: `${API_BASE}/auth/logout`,
    account: `${API_BASE}/auth/account`,
  },

  // Users & Profiles
  users: {
    profile: (userId) => `${API_BASE}/users/${userId}`,
    updateProfile: `${API_BASE}/profile`,
    updateAvatarProfile: `${API_BASE}/profile/avatar`,
    getAvatarProfile: `${API_BASE}/profile/avatar`,
    uploadPicture: `${API_BASE}/profile/upload-picture`,
    uploadCover: `${API_BASE}/profile/upload-cover`,
  },

  // Posts
  posts: {
    create: `${API_BASE}/profile/posts`,
    getUserPosts: `${API_BASE}/profile/posts`,
    getFeedPosts: `${API_BASE}/feed/posts`,
    update: (postId) => `${API_BASE}/profile/posts/${postId}`,
    delete: (postId) => `${API_BASE}/profile/posts/${postId}`,
    like: (postId) => `${API_BASE}/posts/${postId}/like`,
    getLikes: (postId) => `${API_BASE}/posts/${postId}/likes`,
    getComments: (postId) => `${API_BASE}/posts/${postId}/comments`,
    addComment: (postId) => `${API_BASE}/posts/${postId}/comment`,
    uploadImage: `${API_BASE}/posts/upload-image`,
    getUploadUrl: `${API_BASE}/posts/get-upload-url`,
    createWithImage: `${API_BASE}/posts/create-with-image`,
  },

  // Friends
  friends: {
    list: `${API_BASE}/friends`,
    requests: `${API_BASE}/friends/requests`,
    sendRequest: (friendId) => `${API_BASE}/friends/request/${friendId}`,
    acceptRequest: (friendshipId) => `${API_BASE}/friends/accept/${friendshipId}`,
    declineRequest: (friendshipId) => `${API_BASE}/friends/decline/${friendshipId}`,
    remove: (friendId) => `${API_BASE}/friends/${friendId}`,
    suggestions: `${API_BASE}/friends/suggestions`,
  },

  // Messages
  messages: {
    send: `${API_BASE}/messages/send`,
    getConversations: `${API_BASE}/avatar/conversations`,
    getConversation: (userId) => `${API_BASE}/avatar/conversations/${userId}`,
  },

  // Chat
  chat: {
    getMessages: (matchId) => `${API_BASE}/chat/${matchId}/messages`,
    sendMessage: `${API_BASE}/chat/send`,
  },

  // Search
  search: {
    users: `${API_BASE}/search/users`,
  },

  // Gallery
  gallery: {
    photos: `${API_BASE}/gallery/photos`,
    upload: `${API_BASE}/gallery/upload`,
  },

  // Avatar
  avatar: {
    state: `${API_BASE}/avatar/state`,
    fullMemory: `${API_BASE}/avatar/full-memory`,
  },

  // Integrations
  integrations: {
    list: `${API_BASE}/integrations`,
    connect: (platform) => `${API_BASE}/integrations/${platform}/connect`,
    disconnect: (platform) => `${API_BASE}/integrations/${platform}/disconnect`,
  },
};

export default endpoints;

