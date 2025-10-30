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
import { 
  Camera, MapPin, Briefcase, Heart, Users, MessageCircle, 
  Settings as SettingsIcon, Bot, User as UserIcon, Edit2, 
  X, Plus, Send, ThumbsUp, Trash2, MoreHorizontal, Palette 
} from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { useWorldMode } from "@/contexts/WorldModeContext";
import AppHeader from "@/components/AppHeader";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ProfilePageFull = ({ user: currentUser }) => {
  const navigate = useNavigate();
  const { userId } = useParams();
  const { worldMode } = useWorldMode();
  const [profileUser, setProfileUser] = useState(null);
  const [isOwnProfile, setIsOwnProfile] = useState(false);
  const [friendshipStatus, setFriendshipStatus] = useState('none');
  const [friends, setFriends] = useState([]);
  const [loading, setLoading] = useState(true);
  const [posts, setPosts] = useState([]);
  const [newPostText, setNewPostText] = useState('');
  const [editingPost, setEditingPost] = useState(null);
  const [editedPostText, setEditedPostText] = useState('');
  const [viewMode, setViewMode] = useState('single'); // 'single' or 'both'
  
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
    location: ''
  });

  useEffect(() => {
    const targetUserId = userId || currentUser.id;
    setIsOwnProfile(targetUserId === currentUser.id);
    fetchProfile(targetUserId);
    fetchFriends(targetUserId);
    if (targetUserId === currentUser.id) {
      fetchPosts();
    }
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
          location: currentUser.avatar_location || ''
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
      const response = await axios.get(`${API}/friends`, {
        withCredentials: true,
      });
      setFriends(response.data.slice(0, 9));
    } catch (error) {
      console.error("Error fetching friends:", error);
    }
  };

  const fetchPosts = async () => {
    try {
      const postType = worldMode === 'avatar' ? 'avatar' : 'real';
      const response = await axios.get(`${API}/profile/posts?post_type=${postType}`, {
        withCredentials: true,
      });
      setPosts(response.data);
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
                        <Dialog open={showEditAvatarProfile} onOpenChange={setShowEditAvatarProfile}>
                          <DialogTrigger asChild>
                            <Button className="bg-gradient-to-r from-pink-500 to-purple-600 text-white hover:from-pink-600 hover:to-purple-700">
                              <Bot className="w-4 h-4 mr-2" />
                              Edit Maya
                            </Button>
                          </DialogTrigger>
                          <DialogContent className="max-w-2xl">
                            <DialogHeader>
                              <DialogTitle>Edit Maya Profile</DialogTitle>
                            </DialogHeader>
                            <div className="space-y-4 py-4">
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
                                Save Maya Profile
                              </Button>
                            </div>
                          </DialogContent>
                        </Dialog>
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
                          <Button className="bg-blue-500 hover:bg-blue-600 text-white">
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
                  {profileUser.posts && profileUser.posts.length > 0 ? (
                    profileUser.posts.slice(0, 3).map((post) => (
                      <Card key={post.id} className="p-3">
                        <p className="text-sm text-gray-800">{post.text}</p>
                        <p className="text-xs text-gray-500 mt-2">{new Date(post.created_at).toLocaleDateString()}</p>
                      </Card>
                    ))
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
                        <DialogContent className="max-w-2xl">
                          <DialogHeader>
                            <DialogTitle>Edit Maya Profile</DialogTitle>
                          </DialogHeader>
                          <div className="space-y-4 py-4">
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
                            <Button onClick={updateAvatarProfile} className="w-full bg-gradient-to-r from-pink-500 to-purple-600">Save</Button>
                          </div>
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
                  {profileUser.avatar_posts && profileUser.avatar_posts.length > 0 ? (
                    profileUser.avatar_posts.slice(0, 3).map((post) => (
                      <Card key={post.id} className="p-3">
                        <p className="text-sm text-gray-800">{post.text}</p>
                        <p className="text-xs text-gray-500 mt-2">{new Date(post.created_at).toLocaleDateString()}</p>
                      </Card>
                    ))
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
            {isOwnProfile && posts.length > 0 ? (
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
                        
                        <div className="flex items-center space-x-6 text-sm text-gray-500 border-t pt-2">
                          <Button variant="ghost" size="sm" className="text-gray-600 hover:text-blue-600">
                            <ThumbsUp className="w-4 h-4 mr-1" />
                            {post.likes || 0}
                          </Button>
                          <Button variant="ghost" size="sm" className="text-gray-600 hover:text-blue-600">
                            <MessageCircle className="w-4 h-4 mr-1" />
                            {post.comments || 0}
                          </Button>
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
    </div>
  );
};

export default ProfilePageFull;
