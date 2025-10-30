import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Users, MessageCircle, UserMinus } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { useWorldMode } from "@/contexts/WorldModeContext";
import AppHeader from "@/components/AppHeader";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const FriendsPage = ({ user }) => {
  const navigate = useNavigate();
  const { worldMode } = useWorldMode();
  const [friends, setFriends] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFriends();
  }, [worldMode]); // Re-fetch when worldMode changes

  const fetchFriends = async () => {
    try {
      const response = await axios.get(`${API}/friends`, {
        withCredentials: true,
      });
      setFriends(response.data);
    } catch (error) {
      console.error("Error fetching friends:", error);
      toast.error("Failed to load friends");
    } finally {
      setLoading(false);
    }
  };

  const removeFriend = async (friendId) => {
    if (!window.confirm("Are you sure you want to remove this friend?")) return;
    
    try {
      await axios.delete(`${API}/friends/${friendId}`, {
        withCredentials: true,
      });
      toast.success("Friend removed");
      fetchFriends();
    } catch (error) {
      console.error("Error removing friend:", error);
      toast.error("Failed to remove friend");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50">
      <AppHeader user={user} currentPage="friends" />
      
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold gradient-text mb-2">Friends</h1>
          <p className="text-gray-600">Manage your connections</p>
        </div>

        {loading ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 border-4 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-600">Loading friends...</p>
          </div>
        ) : friends.length === 0 ? (
          <Card className="glass-morphism p-12 text-center" data-testid="no-friends">
            <div className="w-24 h-24 bg-gradient-to-br from-purple-200 to-purple-300 rounded-full flex items-center justify-center mx-auto mb-6">
              <Users className="w-12 h-12 text-purple-600" />
            </div>
            <h3 className="text-2xl font-bold text-gray-800 mb-3">No friends yet</h3>
            <p className="text-gray-600 mb-6">Start connecting with people to grow your network</p>
            <Button
              onClick={() => navigate("/search")}
              data-testid="find-friends-btn"
              className="btn-primary text-white px-8 py-3 rounded-full"
            >
              Find Friends
            </Button>
          </Card>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {friends.map((friend, idx) => {
              const displayName = worldMode === 'avatar' 
                ? (friend.avatar_name || friend.name)
                : friend.name;
              const displayPicture = worldMode === 'avatar'
                ? (friend.avatar_picture || friend.picture)
                : friend.picture;
              const displayBio = worldMode === 'avatar'
                ? (friend.avatar_bio || friend.bio)
                : friend.bio;
              const displayInterests = worldMode === 'avatar'
                ? (friend.avatar_interests || friend.interests || [])
                : (friend.interests || []);
              
              return (
                <Card
                  key={friend.id}
                  className="glass-morphism p-6 card-hover friend-card"
                  data-testid={`friend-card-${idx}`}
                >
                  <div className="flex flex-col items-center text-center">
                    <Avatar className="w-24 h-24 border-4 border-white shadow-lg mb-4">
                      <AvatarImage src={displayPicture} />
                      <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white text-2xl">
                        {displayName?.charAt(0)}
                      </AvatarFallback>
                    </Avatar>
                    <h3 className="text-xl font-bold mb-1">{displayName}</h3>
                    <p className="text-sm text-gray-600 mb-3">
                      {friend.age} • {worldMode === 'avatar' ? (friend.avatar_location || friend.location) : friend.location}
                    </p>
                    <p className="text-sm text-gray-600 mb-4 line-clamp-2">{displayBio}</p>
                    {displayInterests && displayInterests.length > 0 && (
                      <div className="flex flex-wrap gap-2 mb-4 justify-center">
                        {displayInterests.slice(0, 3).map((interest, i) => (
                          <span
                            key={i}
                            className="bg-yellow-100 text-purple-700 text-xs px-2 py-1 rounded-full font-semibold"
                          >
                            {interest}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="flex space-x-2 w-full">
                      <Button
                        onClick={() => navigate(`/profile/${friend.id}`)}
                        data-testid={`view-profile-${idx}`}
                        variant="outline"
                        className="flex-1 border-2 border-purple-400 text-purple-700 hover:bg-purple-50 rounded-full font-bold"
                      >
                        View Profile
                      </Button>
                      <Button
                        onClick={() => removeFriend(friend.id)}
                        data-testid={`remove-friend-${idx}`}
                        variant="outline"
                        className="border-2 border-red-400 text-red-600 hover:bg-red-50 rounded-full px-3 font-bold"
                      >
                        <UserMinus className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default FriendsPage;
