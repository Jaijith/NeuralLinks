import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  Camera, MapPin, Briefcase, Heart, Users, MessageCircle, 
  Settings as SettingsIcon, Bot, User as UserIcon, Edit2, 
  X, Plus, Send, ThumbsUp, Trash2, MoreHorizontal, Sparkles,
  FileText, Hand, Eye, Share2, Lock, Globe, UserCheck
} from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { useWorldMode } from "@/contexts/WorldModeContext";
import AppHeader from "@/components/AppHeader";
import SideMessenger from "@/components/SideMessenger";
import ProfilePictureCropper from "@/components/common/ProfilePictureCropper";
import { ImmersivePageWrapper, VoiceAgent } from "@/components/ambient";
import { getVoiceSettings, updateVoiceSettings } from "@/services/api/voiceService";
import { CommentSection, PostCard, LikesDialog, CreatePostCard, CreatePostDialog } from "@/features/posts/components";
import { HomeRightSidebar } from "@/features/home";
import Sidebar, { SidebarSection } from "@/components/layout/Sidebar";
import AvatarStoriesRow from "@/components/AvatarStoriesRow";
import useViewMode from "@/hooks/useViewMode";
import useAvatarState from "@/hooks/useAvatarState";
import EditMayaProfileDialog from "@/components/EditMayaProfileDialog";

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

