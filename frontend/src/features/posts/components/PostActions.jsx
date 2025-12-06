/**
 * PostActions Component
 * Action buttons for posts (Like, Comment, Share)
 */

import { MessageCircle, Share2 } from 'lucide-react';
import { toast } from 'sonner';
import LikeButton from './LikeButton';
import { memo } from 'react';

const PostActions = memo(({ 
  postId,
  isLiked,
  onLike,
  onComment,
  onShare
}) => {
  const handleShare = () => {
    if (onShare) {
      onShare();
    } else if (navigator.share) {
      navigator.share({
        title: 'Check out this post!',
        url: window.location.href,
      }).catch(() => {
        // User cancelled or error
      });
    } else {
      toast.info('Share feature coming soon!');
    }
  };

  return (
    <div className="px-2 py-1.5 border-t border-gray-200">
      <div className="flex items-center justify-around">
        <LikeButton
          postId={postId}
          isLiked={isLiked}
          onClick={onLike}
        />
        <button
          onClick={() => onComment?.(postId)}
          className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg transition-all hover:bg-gray-100 text-gray-700"
          aria-label="Comment on this post"
        >
          <MessageCircle className="w-4 h-4" />
          <span className="font-medium text-sm">Comment</span>
        </button>
        <button
          onClick={handleShare}
          className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg transition-all hover:bg-gray-100 text-gray-700"
          aria-label="Share this post"
        >
          <Share2 className="w-4 h-4" />
          <span className="font-medium text-sm">Share</span>
        </button>
      </div>
    </div>
  );
});

PostActions.displayName = 'PostActions';

export default PostActions;

