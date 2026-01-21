/**
 * PostCard Component
 * Complete post card with all sections
 * Supports both Maya (avatar) and Sense (real) worlds
 */

import { memo, useState } from 'react';
import PostHeader from './PostHeader';
import PostContent from './PostContent';
import PostEngagement from './PostEngagement';
import PostActions from './PostActions';
import CommentSection from './CommentSection';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

/**
 * @typedef {Object} PostCardProps
 * @property {Object} post - The post object
 * @property {Object} currentUser - Current logged-in user
 * @property {string} [worldMode] - Current world mode ('real' or 'avatar')
 * @property {boolean} [isLiked] - Whether the current user liked this post
 * @property {function} [onLike] - Handler for like action
 * @property {function} [onComment] - Handler for comment action
 * @property {function} [onShare] - Handler for share action
 * @property {function} [onUserClick] - Handler when user clicks on post author
 * @property {function} [onMoreClick] - Handler for more options
 * @property {function} [onDelete] - Handler for deleting a post
 * @property {Array} [comments] - Array of comments
 * @property {function} [onAddComment] - Handler for adding a comment
 * @property {boolean} [showComments] - Whether to show comments section
 * @property {function} [onToggleComments] - Handler to toggle comments visibility
 * @property {string} [className] - Additional CSS classes
 * @property {Object} [style] - Additional inline styles
 */

const PostCard = memo(({ 
  post,
  currentUser,
  worldMode = 'real',
  isLiked = false,
  onLike,
  onComment,
  onShare,
  onUserClick,
  onMoreClick,
  onDelete,
  comments = [],
  onAddComment,
  showComments = false,
  onToggleComments,
  className = '',
  style = {}
}) => {
  const [localComments, setLocalComments] = useState(comments);

  const handleAddComment = async (postId, text) => {
    if (onAddComment) {
      const newComment = await onAddComment(postId, text);
      if (newComment) {
        setLocalComments(prev => [...prev, newComment]);
      }
    }
  };

  const displayComments = localComments.length > 0 ? localComments : comments;

  return (
    <Card 
      className={cn("rounded-xl overflow-hidden post-card glass-card", className)}
      style={style}
    >
      <PostHeader
        post={post}
        user={post.user}
        worldMode={worldMode}
        currentUser={currentUser}
        onUserClick={onUserClick}
        onMoreClick={onMoreClick}
        onDelete={onDelete}
      />

      <PostContent post={post} />

      <PostEngagement
        post={post}
        onLikesClick={onLike}
        onCommentsClick={onToggleComments || onComment}
      />

      <PostActions
        postId={post.id}
        isLiked={isLiked}
        onLike={onLike}
        onComment={onToggleComments || onComment}
        onShare={onShare}
      />

      {showComments && (
        <CommentSection
          postId={post.id}
          comments={displayComments}
          currentUser={currentUser}
          onAddComment={handleAddComment}
          onUserClick={onUserClick}
        />
      )}
    </Card>
  );
});

PostCard.displayName = 'PostCard';

export default PostCard;

