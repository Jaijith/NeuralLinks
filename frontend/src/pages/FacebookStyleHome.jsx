import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useWorldMode } from "@/contexts/WorldModeContext";
import { PageContainer } from "@/components/layout";
import { LoadingSpinner } from "@/components/common";
import { CreatePostCard, CreatePostDialog } from "@/features/posts/components";
import { HomeSidebar, HomeRightSidebar, PostsFeed, useHomeFeed, usePostInteractions, useCreatePost } from "@/features/home";
import { friendService } from "@/services/api";
import { Sparkles } from "lucide-react";

// Custom CSS styles for the page - Light theme for avatar world
const customStyles = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
  
  /* Light theme styling for avatar world */
  .home-container,
  .home-container * {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    text-shadow: none !important;
    -webkit-font-smoothing: antialiased !important;
    -moz-osx-font-smoothing: grayscale !important;
    text-rendering: optimizeLegibility !important;
  }
  
  .glass-card {
    background: rgba(255, 255, 255, 0.95) !important;
    backdrop-filter: blur(20px);
    border: 1px solid rgba(0, 0, 0, 0.08);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08), 0 4px 24px rgba(0, 0, 0, 0.04);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }
  
  .glass-card:hover {
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12), 0 8px 32px rgba(0, 0, 0, 0.06);
    transform: translateY(-2px);
  }
  
  .post-card {
    animation: slideUp 0.5s ease-out forwards;
    opacity: 0;
  }
  
  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
`;

const FacebookStyleHome = ({ user: currentUser, setUser }) => {
  const navigate = useNavigate();
  const { worldMode } = useWorldMode();
  const isAvatarWorld = worldMode === 'avatar';

  // Use custom hooks
  const {
    posts,
    friends,
    loading,
    loadingMore,
    hasMore,
    loadMore,
    addPost
  } = useHomeFeed(worldMode, currentUser);

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
    postText,
    setPostText,
    selectedImage,
    imagePreview,
    uploading,
    showDialog,
    setShowDialog,
    handleImageSelect,
    handleRemoveImage,
    createPost,
    reset
  } = useCreatePost(worldMode, (newPost) => {
    addPost(newPost);
    // Update liked posts if needed
    if (newPost.liked_by && Array.isArray(newPost.liked_by) && newPost.liked_by.includes(currentUser?.id)) {
      updateLikedPosts([...Array.from(likedPosts), newPost.id]);
    }
  });

  // Update liked posts when posts change
  useEffect(() => {
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

  if (loading) {
    return (
      <>
        <style>{customStyles}</style>
        <PageContainer 
          user={currentUser} 
          setUser={setUser} 
          currentPage="home"
          showHeader={true}
        >
          <div className="min-h-[60vh] flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
              <p className="text-sm font-medium text-gray-600">
                {isAvatarWorld ? 'Entering Maya...' : 'Loading your feed...'}
              </p>
            </div>
          </div>
        </PageContainer>
      </>
    );
  }

  return (
    <>
      <style>{customStyles}</style>
      <PageContainer 
        user={currentUser} 
        setUser={setUser} 
        currentPage="home"
        showHeader={true}
      >
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="grid grid-cols-12 gap-6">
            
            {/* Left Sidebar */}
            <div className="col-span-3">
              <HomeSidebar 
                user={currentUser}
                worldMode={worldMode}
              />
            </div>

            {/* Main Feed */}
            <div className="col-span-6 space-y-4">
              {/* Create Post Card */}
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

              {/* Create Post Dialog */}
              <CreatePostDialog
                open={showDialog}
                onOpenChange={setShowDialog}
                user={currentUser}
                worldMode={worldMode}
                onPostCreated={(newPost) => {
                  addPost(newPost);
                  reset();
                }}
              />

              {/* Posts Feed */}
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
                onLoadMore={loadMore}
              />
            </div>

            {/* Right Sidebar */}
            <div className="col-span-3">
              <HomeRightSidebar 
                friends={friends}
                worldMode={worldMode}
              />
              
              {/* Footer Links */}
              <div className="text-xs space-y-2 px-2 text-gray-400 mt-6">
                <div className="flex flex-wrap gap-x-2 gap-y-1">
                  <span className="hover:underline cursor-pointer">Privacy</span>
                  <span>•</span>
                  <span className="hover:underline cursor-pointer">Terms</span>
                  <span>•</span>
                  <span className="hover:underline cursor-pointer">Help</span>
                </div>
                <p>© 2024 {isAvatarWorld ? 'Maya World' : 'NeuralLinks'}</p>
              </div>
            </div>
          </div>
        </div>
      </PageContainer>
    </>
  );
};

export default FacebookStyleHome;
