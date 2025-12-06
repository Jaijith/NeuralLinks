import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { MessageCircle, UserMinus, Eye } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * @typedef {Object} FriendCardProps
 * @property {Object} friend - The friend object
 * @property {string} friend.id - Friend ID
 * @property {string} friend.name - Friend's real name
 * @property {string} [friend.avatar_name] - Friend's avatar name
 * @property {string} [friend.picture] - Friend's profile picture URL
 * @property {string} [friend.avatar_picture] - Friend's avatar picture URL
 * @property {string} [worldMode] - Current world mode ('real' or 'avatar')
 * @property {function} [onMessage] - Handler for message action
 * @property {function} [onRemove] - Handler for remove action
 * @property {function} [onViewProfile] - Handler for view profile action
 * @property {string} [className] - Additional CSS classes
 */

/**
 * Reusable Friend Card component for displaying friends consistently.
 * @param {FriendCardProps} props
 */
const FriendCard = React.memo(({ 
  friend, 
  worldMode = 'real',
  onMessage,
  onRemove,
  onViewProfile,
  className
}) => {
  const navigate = useNavigate();
  const isAvatarWorld = worldMode === 'avatar';
  
  const displayName = isAvatarWorld 
    ? (friend.avatar_name || friend.name)
    : friend.name;
  const displayPicture = isAvatarWorld
    ? (friend.avatar_picture || friend.picture)
    : friend.picture;

  const handleViewProfile = () => {
    if (onViewProfile) {
      onViewProfile(friend);
    } else if (friend.id) {
      navigate(`/profile/${friend.id}`);
    }
  };

  const handleMessage = (e) => {
    e.stopPropagation();
    if (onMessage) {
      onMessage(friend);
    }
  };

  const handleRemove = (e) => {
    e.stopPropagation();
    if (onRemove) {
      onRemove(friend);
    }
  };

  return (
    <Card 
      className={cn(
        "p-4 transition-all hover:shadow-md cursor-pointer",
        className
      )}
      onClick={handleViewProfile}
    >
      <div className="flex items-center gap-3">
        <Avatar className="w-12 h-12">
          <AvatarImage src={displayPicture} alt={displayName} />
          <AvatarFallback className="bg-blue-500 text-white font-semibold">
            {displayName?.charAt(0) || '?'}
          </AvatarFallback>
        </Avatar>
        
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 truncate">
            {displayName || 'Unknown User'}
          </h3>
        </div>

        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
          {onMessage && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleMessage}
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
              onClick={handleRemove}
              className="h-8 w-8 p-0 text-red-600 hover:text-red-700 hover:bg-red-50"
              aria-label="Remove friend"
            >
              <UserMinus className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
});

FriendCard.displayName = "FriendCard";

export default FriendCard;

