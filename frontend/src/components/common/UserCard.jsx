import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Bot, MessageCircle, UserMinus, UserPlus, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * @typedef {Object} UserCardProps
 * @property {Object} user - The user object
 * @property {string} user.id - User ID
 * @property {string} user.name - User's real name
 * @property {string} [user.avatar_name] - User's avatar name
 * @property {string} [user.picture] - User's profile picture URL
 * @property {string} [user.avatar_picture] - User's avatar picture URL
 * @property {string} [user.bio] - User's bio
 * @property {boolean} [user.isBot] - Whether the user is a bot
 * @property {string} [worldMode] - Current world mode ('real' or 'avatar')
 * @property {boolean} [showActions] - Whether to show action buttons
 * @property {Array<{label: string, onClick: function, icon: Component, variant?: string}>} [actions] - Action buttons to display
 * @property {function} [onClick] - Click handler for the card
 * @property {string} [className] - Additional CSS classes
 * @property {boolean} [clickable] - Whether the card is clickable (default: true)
 */

/**
 * Reusable User Card component for displaying user information consistently across pages.
 * @param {UserCardProps} props
 */
const UserCard = React.memo(({ 
  user, 
  worldMode = 'real',
  showActions = false,
  actions = [],
  onClick,
  className,
  clickable = true
}) => {
  const navigate = useNavigate();
  const isAvatarWorld = worldMode === 'avatar';
  
  const displayName = isAvatarWorld 
    ? (user.avatar_name || user.name)
    : user.name;
  const displayPicture = isAvatarWorld
    ? (user.avatar_picture || user.picture)
    : user.picture;

  const handleClick = () => {
    if (clickable && user.id) {
      if (onClick) {
        onClick(user);
      } else {
        navigate(`/profile/${user.id}`);
      }
    }
  };

  return (
    <Card 
      className={cn(
        "p-4 transition-all hover:shadow-md",
        clickable && "cursor-pointer",
        className
      )}
      onClick={handleClick}
    >
      <div className="flex items-center gap-3">
        <Avatar className="w-12 h-12">
          <AvatarImage src={displayPicture} alt={displayName} />
          <AvatarFallback className="bg-blue-500 text-white font-semibold">
            {displayName?.charAt(0) || '?'}
          </AvatarFallback>
        </Avatar>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-gray-900 truncate">
              {displayName || 'Unknown User'}
            </h3>
            {user.isBot && (
              <Badge className="text-xs px-1.5 py-0 border-0 bg-purple-100 text-purple-700">
                <Bot className="w-3 h-3 mr-0.5" />
                AI
              </Badge>
            )}
          </div>
          {user.bio && (
            <p className="text-sm text-gray-600 truncate mt-0.5">
              {user.bio}
            </p>
          )}
        </div>

        {showActions && actions.length > 0 && (
          <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
            {actions.map((action, idx) => {
              const Icon = action.icon;
              return (
                <Button
                  key={idx}
                  variant={action.variant || "ghost"}
                  size="sm"
                  onClick={action.onClick}
                  className="h-8 w-8 p-0"
                  aria-label={action.label}
                >
                  <Icon className="w-4 h-4" />
                </Button>
              );
            })}
          </div>
        )}

        {clickable && !showActions && (
          <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
        )}
      </div>
    </Card>
  );
});

UserCard.displayName = "UserCard";

export default UserCard;

