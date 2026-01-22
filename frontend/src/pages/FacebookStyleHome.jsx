import { useState, useEffect, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useWorldMode } from "@/contexts/WorldModeContext";
import { PageContainer } from "@/components/layout";
import { LoadingSpinner } from "@/components/common";
import { CreatePostCard, CreatePostDialog } from "@/features/posts/components";
import { HomeSidebar, HomeRightSidebar, PostsFeed, useHomeFeed, usePostInteractions, useCreatePost } from "@/features/home";
import { friendService, postService } from "@/services/api";
import { Sparkles } from "lucide-react";
import { toast } from "sonner";
import axios from "axios";

// Ambient components
import { 
  Atmosphere, 
  ImmersiveBackground,
  WhisperText, 
  SpiritTrail, 
  AnchorOrb, 
  VoidInput,
  ViewModeToggle,
  AvatarResponseOverlay
} from "@/components/ambient";
import useAvatarState from "@/hooks/useAvatarState";
import useViewMode from "@/hooks/useViewMode";
import { chatService } from "@/services/api/workflowService";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

// Generate aggressive CSS for the mode
const getGlobalStyles = (isImmersive) => {
  if (isImmersive) {
    return `
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
      
      /* IMMERSIVE MODE - Override CSS variables */
      #maya-home-container {
        --card: 12 15 25;
        --card-foreground: 255 255 255;
        --background: transparent;
        --foreground: 255 255 255;
        --muted: 30 35 50;
        --muted-foreground: 200 200 220;
        --border: 255 255 255;
      }
      
      #maya-home-container * {
        font-family: 'Inter', sans-serif !important;
      }
      
      /* Target Card component and all card-like elements */
      #maya-home-container .bg-card,
      #maya-home-container [class*="bg-card"],
      #maya-home-container .glass-card,
      #maya-home-container .rounded-lg,
      #maya-home-container .rounded-xl,
      #maya-home-container .rounded-2xl,
      #maya-home-container .rounded-md,
      #maya-home-container .shadow,
      #maya-home-container .shadow-sm,
      #maya-home-container .shadow-md,
      #maya-home-container .shadow-lg,
      #maya-home-container .border,
      #maya-home-container [class*="shadow"],
      #maya-home-container .bg-white,
      #maya-home-container [class*="bg-white"] {
        background: rgba(12, 15, 25, 0.88) !important;
        backdrop-filter: blur(16px) saturate(1.3) !important;
        -webkit-backdrop-filter: blur(16px) saturate(1.3) !important;
        border-color: rgba(255, 255, 255, 0.1) !important;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.5) !important;
      }
      
      /* Text white - but EXCLUDE colored backgrounds and special components */
      #maya-home-container,
      #maya-home-container div:not([class*="bg-yellow"]):not([class*="bg-green"]):not([class*="bg-red"]):not([class*="bg-blue"]):not([class*="bg-purple"]):not([class*="bg-pink"]):not([class*="bg-orange"]):not([class*="bg-gradient"]):not([class*="from-"]):not(.memory-orb-page):not(.memory-orb-page *),
      #maya-home-container p:not([class*="text-white"]):not(.memory-orb-page *),
      #maya-home-container span:not([class*="bg-"]):not([class*="text-white"]):not(.memory-orb-page *),
      #maya-home-container h1:not(.memory-orb-page *), #maya-home-container h2:not(.memory-orb-page *), #maya-home-container h3:not(.memory-orb-page *),
      #maya-home-container h4:not(.memory-orb-page *), #maya-home-container h5:not(.memory-orb-page *), #maya-home-container h6:not(.memory-orb-page *),
      #maya-home-container a:not([class*="bg-"]):not(.memory-orb-page *),
      #maya-home-container label:not(.memory-orb-page *),
      #maya-home-container li:not(.memory-orb-page *) {
        color: rgba(255, 255, 255, 0.9) !important;
      }
      
      /* PRESERVE MemoryOrb component's own styling */
      #maya-home-container .memory-orb-page,
      #maya-home-container .memory-orb-page * {
        color: inherit !important;
      }
      
      #maya-home-container .memory-orb-page .stat-bars,
      #maya-home-container .memory-orb-page .memory-panel {
        background: rgba(255, 255, 255, 0.95) !important;
      }
      
      #maya-home-container .memory-orb-page .stat-label {
        color: #1f2937 !important;
      }
      
      #maya-home-container .memory-orb-page svg {
        color: inherit !important;
      }
      
      /* Buttons - only non-colored */
      #maya-home-container button:not([class*="bg-"]):not([class*="btn-"]) {
        color: rgba(255, 255, 255, 0.85) !important;
      }
      
      /* PRESERVE colors on badges and colored elements */
      #maya-home-container [class*="bg-yellow"] *,
      #maya-home-container [class*="bg-green"] *,
      #maya-home-container [class*="bg-purple-100"] *,
      #maya-home-container [class*="bg-blue-100"] *,
      #maya-home-container [class*="bg-gradient"] *,
      #maya-home-container [class*="from-pink"] *,
      #maya-home-container [class*="from-purple"] * {
        color: inherit !important;
      }
      
      /* Keep badge backgrounds */
      #maya-home-container [class*="bg-yellow-100"],
      #maya-home-container [class*="bg-purple-100"],
      #maya-home-container [class*="bg-green-100"],
      #maya-home-container [class*="bg-blue-100"] {
        background-color: inherit !important;
      }
      
      /* Muted text - only for non-colored elements */
      #maya-home-container .text-muted-foreground:not([class*="bg-"]),
      #maya-home-container .text-gray-400:not([class*="bg-"]),
      #maya-home-container .text-gray-500:not([class*="bg-"]),
      #maya-home-container .text-gray-600:not([class*="bg-"]) {
        color: rgba(255, 255, 255, 0.65) !important;
      }
      
      /* Inputs */
      #maya-home-container input,
      #maya-home-container textarea,
      #maya-home-container select {
        background: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: rgba(255, 255, 255, 0.9) !important;
      }
      
      #maya-home-container input::placeholder,
      #maya-home-container textarea::placeholder {
        color: rgba(255, 255, 255, 0.4) !important;
      }
      
      /* Borders */
      #maya-home-container .border,
      #maya-home-container [class*="border-gray"],
      #maya-home-container [class*="divide-gray"] > * {
        border-color: rgba(255, 255, 255, 0.1) !important;
      }
      
      /* Background utilities */
      #maya-home-container .bg-gray-50,
      #maya-home-container .bg-gray-100,
      #maya-home-container [class*="bg-gray-"],
      #maya-home-container .bg-muted,
      #maya-home-container [class*="bg-muted"] {
        background: rgba(255, 255, 255, 0.05) !important;
      }
      
      /* SVG/Icons */
      #maya-home-container svg {
        color: rgba(255, 255, 255, 0.7) !important;
      }
      
      /* Animation */
      .post-card {
        animation: slideUp 0.5s ease-out forwards;
        opacity: 0;
      }
      
      @keyframes slideUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
      }
    `;
  } else {
    return `
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
      
      /* CLASSIC MODE */
      #maya-home-container * {
        font-family: 'Inter', sans-serif !important;
      }
      
      /* Light glass cards */
      #maya-home-container .bg-card,
      #maya-home-container .glass-card,
      #maya-home-container .rounded-lg,
      #maya-home-container .rounded-xl,
      #maya-home-container .rounded-2xl,
      #maya-home-container .rounded-md,
      #maya-home-container .shadow,
      #maya-home-container [class*="shadow"],
      #maya-home-container .bg-white,
      #maya-home-container [class*="bg-white"] {
        background: rgba(255, 255, 255, 0.95) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border-color: rgba(0, 0, 0, 0.08) !important;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08) !important;
      }
      
      /* Dark text */
      #maya-home-container,
      #maya-home-container div,
      #maya-home-container p,
      #maya-home-container span,
      #maya-home-container h1, #maya-home-container h2, #maya-home-container h3,
      #maya-home-container h4, #maya-home-container h5, #maya-home-container h6,
      #maya-home-container a,
      #maya-home-container label,
      #maya-home-container li,
      #maya-home-container button,
      #maya-home-container .text-card-foreground,
      #maya-home-container .text-foreground {
        color: rgba(0, 0, 0, 0.85) !important;
      }
      
      /* Muted text */
      #maya-home-container .text-muted-foreground,
      #maya-home-container .text-gray-400,
      #maya-home-container .text-gray-500,
      #maya-home-container .text-gray-600 {
        color: rgba(0, 0, 0, 0.55) !important;
      }
      
      /* SVG/Icons */
      #maya-home-container svg {
        color: rgba(0, 0, 0, 0.6) !important;
      }
      
      /* Animation */
      .post-card {
        animation: slideUp 0.5s ease-out forwards;
        opacity: 0;
      }
      
      @keyframes slideUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
      }
    `;
  }
};

