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
import { ImmersivePageWrapper } from "@/components/ambient";

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
    <ImmersivePageWrapper pageId="search" user={user}>
      <AppHeader user={user} currentPage="search" />
      <div className="max-w-7xl mx-auto px-3 sm:px-4 md:px-6 py-4 sm:py-6 md:py-8 pb-20 sm:pb-8">
        {/* Search Bar */}
        <Card className="glass-morphism p-4 sm:p-6 mb-4 sm:mb-6 md:mb-8" data-testid="search-bar">
          <div className="flex items-center gap-3 sm:gap-4">
            <Search className="w-5 h-5 sm:w-6 sm:h-6 text-purple-600 flex-shrink-0" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by name, interests..."
              className="flex-1 border-2 border-purple-200 focus:border-purple-400 rounded-xl text-base sm:text-lg min-h-[44px]"
              data-testid="search-input"
            />
          </div>
        </Card>

        {/* Friend Requests */}
        {friendRequests.length > 0 && (
          <Card className="glass-morphism p-4 sm:p-6 mb-4 sm:mb-6 md:mb-8" data-testid="friend-requests">
            <h2 className="text-lg sm:text-xl md:text-2xl font-bold text-gray-800 mb-3 sm:mb-4 flex items-center">
              <Users className="w-5 h-5 sm:w-6 sm:h-6 mr-2 text-purple-600" />
              Requests ({friendRequests.length})
            </h2>
            <div className="space-y-3 sm:space-y-4">
              {friendRequests.map((request, idx) => (
                <div
                  key={request.id}
                  className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-white/50 p-3 sm:p-4 rounded-xl"
                  data-testid={`friend-request-${idx}`}
                >
                  <div className="flex items-center gap-3 sm:gap-4">
                    <Avatar className="w-10 h-10 sm:w-12 sm:h-12 border-2 border-white shadow-md flex-shrink-0">
                      <AvatarImage src={request.user?.picture} />
                      <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white">
                        {request.user?.name?.charAt(0)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="min-w-0">
                      <h3 className="font-bold text-gray-800 text-sm sm:text-base truncate">{request.user?.name}</h3>
                      <p className="text-xs sm:text-sm text-gray-600 truncate">{request.user?.bio?.slice(0, 60)}...</p>
                    </div>
                  </div>
                  <div className="flex gap-2 sm:flex-shrink-0">
                    <Button
                      onClick={() => acceptRequest(request.id)}
                      data-testid={`accept-request-${idx}`}
                      className="bg-green-500 hover:bg-green-600 text-white px-3 sm:px-4 py-2 rounded-full flex-1 sm:flex-none min-h-[44px] text-sm"
                    >
                      <Check className="w-4 h-4 mr-1" />
                      Accept
                    </Button>
                    <Button
                      variant="outline"
                      data-testid={`reject-request-${idx}`}
                      className="border-2 border-red-300 text-red-600 hover:bg-red-50 px-3 sm:px-4 py-2 rounded-full min-h-[44px] min-w-[44px]"
                    >
                      <X className="w-4 h-4" />
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
            <h2 className="text-lg sm:text-xl md:text-2xl font-bold text-gray-800 mb-3 sm:mb-4">
              Results {searchResults.length > 0 && `(${searchResults.length})`}
            </h2>
            {loading ? (
              <div className="text-center py-8 sm:py-12">
                <div className="w-10 h-10 sm:w-12 sm:h-12 border-4 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto mb-3 sm:mb-4"></div>
                <p className="text-sm sm:text-base text-gray-600">Searching...</p>
              </div>
            ) : searchResults.length === 0 ? (
              <Card className="glass-morphism p-6 sm:p-8 md:p-12 text-center" data-testid="no-results">
                <Search className="w-12 h-12 sm:w-16 sm:h-16 text-gray-400 mx-auto mb-3 sm:mb-4" />
                <p className="text-sm sm:text-base text-gray-600">No results for "{searchQuery}"</p>
              </Card>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4 md:gap-6">
                {searchResults.map((result, idx) => (
                  <Card
                    key={result.id}
                    className="glass-morphism p-4 sm:p-6 card-hover cursor-pointer"
                    onClick={() => navigate(`/profile/${result.id}`)}
                    data-testid={`search-result-${idx}`}
                  >
                    <div className="flex flex-col items-center text-center">
                      <Avatar className="w-16 h-16 sm:w-20 sm:h-20 border-3 sm:border-4 border-white shadow-lg mb-3 sm:mb-4">
                        <AvatarImage src={worldMode === 'avatar' ? (result.avatar_picture || result.picture) : result.picture} />
                        <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white text-xl sm:text-2xl">
                          {(worldMode === 'avatar' ? (result.avatar_name || result.name) : result.name)?.charAt(0)}
                        </AvatarFallback>
                      </Avatar>
                      <h3 className="text-base sm:text-lg font-bold text-gray-800 mb-1">
                        {worldMode === 'avatar' ? (result.avatar_name || result.name) : result.name}
                      </h3>
                      <p className="text-xs sm:text-sm text-gray-600 mb-2">
                        {result.age} • {worldMode === 'avatar' ? (result.avatar_location || result.location) : result.location}
                      </p>
                      {(worldMode === 'avatar' ? result.avatar_job_title : result.job_title) && (
                        <Badge className="mb-2 sm:mb-3 bg-purple-100 text-purple-700 text-xs">
                          {worldMode === 'avatar' ? result.avatar_job_title : result.job_title}
                        </Badge>
                      )}
                      <p className="text-xs sm:text-sm text-gray-600 mb-3 sm:mb-4 line-clamp-2">
                        {worldMode === 'avatar' ? (result.avatar_bio || result.bio) : result.bio}
                      </p>
                      <div className="flex flex-wrap gap-1.5 sm:gap-2 mb-3 sm:mb-4 justify-center">
                        {(worldMode === 'avatar' ? result.avatar_interests : result.interests)?.slice(0, 3).map((interest, i) => (
                          <span
                            key={i}
                            className="bg-purple-50 text-purple-700 text-[10px] sm:text-xs px-2 py-0.5 sm:py-1 rounded-full"
                          >
                            {interest}
                          </span>
                        ))}
                      </div>
                      {result.is_friend ? (
                        <Badge className="bg-green-100 text-green-700 text-xs">
                          <Check className="w-3 h-3 mr-1" />
                          Friends
                        </Badge>
                      ) : result.friendship_status === 'pending' ? (
                        <Badge className="bg-yellow-100 text-yellow-700 text-xs">Pending</Badge>
                      ) : (
                        <Button
                          onClick={(e) => {
                            e.stopPropagation();
                            sendFriendRequest(result.id);
                          }}
                          data-testid={`add-friend-${idx}`}
                          className="btn-primary text-white px-4 py-2 rounded-full w-full min-h-[44px] text-sm"
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
          <Card className="glass-morphism p-6 sm:p-8 md:p-12 text-center" data-testid="empty-state">
            <Search className="w-16 h-16 sm:w-20 sm:h-20 text-purple-400 mx-auto mb-3 sm:mb-4" />
            <h3 className="text-xl sm:text-2xl font-bold text-gray-800 mb-2">Find Your Connections</h3>
            <p className="text-sm sm:text-base text-gray-600 mb-4 sm:mb-6">
              Search for people by name, interests, location, or profession
            </p>
            <p className="text-xs sm:text-sm text-gray-500">
              Try searching for: "hiking", "photographer", "San Francisco"
            </p>
          </Card>
        )}
      </div>
    </ImmersivePageWrapper>
  );
};

export default SearchPage;
