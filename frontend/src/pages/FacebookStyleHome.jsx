import { useState, useEffect, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { 
  Camera, MapPin, Briefcase, Heart, Users, MessageCircle, 
  Settings as SettingsIcon, Bot, User as UserIcon, Search,
  Home, Image, Video, Smile, Send, ThumbsUp, Share2,
  MoreHorizontal, Globe, Lock, TrendingUp, Eye, Sparkles,
  Bookmark, Zap, Star, Clock, ChevronRight, Plus, Bell
} from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import axios from "axios";
import { toast } from "sonner";
import { useWorldMode } from "@/contexts/WorldModeContext";
import SideMessenger from "@/components/SideMessenger";
import AppHeader from "@/components/AppHeader";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Custom CSS styles for the page - Light theme for avatar world
const customStyles = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
  
  /* Light theme styling for avatar world */
  .home-container,
  .home-container * {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    text-shadow: none !important;
    -webkit-font-smoothing: antialiased !important;
    -moz-osx-font-smoothing: grayscale !important;
    text-rendering: optimizeLegibility !important;
  }
  
  .glass-card {
    background: rgba(255, 255, 255, 0.95) !important;
    backdrop-filter: blur(20px);
    border: 1px solid rgba(0, 0, 0, 0.08);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08), 0 4px 24px rgba(0, 0, 0, 0.04);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }
  
  .glass-card:hover {
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12), 0 8px 32px rgba(0, 0, 0, 0.06);
    transform: translateY(-2px);
  }
  
  .glass-card-dark {
    background: rgba(255, 255, 255, 0.95) !important;
    backdrop-filter: blur(20px);
    border: 1px solid rgba(0, 0, 0, 0.08);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08), 0 4px 24px rgba(0, 0, 0, 0.04);
  }
  
  .glass-card-dark:hover {
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12), 0 8px 32px rgba(0, 0, 0, 0.06);
    border-color: rgba(0, 0, 0, 0.12);
  }
  
  .post-card {
    animation: slideUp 0.4s ease-out forwards;
    opacity: 0;
  }
  
  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  
  .post-card:nth-child(1) { animation-delay: 0.05s; }
  .post-card:nth-child(2) { animation-delay: 0.1s; }
  .post-card:nth-child(3) { animation-delay: 0.15s; }
  .post-card:nth-child(4) { animation-delay: 0.2s; }
  .post-card:nth-child(5) { animation-delay: 0.25s; }
  
  .pulse-dot {
    animation: pulse 2s infinite;
  }
  
  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(1.2); }
  }
  
  .shimmer {
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
    background-size: 200% 100%;
    animation: shimmer 2s infinite;
  }
  
  @keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }
  
  .floating {
    animation: float 3s ease-in-out infinite;
  }
  
  @keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
  }
