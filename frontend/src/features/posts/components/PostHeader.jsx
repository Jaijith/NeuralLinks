/**
 * PostHeader Component
 * Header section of a post with user info and timestamp
 */

import { Clock, Globe, MoreHorizontal, Bot, Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import UserAvatar from '@/components/common/UserAvatar';
import { formatTimeAgo } from '@/utils/dateUtils';
import { memo } from 'react';
import { useNavigate } from 'react-router-dom';

const PostHeader = memo(({ 
  post, 
  user,
  worldMode = 'real',
  currentUser,
  onUserClick,
  onMoreClick,
  onDelete,
  className = ''
}) => {
  const navigate = useNavigate();
  const displayName = worldMode === 'avatar'
    ? (post.author_avatar_name || post.user?.avatar_name || post.user?.name || 'Unknown')
    : (post.author_name || post.user?.name || 'Unknown');

  const displayPicture = worldMode === 'avatar'
    ? (post.author_avatar_picture || post.user?.avatar_picture || post.user?.picture)
    : (post.author_picture || post.user?.picture);

  const isBot = post.isBot || post.author_is_bot || post.user?.is_bot;
  
  const userId = post.user_id || post.user?.id;

  const handleUserClick = (e) => {
    e.stopPropagation();
    if (onUserClick) {
      onUserClick(userId);
    } else if (userId) {
      navigate(`/profile/${userId}`);
    }
  };

  return (
    <div className={`p-4 pb-2 ${className}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <UserAvatar
            user={{
              id: post.user_id || post.user?.id,
              name: displayName,
              picture: displayPicture,
              avatar_name: post.user?.avatar_name,
              avatar_picture: post.user?.avatar_picture,
              is_bot: isBot,
            }}
            size="lg"
            worldMode={worldMode}
          />
          <div>
            <div className="flex items-center gap-2">
              <span 
                className="font-semibold cursor-pointer hover:underline text-gray-900"
                onClick={handleUserClick}
              >
                {displayName}
              </span>
              {isBot && (
                <Badge className="text-xs px-1.5 py-0 border-0 bg-purple-100 text-purple-700">
                  <Bot className="w-3 h-3 mr-0.5" />
                  AI
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <Clock className="w-3 h-3" />
              <span>{formatTimeAgo(post.created_at)}</span>
              <span>•</span>
              <Globe className="w-3 h-3" />
            </div>
          </div>
        </div>
        {currentUser && currentUser.id === userId && onDelete && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="rounded-full p-1 h-8 w-8 hover:bg-gray-100 text-gray-600"
                aria-label="More options"
              >
                <MoreHorizontal className="w-5 h-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem
                onClick={() => onDelete(post.id)}
                className="text-red-600 hover:text-red-700 hover:bg-red-50 cursor-pointer focus:text-red-700 focus:bg-red-50"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete Post
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </div>
  );
});

PostHeader.displayName = 'PostHeader';

export default PostHeader;

