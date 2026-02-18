import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Users, MessageCircle, UserMinus, UserPlus, Check, X, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { useWorldMode } from "@/contexts/WorldModeContext";
import { PageContainer } from "@/components/layout";
import { ConfirmDialog } from "@/components/common";
import { useFriends, useFriendRequests } from "@/features/friends";
import { friendService } from "@/services/api";
import SideMessenger from "@/components/SideMessenger";
import { LoadingSpinner, EmptyState } from "@/components/common";
import { ImmersivePageWrapper } from "@/components/ambient";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const FriendsPage = ({ user }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const viewingUserId = searchParams.get('user'); // If set, we're viewing another user's friends
  const { worldMode } = useWorldMode();
  const [activeTab, setActiveTab] = useState("friends");
  const [showMessenger, setShowMessenger] = useState(false);
  const [selectedFriend, setSelectedFriend] = useState(null);
  const [friendToRemove, setFriendToRemove] = useState(null);
  
  // State for viewing another user's friends
  const [otherUserFriends, setOtherUserFriends] = useState([]);
  const [otherUserInfo, setOtherUserInfo] = useState(null);
  const [otherUserLoading, setOtherUserLoading] = useState(false);

  // Use custom hooks for own friends
  const { friends: myFriends, loading: friendsLoading, refresh: refreshFriends } = useFriends(worldMode);
  const { 
    friendRequests, 
    loading: requestsLoading, 
    processing,
    acceptRequest,
    declineRequest,
    refresh: refreshRequests
  } = useFriendRequests(worldMode);

  // Fetch other user's friends if viewing someone else's
  useEffect(() => {
    if (viewingUserId) {
      setOtherUserLoading(true);
      Promise.all([
        axios.get(`${API}/friends?user_id=${viewingUserId}`, { withCredentials: true }),
        axios.get(`${API}/users/${viewingUserId}`, { withCredentials: true })
      ]).then(([friendsRes, userRes]) => {
        setOtherUserFriends(friendsRes.data || []);
        setOtherUserInfo(userRes.data);
      }).catch(err => {
        console.error('Error fetching user friends:', err);
        toast.error('Failed to load friends');
      }).finally(() => {
        setOtherUserLoading(false);
      });
    }
  }, [viewingUserId]);

  // Use other user's friends if viewing someone else, otherwise own friends
  const friends = viewingUserId ? otherUserFriends : myFriends;
  const loading = viewingUserId ? otherUserLoading : (friendsLoading || requestsLoading);
  const isViewingOtherUser = !!viewingUserId;

  const handleAcceptRequest = async (friendshipId, requesterId) => {
    await acceptRequest(friendshipId, requesterId);
    refreshFriends(); // Refresh friends list after accepting
  };

  const handleRemoveFriend = async () => {
    if (!friendToRemove) return;
    
    try {
      await friendService.removeFriend(friendToRemove.id);
      toast.success("Friend removed");
      refreshFriends();
      setFriendToRemove(null);
    } catch (error) {
      console.error("Error removing friend:", error);
      const errorMessage = error.response?.data?.detail || error.message || "Failed to remove friend";
      toast.error(errorMessage);
    }
  };

  const isAvatarWorld = worldMode === 'avatar';
  const otherUserDisplayName = isViewingOtherUser && otherUserInfo 
    ? (isAvatarWorld ? (otherUserInfo.avatar_name || otherUserInfo.name) : otherUserInfo.name)
    : null;
  const pageTitle = isViewingOtherUser 
    ? `${otherUserDisplayName || 'User'}'s ${isAvatarWorld ? 'Connections' : 'Friends'}`
    : (isAvatarWorld ? 'Connections' : 'Friends');
  const pageSubtitle = isViewingOtherUser
    ? `Viewing ${otherUserDisplayName || 'user'}'s connections`
    : (isAvatarWorld ? 'Manage your digital connections' : 'Manage your connections');

  return (
    <ImmersivePageWrapper pageId="friends" user={user}>
      <PageContainer 
        user={user} 
        currentPage="friends"
        backgroundClass="bg-transparent"
      >
      <div className="max-w-7xl mx-auto px-3 sm:px-4 md:px-6 py-4 sm:py-6 md:py-8 pb-20 sm:pb-8">
        <div className="mb-4 sm:mb-6 md:mb-8">
          {/* Back button when viewing other user's friends */}
          {isViewingOtherUser && (
            <Button
              variant="ghost"
              onClick={() => navigate(-1)}
              className="mb-2 -ml-2"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
          )}
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold gradient-text mb-1 sm:mb-2">{pageTitle}</h1>
          <p className="text-sm sm:text-base text-gray-600">{pageSubtitle}</p>
        </div>

        {/* Tabs for Friends and Requests - Hide requests when viewing other user */}
        <div className="flex gap-2 sm:gap-4 mb-4 sm:mb-6 border-b border-purple-200 overflow-x-auto hide-scrollbar-mobile">
          <button
            onClick={() => setActiveTab("friends")}
            className={`pb-2 sm:pb-3 px-3 sm:px-4 font-semibold transition-colors whitespace-nowrap text-sm sm:text-base min-h-[44px] ${
              activeTab === "friends"
                ? "text-purple-600 border-b-2 border-purple-600"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <Users className="w-4 h-4 inline mr-1 sm:mr-2" />
            {isAvatarWorld ? 'Connections' : 'Friends'} {friends.length > 0 && `(${friends.length})`}
          </button>
          {/* Only show requests tab for own friends page */}
          {!isViewingOtherUser && (
            <button
              onClick={() => setActiveTab("requests")}
              className={`pb-2 sm:pb-3 px-3 sm:px-4 font-semibold transition-colors relative whitespace-nowrap text-sm sm:text-base min-h-[44px] ${
                activeTab === "requests"
                  ? "text-purple-600 border-b-2 border-purple-600"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              <UserPlus className="w-4 h-4 inline mr-1 sm:mr-2" />
              <span className="hidden xs:inline">Friend </span>Requests
              {friendRequests.length > 0 && (
                <span className="ml-1 sm:ml-2 bg-red-500 text-white text-[10px] sm:text-xs rounded-full px-1.5 sm:px-2 py-0.5">
                  {friendRequests.length}
                </span>
              )}
            </button>
          )}
        </div>

        {loading ? (
          <LoadingSpinner message="Loading..." />
        ) : activeTab === "requests" ? (
          // Friend Requests Tab
          friendRequests.length === 0 ? (
            <Card className="glass-morphism p-6 sm:p-8 md:p-12 text-center">
              <div className="w-16 h-16 sm:w-20 sm:h-20 md:w-24 md:h-24 bg-gradient-to-br from-purple-200 to-purple-300 rounded-full flex items-center justify-center mx-auto mb-4 sm:mb-6">
                <UserPlus className="w-8 h-8 sm:w-10 sm:h-10 md:w-12 md:h-12 text-purple-600" />
              </div>
              <h3 className="text-lg sm:text-xl md:text-2xl font-bold text-gray-800 mb-2 sm:mb-3">No pending requests</h3>
              <p className="text-sm sm:text-base text-gray-600">You don't have any friend requests at the moment</p>
            </Card>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
              {friendRequests.map((request) => {
                const requester = request.requester || request.user || request;
                const displayName = isAvatarWorld 
                  ? (requester.avatar_name || requester.name)
                  : requester.name;
                const displayPicture = isAvatarWorld
                  ? (requester.avatar_picture || requester.picture)
                  : requester.picture;
                const displayBio = isAvatarWorld
                  ? (requester.avatar_bio || requester.bio)
                  : requester.bio;
                const requestId = request.friendship_id || request.id || request._id;
                const isProcessing = processing.has(requestId);
                
                return (
                  <Card
                    key={requestId}
                    className="glass-morphism p-4 sm:p-6 card-hover"
                  >
                    <div className="flex flex-col items-center text-center">
                      <Avatar className="w-16 h-16 sm:w-20 sm:h-20 md:w-24 md:h-24 border-3 sm:border-4 border-white shadow-lg mb-3 sm:mb-4">
                        <AvatarImage src={displayPicture} />
                        <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white text-lg sm:text-xl md:text-2xl">
                          {displayName?.charAt(0)}
                        </AvatarFallback>
                      </Avatar>
                      <h3 className="text-base sm:text-lg md:text-xl font-bold mb-1">{displayName}</h3>
                      <p className="text-xs sm:text-sm text-gray-600 mb-3 sm:mb-4 line-clamp-2">{displayBio}</p>
                      <div className="flex gap-2 w-full">
                        <Button
                          onClick={() => navigate(`/profile/${requester.id}`)}
                          variant="outline"
                          className="flex-1 border-2 border-purple-400 text-purple-700 hover:bg-purple-50 rounded-full text-xs sm:text-sm min-h-[44px]"
                        >
                          View Profile
                        </Button>
                      </div>
                      <div className="flex gap-2 w-full mt-2 sm:mt-3">
                        <Button
                          onClick={() => handleAcceptRequest(requestId, requester.id)}
                          disabled={isProcessing}
                          className="flex-1 bg-gradient-to-r from-green-500 to-green-600 text-white hover:from-green-600 hover:to-green-700 rounded-full text-xs sm:text-sm min-h-[44px]"
                        >
                          <Check className="w-4 h-4 mr-1 sm:mr-2" />
                          {isProcessing ? '...' : 'Accept'}
                        </Button>
                        <Button
                          onClick={() => declineRequest(requestId)}
                          disabled={isProcessing}
                          variant="outline"
                          className="border-2 border-red-400 text-red-600 hover:bg-red-50 rounded-full min-h-[44px] min-w-[44px]"
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          )
        ) : friends.length === 0 ? (
          <EmptyState.NoFriends
            action={{
              label: isAvatarWorld ? 'Discover Spirits' : 'Find Friends',
              onClick: () => navigate("/search")
            }}
          />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {friends.map((friend, idx) => {
              const displayName = isAvatarWorld 
                ? (friend.avatar_name || friend.name)
                : friend.name;
              const displayPicture = isAvatarWorld
                ? (friend.avatar_picture || friend.picture)
                : friend.picture;
              const displayBio = isAvatarWorld
                ? (friend.avatar_bio || friend.bio)
                : friend.bio;
              const displayInterests = isAvatarWorld
                ? (friend.avatar_interests || friend.interests || [])
                : (friend.interests || []);
              
              return (
                <Card
                  key={friend.id}
                  className="glass-morphism p-4 sm:p-6 card-hover friend-card"
                  data-testid={`friend-card-${idx}`}
                >
                  <div className="flex flex-col items-center text-center">
                    <Avatar className="w-16 h-16 sm:w-20 sm:h-20 md:w-24 md:h-24 border-3 sm:border-4 border-white shadow-lg mb-3 sm:mb-4">
                      <AvatarImage src={displayPicture} />
                      <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white text-lg sm:text-xl md:text-2xl">
                        {displayName?.charAt(0)}
                      </AvatarFallback>
                    </Avatar>
                    <h3 className="text-base sm:text-lg md:text-xl font-bold mb-1">{displayName}</h3>
                    {(friend.friend_type === 'ai_agent' || friend.is_ai_agent) && (
                      <span className="inline-flex items-center gap-1 text-[10px] sm:text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-semibold mb-1.5">
                        AI Agent {friend.agent_domain_label ? `· ${friend.agent_domain_label}` : ''}
                      </span>
                    )}
                    <p className="text-xs sm:text-sm text-gray-600 mb-2 sm:mb-3">
                      {friend.age} • {isAvatarWorld ? (friend.avatar_location || friend.location) : friend.location}
                    </p>
                    <p className="text-xs sm:text-sm text-gray-600 mb-3 sm:mb-4 line-clamp-2">{displayBio}</p>
                    {displayInterests && displayInterests.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 sm:gap-2 mb-3 sm:mb-4 justify-center">
                        {displayInterests.slice(0, 3).map((interest, i) => (
                          <span
                            key={i}
                            className="bg-yellow-100 text-purple-700 text-[10px] sm:text-xs px-1.5 sm:px-2 py-0.5 sm:py-1 rounded-full font-semibold"
                          >
                            {interest}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="flex gap-2 w-full">
                      <Button
                        onClick={() => navigate(`/profile/${friend.id}`)}
                        data-testid={`view-profile-${idx}`}
                        variant="outline"
                        className="flex-1 border-2 border-purple-400 text-purple-700 hover:bg-purple-50 rounded-full font-bold text-xs sm:text-sm min-h-[44px]"
                      >
                        <span className="hidden xs:inline">View </span>Profile
                      </Button>
                      {!isViewingOtherUser && (
                        <>
                          <Button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedFriend(friend);
                              setShowMessenger(true);
                            }}
                            data-testid={`message-friend-${idx}`}
                            className="bg-blue-500 hover:bg-blue-600 text-white rounded-full font-bold min-h-[44px] min-w-[44px] px-3"
                          >
                            <MessageCircle className="w-4 h-4" />
                          </Button>
                          <Button
                            onClick={(e) => {
                              e.stopPropagation();
                              e.preventDefault();
                              setFriendToRemove(friend);
                            }}
                            data-testid={`remove-friend-${idx}`}
                            variant="outline"
                            className="border-2 border-red-400 text-red-600 hover:bg-red-50 rounded-full font-bold min-h-[44px] min-w-[44px] px-3"
                          >
                            <UserMinus className="w-4 h-4" />
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Remove Friend Confirmation Dialog */}
      <ConfirmDialog
        open={friendToRemove !== null}
        onOpenChange={(open) => !open && setFriendToRemove(null)}
        title="Remove Friend"
        description={`Are you sure you want to remove ${friendToRemove ? (isAvatarWorld ? (friendToRemove.avatar_name || friendToRemove.name) : friendToRemove.name) : ''} from your friends?`}
        confirmLabel="Remove"
        cancelLabel="Cancel"
        onConfirm={handleRemoveFriend}
        variant="destructive"
      />

      {/* Side Messenger */}
      {showMessenger && selectedFriend && (
        <SideMessenger
          user={user}
          otherUserId={selectedFriend.id}
          otherUserData={selectedFriend}
          onClose={() => {
            setShowMessenger(false);
            setSelectedFriend(null);
          }}
        />
      )}
      </PageContainer>
    </ImmersivePageWrapper>
  );
};

export default FriendsPage;
