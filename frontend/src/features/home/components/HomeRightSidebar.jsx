import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Sidebar, SidebarSection } from '@/components/layout';
import { UserListItem } from '@/components/common';
import { Button } from '@/components/ui/button';
import { Plus, Search } from 'lucide-react';
import { friendService } from '@/services/api';
import { useState, useEffect, useCallback } from 'react';
import { toast as sonnerToast } from 'sonner';

/**
 * @typedef {Object} HomeRightSidebarProps
 * @property {Array} friends - Friends list
 * @property {string} [worldMode] - Current world mode ('real' or 'avatar')
 * @property {function} [onSendFriendRequest] - Handler for sending friend requests
 */

/**
 * Home Right Sidebar component with Friends and Suggested users.
 * Supports both Maya (avatar) and Sense (real) worlds.
 */
const HomeRightSidebar = React.memo(({ friends = [], worldMode = 'real', onSendFriendRequest }) => {
  const navigate = useNavigate();
  const isAvatarWorld = worldMode === 'avatar';
  const [suggestedUsers, setSuggestedUsers] = useState([]);
  const [sendingRequests, setSendingRequests] = useState(new Set());

  useEffect(() => {
    fetchSuggestedUsers();
  }, [worldMode]);

  const fetchSuggestedUsers = useCallback(async () => {
    try {
      const response = await friendService.getSuggestions(5, worldMode);
      setSuggestedUsers(response.suggestions || response || []);
    } catch (error) {
      console.error("Error fetching suggested users:", error);
    }
  }, [worldMode]);

  const handleSendFriendRequest = useCallback(async (userId) => {
    if (!userId) return;
    if (sendingRequests.has(userId)) return;

    setSendingRequests(prev => new Set(prev).add(userId));
    try {
      await friendService.sendFriendRequest(userId);
      sonnerToast.success("Friend request sent!");
      fetchSuggestedUsers(); // Refresh suggestions
      if (onSendFriendRequest) {
        onSendFriendRequest(userId);
      }
    } catch (error) {
      console.error("Error sending friend request:", error);
      const errorMessage = error.response?.data?.detail || error.message || "Failed to send friend request";
      sonnerToast.error(errorMessage);
    } finally {
      setSendingRequests(prev => {
        const next = new Set(prev);
        next.delete(userId);
        return next;
      });
    }
  }, [sendingRequests, onSendFriendRequest, fetchSuggestedUsers]);

  return (
    <Sidebar>
      {/* Friends List */}
      {friends.length > 0 && (
        <SidebarSection 
          title={isAvatarWorld ? 'Connections' : 'Friends'}
          headerAction={
            <button 
              onClick={() => navigate('/friends')}
              className="text-xs font-medium hover:opacity-80 text-blue-600"
            >
              See all
            </button>
          }
        >
          <div className="space-y-1">
            {friends.slice(0, 6).map((friend) => (
              <UserListItem
                key={friend.id}
                user={friend}
                worldMode={worldMode}
              />
            ))}
          </div>
        </SidebarSection>
      )}

      {/* Suggested Users */}
      <SidebarSection title={isAvatarWorld ? 'Discover Spirits' : 'Suggested for you'}>
        <div className="space-y-3">
          {suggestedUsers.length > 0 ? (
            suggestedUsers.map((user) => (
              <div 
                key={user.id}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer"
                onClick={() => navigate(`/profile/${user.id}`)}
              >
                <Avatar className="w-10 h-10">
                  <AvatarImage src={user.picture} />
                  <AvatarFallback className="bg-gradient-to-br from-purple-500 to-pink-500 text-white text-sm">
                    {user.name?.charAt(0) || '?'}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-gray-900 truncate">
                    {user.name}
                  </p>
                  {user.mutual_connections > 0 ? (
                    <p className="text-xs text-gray-600">
                      {user.mutual_connections} {user.mutual_connections === 1 ? 'mutual connection' : 'mutual connections'}
                    </p>
                  ) : (
                    <p className="text-xs text-gray-500">
                      {isAvatarWorld ? 'Digital Spirit' : 'New to the network'}
                    </p>
                  )}
                </div>
                <Button 
                  size="sm"
                  variant="outline"
                  className="rounded-full text-xs border-violet-300 text-violet-600 hover:bg-violet-50 flex-shrink-0"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSendFriendRequest(user.id);
                  }}
                  disabled={sendingRequests.has(user.id)}
                >
                  <Plus className="w-3 h-3 mr-1" />
                  {sendingRequests.has(user.id) ? 'Sending...' : 'Add'}
                </Button>
              </div>
            ))
          ) : (
            <div className="text-center py-4">
              <p className="text-sm text-gray-500">
                {isAvatarWorld ? 'No spirits to discover yet' : 'No suggestions available'}
              </p>
              <Button
                size="sm"
                variant="ghost"
                className="mt-2 text-xs text-violet-600 hover:text-violet-700"
                onClick={() => navigate('/search')}
              >
                <Search className="w-3 h-3 mr-1" />
                Search users
              </Button>
            </div>
          )}
        </div>
      </SidebarSection>
    </Sidebar>
  );
});

HomeRightSidebar.displayName = "HomeRightSidebar";

export default HomeRightSidebar;

