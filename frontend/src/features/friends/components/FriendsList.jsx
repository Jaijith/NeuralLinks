import React from 'react';
import { useNavigate } from 'react-router-dom';
import { UserListItem } from '@/components/common';
import { MessageCircle, UserMinus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/common';
import { cn } from '@/lib/utils';

/**
 * @typedef {Object} FriendsListProps
 * @property {Array} friends - Array of friend objects
 * @property {string} [worldMode] - Current world mode ('real' or 'avatar')
 * @property {function} [onMessage] - Handler for message action
 * @property {function} [onRemove] - Handler for remove action
 * @property {boolean} [loading] - Whether the list is loading
 * @property {number} [maxItems] - Maximum number of items to display
 * @property {string} [className] - Additional CSS classes
 */

/**
 * Friends List component for displaying a list of friends consistently.
 * Supports both Maya (avatar) and Sense (real) worlds.
 * @param {FriendsListProps} props
 */
const FriendsList = React.memo(({ 
  friends = [],
  worldMode = 'real',
  onMessage,
  onRemove,
  loading = false,
  maxItems,
  className
}) => {
  const navigate = useNavigate();
  const isAvatarWorld = worldMode === 'avatar';

  const displayFriends = maxItems ? friends.slice(0, maxItems) : friends;

  const handleMessage = (friend) => {
    if (onMessage) {
      onMessage(friend);
    } else {
      // Default: navigate to chat or open messenger
      navigate(`/chat/${friend.id}`);
    }
  };

  const handleRemove = (friend) => {
    if (onRemove) {
      onRemove(friend);
    }
  };

  if (loading) {
    return (
      <div className={cn("space-y-2", className)}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 bg-gray-200 animate-pulse rounded-lg" />
        ))}
      </div>
    );
  }

  if (displayFriends.length === 0) {
    return (
      <EmptyState.NoFriends
        action={{
          label: isAvatarWorld ? 'Discover Spirits' : 'Find Friends',
          onClick: () => navigate('/search')
        }}
        variant="minimal"
      />
    );
  }

  return (
    <div className={cn("space-y-1", className)}>
      {displayFriends.map((friend) => (
        <UserListItem
          key={friend.id}
          user={friend}
          worldMode={worldMode}
          action={
            <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
              {onMessage && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleMessage(friend)}
                  className="h-8 w-8 p-0"
                  aria-label="Message"
                >
                  <MessageCircle className="w-4 h-4" />
                </Button>
              )}
              {onRemove && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleRemove(friend)}
                  className="h-8 w-8 p-0 text-red-600 hover:text-red-700 hover:bg-red-50"
                  aria-label="Remove friend"
                >
                  <UserMinus className="w-4 h-4" />
                </Button>
              )}
            </div>
          }
        />
      ))}
    </div>
  );
});

FriendsList.displayName = "FriendsList";

export default FriendsList;

