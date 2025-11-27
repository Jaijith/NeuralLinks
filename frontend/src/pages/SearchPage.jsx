import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Search, UserPlus, Users, MessageCircle, Check, X } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { useWorldMode } from "@/contexts/WorldModeContext";
import AppHeader from "@/components/AppHeader";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SearchPage = ({ user }) => {
  const navigate = useNavigate();
  const { worldMode } = useWorldMode();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [friendRequests, setFriendRequests] = useState([]);

  useEffect(() => {
    fetchFriendRequests();
  }, []);

  useEffect(() => {
    if (searchQuery.length > 0) {
      const timer = setTimeout(() => {
        performSearch();
      }, 500);
      return () => clearTimeout(timer);
    } else {
      setSearchResults([]);
    }
  }, [searchQuery, worldMode]);

  const fetchFriendRequests = async () => {
    try {
      const response = await axios.get(`${API}/friends/requests`, {
        withCredentials: true,
      });
      setFriendRequests(response.data);
    } catch (error) {
      console.error("Error fetching requests:", error);
    }
  };

  const performSearch = async () => {
    setLoading(true);
    try {
      const response = await axios.get(
        `${API}/search/users?q=${encodeURIComponent(searchQuery)}&world_mode=${worldMode}`,
        { withCredentials: true }
      );
      setSearchResults(response.data);
    } catch (error) {
      console.error("Search error:", error);
      toast.error("Search failed");
    } finally {
      setLoading(false);
    }
  };

  const sendFriendRequest = async (friendId) => {
    try {
      await axios.post(`${API}/friends/request/${friendId}`, {}, {
        withCredentials: true,
      });
      toast.success("Friend request sent!");
      performSearch();
    } catch (error) {
      console.error("Error sending request:", error);
      toast.error("Failed to send friend request");
    }
  };

  const acceptRequest = async (friendshipId) => {
    try {
      await axios.post(`${API}/friends/accept/${friendshipId}`, {}, {
        withCredentials: true,
      });
      toast.success("Friend request accepted!");
      fetchFriendRequests();
    } catch (error) {
      console.error("Error accepting request:", error);
      toast.error("Failed to accept request");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50">
      <AppHeader user={user} currentPage="search" />
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Search Bar */}
        <Card className="glass-morphism p-6 mb-8" data-testid="search-bar">
          <div className="flex items-center space-x-4">
            <Search className="w-6 h-6 text-purple-600" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search for people by name, interests, location..."
              className="flex-1 border-2 border-purple-200 focus:border-purple-400 rounded-xl text-lg"
              data-testid="search-input"
            />
          </div>
        </Card>

        {/* Friend Requests */}
        {friendRequests.length > 0 && (
          <Card className="glass-morphism p-6 mb-8" data-testid="friend-requests">
            <h2 className="text-2xl font-bold text-gray-800 mb-4 flex items-center">
              <Users className="w-6 h-6 mr-2 text-purple-600" />
              Friend Requests ({friendRequests.length})
            </h2>
            <div className="space-y-4">
              {friendRequests.map((request, idx) => (
                <div
                  key={request.id}
                  className="flex items-center justify-between bg-white/50 p-4 rounded-xl"
                  data-testid={`friend-request-${idx}`}
                >
                  <div className="flex items-center space-x-4">
                    <Avatar className="w-12 h-12 border-2 border-white shadow-md">
                      <AvatarImage src={request.user?.picture} />
                      <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white">
                        {request.user?.name?.charAt(0)}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <h3 className="font-bold text-gray-800">{request.user?.name}</h3>
                      <p className="text-sm text-gray-600">{request.user?.bio?.slice(0, 60)}...</p>
                    </div>
                  </div>
                  <div className="flex space-x-2">
                    <Button
                      onClick={() => acceptRequest(request.id)}
                      data-testid={`accept-request-${idx}`}
                      className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-full"
                    >
                      <Check className="w-4 h-4 mr-1" />
                      Accept
                    </Button>
                    <Button
                      variant="outline"
                      data-testid={`reject-request-${idx}`}
                      className="border-2 border-red-300 text-red-600 hover:bg-red-50 px-4 py-2 rounded-full"
                    >
                      <X className="w-4 h-4 mr-1" />
                      Decline
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Search Results */}
        {searchQuery && (
          <div>
            <h2 className="text-2xl font-bold text-gray-800 mb-4">
              Search Results {searchResults.length > 0 && `(${searchResults.length})`}
            </h2>
            {loading ? (
              <div className="text-center py-12">
                <div className="w-12 h-12 border-4 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                <p className="text-gray-600">Searching...</p>
              </div>
            ) : searchResults.length === 0 ? (
              <Card className="glass-morphism p-12 text-center" data-testid="no-results">
                <Search className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600">No results found for "{searchQuery}"</p>
              </Card>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {searchResults.map((result, idx) => (
                  <Card
                    key={result.id}
                    className="glass-morphism p-6 card-hover cursor-pointer"
                    onClick={() => navigate(`/profile/${result.id}`)}
                    data-testid={`search-result-${idx}`}
                  >
                    <div className="flex flex-col items-center text-center">
                      <Avatar className="w-20 h-20 border-4 border-white shadow-lg mb-4">
                        <AvatarImage src={worldMode === 'avatar' ? (result.avatar_picture || result.picture) : result.picture} />
                        <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white text-2xl">
                          {(worldMode === 'avatar' ? (result.avatar_name || result.name) : result.name)?.charAt(0)}
                        </AvatarFallback>
                      </Avatar>
                      <h3 className="text-lg font-bold text-gray-800 mb-1">
                        {worldMode === 'avatar' ? (result.avatar_name || result.name) : result.name}
                      </h3>
                      <p className="text-sm text-gray-600 mb-2">
                        {result.age} • {worldMode === 'avatar' ? (result.avatar_location || result.location) : result.location}
                      </p>
                      {(worldMode === 'avatar' ? result.avatar_job_title : result.job_title) && (
                        <Badge className="mb-3 bg-purple-100 text-purple-700">
                          {worldMode === 'avatar' ? result.avatar_job_title : result.job_title}
                        </Badge>
                      )}
                      <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                        {worldMode === 'avatar' ? (result.avatar_bio || result.bio) : result.bio}
                      </p>
                      <div className="flex flex-wrap gap-2 mb-4">
                        {(worldMode === 'avatar' ? result.avatar_interests : result.interests)?.slice(0, 3).map((interest, i) => (
                          <span
                            key={i}
                            className="bg-purple-50 text-purple-700 text-xs px-2 py-1 rounded-full"
                          >
                            {interest}
                          </span>
                        ))}
                      </div>
                      {result.is_friend ? (
                        <Badge className="bg-green-100 text-green-700">
                          <Check className="w-3 h-3 mr-1" />
                          Friends
                        </Badge>
                      ) : result.friendship_status === 'pending' ? (
                        <Badge className="bg-yellow-100 text-yellow-700">Request Pending</Badge>
                      ) : (
                        <Button
                          onClick={(e) => {
                            e.stopPropagation();
                            sendFriendRequest(result.id);
                          }}
                          data-testid={`add-friend-${idx}`}
                          className="btn-primary text-white px-4 py-2 rounded-full w-full"
                        >
                          <UserPlus className="w-4 h-4 mr-2" />
                          Add Friend
                        </Button>
                      )}
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Empty State */}
        {!searchQuery && (
          <Card className="glass-morphism p-12 text-center" data-testid="empty-state">
            <Search className="w-20 h-20 text-purple-400 mx-auto mb-4" />
            <h3 className="text-2xl font-bold text-gray-800 mb-2">Find Your Connections</h3>
            <p className="text-gray-600 mb-6">
              Search for people by name, interests, location, or profession
            </p>
            <p className="text-sm text-gray-500">
              Try searching for: "hiking", "photographer", "San Francisco"
            </p>
          </Card>
        )}
      </div>
    </div>
  );
};

export default SearchPage;
