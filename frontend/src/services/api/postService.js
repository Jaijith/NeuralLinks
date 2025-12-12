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
   * Create a post with image using presigned S3 URL
   * This bypasses API Gateway payload limits and avoids binary corruption
   */
  createPostWithImage: async (formData) => {
    // Extract file and metadata from FormData
    const file = formData.get('file');
    const caption = formData.get('caption') || '';
    const postType = formData.get('post_type') || 'real';
    
    if (!file) {
      throw new Error('No file provided');
    }
    
    // Step 1: Get presigned URL from backend
    const presignedResponse = await apiClient.post(endpoints.posts.getUploadUrl, {
      filename: file.name,
      content_type: file.type,
    });
    
    const { upload_url, image_url } = presignedResponse.data;
    
    // Step 2: Upload file directly to S3 using presigned URL
    const uploadResponse = await fetch(upload_url, {
      method: 'PUT',
      body: file,
      headers: {
        'Content-Type': file.type,
      },
    });
    
    if (!uploadResponse.ok) {
      throw new Error(`S3 upload failed: ${uploadResponse.status}`);
    }
    
    // Step 3: Create the post with the S3 image URL
    const postResponse = await apiClient.post(endpoints.posts.createWithImage, {
      image_url: image_url,
      caption: caption,
      post_type: postType,
    });
    
    return postResponse.data;
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

