import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Bot, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * @typedef {Object} UserListItemProps
 * @property {Object} user - The user object
 * @property {string} user.id - User ID
 * @property {string} user.name - User's real name
 * @property {string} [user.avatar_name] - User's avatar name
 * @property {string} [user.picture] - User's profile picture URL
 * @property {string} [user.avatar_picture] - User's avatar picture URL
 * @property {boolean} [user.isBot] - Whether the user is a bot
 * @property {string} [worldMode] - Current world mode ('real' or 'avatar')
 * @property {React.ReactNode} [action] - Optional action button/element to display on the right
 * @property {function} [onClick] - Click handler for the list item
 * @property {string} [className] - Additional CSS classes
 * @property {string} [size] - Size variant ('sm' | 'md' | 'lg')
 */

/**
 * Reusable User List Item component for displaying users in lists consistently.
 * @param {UserListItemProps} props
 */
const UserListItem = React.memo(({ 
  user, 
  worldMode = 'real',
  action,
  onClick,
  className,
  size = 'md'
}) => {
  const navigate = useNavigate();
  const isAvatarWorld = worldMode === 'avatar';
  
  const displayName = isAvatarWorld 
    ? (user.avatar_name || user.name)
    : user.name;
  const displayPicture = isAvatarWorld
    ? (user.avatar_picture || user.picture)
    : user.picture;

  const sizeClasses = {
    sm: { avatar: 'w-8 h-8', text: 'text-sm' },
    md: { avatar: 'w-10 h-10', text: 'text-base' },
    lg: { avatar: 'w-12 h-12', text: 'text-lg' }
  };

  const handleClick = () => {
    if (user.id) {
      if (onClick) {
        onClick(user);
      } else {
        navigate(`/profile/${user.id}`);
      }
    }
  };

  return (
    <div 
      className={cn(
        "flex items-center gap-3 p-2 rounded-lg transition-colors cursor-pointer hover:bg-gray-100",
        className
      )}
      onClick={handleClick}
    >
      <Avatar className={sizeClasses[size].avatar}>
        <AvatarImage src={displayPicture} alt={displayName} />
        <AvatarFallback className="bg-blue-500 text-white text-sm">
          {displayName?.charAt(0) || '?'}
        </AvatarFallback>
      </Avatar>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={cn("font-medium text-gray-900 truncate", sizeClasses[size].text)}>
            {displayName || 'Unknown User'}
          </span>
          {user.friend_type === 'ai_agent' || user.is_ai_agent ? (
            <Badge className="text-xs px-1.5 py-0 border-0 bg-emerald-100 text-emerald-700">
              <Sparkles className="w-3 h-3 mr-0.5" />
              AI Agent
            </Badge>
          ) : user.isBot || user.is_bot ? (
            <Badge className="text-xs px-1.5 py-0 border-0 bg-purple-100 text-purple-700">
              <Bot className="w-3 h-3 mr-0.5" />
              AI
            </Badge>
          ) : null}
        </div>
      </div>

      {action && (
        <div onClick={(e) => e.stopPropagation()}>
          {action}
        </div>
      )}
    </div>
  );
});

UserListItem.displayName = "UserListItem";

export default UserListItem;