// Voice Settings Panel Component for Profile Tab
const VoiceSettingsPanel = () => {
  const [settings, setSettings] = useState({
    preset: 'default',
    noise_threshold: 0.5,
    response_speed: 'balanced',
    prefer_shorter_responses: false,
    enable_transcription: true
  });
  const [presets, setPresets] = useState(['default']);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);

  // Preset descriptions
  const presetDescriptions = {
    default: 'Balanced settings for most environments',
    low_latency: 'Fast response time for natural conversations',
    ultra_low_latency: 'Fastest possible - may be sensitive to noise',
    quiet_environment: 'Higher sensitivity for quiet rooms',
    noisy_environment: 'Filters background noise better',
    push_to_talk: 'Manual control - hold to speak'
  };

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const data = await getVoiceSettings();
        if (data.success) {
          setSettings(prev => ({ ...prev, ...data.settings }));
          setPresets(data.presets || ['default']);
        }
      } catch (err) {
        console.error('Error loading voice settings:', err);
      } finally {
        setIsLoading(false);
      }
    };
    loadSettings();
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    setSaveStatus(null);

    try {
      const result = await updateVoiceSettings({
        preset: settings.preset,
        custom: {
          noise_threshold: settings.noise_threshold,
          response_speed: settings.response_speed,
          prefer_shorter_responses: settings.prefer_shorter_responses,
          enable_transcription: settings.enable_transcription
        }
      });

      if (result.success) {
        setSaveStatus('saved');
        toast.success('Voice settings saved');
        setTimeout(() => setSaveStatus(null), 2000);
      } else {
        setSaveStatus('error');
        toast.error('Failed to save voice settings');
      }
    } catch (err) {
      console.error('Error saving voice settings:', err);
      setSaveStatus('error');
      toast.error('Failed to save voice settings');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) return <p className="text-gray-500">Loading voice settings...</p>;

  return (
    <div className="space-y-6">
      {/* Environment Preset */}
      <div>
        <label className="block text-sm font-medium mb-3">Environment Preset</label>
        <div className="grid grid-cols-1 gap-2">
          {presets.map((preset) => (
            <button
              key={preset}
              onClick={() => setSettings(prev => ({ ...prev, preset }))}
              className={`p-3 rounded-lg text-left transition-all border ${
                settings.preset === preset 
                  ? 'border-purple-500 bg-purple-50' 
                  : 'border-gray-200 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium capitalize">
                  {preset.replace(/_/g, ' ')}
                </span>
                {settings.preset === preset && (
                  <span className="text-purple-600">✓</span>
                )}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {presetDescriptions[preset] || 'Custom preset'}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Noise Sensitivity */}
      <div>
        <label className="block text-sm font-medium mb-2">Noise Sensitivity</label>
        <div className="flex items-center gap-4">
          <span className="text-xs text-gray-500">Quiet</span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={settings.noise_threshold}
            onChange={(e) => setSettings(prev => ({ 
              ...prev, 
              noise_threshold: parseFloat(e.target.value) 
            }))}
            className="flex-1 h-2 rounded-full appearance-none cursor-pointer bg-gray-200"
          />
          <span className="text-xs text-gray-500">Noisy</span>
        </div>
        <p className="text-xs text-gray-400 mt-1">
          Higher values filter out more background noise
        </p>
      </div>

      {/* Response Speed */}
      <div>
        <label className="block text-sm font-medium mb-2">Response Speed</label>
        <div className="flex gap-2">
          {['quick', 'balanced', 'thoughtful'].map((speed) => (
            <button
              key={speed}
              onClick={() => setSettings(prev => ({ ...prev, response_speed: speed }))}
              className={`flex-1 py-2 px-3 rounded-lg text-sm transition-all border ${
                settings.response_speed === speed 
                  ? 'border-purple-500 bg-purple-50 text-purple-700' 
                  : 'border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {speed.charAt(0).toUpperCase() + speed.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Toggle options */}
      <div className="space-y-4">
        <div className="flex items-center justify-between p-3 rounded-lg border bg-gray-50">
          <div>
            <p className="text-sm font-medium">Prefer shorter responses</p>
            <p className="text-xs text-gray-500">More concise answers from Maya</p>
          </div>
          <Switch
            checked={settings.prefer_shorter_responses}
            onCheckedChange={(checked) => setSettings(prev => ({ 
              ...prev, 
              prefer_shorter_responses: checked 
            }))}
          />
        </div>

        <div className="flex items-center justify-between p-3 rounded-lg border bg-gray-50">
          <div>
            <p className="text-sm font-medium">Show transcription</p>
            <p className="text-xs text-gray-500">Display text of conversation</p>
          </div>
          <Switch
            checked={settings.enable_transcription}
            onCheckedChange={(checked) => setSettings(prev => ({ 
              ...prev, 
              enable_transcription: checked 
            }))}
          />
        </div>
      </div>

      {/* Save Button */}
      <Button 
        onClick={handleSave} 
        disabled={isSaving}
        className="w-full bg-gradient-to-r from-pink-500 to-purple-600"
      >
        {isSaving ? 'Saving...' : 'Save Voice Settings'}
      </Button>

      {saveStatus === 'saved' && (
        <p className="text-sm text-green-600 text-center">✓ Settings saved successfully</p>
      )}
    </div>
  );
};

const ProfilePageFull = ({ user: currentUser }) => {
  const navigate = useNavigate();
  const { userId } = useParams();
  const { worldMode } = useWorldMode();
  const { isImmersive } = useViewMode(); // Must be called at top level before any returns
  const [profileUser, setProfileUser] = useState(null);
  const [isOwnProfile, setIsOwnProfile] = useState(false);
  const [friendshipStatus, setFriendshipStatus] = useState('none');
  const [showMessenger, setShowMessenger] = useState(false);
  const [friends, setFriends] = useState([]);
  const [loading, setLoading] = useState(true);
  const [posts, setPosts] = useState([]);
  const [newPostText, setNewPostText] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [uploadingProfilePicture, setUploadingProfilePicture] = useState(false);
  const [uploadingCoverPhoto, setUploadingCoverPhoto] = useState(false);
  
  // Image cropper states
  const [profilePictureToCrop, setProfilePictureToCrop] = useState(null);
  const [showProfilePictureCropper, setShowProfilePictureCropper] = useState(false);
  const [coverPhotoToCrop, setCoverPhotoToCrop] = useState(null);
  const [showCoverPhotoCropper, setShowCoverPhotoCropper] = useState(false);
  const [editingPost, setEditingPost] = useState(null);
  const [editedPostText, setEditedPostText] = useState('');
  const [viewMode, setViewMode] = useState('single'); // 'single' or 'both'
  
  // Pagination state
  const [postsSkip, setPostsSkip] = useState(0);
  const [hasMorePosts, setHasMorePosts] = useState(true);
  const [loadingMorePosts, setLoadingMorePosts] = useState(false);
  
  // Like & Comment state
  const [likedPosts, setLikedPosts] = useState(new Set()); // Track which posts user liked
  const [showingLikesFor, setShowingLikesFor] = useState(null); // Post ID for showing likes dialog
  const [likesData, setLikesData] = useState([]); // Users who liked
  const [likesCount, setLikesCount] = useState(0); // Total likes count (for posts with likes but no user details)
  const [showingCommentsFor, setShowingCommentsFor] = useState(null); // Post ID for showing comments
  const [commentsData, setCommentsData] = useState({}); // Comments by post ID
  const [commentText, setCommentText] = useState({}); // Comment input by post ID
  const [profileError, setProfileError] = useState(null); // Error message when profile fails to load
  const [showFriendsDialog, setShowFriendsDialog] = useState(false); // Show friends list dialog
  const [showPostDialog, setShowPostDialog] = useState(false); // Show create post dialog
  const [showVoiceAgent, setShowVoiceAgent] = useState(false); // Voice agent overlay
  
  // Derived state - must be defined before useAvatarState which depends on it
  const isAvatarWorld = worldMode === 'avatar';
  
  // Avatar state for voice feature and orb sync
  const { colors, mood, energy_level } = useAvatarState(isAvatarWorld ? currentUser?.id : null);
  
  // Real Profile Edit
  const [showEditRealProfile, setShowEditRealProfile] = useState(false);
  const [editRealProfileData, setEditRealProfileData] = useState({
    location: '',
    job_title: '',
    bio: '',
    interests: [],
    profile_privacy: 'everyone' // everyone, friends, private
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
    setPostsSkip(0);
    setHasMorePosts(true);
    fetchProfile(targetUserId);
    fetchFriends(targetUserId);
    fetchPosts(targetUserId, 0, false); // Pass the targetUserId to fetch correct posts
  }, [userId, currentUser, worldMode]); // Re-fetch when worldMode changes

  const fetchProfile = async (id) => {
    try {
      setProfileError(null); // Clear any previous errors
      if (id === currentUser.id) {
        setProfileUser(currentUser);
        setEditRealProfileData({
          location: currentUser.location || '',
          job_title: currentUser.job_title || '',
          bio: currentUser.bio || '',
          interests: currentUser.interests || [],
          profile_privacy: currentUser.profile_privacy || 'everyone'
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
      // Display the actual error message from the backend (e.g., "Profile is in private mode")
      const errorMessage = error.response?.data?.detail || "Profile not found";
      setProfileError(errorMessage);
      toast.error(errorMessage);
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

  const fetchPosts = async (targetUserId, skip = 0, append = false) => {
    try {
      if (!append) {
        setPostsSkip(0);
      } else {
        setLoadingMorePosts(true);
      }
      
      const postType = worldMode === 'avatar' ? 'avatar' : 'real';
      const limit = 20;
      // Use the passed targetUserId to get the correct user's posts
      const queryParams = `post_type=${postType}&user_id=${targetUserId}&limit=${limit}&skip=${skip}`;
      console.log(`[DEBUG] Fetching posts for user: ${targetUserId}, postType: ${postType}, skip: ${skip}`);
      const response = await axios.get(`${API}/profile/posts?${queryParams}`, {
        withCredentials: true,
      });
      // API returns { posts: [...], total, skip, limit, has_more }
      const postsData = response.data?.posts || response.data || [];
      const hasMore = response.data?.has_more || false;
      console.log(`[DEBUG] Received ${postsData.length} posts, has_more: ${hasMore}`);
      
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
      
      if (append) {
        setPosts(prev => [...prev, ...sanitizedPosts]);
      } else {
        setPosts(sanitizedPosts);
      }
      
      setHasMorePosts(hasMore);
      setPostsSkip(skip + sanitizedPosts.length);
      
      // Initialize liked posts (check if current user liked any posts)
      const likedSet = new Set();
      const allPostsList = append ? [...posts, ...sanitizedPosts] : sanitizedPosts;
      allPostsList.forEach(post => {
        if (post.liked_by && post.liked_by.includes(currentUser.id)) {
          likedSet.add(post.id);
        }
      });
      setLikedPosts(likedSet);
    } catch (error) {
      console.error("Error fetching posts:", error);
    } finally {
      setLoadingMorePosts(false);
    }
  };
  
  const loadMorePosts = () => {
    const targetUserId = userId || currentUser.id;
    if (!loadingMorePosts && hasMorePosts) {
      fetchPosts(targetUserId, postsSkip, true);
    }
  };

  const handleImageSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error("Please select an image file");
      return;
    }

    setSelectedImage(file);
    setImagePreview(URL.createObjectURL(file));
  };

  const handleProfilePictureUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error("Please select an image file");
      return;
    }

    // Show cropper instead of directly uploading
    const imageUrl = URL.createObjectURL(file);
    setProfilePictureToCrop(imageUrl);
    setShowProfilePictureCropper(true);
    
    // Reset file input
    e.target.value = '';
  };

  const handleProfilePictureCropComplete = async (croppedImageBlob) => {
    setUploadingProfilePicture(true);
    try {
      const formData = new FormData();
      formData.append('file', croppedImageBlob, 'profile-picture.jpg');
      formData.append('world_mode', worldMode === 'avatar' ? 'avatar' : 'real');

      const response = await axios.post(`${API}/profile/upload-picture`, formData, {
        withCredentials: true,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const newImageUrl = response.data.image_url;
      
      // Immediately update the profile user state with new image
      if (worldMode === 'avatar') {
        setProfileUser(prev => ({
          ...prev,
          avatar_picture: newImageUrl
        }));
      } else {
        setProfileUser(prev => ({
          ...prev,
          picture: newImageUrl
        }));
      }

      toast.success(worldMode === 'avatar' ? "Maya profile picture updated!" : "Profile picture updated!");
      
      // Clean up
      URL.revokeObjectURL(profilePictureToCrop);
      setProfilePictureToCrop(null);
    } catch (error) {
      console.error("Error uploading profile picture:", error);
      toast.error("Failed to upload profile picture");
    } finally {
      setUploadingProfilePicture(false);
    }
  };

  const handleCoverPhotoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error("Please select an image file");
      return;
    }

    // Show cropper instead of directly uploading
    const imageUrl = URL.createObjectURL(file);
    setCoverPhotoToCrop(imageUrl);
    setShowCoverPhotoCropper(true);
    
    // Reset file input
    e.target.value = '';
  };

  const handleCoverPhotoCropComplete = async (croppedImageBlob) => {
    setUploadingCoverPhoto(true);
    try {
      const formData = new FormData();
      formData.append('file', croppedImageBlob, 'cover-photo.jpg');
      formData.append('world_mode', worldMode === 'avatar' ? 'avatar' : 'real');

      const response = await axios.post(`${API}/profile/upload-cover`, formData, {
        withCredentials: true,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const newImageUrl = response.data.image_url;
      
      // Immediately update the profile user state with new image
      if (worldMode === 'avatar') {
        setProfileUser(prev => ({
          ...prev,
          avatar_cover_photo: newImageUrl
        }));
      } else {
        setProfileUser(prev => ({
          ...prev,
          cover_photo: newImageUrl
        }));
      }

      toast.success(worldMode === 'avatar' ? "Maya cover photo updated!" : "Cover photo updated!");
      
      // Clean up
      URL.revokeObjectURL(coverPhotoToCrop);
      setCoverPhotoToCrop(null);
    } catch (error) {
      console.error("Error uploading cover photo:", error);
      toast.error("Failed to upload cover photo");
    } finally {
      setUploadingCoverPhoto(false);
    }
  };

  const createPost = async () => {
    if (!newPostText.trim() && !selectedImage) return;
    
    setUploadingImage(true);
    try {
      const postType = worldMode === 'avatar' ? 'avatar' : 'real';
      let response;

      if (selectedImage) {
        // Upload image with caption
        const formData = new FormData();
        formData.append('file', selectedImage);
        formData.append('caption', newPostText);
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
        { text: newPostText, post_type: postType },
        { withCredentials: true }
      );
      }
      
      const newPost = response.data.post || response.data;
      setPosts([newPost, ...posts]);
      setNewPostText('');
      setSelectedImage(null);
      setImagePreview(null);
      toast.success(worldMode === 'avatar' ? "Maya post created!" : "Post created!");
    } catch (error) {
      console.error("Error creating post:", error);
      toast.error("Failed to create post");
    } finally {
      setUploadingImage(false);
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
      // Update local state immediately
      setProfileUser({ ...profileUser, ...editRealProfileData });
      setShowEditRealProfile(false);
      toast.success("Sense profile updated!");
      // No need to reload - graph enrichment happens in background
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
      // No need to reload - updates are instant
    } catch (error) {
      toast.error("Failed to update maya profile");
    }
  };

  const sendFriendRequest = async () => {
    if (!profileUser?.id) {
      toast.error("Invalid user ID");
      return;
    }
    
    try {
      const response = await axios.post(`${API}/friends/request/${profileUser.id}`, {}, {
        withCredentials: true,
      });
      toast.success("Friend request sent!");
      setFriendshipStatus('pending');
      // Refresh profile to update friendship status
      fetchProfile(profileUser.id);
    } catch (error) {
      console.error("Error sending friend request:", error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || "Failed to send friend request";
      toast.error(errorMessage);
    }
  };

  if (loading) {
    return (
      <ImmersivePageWrapper pageId="profile" showToggle={false} user={currentUser}>
        <div className="min-h-screen flex items-center justify-center">
          <div className="w-12 h-12 border-4 border-purple-400 border-t-transparent rounded-full animate-spin"></div>
        </div>
      </ImmersivePageWrapper>
    );
  }

  if (!profileUser) {
    return (
      <ImmersivePageWrapper pageId="profile" showToggle={false} user={currentUser}>
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <Lock className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 text-lg">{profileError || "Profile not found"}</p>
          </div>
        </div>
      </ImmersivePageWrapper>
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
    <ImmersivePageWrapper pageId="profile" user={currentUser}>
      <AppHeader user={currentUser} currentPage="profile" />
      
      {/* Create Post Dialog */}
      {isOwnProfile && (
        <CreatePostDialog
          open={showPostDialog}
          onOpenChange={setShowPostDialog}
          user={currentUser}
          worldMode={worldMode}
          onPostCreated={(newPost) => {
            setPosts(prev => [newPost, ...prev]);
            setShowPostDialog(false);
          }}
        />
      )}
      
      {/* Cover Photo - responsive height, pulled up to fill header padding gap */}
      <div 
        className="relative h-48 sm:h-64 lg:h-96 bg-gradient-to-br from-pink-400 via-purple-500 to-indigo-600 profile-cover overflow-hidden"
        style={{
          marginTop: 'calc(-56px - env(safe-area-inset-top, 0px))',
          paddingTop: 'calc(56px + env(safe-area-inset-top, 0px))',
        }}
      >
        {(worldMode === 'avatar' ? profileUser?.avatar_cover_photo : profileUser?.cover_photo) ? (
          <img
            src={worldMode === 'avatar' ? profileUser.avatar_cover_photo : profileUser.cover_photo}
            alt="Cover photo"
            className="w-full h-full object-cover"
          />
        ) : null}
        <div className="absolute inset-0 bg-black/20"></div>
        {isOwnProfile && (
          <div className="absolute bottom-2 right-2 sm:bottom-4 sm:right-4 z-10">
            <input
              type="file"
              accept="image/*"
              onChange={handleCoverPhotoUpload}
              className="hidden"
              id="cover-photo-upload"
              disabled={uploadingCoverPhoto}
            />
            <button
              type="button"
              disabled={uploadingCoverPhoto}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                document.getElementById('cover-photo-upload')?.click();
              }}
              onTouchEnd={(e) => {
                e.preventDefault();
                e.stopPropagation();
                document.getElementById('cover-photo-upload')?.click();
              }}
              className="flex items-center justify-center rounded-full shadow-lg transition-all"
              style={{
                width: '36px',
                height: '36px',
                backgroundColor: isImmersive ? 'rgba(15, 23, 42, 0.85)' : 'rgba(255, 255, 255, 0.92)',
                border: isImmersive ? '1.5px solid rgba(148, 163, 184, 0.3)' : '1.5px solid rgba(0, 0, 0, 0.08)',
                color: isImmersive ? '#e2e8f0' : '#374151',
                cursor: uploadingCoverPhoto ? 'wait' : 'pointer',
                touchAction: 'manipulation',
                WebkitTapHighlightColor: 'transparent',
                userSelect: 'none',
              }}
              aria-label="Edit cover photo"
            >
              {uploadingCoverPhoto ? (
                <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
              ) : (
                <Camera className="w-4 h-4" />
              )}
            </button>
          </div>
        )}
      </div>

      {/* Profile Info */}
      <div className="max-w-7xl mx-auto px-3 sm:px-6">
        <div className="relative">
          {/* Avatar - responsive positioning */}
          <div className="absolute -top-16 sm:-top-24 lg:-top-32 left-4 sm:left-8 z-10">
            <div className="relative group">
              {/* Hidden file input */}
              {isOwnProfile && (
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleProfilePictureUpload}
                  className="hidden"
                  id="profile-picture-upload"
                  disabled={uploadingProfilePicture}
                />
              )}
              
              {/* Clickable Avatar Container */}
              <div 
                className={`relative ${isOwnProfile ? 'cursor-pointer' : ''}`}
                onClick={isOwnProfile ? (e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  document.getElementById('profile-picture-upload')?.click();
                } : undefined}
                onTouchEnd={isOwnProfile ? (e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  document.getElementById('profile-picture-upload')?.click();
                } : undefined}
                style={isOwnProfile ? { touchAction: 'manipulation', WebkitTapHighlightColor: 'transparent' } : undefined}
              >
                <Avatar className={`w-24 h-24 sm:w-32 sm:h-32 lg:w-44 lg:h-44 border-4 sm:border-8 shadow-xl ${isImmersive ? 'border-slate-800' : 'border-white'}`}>
                  <AvatarImage src={displayPicture} className="object-cover" />
                  <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white text-2xl sm:text-3xl lg:text-4xl">
                    {displayName?.charAt(0)}
                  </AvatarFallback>
                </Avatar>
                
                {/* Centered Edit Overlay - Hidden by default, shows on hover */}
                {isOwnProfile && (
                  <div 
                    className={`absolute inset-0 rounded-full flex items-center justify-center 
                      opacity-0 group-hover:opacity-100 transition-opacity duration-200
                      ${isImmersive ? 'bg-slate-900/70' : 'bg-black/50'}`}
                  >
                    <Camera className={`w-6 h-6 sm:w-8 sm:h-8 lg:w-10 lg:h-10 ${isImmersive ? 'text-white' : 'text-white'}`} />
                  </div>
                )}
              </div>
            </div>
          </div>

          <div 
            className="shadow rounded-b-2xl"
            style={{ 
              backgroundColor: isImmersive ? 'rgba(12, 15, 25, 0.80)' : 'white',
              borderColor: isImmersive ? 'rgba(255, 255, 255, 0.06)' : undefined 
            }}
          >
            {/* Responsive padding - stacks below avatar on mobile, beside on desktop */}
            <div className="pt-14 sm:pt-10 lg:pt-8 pb-4 sm:pb-5 px-4 sm:px-8 ml-0 sm:ml-36 lg:ml-56">
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-3">
                    <h1 
                      className="text-xl sm:text-2xl lg:text-4xl font-bold break-words"
                      style={{ color: isImmersive ? 'white' : '#111827' }}
                    >{displayName}</h1>
                    {profileUser.is_bot && (
                      <Badge className="bg-purple-100 text-purple-700">
                        <Bot className="w-3 h-3 mr-1" />
                        AI Agent
                      </Badge>
                    )}
                  </div>
                  
                  <p 
                    className="text-sm sm:text-base lg:text-lg mb-2 break-words"
                    style={{ color: isImmersive ? '#d1d5db' : '#4b5563' }}
                  >{displayBio}</p>
                  
                  <div 
                    className="flex flex-wrap items-center gap-2 sm:gap-4 text-xs sm:text-sm"
                    style={{ color: isImmersive ? '#9ca3af' : '#6b7280' }}
                  >
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
                    <span 
                      className="flex items-center cursor-pointer hover:text-purple-600 transition-colors"
                      onClick={(e) => {
                        // Guard against ghost clicks when dialog is open
                        if (document.querySelector('[data-state="open"][role="dialog"]')) {
                          e.preventDefault();
                          e.stopPropagation();
                          return;
                        }
                        navigate(`/friends${profileUser?.id && !isOwnProfile ? `?user=${profileUser.id}` : ''}`);
                      }}
                    >
                      <Users className="w-4 h-4 mr-1" />
                      {friends.length} friends
                    </span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 mt-2 sm:mt-0">
                  {isOwnProfile ? (
                    <>
                      {/* Toggle View Mode Button */}
                      <Button
                        onClick={() => setViewMode(viewMode === 'single' ? 'both' : 'single')}
                        variant="outline"
                        size="sm"
                        className={`border-2 text-xs h-8 sm:h-9 px-2 sm:px-3 sm:text-sm ${isImmersive ? 'border-purple-400 text-purple-300 hover:bg-purple-900/30' : 'border-purple-500 text-purple-700 hover:bg-purple-50'}`}
                      >
                        {viewMode === 'single' ? (
                          <>
                            <Users className="w-3 h-3 sm:w-4 sm:h-4 mr-1" />
                            Both
                          </>
                        ) : (
                          <>
                            <UserIcon className="w-3 h-3 sm:w-4 sm:h-4 mr-1" />
                            Single
                          </>
                        )}
                      </Button>
                      
                      {/* Edit Buttons - Show both if in 'both' mode */}
                      {viewMode === 'both' || worldMode === 'real' ? (
                        <Dialog open={showEditRealProfile} onOpenChange={setShowEditRealProfile}>
                          <DialogTrigger asChild>
                            <Button size="sm" className="bg-blue-500 hover:bg-blue-600 text-white text-xs h-8 sm:h-9 px-2 sm:px-3 sm:text-sm">
                              <Globe className="w-3 h-3 sm:w-4 sm:h-4 mr-1" />
                              <span className="hidden sm:inline">Edit Sense</span>
                              <span className="sm:hidden">Sense</span>
                            </Button>
                          </DialogTrigger>
                          <DialogContent 
                            className="max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl p-0 border"
                            style={{ 
                              backgroundColor: isImmersive ? 'rgba(10, 15, 30, 0.98)' : '#ffffff',
                              borderColor: isImmersive ? 'rgba(71, 85, 105, 0.4)' : '#e2e8f0',
                              boxShadow: isImmersive 
                                ? '0 25px 60px rgba(0, 0, 0, 0.6)' 
                                : '0 25px 50px -12px rgba(0, 0, 0, 0.15)',
                            }}
                          >
                            <div 
                              className="px-6 pt-6 pb-4 rounded-t-2xl"
                              style={{ 
                                background: isImmersive 
                                  ? 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(96, 165, 250, 0.06))' 
                                  : 'linear-gradient(135deg, #eff6ff, #f0f9ff)' 
                              }}
                            >
                              <DialogHeader>
                                <DialogTitle 
                                  className="text-xl font-bold flex items-center gap-2.5"
                                  style={{ color: isImmersive ? '#e2e8f0' : '#1e293b' }}
                                >
                                  <div 
                                    className="p-2 rounded-xl"
                                    style={{ background: isImmersive ? 'rgba(59, 130, 246, 0.2)' : '#dbeafe' }}
                                  >
                                    <Globe className="w-5 h-5" style={{ color: isImmersive ? '#60a5fa' : '#2563eb' }} />
                                  </div>
                                  Edit Sense Profile
                                </DialogTitle>
                              </DialogHeader>
                            </div>
                            <div className="space-y-5 px-6 pb-6 pt-2">
                              <div>
                                <label className="block text-sm font-semibold mb-2" style={{ color: isImmersive ? '#cbd5e1' : '#374151' }}>Bio</label>
                                <Textarea
                                  value={editRealProfileData.bio}
                                  onChange={(e) => setEditRealProfileData({...editRealProfileData, bio: e.target.value})}
                                  placeholder="Tell us about yourself..."
                                  rows={3}
                                  className="rounded-xl resize-none"
                                  style={{ 
                                    backgroundColor: isImmersive ? 'rgba(30, 35, 55, 0.8)' : '#ffffff',
                                    borderColor: isImmersive ? 'rgba(71, 85, 105, 0.5)' : '#d1d5db',
                                    color: isImmersive ? '#e2e8f0' : '#1e293b',
                                  }}
                                />
                              </div>
                              <div>
                                <label className="block text-sm font-semibold mb-2" style={{ color: isImmersive ? '#cbd5e1' : '#374151' }}>Job Title</label>
                                <Input
                                  value={editRealProfileData.job_title}
                                  onChange={(e) => setEditRealProfileData({...editRealProfileData, job_title: e.target.value})}
                                  placeholder="Your job title"
                                  className="rounded-xl h-11"
                                  style={{ 
                                    backgroundColor: isImmersive ? 'rgba(30, 35, 55, 0.8)' : '#ffffff',
                                    borderColor: isImmersive ? 'rgba(71, 85, 105, 0.5)' : '#d1d5db',
                                    color: isImmersive ? '#e2e8f0' : '#1e293b',
                                  }}
                                />
                              </div>
                              <div>
                                <label className="block text-sm font-semibold mb-2" style={{ color: isImmersive ? '#cbd5e1' : '#374151' }}>Location</label>
                                <Input
                                  value={editRealProfileData.location}
                                  onChange={(e) => setEditRealProfileData({...editRealProfileData, location: e.target.value})}
                                  placeholder="Your location"
                                  className="rounded-xl h-11"
                                  style={{ 
                                    backgroundColor: isImmersive ? 'rgba(30, 35, 55, 0.8)' : '#ffffff',
                                    borderColor: isImmersive ? 'rgba(71, 85, 105, 0.5)' : '#d1d5db',
                                    color: isImmersive ? '#e2e8f0' : '#1e293b',
                                  }}
                                />
                              </div>
                              
                              {/* Privacy Settings */}
                              <div 
                                className="pt-4"
                                style={{ borderTop: `1px solid ${isImmersive ? 'rgba(71, 85, 105, 0.3)' : '#e5e7eb'}` }}
                              >
                                <label 
                                  className="block text-sm font-semibold mb-2 flex items-center gap-2"
                                  style={{ color: isImmersive ? '#cbd5e1' : '#374151' }}
                                >
                                  <Lock className="w-4 h-4" style={{ color: isImmersive ? '#60a5fa' : '#2563eb' }} />
                                  Who can see your profile?
                                </label>
                                <Select 
                                  value={editRealProfileData.profile_privacy}
                                  onValueChange={(value) => setEditRealProfileData({...editRealProfileData, profile_privacy: value})}
                                >
                                  <SelectTrigger 
                                    className="w-full rounded-xl h-11"
                                    style={{ 
                                      backgroundColor: isImmersive ? 'rgba(30, 35, 55, 0.8)' : '#ffffff',
                                      borderColor: isImmersive ? 'rgba(71, 85, 105, 0.5)' : '#d1d5db',
                                      color: isImmersive ? '#e2e8f0' : '#1e293b',
                                    }}
                                  >
                                    <SelectValue placeholder="Select privacy setting" />
                                  </SelectTrigger>
                                  <SelectContent
                                    style={{ 
                                      backgroundColor: isImmersive ? 'rgb(20, 25, 45)' : undefined,
                                      borderColor: isImmersive ? 'rgba(71, 85, 105, 0.5)' : undefined,
                                    }}
                                  >
                                    <SelectItem value="everyone">
                                      <div className="flex items-center gap-2">
                                        <Globe className="w-4 h-4" />
                                        <span>Everyone</span>
                                      </div>
                                    </SelectItem>
                                    <SelectItem value="friends">
                                      <div className="flex items-center gap-2">
                                        <UserCheck className="w-4 h-4" />
                                        <span>Friends Only</span>
                                      </div>
                                    </SelectItem>
                                    <SelectItem value="private">
                                      <div className="flex items-center gap-2">
                                        <Lock className="w-4 h-4" />
                                        <span>Only Me (Private)</span>
                                      </div>
                                    </SelectItem>
                                  </SelectContent>
                                </Select>
                                <p className="text-xs mt-2" style={{ color: isImmersive ? '#94a3b8' : '#6b7280' }}>
                                  {editRealProfileData.profile_privacy === 'everyone' && "Anyone can view your profile"}
                                  {editRealProfileData.profile_privacy === 'friends' && "Only your friends can view your profile"}
                                  {editRealProfileData.profile_privacy === 'private' && "Your profile is hidden from everyone"}
                                </p>
                              </div>
                              
                              <Button 
                                onClick={updateRealProfile} 
                                className="w-full bg-blue-500 hover:bg-blue-600 text-white font-medium py-2.5 rounded-xl"
                              >
                                Save Sense Profile
                              </Button>
                            </div>
                          </DialogContent>
                        </Dialog>
                      ) : null}
                      
                      {viewMode === 'both' || worldMode === 'avatar' ? (
                        <EditMayaProfileDialog
                          open={showEditAvatarProfile}
                          onOpenChange={setShowEditAvatarProfile}
                          editData={editAvatarProfileData}
                          setEditData={setEditAvatarProfileData}
                          onSave={updateAvatarProfile}
                          isImmersive={isImmersive}
                          triggerVariant="default"
                        />
                      ) : null}
                    </>
                  ) : (
                    <>
                      {friendshipStatus === 'accepted' ? (
                        <>
                          <Button 
                            size="sm"
                            onClick={() => navigate(`/friends?user=${profileUser?.id}`)}
                            className={`text-xs h-8 sm:h-9 px-2.5 sm:px-4 sm:text-sm ${isImmersive ? 'bg-slate-700 hover:bg-slate-600 text-white' : 'bg-gray-200 hover:bg-gray-300 text-gray-800'}`}
                          >
                            <Users className="w-3.5 h-3.5 sm:w-4 sm:h-4 mr-1 sm:mr-2" />
                            Friends
                          </Button>
                          <Button 
                            size="sm"
                            onClick={() => setShowMessenger(true)}
                            className="bg-blue-500 hover:bg-blue-600 text-white text-xs h-8 sm:h-9 px-2.5 sm:px-4 sm:text-sm"
                          >
                            <MessageCircle className="w-3.5 h-3.5 sm:w-4 sm:h-4 mr-1 sm:mr-2" />
                            Message
                          </Button>
                        </>
                      ) : friendshipStatus === 'pending' ? (
                        <Button disabled size="sm" className={`text-xs h-8 sm:h-9 sm:text-sm ${isImmersive ? 'bg-slate-700 text-slate-400' : 'bg-gray-300 text-gray-600'}`}>
                          Pending
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          onClick={sendFriendRequest}
                          className="bg-blue-500 hover:bg-blue-600 text-white text-xs h-8 sm:h-9 px-2.5 sm:px-4 sm:text-sm"
                        >
                          <Users className="w-3.5 h-3.5 sm:w-4 sm:h-4 mr-1 sm:mr-2" />
                          Add Friend
                        </Button>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Navigation Tabs - Hidden for now */}
            <div className={`border-t px-8 ${isImmersive ? 'border-slate-700' : 'border-gray-200'}`} style={{ display: 'none' }}>
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

        {/* Stories + Share Moments Section (Below profile info, above posts) - Sticky */}
        {isOwnProfile && (
          <div 
            className="sticky z-30 mt-0 sm:mt-3 -mx-3 sm:mx-0 pb-3 sm:pb-4 pt-0 sm:pt-1 space-y-2 sm:space-y-3"
            style={{
              top: 'calc(3.5rem + env(safe-area-inset-top, 0px))',
              background: isImmersive 
                ? 'rgba(10, 15, 30, 0.90)'
                : 'rgba(245, 247, 250, 0.90)',
            }}
          >
            {/* Friends Stories Row - Both worlds, full width on mobile */}
            <AvatarStoriesRow 
              currentUser={currentUser}
              className="rounded-none sm:rounded-xl"
              style={{ 
                backgroundColor: isImmersive ? 'rgba(12, 15, 25, 0.80)' : 'white',
                border: isImmersive ? '1px solid rgba(255,255,255,0.06)' : undefined,
                boxShadow: isImmersive ? undefined : '0 1px 3px 0 rgb(0 0 0 / 0.1)'
              }}
            />
            
            {/* Create Post Card with Orb (Maya) or without (Sense) - 80% opacity in immersive */}
            <div style={isImmersive ? { '--card-bg': 'rgba(12, 15, 25, 0.80)' } : undefined}>
              <CreatePostCard
                user={currentUser}
                worldMode={worldMode}
                onCreateClick={() => setShowPostDialog(true)}
                onPhotoClick={() => {
                  setShowPostDialog(true);
                  setTimeout(() => {
                    document.getElementById('post-image-upload')?.click();
                  }, 100);
                }}
                onOrbClick={isAvatarWorld ? () => setShowVoiceAgent(true) : undefined}
                onSearchClick={() => navigate('/search')}
                placeholder={isAvatarWorld ? "Share your Maya moments..." : "Share your Sense moments..."}
                mood={mood}
                energyLevel={energy_level}
                className="w-full !rounded-none sm:!rounded-xl"
              />
            </div>
          </div>
        )}

        {/* Content - responsive grid with top spacing to prevent overlap */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 sm:gap-4 mt-4 sm:mt-6 pb-20 sm:pb-12">
          {/* Left Sidebar - uses same Sidebar/SidebarSection as the right sidebar */}
          <div className="col-span-1 lg:col-span-3 order-2 lg:order-1 relative z-10">
            <div className="lg:sticky space-y-4" style={{ top: 'calc(5rem + env(safe-area-inset-top, 0px))' }}>
            <Sidebar>
              {/* About */}
              <SidebarSection title="About">
                <div className="space-y-2.5">
                  {displayJobTitle && (
                    <div className="flex items-center text-gray-700">
                      <Briefcase className="w-5 h-5 mr-3 flex-shrink-0 text-gray-500" />
                      <span className="text-sm">{displayJobTitle}</span>
                    </div>
                  )}
                  {displayLocation && (
                    <div className="flex items-center text-gray-700">
                      <MapPin className="w-5 h-5 mr-3 flex-shrink-0 text-gray-500" />
                      <span className="text-sm">Lives in {displayLocation}</span>
                    </div>
                  )}
                  {!displayJobTitle && !displayLocation && (
                    <p className="text-sm text-gray-500">No details added yet.</p>
                  )}
                </div>
              </SidebarSection>

              {/* Interests */}
              {displayInterests && displayInterests.length > 0 && (
                <SidebarSection title="Interests">
                  <div className="flex flex-wrap gap-2">
                    {displayInterests.map((interest, idx) => (
                      <Badge 
                        key={idx} 
                        className="px-3 py-1 bg-purple-100 text-purple-700"
                      >
                        {interest}
                      </Badge>
                    ))}
                  </div>
                </SidebarSection>
              )}

              {/* Friends */}
              <SidebarSection 
                title="Friends"
                headerAction={
                  <button 
                    onClick={(e) => {
                      if (document.querySelector('[data-state="open"][role="dialog"]')) {
                        e.preventDefault();
                        return;
                      }
                      navigate('/friends');
                    }}
                    className="text-xs font-medium hover:opacity-80 text-blue-600"
                  >
                    See all
                  </button>
                }
              >
                <div className="grid grid-cols-3 gap-2">
                  {friends.slice(0, 9).map((friend, idx) => {
                    const friendDisplayName = worldMode === 'avatar'
                      ? (friend.avatar_name || friend.name)
                      : friend.name;
                    const friendDisplayPicture = worldMode === 'avatar'
                      ? (friend.avatar_picture || friend.picture)
                      : friend.picture;
                    
                    return (
                      <div 
                        key={idx} 
                        className="cursor-pointer hover:opacity-80 transition-opacity" 
                        onClick={() => navigate(`/profile/${friend.id}`)}
                      >
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
                  {friends.length === 0 && (
                    <p className="text-sm text-gray-500 col-span-3 text-center py-2">No friends yet</p>
                  )}
                </div>
              </SidebarSection>
            </Sidebar>
            </div>
          </div>

          {/* Main Content - full width on mobile, 6 cols on desktop */}
          <div className="col-span-1 lg:col-span-6 space-y-4 order-1 lg:order-2 relative z-10">
            {/* Dual Profile View (Side by Side) */}
            {isOwnProfile && viewMode === 'both' ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* SENSE PROFILE COLUMN */}
                <div className="space-y-4">
                  <Card className="p-4 bg-blue-50 border-2 border-blue-400">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-lg sm:text-xl font-bold text-blue-900">👤 Sense Profile</h3>
                      <Dialog open={showEditRealProfile} onOpenChange={setShowEditRealProfile}>
                        <DialogTrigger asChild>
                          <Button size="sm" className="bg-blue-500 hover:bg-blue-600 text-white text-xs h-8 px-2.5">
                            <Edit2 className="w-3 h-3 mr-1" />
                            Edit
                          </Button>
                        </DialogTrigger>
                        <DialogContent 
                          className="max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl p-0 border"
                          style={{ 
                            backgroundColor: isImmersive ? 'rgba(10, 15, 30, 0.98)' : '#ffffff',
                            borderColor: isImmersive ? 'rgba(71, 85, 105, 0.4)' : '#e2e8f0',
                          }}
                        >
                          <div className="px-6 pt-6 pb-4">
                            <DialogHeader>
                              <DialogTitle style={{ color: isImmersive ? '#e2e8f0' : '#1e293b' }}>Edit Sense Profile</DialogTitle>
                            </DialogHeader>
                          </div>
                          <div className="space-y-4 px-6 pb-6">
                            <div>
                              <label className="block text-sm font-semibold mb-2" style={{ color: isImmersive ? '#cbd5e1' : '#374151' }}>Bio</label>
                              <Textarea
                                value={editRealProfileData.bio}
                                onChange={(e) => setEditRealProfileData({...editRealProfileData, bio: e.target.value})}
                                rows={3}
                                className="rounded-xl resize-none"
                                style={{ backgroundColor: isImmersive ? 'rgba(30, 35, 55, 0.8)' : '#ffffff', borderColor: isImmersive ? 'rgba(71, 85, 105, 0.5)' : '#d1d5db', color: isImmersive ? '#e2e8f0' : '#1e293b' }}
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-semibold mb-2" style={{ color: isImmersive ? '#cbd5e1' : '#374151' }}>Job Title</label>
                              <Input
                                value={editRealProfileData.job_title}
                                onChange={(e) => setEditRealProfileData({...editRealProfileData, job_title: e.target.value})}
                                className="rounded-xl h-11"
                                style={{ backgroundColor: isImmersive ? 'rgba(30, 35, 55, 0.8)' : '#ffffff', borderColor: isImmersive ? 'rgba(71, 85, 105, 0.5)' : '#d1d5db', color: isImmersive ? '#e2e8f0' : '#1e293b' }}
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-semibold mb-2" style={{ color: isImmersive ? '#cbd5e1' : '#374151' }}>Location</label>
                              <Input
                                value={editRealProfileData.location}
                                onChange={(e) => setEditRealProfileData({...editRealProfileData, location: e.target.value})}
                                className="rounded-xl h-11"
                                style={{ backgroundColor: isImmersive ? 'rgba(30, 35, 55, 0.8)' : '#ffffff', borderColor: isImmersive ? 'rgba(71, 85, 105, 0.5)' : '#d1d5db', color: isImmersive ? '#e2e8f0' : '#1e293b' }}
                              />
                            </div>
                            
                            {/* Privacy Settings */}
                            <div className="pt-4" style={{ borderTop: `1px solid ${isImmersive ? 'rgba(71, 85, 105, 0.3)' : '#e5e7eb'}` }}>
                              <label className="block text-sm font-semibold mb-2 flex items-center gap-2" style={{ color: isImmersive ? '#cbd5e1' : '#374151' }}>
                                <Lock className="w-4 h-4" />
                                Who can see your profile?
                              </label>
                              <Select 
                                value={editRealProfileData.profile_privacy}
                                onValueChange={(value) => setEditRealProfileData({...editRealProfileData, profile_privacy: value})}
                              >
                                <SelectTrigger 
                                  className="w-full rounded-xl h-11"
                                  style={{ backgroundColor: isImmersive ? 'rgba(30, 35, 55, 0.8)' : '#ffffff', borderColor: isImmersive ? 'rgba(71, 85, 105, 0.5)' : '#d1d5db', color: isImmersive ? '#e2e8f0' : '#1e293b' }}
                                >
                                  <SelectValue placeholder="Select privacy setting" />
                                </SelectTrigger>
                                <SelectContent style={{ backgroundColor: isImmersive ? 'rgb(20, 25, 45)' : undefined, borderColor: isImmersive ? 'rgba(71, 85, 105, 0.5)' : undefined }}>
                                  <SelectItem value="everyone">
                                    <div className="flex items-center gap-2">
                                      <Globe className="w-4 h-4" />
                                      <span>Everyone</span>
                                    </div>
                                  </SelectItem>
                                  <SelectItem value="friends">
                                    <div className="flex items-center gap-2">
                                      <UserCheck className="w-4 h-4" />
                                      <span>Friends Only</span>
                                    </div>
                                  </SelectItem>
                                  <SelectItem value="private">
                                    <div className="flex items-center gap-2">
                                      <Lock className="w-4 h-4" />
                                      <span>Only Me (Private)</span>
                                    </div>
                                  </SelectItem>
                                </SelectContent>
                              </Select>
                              <p className="text-xs mt-2" style={{ color: isImmersive ? '#94a3b8' : '#6b7280' }}>
                                {editRealProfileData.profile_privacy === 'everyone' && "Anyone can view your profile"}
                                {editRealProfileData.profile_privacy === 'friends' && "Only your friends can view your profile"}
                                {editRealProfileData.profile_privacy === 'private' && "Your profile is hidden from everyone"}
                              </p>
                            </div>
                            
                            <Button onClick={updateRealProfile} className="w-full bg-blue-500 hover:bg-blue-600 text-white rounded-xl">Save</Button>
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
                    profileUser.posts
                      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
                      .slice(0, 3)
                      .map((post) => {
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
                      <h3 className="text-lg sm:text-xl font-bold text-purple-900">🎮 Maya Profile</h3>
                      <EditMayaProfileDialog
                        open={showEditAvatarProfile}
                        onOpenChange={setShowEditAvatarProfile}
                        editData={editAvatarProfileData}
                        setEditData={setEditAvatarProfileData}
                        onSave={updateAvatarProfile}
                        isImmersive={isImmersive}
                        triggerVariant="compact"
                      />
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
                    profileUser.avatar_posts
                      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
                      .slice(0, 3)
                      .map((post) => {
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

            {/* Posts - Using same PostCard component as home page */}
            {posts.length > 0 ? (
              <div className="space-y-4">
                {posts.map((post, idx) => (
                  <PostCard
                    key={post.id || idx}
                    post={post}
                    currentUser={currentUser}
                    worldMode={worldMode}
                    isLiked={likedPosts.has(post.id)}
                    onLike={() => handleLikePost(post.id)}
                    onComment={() => showComments(post.id)}
                    onShowLikes={() => showLikes(post.id)}
                    onDelete={isOwnProfile ? deletePost : null}
                    onEdit={isOwnProfile ? (post) => {
                      setEditingPost(post.id);
                      setEditedPostText(post.text || post.content || '');
                    } : null}
                    comments={Array.isArray(commentsData[post.id]) ? commentsData[post.id] : (post.comments || [])}
                    onAddComment={handleAddComment}
                    showComments={showingCommentsFor === post.id}
                    onToggleComments={() => showComments(post.id)}
                  />
                ))}
                
                {/* Load More Button */}
                {hasMorePosts && (
                  <div className="flex justify-center py-6">
                    <Button
                      onClick={loadMorePosts}
                      disabled={loadingMorePosts}
                      variant="outline"
                      className={`px-8 py-2 ${isImmersive ? 'border-slate-600 text-gray-300 hover:bg-slate-800' : ''}`}
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
              <Card 
                className="p-6"
                style={{ 
                  backgroundColor: isImmersive ? 'rgba(15, 23, 42, 0.8)' : 'white',
                  borderColor: isImmersive ? 'rgba(51, 65, 85, 0.5)' : undefined 
                }}
              >
                <div className="text-center py-12">
                  <MessageCircle style={{ color: isImmersive ? '#4b5563' : '#d1d5db' }} className="w-16 h-16 mx-auto mb-4" />
                  <h3 style={{ color: isImmersive ? 'white' : '#1f2937' }} className="text-xl font-bold mb-2">No posts yet</h3>
                  <p style={{ color: isImmersive ? '#9ca3af' : '#4b5563' }}>
                    {isOwnProfile ? "Share what's on your mind" : `${displayName} hasn't posted anything yet`}
                  </p>
                </div>
              </Card>
            )}
            
            {/* Likes Dialog */}
            <LikesDialog
              open={showingLikesFor !== null}
              onOpenChange={(open) => !open && showLikes(null)}
              postId={showingLikesFor}
              worldMode={worldMode}
            />

            {/* Edit Post Dialog */}
            <Dialog open={editingPost !== null} onOpenChange={(open) => { if (!open) { setEditingPost(null); setEditedPostText(''); } }}>
              <DialogContent 
                className="max-w-lg rounded-2xl border"
                style={{ 
                  backgroundColor: isImmersive ? 'rgba(10, 15, 30, 0.98)' : '#ffffff',
                  borderColor: isImmersive ? 'rgba(71, 85, 105, 0.4)' : '#e2e8f0',
                }}
              >
                <DialogHeader>
                  <DialogTitle style={{ color: isImmersive ? '#e2e8f0' : undefined }}>Edit Post</DialogTitle>
                </DialogHeader>
                <div className="py-4">
                  <Textarea
                    value={editedPostText}
                    onChange={(e) => setEditedPostText(e.target.value)}
                    placeholder="What's on your mind?"
                    className="min-h-[150px] resize-none rounded-xl"
                    style={{ 
                      backgroundColor: isImmersive ? 'rgba(30, 35, 55, 0.8)' : '#ffffff',
                      borderColor: isImmersive ? 'rgba(71, 85, 105, 0.5)' : '#d1d5db',
                      color: isImmersive ? '#e2e8f0' : '#1e293b',
                    }}
                    autoFocus
                  />
                </div>
                <DialogFooter className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => { setEditingPost(null); setEditedPostText(''); }}
                    className={isImmersive ? 'border-slate-600 text-slate-300 hover:bg-slate-800' : ''}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={() => updatePost(editingPost)}
                    disabled={!editedPostText.trim()}
                    className="bg-blue-500 hover:bg-blue-600 text-white"
                  >
                    Save Changes
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
              </>
            )}
          </div>

          {/* Right Sidebar - Discover Spirits only (desktop only) */}
          <aside className="hidden lg:block lg:col-span-3 order-3">
            <div className="lg:sticky" style={{ top: 'calc(5rem + env(safe-area-inset-top, 0px))' }}>
              <HomeRightSidebar 
                friends={[]}
                worldMode={worldMode}
              />
            </div>
          </aside>
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
      
      {/* Friends Dialog */}
      <Dialog open={showFriendsDialog} onOpenChange={setShowFriendsDialog}>
        <DialogContent 
          className="max-w-md max-h-[80vh] overflow-y-auto rounded-2xl border"
          style={{ 
            backgroundColor: isImmersive ? 'rgba(10, 15, 30, 0.98)' : '#ffffff',
            borderColor: isImmersive ? 'rgba(71, 85, 105, 0.4)' : '#e2e8f0',
          }}
        >
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2" style={{ color: isImmersive ? '#e2e8f0' : undefined }}>
              <Users className="w-5 h-5" />
              {profileUser?.name || profileUser?.avatar_name}'s Friends ({friends.length})
            </DialogTitle>
          </DialogHeader>
          <div className="max-h-96 overflow-y-auto space-y-2">
            {friends.length > 0 ? (
              friends.map((friend) => {
                const friendDisplayName = worldMode === 'avatar'
                  ? (friend.avatar_name || friend.name)
                  : friend.name;
                const friendDisplayPicture = worldMode === 'avatar'
                  ? (friend.avatar_picture || friend.picture)
                  : friend.picture;
                return (
                  <div 
                    key={friend.id} 
                    className="flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors"
                    style={{ 
                      ':hover': { backgroundColor: isImmersive ? 'rgba(255,255,255,0.05)' : '#f9fafb' }
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = isImmersive ? 'rgba(255,255,255,0.05)' : '#f9fafb'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                    onClick={() => {
                      setShowFriendsDialog(false);
                      navigate(`/profile/${friend.id}`);
                    }}
                  >
                    <div className="flex items-center space-x-3">
                      <Avatar className="w-12 h-12">
                        <AvatarImage src={friendDisplayPicture} />
                        <AvatarFallback className="bg-purple-500 text-white">
                          {friendDisplayName?.charAt(0).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <p className="font-medium" style={{ color: isImmersive ? '#e2e8f0' : undefined }}>{friendDisplayName}</p>
                        {friend.job_title && (
                          <p className="text-sm" style={{ color: isImmersive ? '#94a3b8' : '#6b7280' }}>{friend.job_title}</p>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-center py-8" style={{ color: isImmersive ? '#94a3b8' : '#6b7280' }}>No friends yet</p>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Likes Dialog */}
      <Dialog open={showingLikesFor !== null} onOpenChange={() => setShowingLikesFor(null)}>
        <DialogContent 
          className="max-w-md rounded-2xl border"
          style={{ 
            backgroundColor: isImmersive ? 'rgba(10, 15, 30, 0.98)' : '#ffffff',
            borderColor: isImmersive ? 'rgba(71, 85, 105, 0.4)' : '#e2e8f0',
          }}
        >
          <DialogHeader>
            <DialogTitle style={{ color: isImmersive ? '#e2e8f0' : undefined }}>People who liked this post</DialogTitle>
          </DialogHeader>
          <div className="max-h-96 overflow-y-auto space-y-2">
            {likesData.length > 0 ? (
              likesData.map((user) => {
                const likeDisplayName = user.name || user.avatar_name || 'Unknown User';
                const likeDisplayPicture = user.picture || user.avatar_picture || '';
                return (
                  <div 
                    key={user.id || Math.random()} 
                    className="flex items-center space-x-3 p-2 rounded cursor-pointer transition-colors"
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = isImmersive ? 'rgba(255,255,255,0.05)' : '#f9fafb'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                    onClick={() => {
                      if (user.id) {
                        navigate(`/profile/${user.id}`);
                      }
                    }}
                  >
                    <Avatar className="w-10 h-10">
                      <AvatarImage src={likeDisplayPicture} />
                      <AvatarFallback className="bg-blue-500 text-white">
                        {likeDisplayName.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="font-medium text-sm" style={{ color: isImmersive ? '#e2e8f0' : undefined }}>{likeDisplayName}</p>
                    </div>
                  </div>
                );
              })
            ) : likesCount > 0 ? (
              <div className="text-center py-4">
                <p className="mb-2" style={{ color: isImmersive ? '#cbd5e1' : '#4b5563' }}>This post has {likesCount} {likesCount === 1 ? 'like' : 'likes'}</p>
                <p className="text-sm" style={{ color: isImmersive ? '#94a3b8' : '#6b7280' }}>We don't have details about who liked this post yet.</p>
                <p className="text-xs mt-2" style={{ color: isImmersive ? '#64748b' : '#9ca3af' }}>New likes will show user details!</p>
              </div>
            ) : (
              <p className="text-center py-4" style={{ color: isImmersive ? '#94a3b8' : '#6b7280' }}>No likes yet</p>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Profile Picture Cropper */}
      <ProfilePictureCropper
        open={showProfilePictureCropper}
        onOpenChange={(open) => {
          setShowProfilePictureCropper(open);
          if (!open && profilePictureToCrop) {
            URL.revokeObjectURL(profilePictureToCrop);
            setProfilePictureToCrop(null);
          }
        }}
        imageSrc={profilePictureToCrop}
        onCropComplete={handleProfilePictureCropComplete}
        aspectRatio={1}
        cropShape="round"
        title={worldMode === 'avatar' ? 'Edit Maya Profile Picture' : 'Edit Profile Picture'}
      />

      {/* Cover Photo Cropper */}
      <ProfilePictureCropper
        open={showCoverPhotoCropper}
        onOpenChange={(open) => {
          setShowCoverPhotoCropper(open);
          if (!open && coverPhotoToCrop) {
            URL.revokeObjectURL(coverPhotoToCrop);
            setCoverPhotoToCrop(null);
          }
        }}
        imageSrc={coverPhotoToCrop}
        onCropComplete={handleCoverPhotoCropComplete}
        aspectRatio={16 / 9}
        cropShape="rect"
        title={worldMode === 'avatar' ? 'Edit Maya Cover Photo' : 'Edit Cover Photo'}
      />

      {/* Voice Agent Overlay - Maya world only */}
      {isAvatarWorld && (
        <VoiceAgent
          isActive={showVoiceAgent}
          onClose={() => setShowVoiceAgent(false)}
          colors={colors}
          avatarId={currentUser?.id}
          settingPreset="low_latency"
        />
      )}
    </ImmersivePageWrapper>
  );
};

export default ProfilePageFull;
