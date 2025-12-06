/**
 * UserAvatar Component
 * Standardized avatar component with fallback and click handling
 */

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { useNavigate } from 'react-router-dom';
import { memo } from 'react';

const UserAvatar = memo(({ 
  user, 
  size = 'md', 
  showName = false,
  onClick,
  className = '',
  worldMode = 'real'
}) => {
  const navigate = useNavigate();

  const sizeClasses = {
    sm: 'w-7 h-7',
    md: 'w-10 h-10',
    lg: 'w-11 h-11',
    xl: 'w-16 h-16',
  };

  const textSizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
    xl: 'text-lg',
  };

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else if (user?.id) {
      navigate(`/profile/${user.id}`);
    }
  };

  const displayName = worldMode === 'avatar' 
    ? (user?.avatar_name || user?.name || '?')
    : (user?.name || '?');

  const displayPicture = worldMode === 'avatar'
    ? (user?.avatar_picture || user?.picture)
    : (user?.picture);

  const initials = displayName.charAt(0).toUpperCase();

  return (
    <div 
      className={`flex items-center gap-2 ${onClick || user?.id ? 'cursor-pointer' : ''} ${className}`}
      onClick={handleClick}
    >
      <Avatar className={sizeClasses[size]}>
        <AvatarImage src={displayPicture} alt={displayName} />
        <AvatarFallback className={`font-medium bg-blue-500 text-white ${textSizeClasses[size]}`}>
          {initials}
        </AvatarFallback>
      </Avatar>
      {showName && (
        <span className="font-medium text-gray-900">{displayName}</span>
      )}
    </div>
  );
});

UserAvatar.displayName = 'UserAvatar';

export default UserAvatar;