`;

const FacebookStyleHome = ({ user: currentUser, setUser }) => {
  const navigate = useNavigate();
  const { worldMode } = useWorldMode();
  const [mode, setMode] = useState('real');
  const [friends, setFriends] = useState([]);
  const [avatarConversations, setAvatarConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [postText, setPostText] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [friendPosts, setFriendPosts] = useState([]);
  const [showMessenger, setShowMessenger] = useState(false);
  const [selectedFriend, setSelectedFriend] = useState(null);
  const [suggestedUsers, setSuggestedUsers] = useState([]);
  const [sendingRequests, setSendingRequests] = useState(new Set());
  
  // Pagination state
  const [postsSkip, setPostsSkip] = useState(0);
  const [hasMorePosts, setHasMorePosts] = useState(true);
  const [loadingMorePosts, setLoadingMorePosts] = useState(false);
  
  // Like & Comment state
  const [likedPosts, setLikedPosts] = useState(new Set());
  const [showingLikesFor, setShowingLikesFor] = useState(null);
  const [likesData, setLikesData] = useState([]);
  const [likesCount, setLikesCount] = useState(0);
  const [showingCommentsFor, setShowingCommentsFor] = useState(null);
  const [commentsData, setCommentsData] = useState({});
  const [commentText, setCommentText] = useState({});
  const [showCreatePost, setShowCreatePost] = useState(false);

  const isAvatarWorld = worldMode === 'avatar';
  // Use light theme for avatar world
  const isDark = false;

  // Memoize world mode dependent values
  const postType = useMemo(() => worldMode === 'avatar' ? 'avatar' : 'real', [worldMode]);

  const fetchData = useCallback(async (skip = 0, append = false) => {
    try {
      if (!append) {
        setLoading(true);
        setPostsSkip(0);
      } else {
        setLoadingMorePosts(true);
      }
      
      const limit = 20;
      
      const [friendsRes, feedPostsRes] = await Promise.all([
        axios.get(`${API}/friends`, { withCredentials: true }),
        axios.get(`${API}/feed/posts?post_type=${postType}&limit=${limit}&skip=${skip}`, { withCredentials: true })
      ]);
      
      setFriends(friendsRes.data.slice(0, 9));
      
      // API returns { posts: [...], total, skip, limit, has_more }
      const allPosts = feedPostsRes.data?.posts || feedPostsRes.data || [];
      const hasMore = feedPostsRes.data?.has_more || false;
      
      const postsWithUsers = [];
      for (const post of allPosts) {
        // Try to find user in friends list first
        let postUser = friendsRes.data.find(f => f.id === post.user_id);
        
        // If not found, create a minimal user object from post's author info
        // This handles bots and users not in friends list
        if (!postUser) {
          postUser = {
            id: post.user_id,
            name: post.author_name || 'Unknown',
            avatar_name: post.author_avatar_name || post.author_name || 'Unknown',
            picture: post.author_picture,
            avatar_picture: post.author_avatar_picture || post.author_picture,
            is_bot: post.author_is_bot || false
          };
        }
        
        postsWithUsers.push({
          ...post,
          user: postUser,
          displayName: worldMode === 'avatar' 
            ? (post.author_avatar_name || postUser.avatar_name || postUser.name)
            : (post.author_name || postUser.name),
          displayPicture: worldMode === 'avatar'
            ? (post.author_avatar_picture || postUser.avatar_picture || postUser.picture)
            : (post.author_picture || postUser.picture),
          isBot: post.author_is_bot || postUser.is_bot
        });
      }
      
      postsWithUsers.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      
      if (append) {
        setFriendPosts(prev => {
          const allPostsList = [...prev, ...postsWithUsers];
          // Update liked posts
          const likedSet = new Set();
          allPostsList.forEach(post => {
            if (post.liked_by && Array.isArray(post.liked_by) && post.liked_by.includes(currentUser?.id)) {
              likedSet.add(post.id);
            }
          });
          setLikedPosts(likedSet);
          return allPostsList;
        });
      } else {
        setFriendPosts(postsWithUsers);
        // Update liked posts
        const likedSet = new Set();
        postsWithUsers.forEach(post => {
          if (post.liked_by && Array.isArray(post.liked_by) && post.liked_by.includes(currentUser?.id)) {
            likedSet.add(post.id);
          }
        });
        setLikedPosts(likedSet);
      }
      
      setHasMorePosts(hasMore);
      setPostsSkip(skip + postsWithUsers.length);
    } catch (error) {
      console.error("Error fetching data:", error);
    } finally {
      setLoading(false);
      setLoadingMorePosts(false);
    }
  }, [worldMode, postType, currentUser?.id]);
  
  const loadMorePosts = useCallback(() => {
    if (!loadingMorePosts && hasMorePosts) {
      fetchData(postsSkip, true);
    }
  }, [loadingMorePosts, hasMorePosts, postsSkip, fetchData]);
  
  const fetchSuggestedUsers = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/friends/suggestions?limit=5&world_mode=${postType}`, {
        withCredentials: true,
      });
      setSuggestedUsers(response.data || []);
    } catch (error) {
      console.error("Error fetching suggested users:", error);
      setSuggestedUsers([]);
    }
  }, [postType]);

  const handleSendFriendRequest = useCallback(async (userId) => {
    if (!userId) {
      toast.error("Invalid user ID");
      return;
    }
    
    if (sendingRequests.has(userId)) return;
    
    setSendingRequests(new Set(sendingRequests).add(userId));
    try {
      const response = await axios.post(`${API}/friends/request/${userId}`, {}, {
        withCredentials: true,
      });
      
      toast.success("Friend request sent!");
      // Remove from suggestions
      setSuggestedUsers(prev => prev.filter(u => u.id !== userId));
      // Refresh friends list to show updated status
      fetchData(0, false);
    } catch (error) {
      console.error("Error sending friend request:", error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || "Failed to send friend request";
      toast.error(errorMessage);
    } finally {
      const newSet = new Set(sendingRequests);
      newSet.delete(userId);
      setSendingRequests(newSet);
    }
  }, [sendingRequests]);

  const handleImageSelect = useCallback((e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error("Please select an image file");
      return;
    }

    setSelectedImage(file);
    setImagePreview(URL.createObjectURL(file));
  }, []);

  const createPost = useCallback(async () => {
    if (!postText.trim() && !selectedImage) return;

    setUploadingImage(true);
    try {
      let response;

      if (selectedImage) {
        // Upload image with caption
      const formData = new FormData();
      formData.append('file', selectedImage);
        formData.append('caption', postText);
        formData.append('post_type', postType);

        response = await axios.post(`${API}/posts/upload-image`, formData, {
        withCredentials: true,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      } else {
        // Create text-only post
        response = await axios.post(`${API}/profile/posts`, 
        { text: postText, post_type: postType },
        { withCredentials: true }
      );
      }
      
      const newPost = {
        ...response.data.post || response.data,
        user_id: (response.data.post || response.data).user_id || currentUser.id,
        user: currentUser,
        displayName: worldMode === 'avatar' 
          ? (currentUser.avatar_name || currentUser.name)
          : currentUser.name,
        displayPicture: worldMode === 'avatar'
          ? (currentUser.avatar_picture || currentUser.picture)
          : currentUser.picture,
        likes: (response.data.post || response.data).likes || 0,
        liked_by: (response.data.post || response.data).liked_by || [],
        comments: (response.data.post || response.data).comments || [],
        comment_count: (response.data.post || response.data).comment_count || 0
      };
      
      setFriendPosts(prev => [newPost, ...prev]);
      setPostText('');
      setSelectedImage(null);
      setImagePreview(null);
      setShowCreatePost(false);
      toast.success(worldMode === 'avatar' ? "✨ Maya post created!" : "🎉 Post created!");
      
      setTimeout(() => {
        fetchData(0, false);
      }, 500);
    } catch (error) {
      console.error("Error creating post:", error);
      toast.error("Failed to create post");
    } finally {
      setUploadingImage(false);
    }
  }, [postText, selectedImage, postType, worldMode, currentUser?.id, fetchData]);
  
  const handleLikePost = useCallback(async (postId) => {
    try {
      const response = await axios.post(`${API}/posts/${postId}/like`, {}, {
        withCredentials: true,
      });
      
      const newLikedPosts = new Set(likedPosts);
      if (response.data.liked) {
        newLikedPosts.add(postId);
      } else {
        newLikedPosts.delete(postId);
      }
      setLikedPosts(newLikedPosts);
      
      setFriendPosts(prev => prev.map(p => {
        if (p.id === postId) {
          const currentLikedBy = Array.isArray(p.liked_by) ? p.liked_by : [];
          const newLikedBy = response.data.liked 
            ? [...currentLikedBy, currentUser?.id]
            : currentLikedBy.filter(id => id !== currentUser?.id);
          return {
            ...p,
            likes: response.data.likes,
            liked_by: newLikedBy
          };
        }
        return p;
      }));
    } catch (error) {
      console.error("Error liking post:", error);
      toast.error("Failed to like post");
    }
  }, [currentUser?.id, likedPosts]);
  
  const showLikes = useCallback(async (postId) => {
    try {
      const response = await axios.get(`${API}/posts/${postId}/likes`, {
        withCredentials: true,
      });
      console.log("Likes response:", response.data);
      const users = response.data.users || [];
      console.log("Users who liked:", users);
      setLikesData(users);
      setLikesCount(response.data.count || 0);
      setShowingLikesFor(postId);
    } catch (error) {
      console.error("Error fetching likes:", error);
      toast.error("Failed to load likes");
    }
  }, []);
  
  const showComments = useCallback(async (postId) => {
    if (showingCommentsFor === postId) {
      setShowingCommentsFor(null);
      return;
    }
    
    try {
      const response = await axios.get(`${API}/posts/${postId}/comments`, {
        withCredentials: true,
      });
      const comments = Array.isArray(response.data?.comments) 
        ? response.data.comments 
        : [];
      setCommentsData({...commentsData, [postId]: comments});
      setShowingCommentsFor(postId);
    } catch (error) {
      console.error("Error fetching comments:", error);
    }
  }, [commentsData]);
  
  const handleAddComment = useCallback(async (postId) => {
    const text = commentText[postId]?.trim();
    if (!text) return;
    
    try {
      const response = await axios.post(
        `${API}/posts/${postId}/comment`,
        { text },
        { withCredentials: true }
      );
      
      const existingComments = Array.isArray(commentsData[postId]) 
        ? commentsData[postId] 
        : [];
      const newComment = response.data?.comment;
      
      if (newComment) {
        setCommentsData({
          ...commentsData,
          [postId]: [newComment, ...existingComments]
        });
      }
      
      setCommentText(prev => ({...prev, [postId]: ''}));
      
      setFriendPosts(prev => prev.map(p => 
        p.id === postId ? {...p, comment_count: (p.comment_count || 0) + 1} : p
      ));
      
      toast.success("💬 Comment added!");
    } catch (error) {
      console.error("Error adding comment:", error);
      toast.error("Failed to add comment");
    }
  }, [commentText, commentsData]);
  
  const fetchAvatarConversations = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/avatar/conversations`, {
        withCredentials: true,
      });
      setAvatarConversations(response.data);
    } catch (error) {
      console.error("Error fetching avatar conversations:", error);
    }
  }, []);

  const formatTimeAgo = useCallback((dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d`;
    return date.toLocaleDateString();
  }, []);

  // useEffect hooks after all functions are defined
  // Only depend on worldMode to avoid infinite loops - functions are stable with useCallback
  useEffect(() => {
    fetchData(0, false);
    fetchSuggestedUsers();
  }, [worldMode]);

  useEffect(() => {
    if (mode === 'avatar') {
      fetchAvatarConversations();
    }
  }, [mode, fetchAvatarConversations]);

  if (loading) {
    return (
      <>
        <style>{customStyles}</style>
        <div className="min-h-screen flex items-center justify-center home-container bg-gradient-to-br from-blue-50 via-white to-slate-50">
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <Sparkles className="w-8 h-8 text-white" />
      </div>
            <p className="text-sm font-medium text-gray-600">
              {isAvatarWorld ? 'Entering Maya...' : 'Loading your feed...'}
            </p>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <style>{customStyles}</style>
      <div className="min-h-screen home-container bg-gradient-to-br from-blue-50 via-white to-slate-50">
      <AppHeader user={currentUser} setUser={setUser} currentPage="home" />

        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="grid grid-cols-12 gap-6">
            
            {/* Left Sidebar */}
            <div className="col-span-3 space-y-4">
              {/* Profile Card */}
              <div className="rounded-xl overflow-hidden glass-card">
                <div className="p-4">
                  <div 
                    className="flex items-center gap-3 cursor-pointer"
                    onClick={() => navigate('/myprofile')}
                  >
                    <Avatar className="w-14 h-14">
                      <AvatarImage src={isAvatarWorld ? (currentUser.avatar_picture || currentUser.picture) : currentUser.picture} />
                      <AvatarFallback className="text-lg font-semibold bg-blue-500 text-white">
                        {(isAvatarWorld ? (currentUser.avatar_name || currentUser.name) : currentUser.name)?.charAt(0)}
                    </AvatarFallback>
                  </Avatar>
                    <div>
                      <h3 className="font-semibold text-gray-900">
                        {isAvatarWorld ? (currentUser.avatar_name || currentUser.name) : currentUser.name}
                    </h3>
                      <p className="text-sm text-gray-600">
                        {currentUser.bio || (isAvatarWorld ? 'Digital spirit in Maya' : 'Welcome to your feed')}
                  </p>
                </div>
                  </div>
                  </div>
                  </div>

              {/* Quick Links */}
              <div className="rounded-xl p-3 glass-card">
                <div className="space-y-1">
                  {[
                    { icon: Users, label: isAvatarWorld ? 'Connections' : 'Friends', path: '/friends', iconColor: '#3b82f6' },
                    { icon: Heart, label: isAvatarWorld ? 'Neural Links' : 'Matches', path: '/matches', iconColor: '#f43f5e' },
                    { icon: Image, label: 'Gallery', path: '/gallery', iconColor: '#10b981' },
                    { icon: Bookmark, label: 'Saved', path: '#', iconColor: '#f59e0b' },
                  ].map((item, idx) => (
                    <button
                      key={idx}
                      onClick={() => item.path !== '#' ? navigate(item.path) : toast.info('Coming soon!')}
                      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all hover:bg-gray-100"
                    >
                      <item.icon className="w-5 h-5" style={{ color: item.iconColor }} />
                      <span className="font-medium text-sm text-gray-700">{item.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Trending Section */}
              <div className="rounded-xl p-4 glass-card">
                <div className="flex items-center gap-2 mb-3">
                  <TrendingUp className="w-4 h-4 text-purple-500" />
                  <h3 className="font-semibold text-sm text-gray-900">
                    {isAvatarWorld ? 'Trending in Maya' : 'Trending'}
                  </h3>
                          </div>
                <div className="space-y-3">
                  {[
                    { tag: '#Connections', posts: 584 },
                    { tag: '#MayaWorld', posts: 803 },
                    { tag: '#AIFriends', posts: 226 },
                  ].map((item, idx) => (
                    <div key={idx}>
                      <span className="font-semibold text-sm text-gray-900">{item.tag}</span>
                      <p className="text-xs text-gray-600">{item.posts} posts</p>
                        </div>
                  ))}
                  </div>
              </div>
            </div>

            {/* Main Feed */}
            <div className="col-span-6 space-y-4">
              {/* Create Post Card */}
              <div className="rounded-xl p-4 glass-card">
                <div className="flex items-center gap-3">
                  <Avatar className="w-10 h-10">
                    <AvatarImage src={isAvatarWorld ? (currentUser.avatar_picture || currentUser.picture) : currentUser.picture} />
                    <AvatarFallback className="bg-blue-500 text-white">
                      {(isAvatarWorld ? (currentUser.avatar_name || currentUser.name) : currentUser.name)?.charAt(0)}
                    </AvatarFallback>
                  </Avatar>
                  <button
                    onClick={() => setShowCreatePost(true)}
                    className="flex-1 text-left px-4 py-2.5 rounded-full transition-all bg-gray-100 hover:bg-gray-200 text-gray-600"
                  >
                    {isAvatarWorld ? "Share a thought in Maya..." : "What's on your mind?"}
                  </button>
                </div>
                <div className="flex items-center justify-around mt-3 pt-3 border-t border-gray-200">
                  {[
                    { icon: Video, label: 'Live', iconColor: '#fb7185' },
                    { icon: Image, label: 'Photo', iconColor: '#34d399' },
                    { icon: Smile, label: 'Feeling', iconColor: '#fbbf24' },
                  ].map((item, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        if (item.label === 'Photo') {
                          setShowCreatePost(true);
                          // Small delay to ensure dialog is open before triggering file input
                          setTimeout(() => {
                        document.getElementById('post-image-upload')?.click();
                          }, 100);
                        } else {
                          toast.info(`${item.label} feature coming soon!`);
                        }
                      }}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg transition-all hover:bg-gray-100"
                    >
                      <item.icon className="w-5 h-5" style={{ color: item.iconColor }} />
                      <span className="font-medium text-sm text-gray-700">{item.label}</span>
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Create Post Dialog */}
              <Dialog open={showCreatePost} onOpenChange={setShowCreatePost}>
                <DialogContent className="max-w-lg bg-white">
                  <DialogHeader>
                    <DialogTitle className="text-xl font-bold text-gray-900">
                      {isAvatarWorld ? '✨ Create Maya Post' : '📝 Create Post'}
                    </DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 mt-4">
                    <div className="flex items-start gap-3">
                      <Avatar className="w-10 h-10">
                        <AvatarImage src={isAvatarWorld ? (currentUser.avatar_picture || currentUser.picture) : currentUser.picture} />
                        <AvatarFallback>{currentUser.name?.charAt(0)}</AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <p className="font-semibold text-gray-900">
                          {isAvatarWorld ? (currentUser.avatar_name || currentUser.name) : currentUser.name}
                        </p>
                        <div className="flex items-center gap-1 text-xs text-gray-500">
                          <Globe className="w-3 h-3" />
                          <span>Public</span>
                        </div>
                      </div>
                    </div>
                    <Textarea
                      placeholder={isAvatarWorld ? "What's your avatar thinking?" : "What's on your mind?"}
                      value={postText}
                      onChange={(e) => setPostText(e.target.value)}
                      rows={5}
                      className="resize-none border-none text-lg bg-gray-50 focus:ring-blue-500/50"
                    />
                    {/* Hidden file input */}
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleImageSelect}
                      className="hidden"
                      id="post-image-upload"
                    />
                    {/* Image Preview */}
                    {imagePreview && (
                      <div className="relative">
                        <img
                          src={imagePreview}
                          alt="Preview"
                          className="w-full h-64 object-cover rounded-lg"
                        />
                        <button
                          onClick={() => {
                            setSelectedImage(null);
                            setImagePreview(null);
                          }}
                          className="absolute top-2 right-2 bg-red-500 hover:bg-red-600 text-white rounded-full p-1.5"
                        >
                          <span className="text-sm">×</span>
                        </button>
                      </div>
                    )}
                    <div className="flex items-center justify-between">
                      <label
                        htmlFor="post-image-upload"
                        className="cursor-pointer flex items-center gap-2 px-4 py-2 rounded-lg transition-all hover:bg-gray-100 text-gray-700"
                      >
                        <Image className="w-5 h-5" style={{ color: '#34d399' }} />
                        <span className="font-medium text-sm">Add Photo</span>
                      </label>
                      <div className="flex gap-2">
                        <Button 
                          variant="ghost" 
                          onClick={() => {
                        setShowCreatePost(false);
                        setPostText('');
                            setSelectedImage(null);
                            setImagePreview(null);
                          }}
                          className="text-gray-600 hover:bg-gray-100"
                        >
                        Cancel
                      </Button>
                      <Button 
                        onClick={createPost}
                          disabled={(!postText.trim() && !selectedImage) || uploadingImage}
                          className="px-6 bg-blue-500 hover:bg-blue-600 text-white"
                      >
                          {uploadingImage ? 'Posting...' : 'Post'}
                      </Button>
                      </div>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>

              {/* Posts Feed */}
              {friendPosts.length > 0 ? (
                  <div className="space-y-4">
                    {friendPosts.map((post, idx) => (
                    <div 
                      key={post.id || idx} 
                      className="rounded-xl overflow-hidden post-card glass-card"
                      style={{ animationDelay: `${idx * 0.05}s` }}
                    >
                      {/* Post Header */}
                      <div className="p-4 pb-2">
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-3">
                            <div 
                              className="cursor-pointer"
                              onClick={() => navigate(`/profile/${post.user_id || post.user?.id}`)}
                          >
                              <Avatar className="w-11 h-11">
                            <AvatarImage src={post.displayPicture} />
                                <AvatarFallback className="font-medium bg-blue-500 text-white">
                                  {post.displayName?.charAt(0)}
                                </AvatarFallback>
                          </Avatar>
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                              <span 
                                  className="font-semibold cursor-pointer hover:underline text-gray-900"
                                  onClick={() => navigate(`/profile/${post.user_id || post.user?.id}`)}
                              >
                                {post.displayName}
                              </span>
                                {post.isBot && (
                                  <Badge className="text-xs px-1.5 py-0 border-0 bg-purple-100 text-purple-700">
                                    <Bot className="w-3 h-3 mr-0.5" />
                                    AI
                                </Badge>
                              )}
                            </div>
                              <div className="flex items-center gap-1.5 text-xs text-gray-500">
                                <Clock className="w-3 h-3" />
                                <span>{formatTimeAgo(post.created_at)}</span>
                                <span>•</span>
                                <Globe className="w-3 h-3" />
                              </div>
                            </div>
                          </div>
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="rounded-full p-1 h-8 w-8 hover:bg-gray-100 text-gray-600"
                          >
                            <MoreHorizontal className="w-5 h-5" />
                          </Button>
                        </div>
                      </div>

                      {/* Post Content */}
                      <div className="px-4 pb-3">
                        {(post.text || post.content) && (
                          <p className="text-sm leading-relaxed whitespace-pre-wrap text-gray-800 mb-3">
                            {post.text || post.content}
                          </p>
                        )}
                        {/* Post Image */}
                        {(post.image_url || post.has_image) && (
                          <div className="mt-3 rounded-lg overflow-hidden">
                                <img
                                  src={post.image_url}
                                  alt={post.text || post.content || 'Post image'}
                                  className="w-full max-h-96 object-cover cursor-pointer"
                              onClick={() => {
                                // Open image in new tab or modal
                                window.open(post.image_url, '_blank');
                              }}
                                  onError={(e) => {
                                console.error("Image load error:", post.image_url);
                                    e.target.style.display = 'none';
                                  }}
                                />
                              </div>
                            )}
                      </div>

                      {/* Engagement Stats */}
                      {(post.likes > 0 || post.comment_count > 0) && (
                        <div className="px-4 py-2 flex items-center justify-between text-sm text-gray-600">
                          <button 
                                  onClick={() => showLikes(post.id)}
                            className="flex items-center gap-1.5 hover:underline"
                          >
                            {post.likes > 0 && (
                              <>
                                <div className="w-5 h-5 rounded-full flex items-center justify-center bg-blue-500">
                                  <ThumbsUp className="w-3 h-3 text-white fill-white" />
                                </div>
                                <span>{post.likes}</span>
                              </>
                            )}
                          </button>
                          {(post.comment_count > 0 || post.comments?.length > 0) && (
                            <button 
                                  onClick={() => showComments(post.id)}
                              className="hover:underline text-gray-600"
                            >
                              {post.comment_count || post.comments?.length || 0} comments
                            </button>
                          )}
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className="px-2 py-1.5 border-t border-gray-200">
                        <div className="flex items-center justify-around">
                          <button
                            onClick={() => handleLikePost(post.id)}
                            className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg transition-all hover:bg-gray-100 text-gray-700"
                            style={{ color: likedPosts.has(post.id) ? '#3b82f6' : '#4b5563' }}
                          >
                            <ThumbsUp className={`w-4 h-4 ${likedPosts.has(post.id) ? 'fill-current' : ''}`} />
                            <span className="font-medium text-sm">Like</span>
                          </button>
                          <button
                            onClick={() => showComments(post.id)}
                            className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg transition-all hover:bg-gray-100 text-gray-700"
                          >
                            <MessageCircle className="w-4 h-4" />
                            <span className="font-medium text-sm">Comment</span>
                          </button>
                          <button
                                  onClick={() => {
                              navigator.share?.({ title: 'Check out this post!', url: window.location.href }) || toast.info('Share feature coming soon!');
                                  }}
                            className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg transition-all hover:bg-gray-100 text-gray-700"
                                >
                            <Share2 className="w-4 h-4" />
                            <span className="font-medium text-sm">Share</span>
                          </button>
                        </div>
                              </div>
                              
                              {/* Comments Section */}
                              {showingCommentsFor === post.id && (
                        <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
                                  {/* Comment Input */}
                          <div className="flex items-start gap-3 mb-4">
                            <Avatar className="w-8 h-8">
                              <AvatarImage src={currentUser.picture} />
                              <AvatarFallback>{currentUser.name?.charAt(0)}</AvatarFallback>
                            </Avatar>
                            <div className="flex-1 flex gap-2">
                              <Input
                                      placeholder="Write a comment..."
                                      value={commentText[post.id] || ''}
                                      onChange={(e) => setCommentText({...commentText, [post.id]: e.target.value})}
                                onKeyPress={(e) => e.key === 'Enter' && handleAddComment(post.id)}
                                className="rounded-full text-sm bg-white border-gray-200"
                                    />
                                    <Button 
                                      onClick={() => handleAddComment(post.id)}
                                      disabled={!commentText[post.id]?.trim()}
                                size="sm"
                                className="rounded-full px-3 bg-blue-500 hover:bg-blue-600 text-white"
                                    >
                                      <Send className="w-4 h-4" />
                                    </Button>
                            </div>
                                  </div>
                                  
                                  {/* Comments List */}
                                  {(() => {
                            const comments = Array.isArray(commentsData[post.id]) ? commentsData[post.id] : [];
                                    return comments.length > 0 ? (
                              <div className="space-y-3 max-h-64 overflow-y-auto">
                                        {comments.map((comment) => {
                                          if (!comment || typeof comment !== 'object') return null;
                                          return (
                                    <div key={comment.id || Math.random()} className="flex gap-2">
                                      <Avatar className="w-7 h-7">
                                                <AvatarImage src={comment.user_picture || ''} />
                                                <AvatarFallback>{(comment.user_name || '?').charAt(0)}</AvatarFallback>
                                              </Avatar>
                                      <div className="flex-1 rounded-2xl px-4 py-2.5 bg-white">
                                        <p className="text-sm font-semibold text-gray-900">
                                                  {comment.user_name || 'Unknown'}
                                                </p>
                                        <p className="text-sm text-gray-700">
                                                  {comment.text || ''}
                                                </p>
                                        <p className="text-xs mt-1 text-gray-500">
                                          {comment.created_at ? formatTimeAgo(comment.created_at) : ''}
                                                </p>
                                              </div>
                                            </div>
                                          );
                                        })}
                                      </div>
                                    ) : (
                              <p className="text-sm text-center py-4 text-gray-500">
                                No comments yet. Be the first to comment!
                                      </p>
                                    );
                                  })()}
                                </div>
                              )}
                            </div>
                  ))}
                  
                  {/* Load More Button */}
                  {hasMorePosts && (
                    <div className="flex justify-center py-6">
                      <Button
                        onClick={loadMorePosts}
                        disabled={loadingMorePosts}
                        variant="outline"
                        className="px-8 py-2"
                      >
                        {loadingMorePosts ? (
                          <>
                            <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin mr-2"></div>
                            Loading...
                          </>
                        ) : (
                          'Load More Posts'
                        )}
                      </Button>
                    </div>
                  )}
                  </div>
                ) : (
                <div className={`rounded-2xl p-12 text-center ${isDark ? 'glass-card-dark' : 'glass-card'}`}>
                  <div className={`w-20 h-20 mx-auto mb-6 rounded-full flex items-center justify-center ${isDark ? 'bg-blue-500/20' : 'bg-violet-100'}`}>
                    <Sparkles className={`w-10 h-10 ${isDark ? 'text-blue-400' : 'text-violet-500'}`} />
                    </div>
                  <h3 className={`text-2xl font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {isDark ? 'Welcome to Maya' : 'Welcome to your feed!'}
                  </h3>
                  <p className={`mb-6 ${isDark ? 'text-blue-300' : 'text-gray-600'}`}>
                    {isDark 
                      ? 'Connect with other digital spirits and share your thoughts'
                      : 'Start by adding friends or creating your first post'
                    }
                  </p>
                              <Button 
                    onClick={() => navigate('/search')}
                    className={`px-8 py-3 rounded-full ${
                      isDark 
                        ? 'bg-blue-600 hover:bg-blue-500 text-white' 
                        : 'bg-gradient-to-r from-violet-500 to-fuchsia-500 hover:from-violet-600 hover:to-fuchsia-600 text-white'
                    }`}
                  >
                    <Search className="w-5 h-5 mr-2" />
                    Find {isDark ? 'Connections' : 'Friends'}
                              </Button>
                </div>
              )}
            </div>

            {/* Right Sidebar */}
            <div className="col-span-3 space-y-4">
              {/* Connections */}
              <div className="rounded-xl p-4 glass-card">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-sm text-gray-900">
                    {isAvatarWorld ? 'Connections' : 'Friends'}
                  </h3>
                  <button 
                    onClick={() => navigate('/friends')}
                    className="text-xs font-medium hover:opacity-80 text-blue-600"
                  >
                    See all
                  </button>
                </div>
                <div className="space-y-1">
                  {friends.slice(0, 6).map((friend, idx) => {
                    const displayName = isAvatarWorld 
                      ? (friend.avatar_name || friend.name)
                      : friend.name;
                    const displayPicture = isAvatarWorld
                      ? (friend.avatar_picture || friend.picture)
                      : friend.picture;

                    return (
                      <div 
                        key={idx} 
                        className="flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-all hover:bg-gray-100"
                        onClick={() => navigate(`/profile/${friend.id}`)}
                      >
                        <Avatar className="w-9 h-9">
                            <AvatarImage src={displayPicture} />
                          <AvatarFallback className="bg-blue-500 text-white text-sm">
                            {displayName?.charAt(0)}
                          </AvatarFallback>
                          </Avatar>
                        <span className="font-medium text-sm text-gray-700">
                              {displayName}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Discover Spirits / Suggested for you */}
              <div className="rounded-xl p-4 glass-card">
                <h3 className="font-semibold text-sm mb-3 text-gray-900">
                  {isAvatarWorld ? 'Discover Spirits' : 'Suggested for you'}
                </h3>
                <div className="space-y-3">
                  {suggestedUsers.length > 0 ? (
                    suggestedUsers.map((user) => (
                      <div 
                        key={user.id}
                        className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer"
                        onClick={() => navigate(`/profile/${user.id}`)}
                      >
                        <Avatar className="w-10 h-10">
                          <AvatarImage src={user.picture} />
                          <AvatarFallback className="bg-gradient-to-br from-purple-500 to-pink-500 text-white text-sm">
                            {user.name?.charAt(0) || '?'}
                          </AvatarFallback>
                        </Avatar>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm text-gray-900 truncate">
                            {user.name}
                          </p>
                          {user.mutual_connections > 0 ? (
                            <p className="text-xs text-gray-600">
                              {user.mutual_connections} {user.mutual_connections === 1 ? 'mutual connection' : 'mutual connections'}
                            </p>
                          ) : (
                            <p className="text-xs text-gray-500">
                              {isAvatarWorld ? 'Digital Spirit' : 'New to the network'}
                          </p>
                          )}
                        </div>
                        <Button 
                          size="sm"
                          variant="outline"
                          className="rounded-full text-xs border-violet-300 text-violet-600 hover:bg-violet-50 flex-shrink-0"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSendFriendRequest(user.id);
                          }}
                          disabled={sendingRequests.has(user.id)}
                        >
                          <Plus className="w-3 h-3 mr-1" />
                          {sendingRequests.has(user.id) ? 'Sending...' : 'Add'}
            </Button>
          </div>
                    ))
                  ) : (
                    <div className="text-center py-4">
                      <p className="text-sm text-gray-500">
                        {isAvatarWorld ? 'No spirits to discover yet' : 'No suggestions available'}
                      </p>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="mt-2 text-xs text-violet-600 hover:text-violet-700"
                        onClick={() => navigate('/search')}
                      >
                        <Search className="w-3 h-3 mr-1" />
                        Search users
                      </Button>
                  </div>
                  )}
                </div>
              </div>

              {/* Footer Links */}
              <div className={`text-xs space-y-2 px-2 ${isDark ? 'text-blue-400/60' : 'text-gray-400'}`}>
                <div className="flex flex-wrap gap-x-2 gap-y-1">
                  <span className="hover:underline cursor-pointer">Privacy</span>
                  <span>•</span>
                  <span className="hover:underline cursor-pointer">Terms</span>
                  <span>•</span>
                  <span className="hover:underline cursor-pointer">Help</span>
                </div>
                <p>© 2024 {isDark ? 'Maya World' : 'NeuralLinks'}</p>
              </div>
            </div>
                    </div>
                  </div>

      {/* Likes Dialog */}
      <Dialog open={showingLikesFor !== null} onOpenChange={() => setShowingLikesFor(null)}>
          <DialogContent className={`max-w-md ${isDark ? 'bg-slate-900 border-blue-500/30' : 'bg-white'}`}>
          <DialogHeader>
              <DialogTitle className={isDark ? 'text-white' : 'text-gray-900'}>
                People who liked this
              </DialogTitle>
          </DialogHeader>
            <div className="max-h-96 overflow-y-auto space-y-2 mt-4">
            {likesData.length > 0 ? (
              likesData.map((user) => {
                const displayName = user.name || user.avatar_name || 'Unknown User';
                const displayPicture = user.picture || user.avatar_picture || '';
                return (
                  <div 
                    key={user.id || Math.random()} 
                    className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer ${
                      isDark ? 'hover:bg-slate-800' : 'hover:bg-gray-50'
                    }`}
                    onClick={() => {
                      setShowingLikesFor(null);
                      if (user.id) {
                        navigate(`/profile/${user.id}`);
                      }
                    }}
                  >
                  <Avatar className="w-10 h-10">
                      <AvatarImage src={displayPicture} />
                      <AvatarFallback className="bg-blue-500 text-white">
                        {displayName.charAt(0).toUpperCase()}
                      </AvatarFallback>
                  </Avatar>
                    <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      {displayName}
                    </p>
                  </div>
                );
              })
            ) : likesCount > 0 ? (
                <div className="text-center py-6">
                  <div className={`w-12 h-12 mx-auto mb-3 rounded-full flex items-center justify-center ${isDark ? 'bg-blue-500/20' : 'bg-blue-100'}`}>
                    <ThumbsUp className={`w-6 h-6 ${isDark ? 'text-blue-400' : 'text-blue-500'}`} />
                  </div>
                  <p className={isDark ? 'text-blue-200' : 'text-gray-600'}>
                    {likesCount} {likesCount === 1 ? 'person likes' : 'people like'} this
                  </p>
              </div>
            ) : (
                <p className={`text-center py-6 ${isDark ? 'text-blue-400' : 'text-gray-500'}`}>
                  No likes yet
                </p>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Side Messenger */}
        {showMessenger && selectedFriend && (
        <SideMessenger
          user={currentUser}
          otherUserId={selectedFriend.id}
          otherUserData={selectedFriend}
          onClose={() => {
            setShowMessenger(false);
            setSelectedFriend(null);
          }}
        />
      )}
    </div>
    </>
  );
};

export default FacebookStyleHome;
