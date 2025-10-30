import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { 
  Camera, MapPin, Briefcase, Heart, Users, MessageCircle, 
  Settings as SettingsIcon, Bot, User as UserIcon, Search,
  Home, Image, Video, Smile, Send, ThumbsUp, Share2,
  MoreHorizontal, Globe, Lock, TrendingUp
} from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { useWorldMode } from "@/contexts/WorldModeContext";
import WorldModeToggle from "@/components/WorldModeToggle";
import SideMessenger from "@/components/SideMessenger";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const FacebookStyleHome = ({ user: currentUser, setUser }) => {
  const navigate = useNavigate();
  const { worldMode } = useWorldMode();
  const [mode, setMode] = useState('real'); // 'real' or 'avatar' - personal view
  const [friends, setFriends] = useState([]);
  const [avatarConversations, setAvatarConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [postText, setPostText] = useState('');
  const [selectedTab, setSelectedTab] = useState('timeline');
  const [friendPosts, setFriendPosts] = useState([]);
  const [showMessenger, setShowMessenger] = useState(false);
  const [selectedFriend, setSelectedFriend] = useState(null);

  // Dynamic labels based on world mode
  const labels = {
    matches: worldMode === 'avatar' ? 'Neural Links' : 'Matches',
    friends: worldMode === 'avatar' ? 'Connections' : 'Friends',
    messages: worldMode === 'avatar' ? 'Neural Sync' : 'Messages',
    profile: worldMode === 'avatar' ? 'Identity Matrix' : 'Profile'
  };

  useEffect(() => {
    fetchData();
  }, [worldMode]); // Re-fetch when worldMode changes

  useEffect(() => {
    if (mode === 'avatar') {
      fetchAvatarConversations();
    }
  }, [mode]);

  const fetchData = async () => {
    try {
      const [friendsRes] = await Promise.all([
        axios.get(`${API}/friends`, { withCredentials: true })
      ]);
      setFriends(friendsRes.data.slice(0, 9));
      
      // Fetch friend posts based on world mode
      const posts = [];
      for (const friend of friendsRes.data.slice(0, 10)) {
        // Choose posts based on world mode
        const postsToShow = worldMode === 'avatar' 
          ? (friend.avatar_posts || [])
          : (friend.posts || []);
        
        if (postsToShow && postsToShow.length > 0) {
          postsToShow.forEach(post => {
            posts.push({
              ...post,
              user: friend,
              // Add display fields based on world mode
              displayName: worldMode === 'avatar' 
                ? (friend.avatar_name || friend.name)
                : friend.name,
              displayPicture: worldMode === 'avatar'
                ? (friend.avatar_picture || friend.picture)
                : friend.picture
            });
          });
        }
      }
      // Sort by date
      posts.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setFriendPosts(posts.slice(0, 20));
    } catch (error) {
      console.error("Error fetching data:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAvatarConversations = async () => {
    try {
      const response = await axios.get(`${API}/avatar/conversations`, {
        withCredentials: true,
      });
      setAvatarConversations(response.data);
    } catch (error) {
      console.error("Error fetching avatar conversations:", error);
    }
  };

  const handleLogout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
      setUser(null);
      navigate("/");
      toast.success("Logged out");
    } catch (error) {
      console.error("Logout error:", error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${worldMode === 'avatar' ? 'bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900' : 'bg-gray-100'}`}>
      {/* Facebook Header */}
      <header className={`shadow-sm sticky top-0 z-50 border-b ${
        worldMode === 'avatar' 
          ? 'bg-slate-900/90 backdrop-blur-md border-blue-500/30' 
          : 'bg-white border-gray-200'
      }`}>
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex items-center justify-between h-14">
            {/* Left - Logo & Search */}
            <div className="flex items-center space-x-2 flex-1">
              <div 
                className={`w-10 h-10 rounded-full flex items-center justify-center cursor-pointer ${
                  worldMode === 'avatar' 
                    ? 'bg-gradient-to-br from-blue-500 to-purple-600 avatar-glow' 
                    : 'bg-blue-500'
                }`}
                onClick={() => setSelectedTab('timeline')}
              >
                <Heart className="w-6 h-6 text-white fill-white" />
              </div>
              <div className="relative hidden md:block">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="Search"
                  onClick={() => navigate('/search')}
                  readOnly
                  className={`pl-10 rounded-full w-60 cursor-pointer border-none ${
                    worldMode === 'avatar'
                      ? 'bg-slate-800 text-blue-100 placeholder:text-blue-300/50'
                      : 'bg-gray-100'
                  }`}
                />
              </div>
            </div>

            {/* Center - Navigation */}
            <div className="flex items-center space-x-1">
              <Button
                variant="ghost"
                onClick={() => setSelectedTab('timeline')}
                className={`px-8 py-2 rounded-lg ${
                  selectedTab === 'timeline' 
                    ? worldMode === 'avatar'
                      ? 'border-b-4 border-blue-400'
                      : 'border-b-4 border-blue-500'
                    : ''
                }`}
              >
                <Home className={`w-6 h-6 ${worldMode === 'avatar' ? 'text-blue-300' : 'text-gray-600'}`} />
              </Button>
              <Button
                variant="ghost"
                onClick={() => navigate('/friends')}
                className="px-8 py-2 rounded-lg"
              >
                <Users className={`w-6 h-6 ${worldMode === 'avatar' ? 'text-blue-300' : 'text-gray-600'}`} />
              </Button>
              <Button
                variant="ghost"
                onClick={() => navigate('/matches')}
                className="px-8 py-2 rounded-lg"
              >
                <Heart className={`w-6 h-6 ${worldMode === 'avatar' ? 'text-blue-300' : 'text-gray-600'}`} />
              </Button>
            </div>

            {/* Right - World Toggle & Profile */}
            <div className="flex items-center space-x-3 flex-1 justify-end">
              {/* Global World Mode Toggle */}
              <WorldModeToggle />

              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/integrations')}
                className="rounded-full p-2"
              >
                <SettingsIcon className={`w-5 h-5 ${worldMode === 'avatar' ? 'text-blue-300' : ''}`} />
              </Button>

              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="rounded-full p-2"
              >
                <MoreHorizontal className={`w-5 h-5 ${worldMode === 'avatar' ? 'text-blue-300' : ''}`} />
              </Button>

              <Avatar 
                className={`w-8 h-8 cursor-pointer ${
                  worldMode === 'avatar' 
                    ? 'border-2 border-blue-400 avatar-glow' 
                    : 'border-2 border-blue-500'
                }`}
                onClick={() => navigate('/myprofile')}
              >
                <AvatarImage src={currentUser.picture} />
                <AvatarFallback className={worldMode === 'avatar' ? 'bg-blue-600 text-white text-sm' : 'bg-blue-500 text-white text-sm'}>
                  {currentUser.name?.charAt(0)}
                </AvatarFallback>
              </Avatar>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-4">
        {selectedTab === 'timeline' ? (
          <div className="grid grid-cols-12 gap-4">
            {/* Left Sidebar */}
            <div className="col-span-3 space-y-2">
              <Card className={worldMode === 'avatar' ? 'card-avatar p-3 hover:bg-slate-800/50 cursor-pointer' : 'p-3 hover:bg-gray-50 cursor-pointer'}>
                <div className="flex items-center space-x-3">
                  <Avatar className={`w-9 h-9 ${worldMode === 'avatar' ? 'avatar-glow' : ''}`}>
                    <AvatarImage src={currentUser.picture} />
                    <AvatarFallback>{currentUser.name?.charAt(0)}</AvatarFallback>
                  </Avatar>
                  <span className={`font-semibold text-sm ${worldMode === 'avatar' ? 'text-blue-100' : ''}`}>
                    {currentUser.name}
                  </span>
                </div>
              </Card>
              <Button 
                variant="ghost" 
                className={`w-full justify-start text-sm font-semibold ${
                  worldMode === 'avatar' ? 'text-blue-200 hover:bg-slate-800/50' : ''
                }`}
                onClick={() => navigate('/friends')}
              >
                <Users className={`w-5 h-5 mr-3 ${worldMode === 'avatar' ? 'text-blue-400' : 'text-blue-500'}`} />
                {labels.friends}
              </Button>
              <Button 
                variant="ghost" 
                className={`w-full justify-start text-sm font-semibold ${
                  worldMode === 'avatar' ? 'text-blue-200 hover:bg-slate-800/50' : ''
                }`}
                onClick={() => navigate('/matches')}
              >
                <Heart className={`w-5 h-5 mr-3 ${worldMode === 'avatar' ? 'text-pink-400 bioluminescent' : 'text-pink-500'}`} />
                {labels.matches}
              </Button>
              {mode === 'avatar' && (
                <Button 
                  variant="ghost" 
                  className={`w-full justify-start text-sm font-semibold ${
                    worldMode === 'avatar' ? 'text-blue-200 hover:bg-slate-800/50' : ''
                  }`}
                  onClick={() => setSelectedTab('messenger')}
                >
                  <MessageCircle className={`w-5 h-5 mr-3 ${worldMode === 'avatar' ? 'text-purple-400 bioluminescent' : 'text-purple-500'}`} />
                  {worldMode === 'avatar' ? 'Neural Sync' : 'Avatar Messenger'}
                </Button>
              )}
            </div>

            {/* Center - Feed */}
            <div className="col-span-6 space-y-4">
              {/* Create Post */}
              <Card className="p-4">
                <div className="flex items-center space-x-3 mb-3">
                  <Avatar className="w-10 h-10">
                    <AvatarImage src={currentUser.picture} />
                    <AvatarFallback>{currentUser.name?.charAt(0)}</AvatarFallback>
                  </Avatar>
                  <Input
                    placeholder={mode === 'real' ? "What's on your mind?" : "What's your avatar thinking?"}
                    className="flex-1 rounded-full bg-gray-100 border-none"
                    onClick={() => {/* Open create post modal */}}
                    readOnly
                  />
                </div>
                <div className="flex items-center justify-around border-t pt-3">
                  <Button variant="ghost" size="sm" className="flex-1">
                    <Video className="w-5 h-5 mr-2 text-red-500" />
                    <span className="text-sm font-semibold text-gray-600">Live video</span>
                  </Button>
                  <Button variant="ghost" size="sm" className="flex-1">
                    <Image className="w-5 h-5 mr-2 text-green-500" />
                    <span className="text-sm font-semibold text-gray-600">Photo/video</span>
                  </Button>
                  <Button variant="ghost" size="sm" className="flex-1">
                    <Smile className="w-5 h-5 mr-2 text-yellow-500" />
                    <span className="text-sm font-semibold text-gray-600">Feeling</span>
                  </Button>
                </div>
              </Card>

              {/* Mode Banner */}
              {mode === 'avatar' && (
                <Card className="p-4 bg-gradient-to-r from-purple-50 to-pink-50 border-2 border-purple-200">
                  <div className="flex items-center space-x-3">
                    <Bot className="w-8 h-8 text-purple-600" />
                    <div>
                      <h3 className="font-bold text-gray-900">Avatar Mode Active</h3>
                      <p className="text-sm text-gray-600">
                        You're viewing what your AI avatar is doing. {avatarConversations.length} active conversations.
                      </p>
                    </div>
                  </div>
                </Card>
              )}

              {/* Posts Feed */}
              {mode === 'real' ? (
                friendPosts.length > 0 ? (
                  <div className="space-y-4">
                    {friendPosts.map((post, idx) => (
                      <Card key={idx} className="p-4">
                        <div className="flex items-start space-x-3">
                          <Avatar 
                            className="w-10 h-10 cursor-pointer"
                            onClick={() => navigate(`/profile/${post.user.id}`)}
                          >
                            <AvatarImage src={post.displayPicture} />
                            <AvatarFallback>{post.displayName?.charAt(0)}</AvatarFallback>
                          </Avatar>
                          <div className="flex-1">
                            <div className="flex items-center space-x-2 mb-1">
                              <span 
                                className="font-semibold cursor-pointer hover:underline"
                                onClick={() => navigate(`/profile/${post.user.id}`)}
                              >
                                {post.displayName}
                              </span>
                              {post.user.is_bot && (
                                <Badge className="bg-purple-100 text-purple-700 text-xs">
                                  <Bot className="w-3 h-3 mr-1" />
                                  Bot
                                </Badge>
                              )}
                              <span className="text-xs text-gray-500">
                                {new Date(post.created_at).toLocaleDateString()}
                              </span>
                            </div>
                            <p className="text-gray-800 mb-3">{post.text}</p>
                            <div className="flex items-center space-x-6 text-sm text-gray-500 border-t pt-2">
                              <Button variant="ghost" size="sm" className="text-gray-600 hover:text-blue-600">
                                <ThumbsUp className="w-4 h-4 mr-1" />
                                {post.likes || 0}
                              </Button>
                              <Button variant="ghost" size="sm" className="text-gray-600 hover:text-blue-600">
                                <MessageCircle className="w-4 h-4 mr-1" />
                                {post.comments || 0}
                              </Button>
                              <Button variant="ghost" size="sm" className="text-gray-600 hover:text-blue-600">
                                <Share2 className="w-4 h-4 mr-1" />
                                Share
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
                      <Home className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                      <h3 className="text-xl font-bold text-gray-800 mb-2">Welcome to your feed!</h3>
                      <p className="text-gray-600 mb-4">Start by adding friends or creating your first post</p>
                      <Button 
                        className="bg-blue-500 hover:bg-blue-600 text-white"
                        onClick={() => navigate('/search')}
                      >
                        Find Friends
                      </Button>
                    </div>
                  </Card>
                )
              ) : (
                // Avatar Activity Feed
                <div className="space-y-4">
                  {avatarConversations.length === 0 ? (
                    <Card className="p-6">
                      <div className="text-center py-12">
                        <Bot className="w-16 h-16 text-purple-300 mx-auto mb-4" />
                        <h3 className="text-xl font-bold text-gray-800 mb-2">Your avatar is ready!</h3>
                        <p className="text-gray-600 mb-4">Start discovery to let your avatar find matches</p>
                        <Button 
                          className="bg-purple-500 hover:bg-purple-600 text-white"
                          onClick={() => navigate('/matches')}
                        >
                          Start Discovery
                        </Button>
                      </div>
                    </Card>
                  ) : (
                    avatarConversations.map((conv, idx) => (
                      <Card key={idx} className="p-4">
                        <div className="flex items-start space-x-3">
                          <Avatar className="w-10 h-10">
                            <AvatarImage src={currentUser.picture} />
                            <AvatarFallback>{currentUser.name?.charAt(0)}</AvatarFallback>
                          </Avatar>
                          <div className="flex-1">
                            <div className="flex items-center space-x-2 mb-1">
                              <span className="font-semibold">{currentUser.name}'s Avatar</span>
                              <Badge className="bg-purple-100 text-purple-700 text-xs">
                                <Bot className="w-3 h-3 mr-1" />
                                AI Agent
                              </Badge>
                              <span className="text-xs text-gray-500">
                                {new Date(conv.created_at).toLocaleDateString()}
                              </span>
                            </div>
                            <p className="text-sm text-gray-700 mb-2">
                              Started a conversation with <span className="font-semibold">{conv.other_user?.name}</span>'s avatar
                            </p>
                            <div className="bg-gray-50 rounded-lg p-3 mb-3">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-semibold text-gray-600">Compatibility Score</span>
                                <Badge className="bg-green-100 text-green-700">
                                  {Math.round(conv.compatibility_score || 0)}%
                                </Badge>
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-2">
                                <div
                                  className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full"
                                  style={{ width: `${conv.compatibility_score || 0}%` }}
                                ></div>
                              </div>
                              {conv.conversation_summary && (
                                <p className="text-xs text-gray-600 mt-2">{conv.conversation_summary}</p>
                              )}
                            </div>
                            <div className="flex items-center space-x-4 text-sm">
                              <Button variant="ghost" size="sm" className="text-gray-600">
                                <ThumbsUp className="w-4 h-4 mr-1" />
                                Approve
                              </Button>
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                className="text-gray-600"
                                onClick={() => setSelectedTab('messenger')}
                              >
                                <MessageCircle className="w-4 h-4 mr-1" />
                                View Chat
                              </Button>
                              <Button variant="ghost" size="sm" className="text-gray-600">
                                <Share2 className="w-4 h-4 mr-1" />
                                Share
                              </Button>
                            </div>
                          </div>
                        </div>
                      </Card>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Right Sidebar */}
            <div className="col-span-3 space-y-4">
              <Card className={worldMode === 'avatar' ? 'card-avatar p-4' : 'p-4'}>
                <h3 className={`font-semibold mb-3 ${worldMode === 'avatar' ? 'text-blue-200' : 'text-gray-700'}`}>
                  {labels.friends}
                </h3>
                <div className="space-y-2">
                  {friends.slice(0, 6).map((friend, idx) => {
                    const displayName = worldMode === 'avatar' 
                      ? (friend.avatar_name || friend.name)
                      : friend.name;
                    const displayPicture = worldMode === 'avatar'
                      ? (friend.avatar_picture || friend.picture)
                      : friend.picture;
                    
                    return (
                      <div 
                        key={idx} 
                        className={`flex items-center justify-between p-2 rounded group ${
                          worldMode === 'avatar' ? 'hover:bg-slate-800/50' : 'hover:bg-gray-50'
                        }`}
                      >
                        <div 
                          className="flex items-center space-x-2 cursor-pointer flex-1"
                          onClick={() => navigate(`/profile/${friend.id}`)}
                        >
                          <Avatar className={`w-8 h-8 ${worldMode === 'avatar' ? 'avatar-glow' : ''}`}>
                            <AvatarImage src={displayPicture} />
                            <AvatarFallback>{displayName?.charAt(0)}</AvatarFallback>
                          </Avatar>
                          <span className={`text-sm font-medium ${worldMode === 'avatar' ? 'text-blue-100' : ''}`}>
                            {displayName}
                          </span>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="opacity-0 group-hover:opacity-100 transition-opacity p-1 h-auto"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedFriend(friend);
                            setShowMessenger(true);
                          }}
                        >
                          <MessageCircle className="w-4 h-4 text-blue-500" />
                        </Button>
                      </div>
                    );
                  })}
                </div>
              </Card>

              {mode === 'avatar' && (
                <Card className={worldMode === 'avatar' ? 'card-avatar p-4' : 'p-4'}>
                  <h3 className={`font-semibold mb-3 flex items-center ${worldMode === 'avatar' ? 'text-blue-200' : 'text-gray-700'}`}>
                    <TrendingUp className={`w-4 h-4 mr-2 ${worldMode === 'avatar' ? 'text-purple-400' : 'text-purple-600'}`} />
                    {worldMode === 'avatar' ? 'Neural Stats' : 'Avatar Stats'}
                  </h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className={worldMode === 'avatar' ? 'text-blue-300' : 'text-gray-600'}>Conversations</span>
                      <span className={`font-semibold ${worldMode === 'avatar' ? 'text-blue-100' : ''}`}>
                        {avatarConversations.length}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className={worldMode === 'avatar' ? 'text-blue-300' : 'text-gray-600'}>Avg Score</span>
                      <span className={`font-semibold ${worldMode === 'avatar' ? 'text-blue-100' : ''}`}>
                        {avatarConversations.length > 0
                          ? Math.round(
                              avatarConversations.reduce((acc, c) => acc + (c.compatibility_score || 0), 0) /
                                avatarConversations.length
                            )
                          : 0}%
                      </span>
                    </div>
                  </div>
                </Card>
              )}
            </div>
          </div>
        ) : selectedTab === 'messenger' ? (
          // Avatar Messenger View
          <AvatarMessenger 
            conversations={avatarConversations}
            currentUser={currentUser}
            onBack={() => setSelectedTab('timeline')}
          />
        ) : null}
      </div>
    </div>
  );
};

// Avatar Messenger Component
const AvatarMessenger = ({ conversations, currentUser, onBack }) => {
  const [selectedConv, setSelectedConv] = useState(null);

  return (
    <div className="grid grid-cols-12 gap-4 h-[calc(100vh-120px)]">
      {/* Conversations List */}
      <Card className="col-span-4 p-0 overflow-hidden">
        <div className="p-4 border-b bg-white">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xl font-bold">Avatar Messenger</h2>
            <Button variant="ghost" size="sm" onClick={onBack}>
              <Home className="w-4 h-4" />
            </Button>
          </div>
          <p className="text-sm text-gray-600">Your avatar's conversations</p>
        </div>
        <div className="overflow-y-auto h-full">
          {conversations.map((conv, idx) => (
            <div
              key={idx}
              className={`p-4 border-b cursor-pointer hover:bg-gray-50 ${
                selectedConv?.id === conv.id ? 'bg-blue-50' : ''
              }`}
              onClick={() => setSelectedConv(conv)}
            >
              <div className="flex items-center space-x-3">
                <Avatar className="w-12 h-12">
                  <AvatarImage src={conv.other_user?.picture} />
                  <AvatarFallback>{conv.other_user?.name?.charAt(0)}</AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-sm">{conv.other_user?.name}'s Avatar</span>
                    <Badge className="bg-purple-100 text-purple-700 text-xs">
                      {Math.round(conv.compatibility_score || 0)}%
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-600 truncate">{conv.conversation_summary}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Chat Window */}
      <Card className="col-span-8 p-0 overflow-hidden flex flex-col">
        {selectedConv ? (
          <>
            <div className="p-4 border-b bg-white">
              <div className="flex items-center space-x-3">
                <Avatar className="w-10 h-10">
                  <AvatarImage src={selectedConv.other_user?.picture} />
                  <AvatarFallback>{selectedConv.other_user?.name?.charAt(0)}</AvatarFallback>
                </Avatar>
                <div>
                  <h3 className="font-semibold">{selectedConv.other_user?.name}'s Avatar</h3>
                  <p className="text-xs text-gray-600">{selectedConv.other_user?.bio}</p>
                </div>
              </div>
            </div>
            <div className="flex-1 p-4 overflow-y-auto bg-gray-50">
              {selectedConv.messages && selectedConv.messages.length > 0 ? (
                selectedConv.messages.map((msg, idx) => (
                  <div key={idx} className={`flex mb-3 ${msg.sender === currentUser.id ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-xs px-4 py-2 rounded-2xl ${
                      msg.sender === currentUser.id
                        ? 'bg-blue-500 text-white'
                        : 'bg-white text-gray-800 border'
                    }`}>
                      <p className="text-sm">{msg.message}</p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-12">
                  <MessageCircle className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-600">Conversation in progress...</p>
                </div>
              )}
            </div>
            <div className="p-4 border-t bg-white">
              <div className="flex items-center space-x-2">
                <Input
                  placeholder="Your avatar is chatting..."
                  disabled
                  className="flex-1 rounded-full"
                />
                <Button size="sm" className="rounded-full bg-blue-500" disabled>
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <MessageCircle className="w-20 h-20 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-600">Select a conversation to view</p>
            </div>
          </div>
        )}
      </Card>

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
  );
};

export default FacebookStyleHome;
