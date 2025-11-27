import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  Camera, MapPin, Briefcase, Heart, Users, MessageCircle, 
  Settings as SettingsIcon, Bot, User as UserIcon, Edit2, 
  X, Plus, Send, ThumbsUp, Trash2, MoreHorizontal, Palette,
  FileText, Hand, Eye, Share2
} from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { useWorldMode } from "@/contexts/WorldModeContext";
import AppHeader from "@/components/AppHeader";
import SideMessenger from "@/components/SideMessenger";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Avatar Activity Log Component
const AvatarActivityLog = () => {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchActivities = async () => {
      try {
        const response = await axios.get(`${API}/avatar/activity?limit=20`, {
          withCredentials: true,
        });
        setActivities(response.data.activities || []);
      } catch (error) {
        console.error('Failed to fetch activities:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchActivities();
  }, []);

  if (loading) return <p className="text-gray-500">Loading activities...</p>;
  if (activities.length === 0) return <p className="text-gray-500">No activities yet. Enable autonomy to see your avatar in action!</p>;

  return (
    <div className="space-y-3 max-h-96 overflow-y-auto">
      {activities.map((activity, idx) => {
        // Get icon based on action type
        let IconComponent;
        let iconColor;
        if (activity.action_type === 'post') {
          IconComponent = FileText;
          iconColor = 'text-blue-600';
        } else if (activity.action_type === 'comment') {
          IconComponent = MessageCircle;
          iconColor = 'text-green-600';
        } else if (activity.action_type === 'like') {
          IconComponent = Heart;
          iconColor = 'text-red-600';
        } else {
          IconComponent = Hand;
          iconColor = 'text-yellow-600';
        }

        return (
          <Card key={idx} className="p-3 hover:bg-gray-50 transition-colors">
            <div className="flex items-start space-x-4">
              <div className={`p-2 rounded-lg bg-gray-100 ${iconColor}`}>
                <IconComponent className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-800">{activity.description}</p>
                <p className="text-xs text-gray-500 mt-1">{new Date(activity.timestamp).toLocaleString()}</p>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
};

// Avatar Status Component
const AvatarStatus = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await axios.get(`${API}/avatar/status`, {
          withCredentials: true,
        });
        setStatus(response.data);
      } catch (error) {
        console.error('Failed to fetch status:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchStatus();
  }, []);

  if (loading) return <p className="text-gray-500">Loading status...</p>;
  if (!status) return <p className="text-gray-500">Status unavailable</p>;

  return (
    <div className="space-y-4">
      <Card className="p-4">
        <h4 className="font-semibold mb-2">Avatar Configuration</h4>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">Status:</span>
            <span className="font-medium">{status.is_autonomous ? '✅ Active' : '⏸️ Inactive'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Personality:</span>
            <span className="font-medium">{status.archetype}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Activity Level:</span>
            <span className="font-medium">{status.activity_level}</span>
          </div>
        </div>
      </Card>
      
      <Card className="p-4">
        <h4 className="font-semibold mb-2">Recent Performance</h4>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">Last Activity:</span>
            <span className="font-medium">{status.last_activity ? new Date(status.last_activity).toLocaleString() : 'Never'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Actions (Last Hour):</span>
            <span className="font-medium">{status.actions_last_hour || 0}</span>
          </div>
        </div>
      </Card>
      
      {!status.has_avatar && (
        <Card className="p-4 bg-yellow-50 border-yellow-200">
          <p className="text-sm text-yellow-800">⚠️ Avatar profile not yet configured</p>
        </Card>
      )}
    </div>
  );
};

const ProfilePageFull = ({ user: currentUser }) => {
  const navigate = useNavigate();
  const { userId } = useParams();
  const { worldMode } = useWorldMode();
  const [profileUser, setProfileUser] = useState(null);
  const [isOwnProfile, setIsOwnProfile] = useState(false);
  const [friendshipStatus, setFriendshipStatus] = useState('none');
  const [showMessenger, setShowMessenger] = useState(false);
  const [friends, setFriends] = useState([]);
  const [loading, setLoading] = useState(true);
  const [posts, setPosts] = useState([]);
  const [newPostText, setNewPostText] = useState('');
  const [editingPost, setEditingPost] = useState(null);
  const [editedPostText, setEditedPostText] = useState('');
  const [viewMode, setViewMode] = useState('single'); // 'single' or 'both'
  
  // Like & Comment state
  const [likedPosts, setLikedPosts] = useState(new Set()); // Track which posts user liked
  const [showingLikesFor, setShowingLikesFor] = useState(null); // Post ID for showing likes dialog
  const [likesData, setLikesData] = useState([]); // Users who liked
  const [likesCount, setLikesCount] = useState(0); // Total likes count (for posts with likes but no user details)
  const [showingCommentsFor, setShowingCommentsFor] = useState(null); // Post ID for showing comments
  const [commentsData, setCommentsData] = useState({}); // Comments by post ID
  const [commentText, setCommentText] = useState({}); // Comment input by post ID
  
  // Real Profile Edit
  const [showEditRealProfile, setShowEditRealProfile] = useState(false);
  const [editRealProfileData, setEditRealProfileData] = useState({
    location: '',
    job_title: '',
    bio: '',
    interests: []
  });
  
  // Avatar Profile Edit
  const [showEditAvatarProfile, setShowEditAvatarProfile] = useState(false);
  const [editAvatarProfileData, setEditAvatarProfileData] = useState({
    name: '',
    bio: '',
    picture: '',
    interests: [],
    job_title: '',
    location: '',
    avatar_autonomous: false,
    avatar_activity_level: 'medium',
    archetype: 'casual_observer',
    avatar_actions_enabled: {
      like_posts: true,
      comment_posts: true,
      create_posts: true,
      send_friend_requests: true,
      accept_friend_requests: true,
      message_friends: true,
      discover_profiles: true,
      share_posts: false
    }
  });

  useEffect(() => {
    const targetUserId = userId || currentUser.id;
    setIsOwnProfile(targetUserId === currentUser.id);
    setPosts([]); // Clear posts immediately when navigating to a new profile
    fetchProfile(targetUserId);
    fetchFriends(targetUserId);
    fetchPosts(targetUserId); // Pass the targetUserId to fetch correct posts
  }, [userId, currentUser, worldMode]); // Re-fetch when worldMode changes

  const fetchProfile = async (id) => {
    try {
      if (id === currentUser.id) {
        setProfileUser(currentUser);
        setEditRealProfileData({
          location: currentUser.location || '',
          job_title: currentUser.job_title || '',
          bio: currentUser.bio || '',
          interests: currentUser.interests || []
        });
        setEditAvatarProfileData({
          name: currentUser.avatar_name || '',
          bio: currentUser.avatar_bio || '',
          picture: currentUser.avatar_picture || '',
          interests: currentUser.avatar_interests || [],
          job_title: currentUser.avatar_job_title || '',
          location: currentUser.avatar_location || '',
          avatar_autonomous: currentUser.avatar_autonomous || false,
          avatar_activity_level: currentUser.avatar_activity_level || 'medium',
          archetype: currentUser.archetype || 'casual_observer',
          avatar_actions_enabled: currentUser.avatar_actions_enabled || {
            like_posts: true,
            comment_posts: true,
            create_posts: true,
            send_friend_requests: true,
            accept_friend_requests: true,
            message_friends: true,
            discover_profiles: true,
            share_posts: false
          }
        });
      } else {
        const response = await axios.get(`${API}/users/${id}?world_mode=${worldMode}`, {
          withCredentials: true,
        });
        setProfileUser(response.data);
        setFriendshipStatus(response.data.friendship_status || 'none');
      }
    } catch (error) {
      console.error("Error fetching profile:", error);
      toast.error("Profile not found");
    } finally {
      setLoading(false);
    }
  };

  const fetchFriends = async (id) => {
    try {
      // Pass user_id to get that user's friends (not current user's friends)
      const response = await axios.get(`${API}/friends?user_id=${id}`, {
        withCredentials: true,
      });
      setFriends(response.data.slice(0, 9));
    } catch (error) {
      console.error("Error fetching friends:", error);
    }
  };

  const fetchPosts = async (targetUserId) => {
    try {
      const postType = worldMode === 'avatar' ? 'avatar' : 'real';
      // Use the passed targetUserId to get the correct user's posts
      const queryParams = `post_type=${postType}&user_id=${targetUserId}`;
      console.log(`[DEBUG] Fetching posts for user: ${targetUserId}, postType: ${postType}`);
      const response = await axios.get(`${API}/profile/posts?${queryParams}`, {
        withCredentials: true,
      });
      // API returns { posts: [...], total, skip, limit, has_more }
      const postsData = response.data?.posts || response.data || [];
      console.log(`[DEBUG] Received ${postsData.length} posts:`, postsData.map(p => ({id: p.id, text: p.text?.substring(0, 30)})));
      
      // Sanitize posts - ensure comments array is not included (we fetch comments separately)
      // Only keep comment_count, not the full comments array
      const sanitizedPosts = postsData.map(post => {
        const { comments, ...postWithoutComments } = post;
        // Only keep comment_count, not the full comments array to avoid rendering issues
        return {
          ...postWithoutComments,
          comment_count: post.comment_count || (Array.isArray(comments) ? comments.length : 0)
        };
      });
      
      setPosts(sanitizedPosts);
      
      // Initialize liked posts (check if current user liked any posts)
      const likedSet = new Set();
      sanitizedPosts.forEach(post => {
        if (post.liked_by && post.liked_by.includes(currentUser.id)) {
          likedSet.add(post.id);
        }
      });
      setLikedPosts(likedSet);
    } catch (error) {
      console.error("Error fetching posts:", error);
    }
  };

  const createPost = async () => {
    if (!newPostText.trim()) return;
    
    try {
      const postType = worldMode === 'avatar' ? 'avatar' : 'real';
      const response = await axios.post(`${API}/profile/posts`, 
        { text: newPostText, post_type: postType },
        { withCredentials: true }
      );
      setPosts([response.data, ...posts]);
      setNewPostText('');
      toast.success(worldMode === 'avatar' ? "Maya post created!" : "Post created!");
    } catch (error) {
      toast.error("Failed to create post");
    }
  };

  const deletePost = async (postId) => {
    try {
      const postType = worldMode === 'avatar' ? 'avatar' : 'real';
      await axios.delete(`${API}/profile/posts/${postId}?post_type=${postType}`, {
        withCredentials: true,
      });
      setPosts(posts.filter(p => p.id !== postId));
      toast.success("Post deleted");
    } catch (error) {
      toast.error("Failed to delete post");
    }
  };

  // Like/Unlike post
  const handleLikePost = async (postId) => {
    try {
      const response = await axios.post(`${API}/posts/${postId}/like`, {}, {
        withCredentials: true,
      });
      
      // Update local state
      const newLikedPosts = new Set(likedPosts);
      if (response.data.liked) {
        newLikedPosts.add(postId);
      } else {
        newLikedPosts.delete(postId);
      }
      setLikedPosts(newLikedPosts);
      
      // Update post in state
      setPosts(posts.map(p => 
        p.id === postId ? {...p, likes: response.data.likes} : p
      ));
      
      toast.success(response.data.liked ? "Post liked!" : "Post unliked");
    } catch (error) {
      console.error("Error liking post:", error);
      toast.error("Failed to like post");
    }
  };

  // Show who liked a post
  const showLikes = async (postId) => {
    try {
      const response = await axios.get(`${API}/posts/${postId}/likes`, {
        withCredentials: true,
      });
      setLikesData(response.data.users || []);
      setLikesCount(response.data.count || 0);
      setShowingLikesFor(postId);
    } catch (error) {
      console.error("Error fetching likes:", error);
      toast.error("Failed to load likes");
    }
  };

  // Show comments for a post
  const showComments = async (postId) => {
    if (showingCommentsFor === postId) {
      setShowingCommentsFor(null);
      return;
    }
    
    try {
      const response = await axios.get(`${API}/posts/${postId}/comments`, {
        withCredentials: true,
      });
      // Ensure comments is always an array
      const comments = Array.isArray(response.data?.comments) 
        ? response.data.comments 
        : [];
      setCommentsData({...commentsData, [postId]: comments});
      setShowingCommentsFor(postId);
    } catch (error) {
      console.error("Error fetching comments:", error);
      toast.error("Failed to load comments");
    }
  };

  // Add comment to a post
  const handleAddComment = async (postId) => {
    const text = commentText[postId]?.trim();
    if (!text) return;
    
    try {
      const response = await axios.post(
        `${API}/posts/${postId}/comment`,
        { text },
        { withCredentials: true }
      );
      
      // Update comments - ensure we always have an array
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
      
      // Clear input
      setCommentText({...commentText, [postId]: ''});
      
      // Update post comment count
      setPosts(posts.map(p => 
        p.id === postId ? {...p, comment_count: (p.comment_count || 0) + 1} : p
      ));
      
      toast.success("Comment added!");
    } catch (error) {
      console.error("Error adding comment:", error);
      toast.error("Failed to add comment");
    }
  };

  const updatePost = async (postId) => {
    try {
      const postType = worldMode === 'avatar' ? 'avatar' : 'real';
      await axios.put(`${API}/profile/posts/${postId}`, 
        { text: editedPostText, post_type: postType },
        { withCredentials: true }
      );
      setPosts(posts.map(p => p.id === postId ? { ...p, text: editedPostText } : p));
      setEditingPost(null);
      toast.success("Post updated!");
    } catch (error) {
      toast.error("Failed to update post");
    }
  };

  const updateRealProfile = async () => {
    try {
      await axios.put(`${API}/profile`, editRealProfileData, {
        withCredentials: true,
      });
      setProfileUser({ ...profileUser, ...editRealProfileData });
      setShowEditRealProfile(false);
      toast.success("Sense profile updated!");
      // Refresh
      window.location.reload();
    } catch (error) {
      toast.error("Failed to update profile");
    }
  };

  const updateAvatarProfile = async () => {
    try {
      await axios.put(`${API}/profile/avatar`, editAvatarProfileData, {
        withCredentials: true,
      });
      setShowEditAvatarProfile(false);
      toast.success("Maya profile updated!");
      // Refresh
      window.location.reload();
    } catch (error) {
      toast.error("Failed to update maya profile");
    }
  };

  const sendFriendRequest = async () => {
    try {
      await axios.post(`${API}/friends/request/${profileUser.id}`, {}, {
        withCredentials: true,
      });
      toast.success("Friend request sent!");
      setFriendshipStatus('pending');
    } catch (error) {
      toast.error("Failed to send request");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-purple-400 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!profileUser) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <p className="text-gray-600">Profile not found</p>
      </div>
    );
  }

  // Determine what to display based on world mode
  let displayName, displayPicture, displayBio, displayInterests, displayJobTitle, displayLocation;
  
  if (worldMode === 'avatar') {
    // Avatar World - Show avatar identity
    if (isOwnProfile) {
      displayName = profileUser.avatar_name || 'Set Avatar Nickname';
      displayPicture = profileUser.avatar_picture || 'https://api.dicebear.com/7.x/adventurer/svg?seed=default';
      displayBio = profileUser.avatar_bio || 'Configure your maya profile!';
      displayInterests = profileUser.avatar_interests || [];
      displayJobTitle = profileUser.avatar_job_title || '';
      displayLocation = profileUser.avatar_location || '';
    } else {
      // For bots/other users
      if (profileUser.is_bot) {
        displayName = profileUser.avatar_name || profileUser.name;
        displayPicture = profileUser.avatar_picture || profileUser.picture;
        displayBio = profileUser.avatar_bio || profileUser.bio;
      } else {
        displayName = profileUser.avatar_name || profileUser.name;
        displayPicture = profileUser.avatar_picture || profileUser.picture;
        displayBio = profileUser.avatar_bio || profileUser.bio;
      }
      displayInterests = profileUser.avatar_interests || profileUser.interests || [];
      displayJobTitle = profileUser.avatar_job_title || profileUser.job_title;
      displayLocation = profileUser.avatar_location || profileUser.location;
    }
  } else {
    // Real World - Show real identity
    displayName = profileUser.name;
    displayPicture = profileUser.picture;
    displayBio = profileUser.bio;
    displayInterests = profileUser.interests || [];
    displayJobTitle = profileUser.job_title;
    displayLocation = profileUser.location;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <AppHeader user={currentUser} currentPage="profile" />
      
      {/* Cover Photo */}
      <div className="relative h-96 bg-gradient-to-br from-pink-400 via-purple-500 to-indigo-600 profile-cover">
        <div className="absolute inset-0 bg-black/20"></div>
        {isOwnProfile && (
          <Button
            variant="secondary"
            className="absolute bottom-4 right-4 bg-white/90 hover:bg-white"
            onClick={() => toast.info("Cover photo edit coming soon!")}
          >
            <Camera className="w-4 h-4 mr-2" />
            Edit Cover Photo
          </Button>
        )}
      </div>

      {/* Profile Info */}
      <div className="max-w-6xl mx-auto px-6">
        <div className="relative">
          <div className="absolute -top-32 left-8">
            <Avatar className="w-44 h-44 border-8 border-white shadow-xl">
              <AvatarImage src={displayPicture} className="object-cover" />
              <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white text-4xl">
                {displayName?.charAt(0)}
              </AvatarFallback>
            </Avatar>
            {isOwnProfile && (
              <Button
                size="sm"
                className="absolute bottom-2 right-2 rounded-full w-10 h-10 p-0 bg-white hover:bg-gray-100"
                onClick={() => toast.info("Profile photo upload coming soon!")}
              >
                <Camera className="w-5 h-5 text-gray-700" />
              </Button>
            )}
          </div>

          <div className="bg-white shadow rounded-b-2xl">
            <div className="pt-8 pb-4 px-8 ml-56">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h1 className="text-4xl font-bold text-gray-900">{displayName}</h1>
                    {profileUser.is_bot && (
                      <Badge className="bg-purple-100 text-purple-700">
                        <Bot className="w-3 h-3 mr-1" />
                        AI Agent
                      </Badge>
                    )}
                    {worldMode === 'avatar' && (
                      <Badge className="bg-gradient-to-r from-pink-500 to-purple-600 text-white">
                        <Palette className="w-3 h-3 mr-1" />
                        Avatar Mode
                      </Badge>
                    )}
                  </div>
                  
                  <p className="text-gray-600 text-lg mb-2">{displayBio}</p>
                  
                  <div className="flex items-center space-x-4 text-sm text-gray-500">
                    {displayJobTitle && (
                      <span className="flex items-center">
                        <Briefcase className="w-4 h-4 mr-1" />
                        {displayJobTitle}
                      </span>
                    )}
                    {displayLocation && (
                      <span className="flex items-center">
                        <MapPin className="w-4 h-4 mr-1" />
                        {displayLocation}
                      </span>
                    )}
                    <span className="flex items-center">
                      <Users className="w-4 h-4 mr-1" />
                      {friends.length} friends
                    </span>
                  </div>
                </div>

                <div className="flex space-x-2">
                  {isOwnProfile ? (
                    <>
                      {/* Toggle View Mode Button */}
                      <Button
                        onClick={() => setViewMode(viewMode === 'single' ? 'both' : 'single')}
                        variant="outline"
                        className="border-2 border-purple-500 text-purple-700 hover:bg-purple-50"
                      >
                        {viewMode === 'single' ? (
                          <>
                            <Users className="w-4 h-4 mr-2" />
                            View Both Profiles
                          </>
                        ) : (
                          <>
                            <UserIcon className="w-4 h-4 mr-2" />
                            Single View
                          </>
                        )}
                      </Button>
                      
                      {/* Edit Buttons - Show both if in 'both' mode */}
                      {viewMode === 'both' || worldMode === 'real' ? (
                        <Dialog open={showEditRealProfile} onOpenChange={setShowEditRealProfile}>
                          <DialogTrigger asChild>
                            <Button className="bg-blue-500 hover:bg-blue-600 text-white">
                              <SettingsIcon className="w-4 h-4 mr-2" />
                              Edit Sense
                            </Button>
                          </DialogTrigger>
                          <DialogContent className="max-w-2xl">
                            <DialogHeader>
                              <DialogTitle>Edit Sense Profile</DialogTitle>
                            </DialogHeader>
                            <div className="space-y-4 py-4">
                              <div>
                                <label className="block text-sm font-medium mb-2">Bio</label>
                                <Textarea
                                  value={editRealProfileData.bio}
                                  onChange={(e) => setEditRealProfileData({...editRealProfileData, bio: e.target.value})}
                                  placeholder="Tell us about yourself..."
                                  rows={3}
                                />
                              </div>
                              <div>
                                <label className="block text-sm font-medium mb-2">Job Title</label>
                                <Input
                                  value={editRealProfileData.job_title}
                                  onChange={(e) => setEditRealProfileData({...editRealProfileData, job_title: e.target.value})}
                                  placeholder="Your job title"
                                />
                              </div>
                              <div>
                                <label className="block text-sm font-medium mb-2">Location</label>
                                <Input
                                  value={editRealProfileData.location}
                                  onChange={(e) => setEditRealProfileData({...editRealProfileData, location: e.target.value})}
                                  placeholder="Your location"
                                />
                              </div>
                              <Button onClick={updateRealProfile} className="w-full">
                                Save Sense Profile
                              </Button>
                            </div>
                          </DialogContent>
                        </Dialog>
                      ) : null}
                      
                      {viewMode === 'both' || worldMode === 'avatar' ? (
                        <>
                          <Dialog open={showEditAvatarProfile} onOpenChange={setShowEditAvatarProfile}>
                            <DialogTrigger asChild>
                              <Button className="bg-gradient-to-r from-pink-500 to-purple-600 text-white hover:from-pink-600 hover:to-purple-700">
                                <Bot className="w-4 h-4 mr-2" />
                                Edit Maya
                              </Button>
                            </DialogTrigger>
                          <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
                            <DialogHeader>
                              <DialogTitle>Edit Maya Profile</DialogTitle>
                            </DialogHeader>
                            <Tabs defaultValue="profile" className="w-full">
                              <TabsList className="grid w-full grid-cols-4">
                                <TabsTrigger value="profile">Profile</TabsTrigger>
                                <TabsTrigger value="autonomy">Autonomy</TabsTrigger>
                                <TabsTrigger value="activity">Activity</TabsTrigger>
                                <TabsTrigger value="status">Status</TabsTrigger>
                              </TabsList>
                              
                              <TabsContent value="profile" className="space-y-4 py-4">
                              <div>
                                <label className="block text-sm font-medium mb-2">Avatar Nickname</label>
                                <Input
                                  value={editAvatarProfileData.name}
                                  onChange={(e) => setEditAvatarProfileData({...editAvatarProfileData, name: e.target.value})}
                                  placeholder="Your avatar's nickname (e.g., 'Phoenix', 'Shadow')"
                                />
                              </div>
                              <div>
                                <label className="block text-sm font-medium mb-2">Avatar Bio</label>
                                <Textarea
                                  value={editAvatarProfileData.bio}
                                  onChange={(e) => setEditAvatarProfileData({...editAvatarProfileData, bio: e.target.value})}
                                  placeholder="Your avatar's story..."
                                  rows={3}
                                />
                              </div>
                              <div>
                                <label className="block text-sm font-medium mb-2">Avatar Image URL</label>
                                <Input
                                  value={editAvatarProfileData.picture}
                                  onChange={(e) => setEditAvatarProfileData({...editAvatarProfileData, picture: e.target.value})}
                                  placeholder="https://api.dicebear.com/7.x/adventurer/svg?seed=YourName"
                                />
                                <p className="text-xs text-gray-500 mt-1">
                                  Try: https://api.dicebear.com/7.x/adventurer/svg?seed=YourName (replace YourName)
                                </p>
                              </div>
                              <div>
                                <label className="block text-sm font-medium mb-2">Avatar Job Title</label>
                                <Input
                                  value={editAvatarProfileData.job_title}
                                  onChange={(e) => setEditAvatarProfileData({...editAvatarProfileData, job_title: e.target.value})}
                                  placeholder="Digital Warrior, Dream Architect, etc."
                                />
                              </div>
                              <div>
                                <label className="block text-sm font-medium mb-2">Avatar Location</label>
                                <Input
                                  value={editAvatarProfileData.location}
                                  onChange={(e) => setEditAvatarProfileData({...editAvatarProfileData, location: e.target.value})}
                                  placeholder="Virtual Realm, Cyberspace, etc."
                                />
                              </div>
                              <Button onClick={updateAvatarProfile} className="w-full bg-gradient-to-r from-pink-500 to-purple-600">
                                Save Profile
                              </Button>
                              </TabsContent>
                              
                              <TabsContent value="autonomy" className="space-y-4 py-4">
                                <h3 className="text-lg font-semibold mb-4">🤖 Avatar Autonomy Settings</h3>
                                
                                <div className="flex items-center justify-between mb-4">
                                  <div>
                                    <label className="block text-sm font-medium">Enable Autonomy</label>
                                    <p className="text-xs text-gray-500">Let your avatar act automatically</p>
                                  </div>
                                  <Switch
                                    checked={editAvatarProfileData.avatar_autonomous || false}
                                    onCheckedChange={(checked) => setEditAvatarProfileData({...editAvatarProfileData, avatar_autonomous: checked})}
                                  />
                                </div>

                                <div className="mb-4">
                                  <label className="block text-sm font-medium mb-2">Activity Level</label>
                                  <Select
                                    value={editAvatarProfileData.avatar_activity_level || 'medium'}
                                    onValueChange={(value) => setEditAvatarProfileData({...editAvatarProfileData, avatar_activity_level: value})}
                                  >
                                    <SelectTrigger>
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="hypo">Hypo (1 action/2 mins - Testing)</SelectItem>
                                      <SelectItem value="low">Low (1-2 actions/day)</SelectItem>
                                      <SelectItem value="medium">Medium (5-10 actions/day)</SelectItem>
                                      <SelectItem value="high">High (15-20 actions/day)</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </div>

                                <div className="mb-4">
                                  <label className="block text-sm font-medium mb-2">Personality Archetype</label>
                                  <Select
                                    value={editAvatarProfileData.archetype || 'casual_observer'}
                                    onValueChange={(value) => setEditAvatarProfileData({...editAvatarProfileData, archetype: value})}
                                  >
                                    <SelectTrigger>
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="social_butterfly">Social Butterfly - Highly active, loves conversations</SelectItem>
                                      <SelectItem value="thoughtful_contributor">Thoughtful Contributor - Quality over quantity</SelectItem>
                                      <SelectItem value="casual_observer">Casual Observer - Occasional contributions</SelectItem>
                                      <SelectItem value="niche_expert">Niche Expert - Focused deep knowledge</SelectItem>
                                      <SelectItem value="enthusiastic_newcomer">Enthusiastic Newcomer - Excited and learning</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </div>

                                {/* Avatar Action Controls */}
                                <div className="border-t pt-4 mt-4">
                                  <h4 className="text-md font-semibold mb-3">🎮 Allowed Actions</h4>
                                  <p className="text-xs text-gray-500 mb-4">Control what your avatar can do autonomously</p>
                                  
                                  <div className="space-y-3">
                                    {[
                                      { key: 'like_posts', label: 'Like Posts', icon: '👍', desc: 'Like posts from friends' },
                                      { key: 'comment_posts', label: 'Comment on Posts', icon: '💬', desc: 'Comment on posts from friends' },
                                      { key: 'create_posts', label: 'Create Posts', icon: '📝', desc: 'Create and publish new posts' },
                                      { key: 'send_friend_requests', label: 'Send Friend Requests', icon: '👥', desc: 'Send friend requests to other avatars' },
                                      { key: 'accept_friend_requests', label: 'Accept Friend Requests', icon: '✅', desc: 'Accept incoming friend requests' },
                                      { key: 'message_friends', label: 'Message Friends', icon: '💌', desc: 'Send messages to friends' },
                                      { key: 'discover_profiles', label: 'Discover Profiles', icon: '🔍', desc: 'Browse and view other profiles' },
                                      { key: 'share_posts', label: 'Share Posts', icon: '📤', desc: 'Share posts (coming soon)' }
                                    ].map((action) => (
                                      <div key={action.key} className="flex items-center justify-between p-3 rounded-lg border bg-gray-50 hover:bg-gray-100 transition-colors">
                                        <div className="flex items-center space-x-3 flex-1">
                                          <span className="text-xl">{action.icon}</span>
                                          <div className="flex-1">
                                            <label className="text-sm font-medium cursor-pointer" htmlFor={`action-${action.key}`}>
                                              {action.label}
                                            </label>
                                            <p className="text-xs text-gray-500">{action.desc}</p>
                                          </div>
                                        </div>
                                        <Switch
                                          id={`action-${action.key}`}
                                          checked={editAvatarProfileData.avatar_actions_enabled?.[action.key] ?? true}
                                          onCheckedChange={(checked) => {
                                            setEditAvatarProfileData({
                                              ...editAvatarProfileData,
                                              avatar_actions_enabled: {
                                                ...editAvatarProfileData.avatar_actions_enabled,
                                                [action.key]: checked
                                              }
                                            });
                                          }}
                                          disabled={!editAvatarProfileData.avatar_autonomous}
                                        />
                                      </div>
                                    ))}
                                  </div>
                                  
                                  {!editAvatarProfileData.avatar_autonomous && (
                                    <p className="text-xs text-gray-400 mt-3 text-center">
                                      Enable autonomy above to configure actions
                                    </p>
                                  )}
                                </div>

                              <Button onClick={updateAvatarProfile} className="w-full bg-gradient-to-r from-pink-500 to-purple-600 mt-4">
                                Save Autonomy Settings
                              </Button>
                              </TabsContent>
                              
                              <TabsContent value="activity" className="space-y-4 py-4">
                                <h3 className="text-lg font-semibold mb-4">📊 Recent Activity</h3>
                                <AvatarActivityLog />
                              </TabsContent>
                              
                              <TabsContent value="status" className="space-y-4 py-4">
                                <h3 className="text-lg font-semibold mb-4">⚡ Avatar Status</h3>
                                <AvatarStatus />
                              </TabsContent>
                            </Tabs>
                          </DialogContent>
                        </Dialog>
                      </>
                      ) : null}
                    </>
                  ) : (
                    <>
                      {friendshipStatus === 'accepted' ? (
                        <>
                          <Button className="bg-gray-200 hover:bg-gray-300 text-gray-800">
                            <Users className="w-4 h-4 mr-2" />
                            Friends
                          </Button>
                          <Button 
                            onClick={() => setShowMessenger(true)}
                            className="bg-blue-500 hover:bg-blue-600 text-white"
                          >
                            <MessageCircle className="w-4 h-4 mr-2" />
                            Message
                          </Button>
                        </>
                      ) : friendshipStatus === 'pending' ? (
                        <Button disabled className="bg-gray-300 text-gray-600">
                          Request Pending
                        </Button>
                      ) : (
                        <Button
                          onClick={sendFriendRequest}
                          className="bg-blue-500 hover:bg-blue-600 text-white"
                        >
                          <Users className="w-4 h-4 mr-2" />
                          Add Friend
                        </Button>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="border-t border-gray-200 px-8">
              <Tabs defaultValue="posts" className="w-full">
                <TabsList className="bg-transparent border-none h-auto p-0 space-x-2">
                  <TabsTrigger
                    value="posts"
                    className="data-[state=active]:border-b-4 data-[state=active]:border-purple-600 rounded-none pb-3 pt-3"
                  >
                    Posts
                  </TabsTrigger>
                  <TabsTrigger
                    value="about"
                    className="data-[state=active]:border-b-4 data-[state=active]:border-purple-600 rounded-none pb-3 pt-3"
                  >
                    About
                  </TabsTrigger>
                  <TabsTrigger
                    value="friends"
                    className="data-[state=active]:border-b-4 data-[state=active]:border-purple-600 rounded-none pb-3 pt-3"
                  >
                    Friends
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="grid grid-cols-5 gap-6 mt-6 pb-12">
          {/* Left Sidebar */}
          <div className="col-span-2 space-y-4">
            {/* About Card */}
            <Card className="p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">About</h2>
              <div className="space-y-3">
                {displayJobTitle && (
                  <div className="flex items-center text-gray-700">
                    <Briefcase className="w-5 h-5 mr-3 text-gray-500" />
                    <span>{displayJobTitle}</span>
                  </div>
                )}
                {displayLocation && (
                  <div className="flex items-center text-gray-700">
                    <MapPin className="w-5 h-5 mr-3 text-gray-500" />
                    <span>Lives in {displayLocation}</span>
                  </div>
                )}
              </div>
            </Card>

            {/* Interests */}
            {displayInterests && displayInterests.length > 0 && (
              <Card className="p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Interests</h2>
                <div className="flex flex-wrap gap-2">
                  {displayInterests.map((interest, idx) => (
                    <Badge key={idx} className="bg-purple-100 text-purple-700 px-3 py-1">
                      {interest}
                    </Badge>
                  ))}
                </div>
              </Card>
            )}

            {/* Friends */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900">Friends</h2>
                <Button
                  variant="ghost"
                  onClick={() => navigate('/friends')}
                  className="text-purple-600 hover:text-purple-700"
                >
                  See All
                </Button>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {friends.slice(0, 9).map((friend, idx) => {
                  const friendDisplayName = worldMode === 'avatar'
                    ? (friend.avatar_name || friend.name)
                    : friend.name;
                  const friendDisplayPicture = worldMode === 'avatar'
                    ? (friend.avatar_picture || friend.picture)
                    : friend.picture;
                  
                  return (
                    <div key={idx} className="cursor-pointer" onClick={() => navigate(`/profile/${friend.id}`)}>
                      <div className="w-full aspect-square mb-1 rounded-lg overflow-hidden">
                        <img 
                          src={friendDisplayPicture} 
                          alt={friendDisplayName}
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <p className="text-xs font-medium text-gray-900 truncate">{friendDisplayName}</p>
                    </div>
                  );
                })}
              </div>
            </Card>
          </div>

          {/* Main Content */}
          <div className="col-span-3 space-y-4">
            {/* View Mode Selector Banner for Own Profile */}
            {isOwnProfile && viewMode === 'both' && (
              <Card className="p-6 bg-gradient-to-r from-blue-50 to-purple-50 border-2 border-blue-300">
                <div className="flex items-center space-x-3 mb-3">
                  <Users className="w-6 h-6 text-blue-600" />
                  <h3 className="text-lg font-bold text-gray-900">👤 Viewing Both Profiles</h3>
                </div>
                <p className="text-gray-700">
                  You're viewing both your Sense and Maya profiles side-by-side. Edit either profile independently!
                </p>
              </Card>
            )}
            
            {worldMode === 'avatar' && viewMode === 'single' && (
              <Card className="p-6 bg-gradient-to-r from-pink-50 to-purple-50 border-2 border-purple-300">
                <div className="flex items-center space-x-3 mb-3">
                  <Bot className="w-6 h-6 text-purple-600" />
                  <h3 className="text-lg font-bold text-gray-900">
                    {isOwnProfile ? '🎮 Maya Mode - Your Digital Identity' : '🎮 Maya Mode'}
                  </h3>
                </div>
                <p className="text-gray-700">
                  {isOwnProfile 
                    ? `You're viewing your Maya profile as ${displayName}. Create Maya-specific posts here that are different from your Sense posts! Your Maya identity is automatically tied to your Sense profile.`
                    : `You're viewing ${displayName}'s Maya profile. This is their digital persona with unique content and identity.`
                  }
                </p>
              </Card>
            )}

            {/* Dual Profile View (Side by Side) */}
            {isOwnProfile && viewMode === 'both' ? (
              <div className="grid grid-cols-2 gap-4">
                {/* SENSE PROFILE COLUMN */}
                <div className="space-y-4">
                  <Card className="p-4 bg-blue-50 border-2 border-blue-400">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-xl font-bold text-blue-900">👤 Sense Profile</h3>
                      <Dialog open={showEditRealProfile} onOpenChange={setShowEditRealProfile}>
                        <DialogTrigger asChild>
                          <Button size="sm" className="bg-blue-500 hover:bg-blue-600 text-white">
                            <Edit2 className="w-3 h-3 mr-1" />
                            Edit
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-2xl">
                          <DialogHeader>
                            <DialogTitle>Edit Sense Profile</DialogTitle>
                          </DialogHeader>
                          <div className="space-y-4 py-4">
                            <div>
                              <label className="block text-sm font-medium mb-2">Bio</label>
                              <Textarea
                                value={editRealProfileData.bio}
                                onChange={(e) => setEditRealProfileData({...editRealProfileData, bio: e.target.value})}
                                rows={3}
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium mb-2">Job Title</label>
                              <Input
                                value={editRealProfileData.job_title}
                                onChange={(e) => setEditRealProfileData({...editRealProfileData, job_title: e.target.value})}
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium mb-2">Location</label>
                              <Input
                                value={editRealProfileData.location}
                                onChange={(e) => setEditRealProfileData({...editRealProfileData, location: e.target.value})}
                              />
                            </div>
                            <Button onClick={updateRealProfile} className="w-full">Save</Button>
                          </div>
                        </DialogContent>
                      </Dialog>
                    </div>
                    <div className="flex flex-col items-center mb-4">
                      <Avatar className="w-20 h-20 mb-2">
                        <AvatarImage src={profileUser.picture} className="object-cover" />
                        <AvatarFallback>{profileUser.name?.charAt(0)}</AvatarFallback>
                      </Avatar>
                      <h4 className="font-bold text-lg">{profileUser.name}</h4>
                      <p className="text-sm text-gray-600">{profileUser.bio}</p>
                      <p className="text-xs text-gray-500 mt-2">{profileUser.job_title} • {profileUser.location}</p>
                    </div>
                  </Card>
                  
                  {/* Sense Posts */}
                  <h4 className="font-semibold text-gray-700">Sense Posts</h4>
                  {profileUser.posts && Array.isArray(profileUser.posts) && profileUser.posts.length > 0 ? (
                    profileUser.posts.slice(0, 3).map((post) => {
                      // Ensure post is a valid object and extract only safe fields
                      if (!post || typeof post !== 'object') return null;
                      const { comments, ...safePost } = post;
                      return (
                        <Card key={safePost.id || Math.random()} className="p-3">
                          <p className="text-sm text-gray-800">{safePost.text || ''}</p>
                          <p className="text-xs text-gray-500 mt-2">
                            {safePost.created_at ? new Date(safePost.created_at).toLocaleDateString() : ''}
                          </p>
                        </Card>
                      );
                    })
                  ) : (
                    <Card className="p-4 text-center">
                      <p className="text-sm text-gray-500">No sense posts yet</p>
                    </Card>
                  )}
                </div>

                {/* MAYA PROFILE COLUMN */}
                <div className="space-y-4">
                  <Card className="p-4 bg-purple-50 border-2 border-purple-400">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-xl font-bold text-purple-900">🎮 Maya Profile</h3>
                      <Dialog open={showEditAvatarProfile} onOpenChange={setShowEditAvatarProfile}>
                        <DialogTrigger asChild>
                          <Button size="sm" className="bg-gradient-to-r from-pink-500 to-purple-600 text-white">
                            <Edit2 className="w-3 h-3 mr-1" />
                            Edit
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
                          <DialogHeader>
                            <DialogTitle>Edit Maya Profile</DialogTitle>
                          </DialogHeader>
                          <Tabs defaultValue="profile" className="w-full">
                            <TabsList className="grid w-full grid-cols-4">
                              <TabsTrigger value="profile">Profile</TabsTrigger>
                              <TabsTrigger value="autonomy">Autonomy</TabsTrigger>
                              <TabsTrigger value="activity">Activity</TabsTrigger>
                              <TabsTrigger value="status">Status</TabsTrigger>
                            </TabsList>
                            
                            <TabsContent value="profile" className="space-y-4 py-4">
                            <div>
                              <label className="block text-sm font-medium mb-2">Maya Nickname</label>
                              <Input
                                value={editAvatarProfileData.name}
                                onChange={(e) => setEditAvatarProfileData({...editAvatarProfileData, name: e.target.value})}
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium mb-2">Maya Bio</label>
                              <Textarea
                                value={editAvatarProfileData.bio}
                                onChange={(e) => setEditAvatarProfileData({...editAvatarProfileData, bio: e.target.value})}
                                rows={3}
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium mb-2">Maya Image URL</label>
                              <Input
                                value={editAvatarProfileData.picture}
                                onChange={(e) => setEditAvatarProfileData({...editAvatarProfileData, picture: e.target.value})}
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium mb-2">Maya Job Title</label>
                              <Input
                                value={editAvatarProfileData.job_title}
                                onChange={(e) => setEditAvatarProfileData({...editAvatarProfileData, job_title: e.target.value})}
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium mb-2">Maya Location</label>
                              <Input
                                value={editAvatarProfileData.location}
                                onChange={(e) => setEditAvatarProfileData({...editAvatarProfileData, location: e.target.value})}
                              />
                            </div>
                            <Button onClick={updateAvatarProfile} className="w-full bg-gradient-to-r from-pink-500 to-purple-600">Save Profile</Button>
                            </TabsContent>
                            
                            <TabsContent value="autonomy" className="space-y-4 py-4">
                              <h3 className="text-lg font-semibold mb-4">🤖 Avatar Autonomy Settings</h3>
                              
                              <div className="flex items-center justify-between mb-4">
                                <div>
                                  <label className="block text-sm font-medium">Enable Autonomy</label>
                                  <p className="text-xs text-gray-500">Let your avatar act automatically</p>
                                </div>
                                <Switch
                                  checked={editAvatarProfileData.avatar_autonomous || false}
                                  onCheckedChange={(checked) => setEditAvatarProfileData({...editAvatarProfileData, avatar_autonomous: checked})}
                                />
                              </div>

                              <div className="mb-4">
                                <label className="block text-sm font-medium mb-2">Activity Level</label>
                                <Select
                                  value={editAvatarProfileData.avatar_activity_level || 'medium'}
                                  onValueChange={(value) => setEditAvatarProfileData({...editAvatarProfileData, avatar_activity_level: value})}
                                >
                                  <SelectTrigger>
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="hypo">Hypo (1 action/2 mins - Testing)</SelectItem>
                                    <SelectItem value="low">Low (1-2 actions/day)</SelectItem>
                                    <SelectItem value="medium">Medium (5-10 actions/day)</SelectItem>
                                    <SelectItem value="high">High (15-20 actions/day)</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>

                              <div className="mb-4">
                                <label className="block text-sm font-medium mb-2">Personality Archetype</label>
                                <Select
                                  value={editAvatarProfileData.archetype || 'casual_observer'}
                                  onValueChange={(value) => setEditAvatarProfileData({...editAvatarProfileData, archetype: value})}
                                >
                                  <SelectTrigger>
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="social_butterfly">Social Butterfly - Highly active, loves conversations</SelectItem>
                                    <SelectItem value="thoughtful_contributor">Thoughtful Contributor - Quality over quantity</SelectItem>
                                    <SelectItem value="casual_observer">Casual Observer - Occasional contributions</SelectItem>
                                    <SelectItem value="niche_expert">Niche Expert - Focused deep knowledge</SelectItem>
                                    <SelectItem value="enthusiastic_newcomer">Enthusiastic Newcomer - Excited and learning</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>

                              {/* Avatar Action Controls */}
                              <div className="border-t pt-4 mt-4">
                                <h4 className="text-md font-semibold mb-3">🎮 Allowed Actions</h4>
                                <p className="text-xs text-gray-500 mb-4">Control what your avatar can do autonomously</p>
                                
                                <div className="space-y-3">
                                  {[
                                    { key: 'like_posts', label: 'Like Posts', icon: '👍', desc: 'Like posts from friends' },
                                    { key: 'comment_posts', label: 'Comment on Posts', icon: '💬', desc: 'Comment on posts from friends' },
                                    { key: 'create_posts', label: 'Create Posts', icon: '📝', desc: 'Create and publish new posts' },
                                    { key: 'send_friend_requests', label: 'Send Friend Requests', icon: '👥', desc: 'Send friend requests to other avatars' },
                                    { key: 'accept_friend_requests', label: 'Accept Friend Requests', icon: '✅', desc: 'Accept incoming friend requests' },
                                    { key: 'message_friends', label: 'Message Friends', icon: '💌', desc: 'Send messages to friends' },
                                    { key: 'discover_profiles', label: 'Discover Profiles', icon: '🔍', desc: 'Browse and view other profiles' },
                                    { key: 'share_posts', label: 'Share Posts', icon: '📤', desc: 'Share posts (coming soon)' }
                                  ].map((action) => (
                                    <div key={action.key} className="flex items-center justify-between p-3 rounded-lg border bg-gray-50 hover:bg-gray-100 transition-colors">
                                      <div className="flex items-center space-x-3 flex-1">
                                        <span className="text-xl">{action.icon}</span>
                                        <div className="flex-1">
                                          <label className="text-sm font-medium cursor-pointer" htmlFor={`action-${action.key}-2`}>
                                            {action.label}
                                          </label>
                                          <p className="text-xs text-gray-500">{action.desc}</p>
                                        </div>
                                      </div>
                                      <Switch
                                        id={`action-${action.key}-2`}
                                        checked={editAvatarProfileData.avatar_actions_enabled?.[action.key] ?? true}
                                        onCheckedChange={(checked) => {
                                          setEditAvatarProfileData({
                                            ...editAvatarProfileData,
                                            avatar_actions_enabled: {
                                              ...editAvatarProfileData.avatar_actions_enabled,
                                              [action.key]: checked
                                            }
                                          });
                                        }}
                                        disabled={!editAvatarProfileData.avatar_autonomous}
                                      />
                                    </div>
                                  ))}
                                </div>
                                
                                {!editAvatarProfileData.avatar_autonomous && (
                                  <p className="text-xs text-gray-400 mt-3 text-center">
                                    Enable autonomy above to configure actions
                                  </p>
                                )}
                              </div>

                              <Button onClick={updateAvatarProfile} className="w-full bg-gradient-to-r from-pink-500 to-purple-600 mt-4">Save Autonomy Settings</Button>
                            </TabsContent>
                            
                            <TabsContent value="activity" className="space-y-4 py-4">
                              <h3 className="text-lg font-semibold mb-4">📊 Recent Activity</h3>
                              <AvatarActivityLog />
                            </TabsContent>
                            
                            <TabsContent value="status" className="space-y-4 py-4">
                              <h3 className="text-lg font-semibold mb-4">⚡ Avatar Status</h3>
                              <AvatarStatus />
                            </TabsContent>
                          </Tabs>
                        </DialogContent>
                      </Dialog>
                    </div>
                    <div className="flex flex-col items-center mb-4">
                      <Avatar className="w-20 h-20 mb-2 border-2 border-purple-400">
                        <AvatarImage src={profileUser.avatar_picture} className="object-cover" />
                        <AvatarFallback>{profileUser.avatar_name?.charAt(0)}</AvatarFallback>
                      </Avatar>
                      <h4 className="font-bold text-lg">{profileUser.avatar_name}</h4>
                      <p className="text-sm text-gray-600">{profileUser.avatar_bio}</p>
                      <p className="text-xs text-gray-500 mt-2">{profileUser.avatar_job_title} • {profileUser.avatar_location}</p>
                    </div>
                  </Card>
                  
                  {/* Maya Posts */}
                  <h4 className="font-semibold text-gray-700">Maya Posts</h4>
                  {profileUser.avatar_posts && Array.isArray(profileUser.avatar_posts) && profileUser.avatar_posts.length > 0 ? (
                    profileUser.avatar_posts.slice(0, 3).map((post) => {
                      // Ensure post is a valid object and extract only safe fields
                      if (!post || typeof post !== 'object') return null;
                      const { comments, ...safePost } = post;
                      return (
                        <Card key={safePost.id || Math.random()} className="p-3">
                          <p className="text-sm text-gray-800">{safePost.text || ''}</p>
                          <p className="text-xs text-gray-500 mt-2">
                            {safePost.created_at ? new Date(safePost.created_at).toLocaleDateString() : ''}
                          </p>
                        </Card>
                      );
                    })
                  ) : (
                    <Card className="p-4 text-center">
                      <p className="text-sm text-gray-500">No maya posts yet</p>
                    </Card>
                  )}
                </div>
              </div>
            ) : (
              <>
                {/* Single View - Original Layout */}

            {/* Create Post (Own Profile Only) */}
            {isOwnProfile && (
              <Card className="p-4">
                <div className="flex items-start space-x-3">
                  <Avatar className="w-10 h-10">
                    <AvatarImage src={displayPicture} className="object-cover" />
                    <AvatarFallback>{displayName?.charAt(0)}</AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <Textarea
                      placeholder={worldMode === 'real' ? "What's on your mind?" : "What's your maya thinking?"}
                      value={newPostText}
                      onChange={(e) => setNewPostText(e.target.value)}
                      className="mb-2"
                      rows={2}
                    />
                    <Button 
                      onClick={createPost}
                      disabled={!newPostText.trim()}
                      className="bg-purple-600 hover:bg-purple-700 text-white"
                    >
                      <Send className="w-4 h-4 mr-2" />
                      Post
                    </Button>
                  </div>
                </div>
              </Card>
            )}

            {/* Posts */}
            {posts.length > 0 ? (
              <div className="space-y-4">
                {posts.map((post) => (
                  <Card key={post.id} className="p-4">
                    <div className="flex items-start space-x-3">
                      <Avatar className="w-10 h-10">
                        <AvatarImage src={displayPicture} className="object-cover" />
                        <AvatarFallback>{displayName?.charAt(0)}</AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-semibold">{displayName}</span>
                          <div className="flex items-center space-x-2">
                            <span className="text-xs text-gray-500">
                              {new Date(post.created_at).toLocaleDateString()}
                            </span>
                            {isOwnProfile && (
                              <>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => {
                                    setEditingPost(post.id);
                                    setEditedPostText(post.text);
                                  }}
                                  className="p-1 h-auto"
                                >
                                  <Edit2 className="w-4 h-4" />
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => deletePost(post.id)}
                                  className="p-1 h-auto text-red-600 hover:text-red-700"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </>
                            )}
                          </div>
                        </div>
                        
                        {editingPost === post.id ? (
                          <div className="space-y-2">
                            <Textarea
                              value={editedPostText}
                              onChange={(e) => setEditedPostText(e.target.value)}
                              rows={2}
                            />
                            <div className="flex space-x-2">
                              <Button size="sm" onClick={() => updatePost(post.id)}>
                                Save
                              </Button>
                              <Button size="sm" variant="ghost" onClick={() => setEditingPost(null)}>
                                Cancel
                              </Button>
                            </div>
                          </div>
                        ) : (
                          <p className="text-gray-800 mb-3">{post.text}</p>
                        )}
                        
                        <div className="space-y-3">
                          <div className="flex items-center space-x-6 text-sm border-t pt-2">
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="hover:bg-blue-50"
                              onClick={() => handleLikePost(post.id)}
                            >
                              <ThumbsUp 
                                className="w-5 h-5 mr-1" 
                                style={{ 
                                  color: '#1d4ed8', 
                                  fill: likedPosts.has(post.id) ? '#1d4ed8' : 'none' 
                                }} 
                              />
                              <span className="font-semibold" style={{ color: '#1d4ed8' }}>{post.likes || 0}</span>
                            </Button>
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="hover:bg-purple-50"
                              onClick={() => showLikes(post.id)}
                            >
                              <Eye className="w-5 h-5 mr-1" style={{ color: '#7e22ce' }} />
                            </Button>
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="hover:bg-green-50"
                              onClick={() => showComments(post.id)}
                            >
                              <MessageCircle className="w-5 h-5 mr-1" style={{ color: '#15803d' }} />
                              <span className="font-semibold" style={{ color: '#15803d' }}>{Array.isArray(post.comments) ? post.comments.length : (post.comment_count || 0)}</span>
                            </Button>
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="hover:bg-orange-50"
                              onClick={() => {
                                // Share functionality - can be implemented later
                                navigator.share?.({ title: 'Check out this post!', url: window.location.href }) || toast.info('Share feature coming soon');
                              }}
                            >
                              <Share2 className="w-5 h-5 mr-1" style={{ color: '#c2410c' }} />
                            </Button>
                          </div>
                          
                          {/* Comments Section */}
                          {showingCommentsFor === post.id && (
                            <div className="border-t pt-3 space-y-3">
                              {/* Comment Input */}
                              <div className="flex space-x-2">
                                <Textarea
                                  placeholder="Write a comment..."
                                  value={commentText[post.id] || ''}
                                  onChange={(e) => setCommentText({...commentText, [post.id]: e.target.value})}
                                  className="flex-1"
                                  rows={2}
                                />
                                <Button 
                                  onClick={() => handleAddComment(post.id)}
                                  disabled={!commentText[post.id]?.trim()}
                                  className="bg-purple-600 hover:bg-purple-700"
                                >
                                  <Send className="w-4 h-4" />
                                </Button>
                              </div>
                              
                              {/* Comments List */}
                              {(() => {
                                const comments = Array.isArray(commentsData[post.id]) 
                                  ? commentsData[post.id] 
                                  : [];
                                return comments.length > 0 ? (
                                  <div className="space-y-2 max-h-64 overflow-y-auto">
                                    {comments.map((comment) => {
                                      // Ensure comment is an object with required fields
                                      if (!comment || typeof comment !== 'object') {
                                        return null;
                                      }
                                      return (
                                        <div key={comment.id || Math.random()} className="flex space-x-2 p-2 bg-gray-50 rounded">
                                          <Avatar className="w-8 h-8">
                                            <AvatarImage src={comment.user_picture || ''} />
                                            <AvatarFallback>{(comment.user_name || '?').charAt(0)}</AvatarFallback>
                                          </Avatar>
                                          <div className="flex-1">
                                            <p className="text-sm font-medium">{comment.user_name || 'Unknown'}</p>
                                            <p className="text-sm text-gray-700">{comment.text || ''}</p>
                                            <p className="text-xs text-gray-500 mt-1">
                                              {comment.created_at ? new Date(comment.created_at).toLocaleString() : ''}
                                            </p>
                                          </div>
                                        </div>
                                      );
                                    })}
                                  </div>
                                ) : (
                                  <p className="text-sm text-gray-500 text-center py-4">No comments yet</p>
                                );
                              })()}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <Card className="p-6">
                <div className="text-center py-12">
                  <MessageCircle className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-xl font-bold text-gray-800 mb-2">No posts yet</h3>
                  <p className="text-gray-600">
                    {isOwnProfile ? "Share what's on your mind" : `${displayName} hasn't posted anything yet`}
                  </p>
                </div>
              </Card>
            )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Side Messenger */}
      {showMessenger && profileUser && !isOwnProfile && (
        <SideMessenger
          user={currentUser}
          otherUserId={profileUser.id}
          otherUserData={profileUser}
          onClose={() => setShowMessenger(false)}
        />
      )}
      
      {/* Likes Dialog */}
      <Dialog open={showingLikesFor !== null} onOpenChange={() => setShowingLikesFor(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>People who liked this post</DialogTitle>
          </DialogHeader>
          <div className="max-h-96 overflow-y-auto space-y-2">
            {likesData.length > 0 ? (
              likesData.map((user) => (
                <div key={user.id} className="flex items-center space-x-3 p-2 hover:bg-gray-50 rounded">
                  <Avatar className="w-10 h-10">
                    <AvatarImage src={user.picture} />
                    <AvatarFallback>{user.name?.charAt(0)}</AvatarFallback>
                  </Avatar>
                  <div>
                    <p className="font-medium text-sm">{user.name}</p>
                  </div>
                </div>
              ))
            ) : likesCount > 0 ? (
              <div className="text-center py-4">
                <p className="text-gray-600 mb-2">This post has {likesCount} {likesCount === 1 ? 'like' : 'likes'}</p>
                <p className="text-sm text-gray-500">We don't have details about who liked this post yet.</p>
                <p className="text-xs text-gray-400 mt-2">New likes will show user details!</p>
              </div>
            ) : (
              <p className="text-center text-gray-500 py-4">No likes yet</p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ProfilePageFull;
