import { useState, useEffect, useCallback } from 'react';
import { postService } from '@/services/api';
import { toast } from 'sonner';

/**
 * Custom hook for managing profile posts
 * Supports both Maya (avatar) and Sense (real) worlds
 */
const useProfilePosts = (userId, worldMode = 'real', currentUser) => {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [likedPosts, setLikedPosts] = useState(new Set());

  const postType = worldMode === 'avatar' ? 'avatar' : 'real';
  const limit = 20;

  const fetchPosts = useCallback(async (currentSkip = 0, append = false) => {
    if (!userId) return;

    try {
      if (!append) {
        setLoading(true);
        setSkip(0);
      } else {
        setLoadingMore(true);
      }

      const response = await postService.getUserPosts(userId, postType, limit, currentSkip);
      const allPosts = response.posts || response || [];
      const hasMoreData = response.has_more !== undefined 
        ? response.has_more 
        : (currentSkip + allPosts.length < (response.total || allPosts.length));

      // Update liked posts
      const likedSet = new Set();
      allPosts.forEach(post => {
        if (post.liked_by && Array.isArray(post.liked_by) && post.liked_by.includes(currentUser?.id)) {
          likedSet.add(post.id);
        }
      });

      if (append) {
        setPosts(prev => [...prev, ...allPosts]);
        setLikedPosts(prev => new Set([...prev, ...likedSet]));
      } else {
        setPosts(allPosts);
        setLikedPosts(likedSet);
      }

      setHasMore(hasMoreData);
      setSkip(currentSkip + allPosts.length);
    } catch (err) {
      console.error("Error fetching profile posts:", err);
      setError(err);
      toast.error("Failed to load posts");
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [userId, postType, currentUser?.id]);

  useEffect(() => {
    if (userId) {
      fetchPosts(0, false);
    }
  }, [userId, worldMode, fetchPosts]);

  const loadMore = useCallback(() => {
    if (hasMore && !loadingMore && !loading) {
      fetchPosts(skip, true);
    }
  }, [hasMore, loadingMore, loading, skip, fetchPosts]);

  const addPost = useCallback((newPost) => {
    setPosts(prev => [newPost, ...prev]);
  }, []);

  const removePost = useCallback((postId) => {
    setPosts(prev => prev.filter(p => p.id !== postId));
  }, []);

  const updateLikedPosts = useCallback((postIds) => {
    setLikedPosts(new Set(postIds));
  }, []);

  return {
    posts,
    loading,
    loadingMore,
    error,
    hasMore,
    likedPosts,
    loadMore,
    addPost,
    removePost,
    updateLikedPosts,
    refresh: () => fetchPosts(0, false)
  };
};

export default useProfilePosts;
