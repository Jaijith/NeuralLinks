/**
 * LikeButton Component
 * Reusable like button with state management
 */

import { ThumbsUp } from 'lucide-react';
import { memo } from 'react';
import useViewMode from '@/hooks/useViewMode';

const LikeButton = memo(({ 
  postId, 
  isLiked, 
  likesCount = 0,
  onClick,
  showCount = false,
  variant = 'button' // 'button' or 'icon'
}) => {
  const { isImmersive } = useViewMode();
  
  const handleClick = (e) => {
    e.stopPropagation();
    if (onClick) {
      onClick(postId);
    }
  };

  if (variant === 'icon') {
    return (
      <button
        onClick={handleClick}
        className={`flex items-center gap-1.5 hover:underline text-sm ${isImmersive ? 'text-gray-400' : 'text-gray-600'}`}
        aria-label={`${isLiked ? 'Unlike' : 'Like'} this post`}
      >
        {likesCount > 0 && (
          <>
            <div className="w-5 h-5 rounded-full flex items-center justify-center bg-blue-500">
              <ThumbsUp className="w-3 h-3 text-white fill-white" />
            </div>
            {showCount && <span>{likesCount}</span>}
          </>
        )}
      </button>
    );
  }

  return (
    <button
      onClick={handleClick}
      className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg transition-all ${isImmersive ? 'hover:bg-slate-800' : 'hover:bg-gray-100'}`}
      style={{ color: isLiked ? '#3b82f6' : (isImmersive ? '#d1d5db' : '#4b5563') }}
      aria-label={`${isLiked ? 'Unlike' : 'Like'} this post`}
    >
      <ThumbsUp className={`w-4 h-4 ${isLiked ? 'fill-current' : ''}`} />
      <span className="font-medium text-sm">Like</span>
    </button>
  );
});

LikeButton.displayName = 'LikeButton';

export default LikeButton;

