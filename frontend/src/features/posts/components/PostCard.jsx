/**
 * PostCard Component
 * Complete post card with all sections
 */

import { memo, useState } from 'react';
import PostHeader from './PostHeader';
import PostContent from './PostContent';
import PostEngagement from './PostEngagement';
import PostActions from './PostActions';
import CommentSection from './CommentSection';

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
    <div 
      className={`rounded-xl overflow-hidden post-card glass-card ${className}`}
      style={style}
    >
      <PostHeader
        post={post}
        user={post.user}
        worldMode={worldMode}
        onMoreClick={onMoreClick}
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
    </div>
  );
});

PostCard.displayName = 'PostCard';

export default PostCard;

