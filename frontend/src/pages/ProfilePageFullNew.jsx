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
  X, Plus, Send, ThumbsUp, Trash2, MoreHorizontal 
} from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { useWorldMode } from "@/contexts/WorldModeContext";

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
  const [mode, setMode] = useState('real'); // Personal mode (separate from global)
  const [posts, setPosts] = useState([]);
  const [newPostText, setNewPostText] = useState('');
  const [editingBio, setEditingBio] = useState(false);
  const [editedBio, setEditedBio] = useState('');
  const [editingPost, setEditingPost] = useState(null);
  const [editedPostText, setEditedPostText] = useState('');
  const [showEditProfile, setShowEditProfile] = useState(false);
  const [editProfileData, setEditProfileData] = useState({
    location: '',
    job_title: '',
    bio: ''
  });

  useEffect(() => {
    const targetUserId = userId || currentUser.id;
    setIsOwnProfile(targetUserId === currentUser.id);
    fetchProfile(targetUserId);
    fetchFriends(targetUserId);
    if (targetUserId === currentUser.id) {
      fetchPosts();
    }
  }, [userId, currentUser]);

  const fetchProfile = async (id) => {
    try {
      if (id === currentUser.id) {
        setProfileUser(currentUser);
        setEditedBio(currentUser.bio || '');
        setEditProfileData({
          location: currentUser.location || '',
          job_title: currentUser.job_title || '',
          bio: currentUser.bio || ''
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
      const response = await axios.get(`${API}/profile/posts`, {
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
      const response = await axios.post(`${API}/profile/posts`, 
        { text: newPostText },
        { withCredentials: true }
      );
      setPosts([response.data, ...posts]);
      setNewPostText('');
      toast.success("Post created!");
    } catch (error) {
      toast.error("Failed to create post");
    }
  };

  const deletePost = async (postId) => {
    try {
      await axios.delete(`${API}/profile/posts/${postId}`, {
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
      await axios.put(`${API}/profile/posts/${postId}`, 
        { text: editedPostText },
        { withCredentials: true }
      );
      setPosts(posts.map(p => p.id === postId ? { ...p, text: editedPostText } : p));
      setEditingPost(null);
      toast.success("Post updated!");
    } catch (error) {
      toast.error("Failed to update post");
    }
  };

  const updateProfile = async () => {
    try {
      await axios.put(`${API}/profile`, editProfileData, {
        withCredentials: true,
      });
      setProfileUser({ ...profileUser, ...editProfileData });
      setShowEditProfile(false);
      toast.success("Profile updated!");
    } catch (error) {
      toast.error("Failed to update profile");
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

  // Use display fields for bots in avatar mode
  const displayName = profileUser.display_name || profileUser.name;
  const displayPicture = profileUser.display_picture || profileUser.picture;
  const displayBio = profileUser.display_bio || profileUser.bio;

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Cover Photo */}
      <div className="relative h-96 bg-gradient-to-br from-pink-400 via-purple-500 to-indigo-600 profile-cover">
        <div className="absolute inset-0 bg-black/20"></div>
        {isOwnProfile && (
          <Button
            variant="secondary"
            className="absolute bottom-4 right-4 bg-white/90 hover:bg-white"
            data-testid="edit-cover-btn"
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
              <AvatarImage src={displayPicture} />
              <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white text-4xl">
                {displayName?.charAt(0)}
              </AvatarFallback>
            </Avatar>
            {isOwnProfile && (
              <Button
                size="sm"
                className="absolute bottom-2 right-2 rounded-full w-10 h-10 p-0 bg-white hover:bg-gray-100"
                data-testid="edit-photo-btn"
                onClick={() => toast.info("Profile photo edit coming soon!")}
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
                  </div>
                  
                  {/* Bio with Edit */}
                  {isOwnProfile && editingBio ? (
                    <div className="flex items-center space-x-2 mb-2">
                      <Input
                        value={editedBio}
                        onChange={(e) => setEditedBio(e.target.value)}
                        className="flex-1"
                        placeholder="Write your bio..."
                      />
                      <Button size="sm" onClick={async () => {
                        await updateProfile();
                        setEditingBio(false);
                      }}>
                        Save
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setEditingBio(false)}>
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  ) : (
                    <div className="flex items-center space-x-2 mb-2">
                      <p className="text-gray-600 text-lg">{displayBio}</p>
                      {isOwnProfile && (
                        <Button 
                          size="sm" 
                          variant="ghost" 
                          onClick={() => setEditingBio(true)}
                          className="p-1 h-auto"
                        >
                          <Edit2 className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  )}
                  
                  <div className="flex items-center space-x-4 text-sm text-gray-500">
                    {profileUser.job_title && (
                      <span className="flex items-center">
                        <Briefcase className="w-4 h-4 mr-1" />
                        {profileUser.job_title}
                      </span>
                    )}
                    {profileUser.location && (
                      <span className="flex items-center">
                        <MapPin className="w-4 h-4 mr-1" />
                        {profileUser.location}
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
                      <Dialog open={showEditProfile} onOpenChange={setShowEditProfile}>
                        <DialogTrigger asChild>
                          <Button
                            data-testid="edit-profile-btn"
                            className="bg-blue-500 hover:bg-blue-600 text-white"
                          >
                            <SettingsIcon className="w-4 h-4 mr-2" />
                            Edit Profile
                          </Button>
                        </DialogTrigger>
                        <DialogContent>
                          <DialogHeader>
                            <DialogTitle>Edit Profile</DialogTitle>
                          </DialogHeader>
                          <div className="space-y-4 py-4">
                            <div>
                              <label className="block text-sm font-medium mb-2">Bio</label>
                              <Textarea
                                value={editProfileData.bio}
                                onChange={(e) => setEditProfileData({...editProfileData, bio: e.target.value})}
                                placeholder="Tell us about yourself..."
                                rows={3}
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium mb-2">Job Title</label>
                              <Input
                                value={editProfileData.job_title}
                                onChange={(e) => setEditProfileData({...editProfileData, job_title: e.target.value})}
                                placeholder="Your job title"
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium mb-2">Location</label>
                              <Input
                                value={editProfileData.location}
                                onChange={(e) => setEditProfileData({...editProfileData, location: e.target.value})}
                                placeholder="Your location"
                              />
                            </div>
                            <Button onClick={updateProfile} className="w-full">
                              Save Changes
                            </Button>
                          </div>
                        </DialogContent>
                      </Dialog>
                      
                      {/* Personal Mode Switcher */}
                      <div className="flex bg-white border-2 border-purple-300 rounded-full p-1">
                        <Button
                          onClick={() => setMode('real')}
                          data-testid="real-mode-btn"
                          size="sm"
                          className={`rounded-full px-4 py-2 ${
                            mode === 'real'
                              ? 'bg-gradient-to-r from-pink-500 to-purple-600 text-white'
                              : 'bg-transparent text-gray-600 hover:bg-gray-100'
                          }`}
                        >
                          <UserIcon className="w-4 h-4 mr-2" />
                          Real
                        </Button>
                        <Button
                          onClick={() => setMode('avatar')}
                          data-testid="avatar-mode-btn"
                          size="sm"
                          className={`rounded-full px-4 py-2 ${
                            mode === 'avatar'
                              ? 'bg-gradient-to-r from-pink-500 to-purple-600 text-white'
                              : 'bg-transparent text-gray-600 hover:bg-gray-100'
                          }`}
                        >
                          <Bot className="w-4 h-4 mr-2" />
                          Avatar
                        </Button>
                      </div>
                    </>
                  ) : (
                    <>
                      {friendshipStatus === 'accepted' ? (
                        <>
                          <Button
                            className="bg-gray-200 hover:bg-gray-300 text-gray-800"
                            data-testid="friends-btn"
                          >
                            <Users className="w-4 h-4 mr-2" />
                            Friends
                          </Button>
                          <Button
                            className="bg-blue-500 hover:bg-blue-600 text-white"
                            data-testid="message-btn"
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
                          data-testid="add-friend-btn"
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
                    data-testid="posts-tab"
                  >
                    Posts
                  </TabsTrigger>
                  <TabsTrigger
                    value="about"
                    className="data-[state=active]:border-b-4 data-[state=active]:border-purple-600 rounded-none pb-3 pt-3"
                    data-testid="about-tab"
                  >
                    About
                  </TabsTrigger>
                  <TabsTrigger
                    value="friends"
                    className="data-[state=active]:border-b-4 data-[state=active]:border-purple-600 rounded-none pb-3 pt-3"
                    data-testid="friends-tab"
                  >
                    Friends
                  </TabsTrigger>
                  {mode === 'avatar' && (
                    <TabsTrigger
                      value="activity"
                      className="data-[state=active]:border-b-4 data-[state=active]:border-purple-600 rounded-none pb-3 pt-3"
                      data-testid="activity-tab"
                    >
                      Avatar Activity
                    </TabsTrigger>
                  )}
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
                {profileUser.job_title && (
                  <div className="flex items-center text-gray-700">
                    <Briefcase className="w-5 h-5 mr-3 text-gray-500" />
                    <span>{profileUser.job_title}</span>
                  </div>
                )}
                {profileUser.location && (
                  <div className="flex items-center text-gray-700">
                    <MapPin className="w-5 h-5 mr-3 text-gray-500" />
                    <span>Lives in {profileUser.location}</span>
                  </div>
                )}
              </div>
            </Card>

            {/* Interests */}
            {profileUser.interests && profileUser.interests.length > 0 && (
              <Card className="p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Interests</h2>
                <div className="flex flex-wrap gap-2">
                  {profileUser.interests.map((interest, idx) => (
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
                {friends.slice(0, 9).map((friend, idx) => (
                  <div key={idx} className="cursor-pointer" onClick={() => navigate(`/profile/${friend.id}`)}>
                    <Avatar className="w-full aspect-square mb-1">
                      <AvatarImage src={friend.picture} />
                      <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white">
                        {friend.name?.charAt(0)}
                      </AvatarFallback>
                    </Avatar>
                    <p className="text-xs font-medium text-gray-900 truncate">{friend.name}</p>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* Main Content */}
          <div className="col-span-3 space-y-4">
            {mode === 'avatar' && (
              <Card className="p-6 bg-gradient-to-r from-purple-50 to-pink-50 border-2 border-purple-200">
                <div className="flex items-center space-x-3 mb-3">
                  <Bot className="w-6 h-6 text-purple-600" />
                  <h3 className="text-lg font-bold text-gray-900">Avatar Mode</h3>
                </div>
                <p className="text-gray-700">
                  You're viewing {displayName}'s AI avatar profile. The avatar learns from connected platforms and represents them in conversations.
                </p>
              </Card>
            )}

            {/* Create Post (Own Profile Only) */}
            {isOwnProfile && (
              <Card className="p-4">
                <div className="flex items-start space-x-3">
                  <Avatar className="w-10 h-10">
                    <AvatarImage src={currentUser.picture} />
                    <AvatarFallback>{currentUser.name?.charAt(0)}</AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <Textarea
                      placeholder={mode === 'real' ? "What's on your mind?" : "What's your avatar thinking?"}
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
                        <AvatarImage src={currentUser.picture} />
                        <AvatarFallback>{currentUser.name?.charAt(0)}</AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-semibold">{currentUser.name}</span>
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
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePageFull;