const FacebookStyleHome = ({ user: currentUser, setUser }) => {
  const navigate = useNavigate();
  const { worldMode } = useWorldMode();
  const isAvatarWorld = worldMode === 'avatar';
  
  // View mode toggle (Classic vs Immersive) - only for avatar world
  const { isImmersive, toggleViewMode } = useViewMode();

  // Ambient state from backend (only in avatar world)
  const {
    mood,
    energy_level,
    social_desire,
    creative_urge,
    current_state,
    colors,
    whisperText,
    presenceIntensity,
    pulseSpeed,
    sendUserEvent,
    isLoading: avatarStateLoading
  } = useAvatarState(isAvatarWorld ? currentUser?.id : null);

  // Void input state
  const [showVoidInput, setShowVoidInput] = useState(false);
  const [customWhisper, setCustomWhisper] = useState(null);
  const [interests, setInterests] = useState([]);
  const [avatarResponse, setAvatarResponse] = useState(null);
  const [showResponse, setShowResponse] = useState(false);
  const [chatSessionId, setChatSessionId] = useState(null);
  
  // Initialize chat session when user is available
  useEffect(() => {
    if (isAvatarWorld && currentUser?.id && !chatSessionId) {
      chatService.createSession(currentUser.id)
        .then(session => {
          setChatSessionId(session.session_id);
        })
        .catch(err => {
          console.error('Failed to create chat session:', err);
        });
    }
  }, [isAvatarWorld, currentUser?.id, chatSessionId]);

  // Fetch user interests for spirit trail text particles
  useEffect(() => {
    if (isAvatarWorld && currentUser?.id) {
      axios.get(`${BACKEND_URL}/api/users/${currentUser.id}/avatar`)
        .then(res => {
          const avatar = res.data;
          if (avatar?.interests) {
            setInterests(avatar.interests.slice(0, 10));
          }
        })
        .catch(() => {});
    }
  }, [currentUser?.id, isAvatarWorld]);

  // Spacebar triggers void input (only in avatar world)
  useEffect(() => {
    if (!isAvatarWorld) return;
    
    const handleKeyDown = (e) => {
      // Don't trigger if user is typing in an input
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
        return;
      }
      
      if (e.code === 'Space' && !showVoidInput) {
        e.preventDefault();
        setShowVoidInput(true);
        sendUserEvent?.('input_started');
      }
      
      if (e.code === 'Escape' && showVoidInput) {
        setShowVoidInput(false);
        sendUserEvent?.('input_cancelled');
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showVoidInput, isAvatarWorld, sendUserEvent]);

  // Handle void input submission - use chatService for proper AI responses
  const handleVoidSubmit = useCallback(async (message) => {
    if (!message.trim()) return;
    
    // Show thinking whisper
    setCustomWhisper("THINKING...");
    setShowVoidInput(false);
    
    try {
      // Ensure we have a chat session
      let sessionId = chatSessionId;
      if (!sessionId && currentUser?.id) {
        const session = await chatService.createSession(currentUser.id);
        sessionId = session.session_id;
        setChatSessionId(sessionId);
      }
      
      if (!sessionId) {
        throw new Error('No chat session available');
      }
      
      // Use chatService for proper AI response
      const response = await chatService.sendMessage(sessionId, message);
      
      if (response.success && response.avatar_response) {
        setCustomWhisper("...");
        
        // Format response for overlay
        const formattedResponse = {
          success: true,
          cards: [{
            type: response.intent || 'general_chat',
            content: response.avatar_response
          }],
          detected_intent: response.intent,
          new_mood: response.mood_after || 'neutral',
          metrics: response.metrics || {}
        };
        
        // Short delay then show response
        setTimeout(() => {
          setAvatarResponse(formattedResponse);
          setShowResponse(true);
          setCustomWhisper(null);
        }, 500);
      } else {
        setCustomWhisper("HEARD");
        setTimeout(() => setCustomWhisper(null), 2000);
      }
    } catch (err) {
      console.error('Failed to send void input:', err);
      setCustomWhisper("...");
      setTimeout(() => setCustomWhisper(null), 2000);
    }
  }, [currentUser?.id, chatSessionId]);
  
  // Handle response overlay close
  const handleResponseClose = useCallback(() => {
    setShowResponse(false);
    setAvatarResponse(null);
  }, []);

  // Handle orb activation
  const handleOrbActivate = useCallback(() => {
    setShowVoidInput(true);
    sendUserEvent?.('input_started');
  }, [sendUserEvent]);

  // Use custom hooks
  const {
    posts,
    friends,
    loading,
    loadingMore,
    hasMore,
    loadMore,
    addPost,
    removePost
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

  // Handle delete post
  const handleDeletePost = async (postId) => {
    try {
      await postService.deletePost(postId);
      // Remove post from local state
      removePost(postId);
      toast.success("Post deleted successfully");
    } catch (error) {
      console.error("Error deleting post:", error);
      toast.error("Failed to delete post");
    }
  };

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

  // Determine the mode class
  const modeClass = isAvatarWorld && isImmersive ? 'immersive-mode' : 'classic-mode';

  if (loading) {
    return (
      <>
        <style>{getGlobalStyles(isAvatarWorld && isImmersive)}</style>
        <div id="maya-home-container" className={modeClass}>
          {/* Ambient presence while loading */}
          {isAvatarWorld && isImmersive && (
            <ImmersiveBackground 
              colors={colors} 
              energy={energy_level} 
              presenceIntensity={presenceIntensity} 
            />
          )}
          {isAvatarWorld && !isImmersive && (
            <Atmosphere 
              mood={mood} 
              energy={energy_level} 
              colors={colors} 
              presenceIntensity={presenceIntensity} 
            />
          )}
          <PageContainer 
            user={currentUser} 
            setUser={setUser} 
            currentPage="home"
            showHeader={true}
            backgroundClass={isAvatarWorld && isImmersive ? "bg-transparent" : "bg-gradient-to-br from-blue-50 via-white to-slate-50"}
          >
            <div className="min-h-[60vh] flex items-center justify-center relative z-10">
              <div className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                  <Sparkles className="w-8 h-8 text-white" />
                </div>
                <p className={`text-sm font-medium ${isImmersive ? 'text-white/70' : 'text-gray-600'}`}>
                  {isAvatarWorld ? 'Entering Maya...' : 'Loading your feed...'}
                </p>
              </div>
            </div>
          </PageContainer>
        </div>
      </>
    );
  }

  return (
    <>
      <style>{getGlobalStyles(isAvatarWorld && isImmersive)}</style>
      <div id="maya-home-container" className={modeClass}>
        {/* === BACKGROUND LAYERS (Avatar World Only) === */}
        {isAvatarWorld && (
          <>
            {/* Immersive: Space/cosmic background */}
            {isImmersive && (
              <ImmersiveBackground 
                colors={colors} 
                energy={energy_level} 
                presenceIntensity={presenceIntensity} 
              />
            )}
            
            {/* Classic: Subtle edge glows */}
            {!isImmersive && (
              <Atmosphere 
                mood={mood} 
                energy={energy_level} 
                colors={colors} 
                presenceIntensity={presenceIntensity} 
              />
            )}
            
            {/* Presence indicator (both modes) */}
            <WhisperText 
              text={customWhisper || whisperText}
              mood={mood}
              colors={colors}
              isInputActive={showVoidInput}
            />
            
            {/* Ghost mouse trail (both modes, subtle) */}
            <SpiritTrail 
              colors={colors}
              energy={energy_level}
              interests={interests}
            />
          </>
        )}
        
        {/* === MAIN CONTENT === */}
        <PageContainer 
          user={currentUser} 
          setUser={setUser} 
          currentPage="home"
          showHeader={true}
          backgroundClass={isAvatarWorld && isImmersive ? "bg-transparent" : "bg-gradient-to-br from-blue-50 via-white to-slate-50"}
        >
          <div className="max-w-7xl mx-auto px-4 py-6 relative z-10">
            {/* View Mode Toggle - only in Avatar World */}
            {isAvatarWorld && (
              <div className="flex justify-end mb-4">
                <ViewModeToggle 
                  isImmersive={isImmersive}
                  onToggle={toggleViewMode}
                  colors={colors}
                />
              </div>
            )}
            
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
                  onDelete={handleDeletePost}
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
                <div className={`text-xs space-y-2 px-2 mt-6 ${isImmersive ? 'text-white/40' : 'text-gray-400'}`}>
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
        
        {/* === LIVING SPIRIT ORB (Avatar World Only) === */}
        {isAvatarWorld && (
          <>
            {/* The magical anchor orb - always present */}
            <AnchorOrb 
              colors={colors}
              pulseSpeed={pulseSpeed}
              onActivate={handleOrbActivate}
              presenceIntensity={presenceIntensity}
            />
            
            {/* Void Input - triggered by spacebar or orb click */}
            <VoidInput 
              isActive={showVoidInput}
              onSubmit={handleVoidSubmit}
              onClose={() => {
                setShowVoidInput(false);
                sendUserEvent?.('input_cancelled');
              }}
              colors={colors}
            />
            
            {/* Avatar Response Overlay */}
            <AvatarResponseOverlay
              isVisible={showResponse}
              response={avatarResponse}
              onClose={handleResponseClose}
              colors={colors}
              autoCloseDelay={10000}
            />
          </>
        )}
      </div>
    </>
  );
};

export default FacebookStyleHome;
