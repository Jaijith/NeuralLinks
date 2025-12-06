import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Check, X, Eye } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * @typedef {Object} FriendRequestCardProps
 * @property {Object} request - The friend request object
 * @property {string} request.id - Request ID (friendship ID)
 * @property {Object} request.user - The user who sent the request
 * @property {string} request.user.id - User ID
 * @property {string} request.user.name - User's real name
 * @property {string} [request.user.avatar_name] - User's avatar name
 * @property {string} [request.user.picture] - User's profile picture URL
 * @property {string} [request.user.avatar_picture] - User's avatar picture URL
 * @property {string} [worldMode] - Current world mode ('real' or 'avatar')
 * @property {function} onAccept - Handler for accept action
 * @property {function} onDecline - Handler for decline action
 * @property {function} [onViewProfile] - Handler for view profile action
 * @property {boolean} [loading] - Whether actions are loading
 * @property {string} [className] - Additional CSS classes
 */

/**
 * Reusable Friend Request Card component for displaying friend requests consistently.
 * @param {FriendRequestCardProps} props
 */
const FriendRequestCard = React.memo(({ 
  request, 
  worldMode = 'real',
  onAccept,
  onDecline,
  onViewProfile,
  loading = false,
  className
}) => {
  const navigate = useNavigate();
  const isAvatarWorld = worldMode === 'avatar';
  
  const user = request.user || request;
  const displayName = isAvatarWorld 
    ? (user.avatar_name || user.name)
    : user.name;
  const displayPicture = isAvatarWorld
    ? (user.avatar_picture || user.picture)
    : user.picture;

  const handleViewProfile = () => {
    if (onViewProfile) {
      onViewProfile(user);
    } else if (user.id) {
      navigate(`/profile/${user.id}`);
    }
  };

  const handleAccept = (e) => {
    e.stopPropagation();
    if (onAccept) {
      onAccept(request.id || request._id, user.id);
    }
  };

  const handleDecline = (e) => {
    e.stopPropagation();
    if (onDecline) {
      onDecline(request.id || request._id);
    }
  };

  return (
    <Card 
      className={cn(
        "p-4 transition-all hover:shadow-md",
        className
      )}
    >
      <div className="flex items-center gap-3">
        <div 
          className="cursor-pointer"
          onClick={handleViewProfile}
        >
          <Avatar className="w-12 h-12">
            <AvatarImage src={displayPicture} alt={displayName} />
            <AvatarFallback className="bg-blue-500 text-white font-semibold">
              {displayName?.charAt(0) || '?'}
            </AvatarFallback>
          </Avatar>
        </div>
        
        <div className="flex-1 min-w-0">
          <h3 
            className="font-semibold text-gray-900 truncate cursor-pointer hover:underline"
            onClick={handleViewProfile}
          >
            {displayName || 'Unknown User'}
          </h3>
          <p className="text-sm text-gray-600 mt-0.5">
            sent you a friend request
          </p>
        </div>

        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
          <Button
            variant="outline"
            size="sm"
            onClick={handleAccept}
            disabled={loading}
            className="h-8 px-3 bg-green-50 hover:bg-green-100 text-green-700 border-green-200"
            aria-label="Accept request"
          >
            <Check className="w-4 h-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDecline}
            disabled={loading}
            className="h-8 px-3 bg-red-50 hover:bg-red-100 text-red-700 border-red-200"
            aria-label="Decline request"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </Card>
  );
});

FriendRequestCard.displayName = "FriendRequestCard";

export default FriendRequestCard;

