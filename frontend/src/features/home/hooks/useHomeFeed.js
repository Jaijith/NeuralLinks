import { useState, useEffect, useCallback } from 'react';
import { postService, friendService } from '@/services/api';
import { toast } from 'sonner';

/**
 * Custom hook for managing home feed (posts and friends)
 * Supports both Maya (avatar) and Sense (real) worlds
 */
const useHomeFeed = (worldMode = 'real', currentUser) => {
  const [posts, setPosts] = useState([]);
  const [friends, setFriends] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const postType = worldMode === 'avatar' ? 'avatar' : 'real';
  const limit = 20;

  const fetchData = useCallback(async (currentSkip = 0, append = false) => {
    try {
      if (!append) {
        setLoading(true);
        setSkip(0);
      } else {
        setLoadingMore(true);
      }

      // Fetch friends and posts in parallel
      const [friendsRes, feedPostsRes] = await Promise.all([
        friendService.getFriends(),
        postService.getFeedPosts(postType, limit, currentSkip)
      ]);

      // Handle friends response
      const friendsList = Array.isArray(friendsRes) ? friendsRes : (friendsRes.friends || []);
      setFriends(friendsList.slice(0, 9));

      // Handle posts response
      const allPosts = feedPostsRes.posts || feedPostsRes || [];
      const hasMoreData = feedPostsRes.has_more !== undefined 
        ? feedPostsRes.has_more 
        : (currentSkip + allPosts.length < (feedPostsRes.total || allPosts.length));

      // Enrich posts with user data
      const postsWithUsers = allPosts.map(post => {
        // Try to find user in friends list first
        let postUser = friendsList.find(f => f.id === post.user_id);
        
        if (!postUser && post.user_id === currentUser?.id) {
          // Current user's post
          postUser = currentUser;
        }

        // Create minimal user object if not found
        if (!postUser) {
          postUser = {
            id: post.user_id,
            name: post.author_name || 'Unknown',
            avatar_name: post.author_avatar_name,
            picture: post.author_picture,
            avatar_picture: post.author_avatar_picture,
            is_bot: post.isBot || post.author_is_bot
          };
        }

        return {
          ...post,
          user_id: post.user_id || post.user?.id,
          user: postUser,
          displayName: worldMode === 'avatar'
            ? (post.author_avatar_name || postUser.avatar_name || postUser.name)
            : (post.author_name || postUser.name),
          displayPicture: worldMode === 'avatar'
            ? (post.author_avatar_picture || postUser.avatar_picture || postUser.picture)
            : (post.author_picture || postUser.picture),
          isBot: post.isBot || post.author_is_bot || postUser.is_bot
        };
      });

      if (append) {
        setPosts(prev => [...prev, ...postsWithUsers]);
      } else {
        setPosts(postsWithUsers);
      }

      setHasMore(hasMoreData);
      setSkip(currentSkip + postsWithUsers.length);
    } catch (err) {
      console.error("Error fetching feed:", err);
      setError(err);
      toast.error("Failed to load feed");
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [postType, worldMode, currentUser]);

  useEffect(() => {
    if (currentUser) {
      fetchData(0, false);
    }
  }, [worldMode, currentUser]); // Re-fetch when worldMode changes

  const loadMore = useCallback(() => {
    if (hasMore && !loadingMore && !loading) {
      fetchData(skip, true);
    }
  }, [hasMore, loadingMore, loading, skip, fetchData]);

  const refresh = useCallback(() => {
    setPosts([]);
    setSkip(0);
    setHasMore(true);
    fetchData(0, false);
  }, [fetchData]);

  const addPost = useCallback((newPost) => {
    // Enrich new post with current user data
    const enrichedPost = {
      ...newPost,
      user_id: newPost.user_id || currentUser?.id,
      user: currentUser,
      author_name: newPost.author_name || currentUser?.name,
      author_avatar_name: newPost.author_avatar_name || currentUser?.avatar_name,
      author_picture: newPost.author_picture || currentUser?.picture,
      author_avatar_picture: newPost.author_avatar_picture || currentUser?.avatar_picture,
      displayName: worldMode === 'avatar'
        ? (newPost.author_avatar_name || currentUser?.avatar_name || currentUser?.name)
        : (newPost.author_name || currentUser?.name),
      displayPicture: worldMode === 'avatar'
        ? (newPost.author_avatar_picture || currentUser?.avatar_picture || currentUser?.picture)
        : (newPost.author_picture || currentUser?.picture),
    };
    setPosts(prev => [enrichedPost, ...prev]);
  }, [currentUser, worldMode]);

  const removePost = useCallback((postId) => {
    setPosts(prev => prev.filter(p => p.id !== postId));
  }, []);

  const updatePost = useCallback((postId, updatedData) => {
    setPosts(prev => prev.map(post => 
      post.id === postId ? { ...post, ...updatedData } : post
    ));
  }, []);

  return {
    posts,
    friends,
    loading,
    loadingMore,
    error,
    hasMore,
    loadMore,
    refresh,
    addPost,
    removePost,
    updatePost,
    refetch: refresh
  };
};

export default useHomeFeed;

