/**
 * CommentItem Component
 * Individual comment display component
 */

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { formatTimeAgo } from '@/utils/dateUtils';
import { memo } from 'react';

const CommentItem = memo(({ comment, onUserClick }) => {
  if (!comment || typeof comment !== 'object') return null;

  const userName = comment.user_name || 'Unknown';
  const userPicture = comment.user_picture || '';
  const text = comment.text || '';
  const createdAt = comment.created_at;

  return (
    <div className="flex gap-2">
      <Avatar 
        className="w-7 h-7 cursor-pointer"
        onClick={() => onUserClick?.(comment.user_id)}
      >
        <AvatarImage src={userPicture} alt={userName} />
        <AvatarFallback>{userName.charAt(0).toUpperCase()}</AvatarFallback>
      </Avatar>
      <div className="flex-1 rounded-2xl px-4 py-2.5 bg-white">
        <p 
          className="text-sm font-semibold text-gray-900 cursor-pointer hover:underline"
          onClick={() => onUserClick?.(comment.user_id)}
        >
          {userName}
        </p>
        <p className="text-sm text-gray-700 whitespace-pre-wrap">{text}</p>
        {createdAt && (
          <p className="text-xs mt-1 text-gray-500">
            {formatTimeAgo(createdAt)}
          </p>
        )}
      </div>
    </div>
  );
});

CommentItem.displayName = 'CommentItem';

export default CommentItem;

