import React from 'react';
import { CreatePostCard, CreatePostDialog, PostCard, LikesDialog } from '@/features/posts/components';
import { usePostInteractions, useCreatePost } from '@/features/home';
import { PostsFeed } from '@/features/home/components';
import { Card } from '@/components/ui/card';
import { EmptyState } from '@/components/common';

/**
 * @typedef {Object} ProfilePostsTabProps
 * @property {Array} posts - Array of post objects
 * @property {Object} currentUser - Current logged-in user
 * @property {Object} profileUser - Profile user object
 * @property {boolean} isOwnProfile - Whether this is the current user's own profile
 * @property {string} [worldMode] - Current world mode ('real' or 'avatar')
 * @property {boolean} hasMore - Whether there are more posts to load
 * @property {boolean} loadingMore - Whether more posts are loading
 * @property {function} onLoadMore - Handler for loading more posts
 * @property {function} onPostCreated - Callback when a post is created
 * @property {function} onPostDeleted - Callback when a post is deleted
 */

/**
 * Profile Posts Tab component for displaying posts on a profile page.
 * Supports both Maya (avatar) and Sense (real) worlds.
 */
const ProfilePostsTab = React.memo(({
  posts = [],
  currentUser,
  profileUser,
  isOwnProfile,
  worldMode = 'real',
  hasMore = false,
  loadingMore = false,
  onLoadMore,
  onPostCreated,
  onPostDeleted
}) => {
  const {
    likedPosts,
    showingLikesFor,
    showingCommentsFor,
    commentsData,
    handleLikePost,
    showLikes,
    showComments,
    handleAddComment,
    updateLikedPosts,
    setShowingLikesFor,
    setShowingCommentsFor
  } = usePostInteractions();

  const {
    showDialog,
    setShowDialog,
    createPost,
    reset
  } = useCreatePost(worldMode, (newPost) => {
    if (onPostCreated) {
      onPostCreated(newPost);
    }
    reset();
  });

  // Update liked posts when posts change
  React.useEffect(() => {
    if (posts.length > 0 && currentUser) {
      const likedSet = new Set();
      posts.forEach(post => {
        if (post.liked_by && Array.isArray(post.liked_by) && post.liked_by.includes(currentUser.id)) {
          likedSet.add(post.id);
        }
      });
      updateLikedPosts(Array.from(likedSet));
    }
  }, [posts, currentUser?.id]);

  return (
    <div className="space-y-4">
      {/* Create Post (Own Profile Only) */}
      {isOwnProfile && (
        <>
          <CreatePostCard
            user={currentUser}
            worldMode={worldMode}
            onCreateClick={() => setShowDialog(true)}
            onPhotoClick={() => {
              setShowDialog(true);
              setTimeout(() => {
                document.getElementById('post-image-upload')?.click();
              }, 100);
            }}
          />
          <CreatePostDialog
            open={showDialog}
            onOpenChange={setShowDialog}
            user={currentUser}
            worldMode={worldMode}
            onPostCreated={(newPost) => {
              if (onPostCreated) {
                onPostCreated(newPost);
              }
              reset();
            }}
          />
        </>
      )}

      {/* Posts Feed */}
      {posts.length > 0 ? (
        <PostsFeed
          posts={posts}
          currentUser={currentUser}
          worldMode={worldMode}
          likedPosts={likedPosts}
          onLike={handleLikePost}
          onShowLikes={showLikes}
          onShowComments={showComments}
          onAddComment={handleAddComment}
          commentsData={commentsData}
          showingCommentsFor={showingCommentsFor}
          showingLikesFor={showingLikesFor}
          hasMore={hasMore}
          loadingMore={loadingMore}
          onLoadMore={onLoadMore}
        />
      ) : (
        <Card className="p-12 text-center">
          <EmptyState
            title={isOwnProfile ? "No posts yet" : "No posts"}
            description={isOwnProfile 
              ? "Start sharing your thoughts!"
              : "This user hasn't posted anything yet"
            }
            variant="minimal"
          />
        </Card>
      )}
    </div>
  );
});

ProfilePostsTab.displayName = "ProfilePostsTab";

export default ProfilePostsTab;
