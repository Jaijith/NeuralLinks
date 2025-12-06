import React from 'react';
import { PostCard, LikesDialog } from '@/features/posts/components';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/common';
import { Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';

/**
 * @typedef {Object} PostsFeedProps
 * @property {Array} posts - Array of post objects
 * @property {Object} currentUser - Current logged-in user
 * @property {string} [worldMode] - Current world mode ('real' or 'avatar')
 * @property {Set} likedPosts - Set of post IDs that user has liked
 * @property {function} onLike - Handler for like action
 * @property {function} onShowLikes - Handler for showing likes
 * @property {function} onShowComments - Handler for showing comments
 * @property {function} onAddComment - Handler for adding comment
 * @property {Object} commentsData - Comments data by post ID
 * @property {string} showingCommentsFor - Post ID for which comments are shown
 * @property {string} showingLikesFor - Post ID for which likes are shown
 * @property {boolean} hasMore - Whether there are more posts to load
 * @property {boolean} loadingMore - Whether more posts are loading
 * @property {function} onLoadMore - Handler for loading more posts
 * @property {string} [className] - Additional CSS classes
 */

/**
 * Posts Feed component for displaying a list of posts.
 * Supports both Maya (avatar) and Sense (real) worlds.
 */
const PostsFeed = React.memo(({
  posts = [],
  currentUser,
  worldMode = 'real',
  likedPosts = new Set(),
  onLike,
  onShowLikes,
  onShowComments,
  onAddComment,
  commentsData = {},
  showingCommentsFor,
  showingLikesFor,
  hasMore = false,
  loadingMore = false,
  onLoadMore,
  className
}) => {
  const navigate = useNavigate();
  const isAvatarWorld = worldMode === 'avatar';

  if (posts.length === 0) {
    return (
      <EmptyState
        icon={Search}
        title={isAvatarWorld ? 'Welcome to Maya' : 'Welcome to your feed!'}
        description={isAvatarWorld 
          ? 'Connect with other digital spirits and share your thoughts'
          : 'Start by adding friends or creating your first post'
        }
        action={{
          label: isAvatarWorld ? 'Discover Spirits' : 'Find Friends',
          onClick: () => navigate('/search')
        }}
      />
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      {posts.map((post, idx) => {
        const isLiked = likedPosts.has(post.id);
        const showComments = showingCommentsFor === post.id;
        const comments = commentsData[post.id] || post.comments || [];

        return (
          <PostCard
            key={post.id || idx}
            post={post}
            currentUser={currentUser}
            worldMode={worldMode}
            isLiked={isLiked}
            onLike={() => onLike(post.id, isLiked)}
            onComment={() => onShowComments(post.id)}
            onShowLikes={() => onShowLikes(post.id)}
            comments={comments}
            onAddComment={onAddComment}
            showComments={showComments}
            onToggleComments={() => onShowComments(post.id)}
            style={{ animationDelay: `${idx * 0.05}s` }}
          />
        );
      })}

      {/* Load More Button */}
      {hasMore && (
        <div className="flex justify-center py-6">
          <Button
            onClick={onLoadMore}
            disabled={loadingMore}
            variant="outline"
            className="px-8 py-2"
          >
            {loadingMore ? (
              <>
                <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin mr-2"></div>
                Loading...
              </>
            ) : (
              'Load More Posts'
            )}
          </Button>
        </div>
      )}

      {/* Likes Dialog */}
      <LikesDialog
        open={showingLikesFor !== null}
        onOpenChange={(open) => !open && onShowLikes(null)}
        postId={showingLikesFor}
        worldMode={worldMode}
      />
    </div>
  );
});

PostsFeed.displayName = "PostsFeed";

export default PostsFeed;

