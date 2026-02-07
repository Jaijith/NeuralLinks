/**
 * PostEngagement Component
 * Engagement stats (likes and comments count)
 */

import { ThumbsUp } from 'lucide-react';
import { memo } from 'react';
import useViewMode from '@/hooks/useViewMode';

const PostEngagement = memo(({ 
  post, 
  onLikesClick,
  onCommentsClick
}) => {
  const { isImmersive } = useViewMode();
  const likesCount = post.likes || 0;
  const commentsCount = post.comment_count || post.comments?.length || 0;
  const hasEngagement = likesCount > 0 || commentsCount > 0;

  if (!hasEngagement) return null;

  return (
    <div className={`px-4 py-2 flex items-center justify-between text-sm ${isImmersive ? 'text-gray-400' : 'text-gray-600'}`}>
      {likesCount > 0 && (
        <button
          onClick={() => onLikesClick?.(post.id)}
          className="flex items-center gap-1.5 hover:underline"
          aria-label={`${likesCount} like${likesCount !== 1 ? 's' : ''}`}
        >
          <div className="w-5 h-5 rounded-full flex items-center justify-center bg-blue-500">
            <ThumbsUp className="w-3 h-3 text-white fill-white" />
          </div>
          <span>{likesCount}</span>
        </button>
      )}
      {commentsCount > 0 && (
        <button
          onClick={() => onCommentsClick?.(post.id)}
          className={`hover:underline ${isImmersive ? 'text-gray-400' : 'text-gray-600'}`}
          aria-label={`${commentsCount} comment${commentsCount !== 1 ? 's' : ''}`}
        >
          {commentsCount} comment{commentsCount !== 1 ? 's' : ''}
        </button>
      )}
    </div>
  );
});

PostEngagement.displayName = 'PostEngagement';

export default PostEngagement;

