import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Users, MessageCircle, UserMinus, UserPlus, Check, X } from "lucide-react";
import { toast } from "sonner";
import { useWorldMode } from "@/contexts/WorldModeContext";
import { PageContainer } from "@/components/layout";
import { ConfirmDialog } from "@/components/common";
import { useFriends, useFriendRequests } from "@/features/friends";
import { friendService } from "@/services/api";
import SideMessenger from "@/components/SideMessenger";
import { LoadingSpinner, EmptyState } from "@/components/common";
import { ImmersivePageWrapper } from "@/components/ambient";

const FriendsPage = ({ user }) => {
  const navigate = useNavigate();
  const { worldMode } = useWorldMode();
  const [activeTab, setActiveTab] = useState("friends");
  const [showMessenger, setShowMessenger] = useState(false);
  const [selectedFriend, setSelectedFriend] = useState(null);
  const [friendToRemove, setFriendToRemove] = useState(null);

  // Use custom hooks
  const { friends, loading: friendsLoading, refresh: refreshFriends } = useFriends(worldMode);
  const { 
    friendRequests, 
    loading: requestsLoading, 
    processing,
    acceptRequest,
    declineRequest,
    refresh: refreshRequests
  } = useFriendRequests(worldMode);

  const loading = friendsLoading || requestsLoading;

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
  const pageTitle = isAvatarWorld ? 'Connections' : 'Friends';
  const pageSubtitle = isAvatarWorld ? 'Manage your digital connections' : 'Manage your connections';

  return (
    <ImmersivePageWrapper pageId="friends" user={user}>
      <PageContainer 
        user={user} 
        currentPage="friends"
        backgroundClass="bg-transparent"
      >
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold gradient-text mb-2">{pageTitle}</h1>
          <p className="text-gray-600">{pageSubtitle}</p>
        </div>

        {/* Tabs for Friends and Requests */}
        <div className="flex gap-4 mb-6 border-b border-purple-200">
          <button
            onClick={() => setActiveTab("friends")}
            className={`pb-3 px-4 font-semibold transition-colors ${
              activeTab === "friends"
                ? "text-purple-600 border-b-2 border-purple-600"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <Users className="w-4 h-4 inline mr-2" />
            {pageTitle} {friends.length > 0 && `(${friends.length})`}
          </button>
          <button
            onClick={() => setActiveTab("requests")}
            className={`pb-3 px-4 font-semibold transition-colors relative ${
              activeTab === "requests"
                ? "text-purple-600 border-b-2 border-purple-600"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <UserPlus className="w-4 h-4 inline mr-2" />
            Friend Requests
            {friendRequests.length > 0 && (
              <span className="ml-2 bg-red-500 text-white text-xs rounded-full px-2 py-0.5">
                {friendRequests.length}
              </span>
            )}
          </button>
        </div>

        {loading ? (
          <LoadingSpinner message="Loading..." />
        ) : activeTab === "requests" ? (
          // Friend Requests Tab
          friendRequests.length === 0 ? (
            <Card className="glass-morphism p-12 text-center">
              <div className="w-24 h-24 bg-gradient-to-br from-purple-200 to-purple-300 rounded-full flex items-center justify-center mx-auto mb-6">
                <UserPlus className="w-12 h-12 text-purple-600" />
              </div>
              <h3 className="text-2xl font-bold text-gray-800 mb-3">No pending requests</h3>
              <p className="text-gray-600">You don't have any friend requests at the moment</p>
            </Card>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
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
                    className="glass-morphism p-6 card-hover"
                  >
                    <div className="flex flex-col items-center text-center">
                      <Avatar className="w-24 h-24 border-4 border-white shadow-lg mb-4">
                        <AvatarImage src={displayPicture} />
                        <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white text-2xl">
                          {displayName?.charAt(0)}
                        </AvatarFallback>
                      </Avatar>
                      <h3 className="text-xl font-bold mb-1">{displayName}</h3>
                      <p className="text-sm text-gray-600 mb-4 line-clamp-2">{displayBio}</p>
                      <div className="flex gap-2 w-full">
                        <Button
                          onClick={() => navigate(`/profile/${requester.id}`)}
                          variant="outline"
                          className="flex-1 border-2 border-purple-400 text-purple-700 hover:bg-purple-50 rounded-full"
                        >
                          View Profile
                        </Button>
                      </div>
                      <div className="flex gap-2 w-full mt-3">
                        <Button
                          onClick={() => handleAcceptRequest(requestId, requester.id)}
                          disabled={isProcessing}
                          className="flex-1 bg-gradient-to-r from-green-500 to-green-600 text-white hover:from-green-600 hover:to-green-700 rounded-full"
                        >
                          <Check className="w-4 h-4 mr-2" />
                          {isProcessing ? 'Processing...' : 'Accept'}
                        </Button>
                        <Button
                          onClick={() => declineRequest(requestId)}
                          disabled={isProcessing}
                          variant="outline"
                          className="border-2 border-red-400 text-red-600 hover:bg-red-50 rounded-full"
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
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
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
                      {friend.age} • {isAvatarWorld ? (friend.avatar_location || friend.location) : friend.location}
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
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedFriend(friend);
                          setShowMessenger(true);
                        }}
                        data-testid={`message-friend-${idx}`}
                        className="bg-blue-500 hover:bg-blue-600 text-white rounded-full px-3 font-bold"
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
