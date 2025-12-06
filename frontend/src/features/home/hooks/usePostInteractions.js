import { useState, useCallback } from 'react';
import { postService } from '@/services/api';
import { toast } from 'sonner';

/**
 * Custom hook for managing post interactions (likes, comments)
 * Supports both Maya (avatar) and Sense (real) worlds
 */
const usePostInteractions = () => {
  const [likedPosts, setLikedPosts] = useState(new Set());
  const [showingLikesFor, setShowingLikesFor] = useState(null);
  const [likesData, setLikesData] = useState([]);
  const [showingCommentsFor, setShowingCommentsFor] = useState(null);
  const [commentsData, setCommentsData] = useState({});

  const handleLikePost = useCallback(async (postId, currentLiked) => {
    try {
      await postService.likePost(postId);
      
      // Update liked posts set
      setLikedPosts(prev => {
        const next = new Set(prev);
        if (currentLiked) {
          next.delete(postId);
        } else {
          next.add(postId);
        }
        return next;
      });

      return !currentLiked; // Return new liked state
    } catch (error) {
      console.error("Error liking post:", error);
      toast.error("Failed to like post");
      return currentLiked; // Return unchanged state on error
    }
  }, []);

  const showLikes = useCallback(async (postId) => {
    setShowingLikesFor(postId);
    try {
      const response = await postService.getPostLikes(postId);
      
      // Handle different response formats
      if (Array.isArray(response)) {
        setLikesData(response);
      } else if (response.likes) {
        setLikesData(response.likes);
      } else if (response.users) {
        setLikesData(response.users);
      } else {
        setLikesData([]);
      }
    } catch (error) {
      console.error("Error fetching likes:", error);
      toast.error("Failed to load likes");
      setLikesData([]);
    }
  }, []);

  const showComments = useCallback(async (postId) => {
    if (showingCommentsFor === postId) {
      // Toggle off
      setShowingCommentsFor(null);
      return;
    }

    setShowingCommentsFor(postId);
    
    // If comments already loaded, don't fetch again
    if (commentsData[postId]) {
      return;
    }

    try {
      const response = await postService.getPostComments(postId);
      const comments = Array.isArray(response) ? response : (response.comments || []);
      setCommentsData(prev => ({
        ...prev,
        [postId]: comments
      }));
    } catch (error) {
      console.error("Error fetching comments:", error);
      toast.error("Failed to load comments");
      setCommentsData(prev => ({
        ...prev,
        [postId]: []
      }));
    }
  }, [showingCommentsFor, commentsData]);

  const handleAddComment = useCallback(async (postId, commentText) => {
    try {
      const response = await postService.addComment(postId, commentText);
      const newComment = response.comment || response;

      // Update comments data
      setCommentsData(prev => ({
        ...prev,
        [postId]: [newComment, ...(prev[postId] || [])]
      }));

      toast.success("💬 Comment added!");
      return newComment;
    } catch (error) {
      console.error("Error adding comment:", error);
      toast.error("Failed to add comment");
      return null;
    }
  }, []);

  const updateLikedPosts = useCallback((postIds) => {
    setLikedPosts(new Set(postIds));
  }, []);

  return {
    likedPosts,
    showingLikesFor,
    likesData,
    showingCommentsFor,
    commentsData,
    handleLikePost,
    showLikes,
    showComments,
    handleAddComment,
    updateLikedPosts,
    setShowingLikesFor,
    setShowingCommentsFor
  };
};

export default usePostInteractions;

