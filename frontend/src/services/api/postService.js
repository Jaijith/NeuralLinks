/**
 * Post service
 * Handles all post-related API calls
 */

import apiClient from './apiClient';
import endpoints from './endpoints';

export const postService = {
  /**
   * Get feed posts with pagination
   */
  getFeedPosts: async (postType = 'real', limit = 20, skip = 0) => {
    const response = await apiClient.get(endpoints.posts.getFeedPosts, {
      params: { post_type: postType, limit, skip },
    });
    return response.data;
  },

  /**
   * Get user posts with pagination
   */
  getUserPosts: async (userId = null, postType = 'real', limit = 20, skip = 0) => {
    const params = { post_type: postType, limit, skip };
    if (userId) {
      params.user_id = userId;
    }
    const response = await apiClient.get(endpoints.posts.getUserPosts, { params });
    return response.data;
  },

  /**
   * Create a new post
   */
  createPost: async (postData) => {
    const response = await apiClient.post(endpoints.posts.create, postData);
    return response.data;
  },

  /**
   * Create a post with image
   */
  createPostWithImage: async (formData) => {
    const response = await apiClient.post(endpoints.posts.uploadImage, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Delete a post
   */
  deletePost: async (postId) => {
    const response = await apiClient.delete(endpoints.posts.delete(postId));
    return response.data;
  },

  /**
   * Like/unlike a post
   */
  likePost: async (postId) => {
    const response = await apiClient.post(endpoints.posts.like(postId), {});
    return response.data;
  },

  /**
   * Get users who liked a post
   */
  getPostLikes: async (postId) => {
    const response = await apiClient.get(endpoints.posts.getLikes(postId));
    return response.data;
  },

  /**
   * Get comments for a post
   */
  getPostComments: async (postId) => {
    const response = await apiClient.get(endpoints.posts.getComments(postId));
    return response.data;
  },

  /**
   * Add a comment to a post
   */
  addComment: async (postId, commentText) => {
    const response = await apiClient.post(endpoints.posts.addComment(postId), {
      text: commentText,
    });
    return response.data;
  },
};

export default postService;

