import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Camera, MapPin, Briefcase, Heart, Users, MessageCircle, Settings as SettingsIcon, Bot, User as UserIcon } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ProfilePageFull = ({ user: currentUser }) => {
  const navigate = useNavigate();
  const { userId } = useParams();
  const [profileUser, setProfileUser] = useState(null);
  const [isOwnProfile, setIsOwnProfile] = useState(false);
  const [friendshipStatus, setFriendshipStatus] = useState('none');
  const [friends, setFriends] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState('real'); // 'real' or 'avatar'

  useEffect(() => {
    const targetUserId = userId || currentUser.id;
    setIsOwnProfile(targetUserId === currentUser.id);
    fetchProfile(targetUserId);
    fetchFriends(targetUserId);
  }, [userId, currentUser]);

  const fetchProfile = async (id) => {
    try {
      if (id === currentUser.id) {
        setProfileUser(currentUser);
      } else {
        const response = await axios.get(`${API}/users/${id}`, {
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

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Cover Photo */}
      <div className="relative h-96 bg-gradient-to-br from-pink-400 via-purple-500 to-indigo-600">
        <div className="absolute inset-0 bg-black/20"></div>
        {isOwnProfile && (
          <Button
            variant="secondary"
            className="absolute bottom-4 right-4 bg-white/90 hover:bg-white"
            data-testid="edit-cover-btn"
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
              <AvatarImage src={profileUser.picture} />
              <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white text-4xl">
                {profileUser.name?.charAt(0)}
              </AvatarFallback>
            </Avatar>
            {isOwnProfile && (
              <Button
                size="sm"
                className="absolute bottom-2 right-2 rounded-full w-10 h-10 p-0 bg-white hover:bg-gray-100"
                data-testid="edit-photo-btn"
              >
                <Camera className="w-5 h-5 text-gray-700" />
              </Button>
            )}
          </div>

          <div className="bg-white shadow rounded-b-2xl">
            <div className="pt-8 pb-4 px-8 ml-56">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-3 mb-2">
                    <h1 className="text-4xl font-bold text-gray-900">{profileUser.name}</h1>
                    {profileUser.is_bot && (
                      <Badge className="bg-purple-100 text-purple-700">
                        <Bot className="w-3 h-3 mr-1" />
                        AI Agent
                      </Badge>
                    )}
                  </div>
                  <p className="text-gray-600 text-lg mb-2">{profileUser.bio}</p>
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
                      <Button
                        onClick={() => navigate("/profile")}
                        data-testid="edit-profile-btn"
                        className="bg-gray-200 hover:bg-gray-300 text-gray-800"
                      >
                        <SettingsIcon className="w-4 h-4 mr-2" />
                        Edit Profile
                      </Button>
                      {/* Mode Switcher */}
                      <div className="flex bg-white border-2 border-purple-300 rounded-full p-1">
                        <Button
                          onClick={() => setMode('real')}
                          data-testid="real-mode-btn"
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
                            className="btn-primary text-white"
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
                          className="btn-primary text-white"
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
                  You're viewing {profileUser.name}'s AI avatar profile. The avatar learns from connected platforms and represents them in conversations.
                </p>
              </Card>
            )}

            {/* Posts */}
            <Card className="p-6">
              <div className="text-center py-12">
                <MessageCircle className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-xl font-bold text-gray-800 mb-2">No posts yet</h3>
                <p className="text-gray-600">
                  {isOwnProfile ? "Share what's on your mind" : `${profileUser.name} hasn't posted anything yet`}
                </p>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePageFull;
