import { useState, useEffect, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useWorldMode } from "@/contexts/WorldModeContext";
import { PageContainer } from "@/components/layout";
import { LoadingSpinner } from "@/components/common";
import { CreatePostCard, CreatePostDialog } from "@/features/posts/components";
import { HomeSidebar, HomeRightSidebar, PostsFeed, useHomeFeed, usePostInteractions, useCreatePost } from "@/features/home";
import { friendService, postService } from "@/services/api";
import { Sparkles, X } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import axios from "axios";
import AvatarStoriesRow from "@/components/AvatarStoriesRow";

// Ambient components
import { 
  Atmosphere, 
  ImmersiveBackground,
  WhisperText, 
  SpiritTrail, 
  VoidInput,
  AvatarResponseOverlay,
  VoiceAgent
} from "@/components/ambient";
import useAvatarState from "@/hooks/useAvatarState";
import useViewMode from "@/hooks/useViewMode";
import useSwipeNavigation from "@/hooks/useSwipeNavigation";
import { chatService } from "@/services/api/workflowService";
// prewarmContext is now handled in the VoiceAgent component

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

// Generate aggressive CSS for the mode
const getGlobalStyles = (isImmersive) => {
  // Mobile responsive styles - always included
  const mobileStyles = `
    /* MOBILE SIDEBAR HIDING - Force hide sidebars below 1024px */
    @media (max-width: 1023px) {
      #maya-home-container aside,
      #maya-home-container [data-sidebar="left"],
      #maya-home-container [data-sidebar="right"] {
        display: none !important;
      }
      
      #maya-home-container main {
        width: 100% !important;
        max-width: 100% !important;
      }
    }
    
    /* Desktop grid layout */
    @media (min-width: 1024px) {
      #maya-home-container aside,
      #maya-home-container [data-sidebar="left"],
      #maya-home-container [data-sidebar="right"] {
        display: block !important;
      }
    }
  `;

  if (isImmersive) {
    return `
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
      
      ${mobileStyles}
      
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
        background: rgba(12, 15, 25, 0.70) !important;
        border-color: rgba(255, 255, 255, 0.08) !important;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4) !important;
      }
      
      /* Sticky top cards (stories, create post) - slightly more opaque for readability */
      #maya-home-container .sticky .rounded-lg,
      #maya-home-container .sticky .rounded-xl,
      #maya-home-container .sticky .rounded-2xl,
      #maya-home-container .sticky .shadow,
      #maya-home-container .sticky .shadow-sm,
      #maya-home-container .sticky .border,
      #maya-home-container .sticky [class*="shadow"],
      #maya-home-container .sticky .bg-white,
      #maya-home-container .sticky [class*="bg-white"],
      #maya-home-container .sticky [class*="bg-card"] {
        background: rgba(12, 15, 25, 0.80) !important;
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
      
    `;
  } else {
    return `
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
      
      ${mobileStyles}
      
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
    `;
  }
};

const FacebookStyleHome = ({ user: currentUser, setUser }) => {
  const navigate = useNavigate();
  const { worldMode } = useWorldMode();
  const isAvatarWorld = worldMode === 'avatar';
  
  // View mode toggle (Classic vs Immersive) - only for avatar world
  const { isImmersive, toggleViewMode } = useViewMode();

  // Swipe navigation for PWA (Home ↔ Profile)
  useSwipeNavigation({ enabled: true, threshold: 80 });

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
  
  // Voice mode state - voice is the PRIMARY interaction method
  const [showVoiceAgent, setShowVoiceAgent] = useState(false);
  
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

  // Spacebar triggers voice session (only in avatar world)
  useEffect(() => {
    if (!isAvatarWorld) return;
    
    const handleKeyDown = (e) => {
      // Don't trigger if user is typing in an input
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
        return;
      }
      
      // Spacebar - start voice session
      if (e.code === 'Space' && !showVoidInput && !showVoiceAgent) {
        e.preventDefault();
        setShowVoiceAgent(true);
        setCustomWhisper("CONNECTING...");
        sendUserEvent?.('voice_started');
      }
      
      // T key - open text input instead
      if (e.code === 'KeyT' && !showVoidInput && !showVoiceAgent) {
        e.preventDefault();
        setShowVoidInput(true);
        setCustomWhisper("TYPE...");
        sendUserEvent?.('input_started');
      }
      
      if (e.code === 'Escape') {
        if (showVoidInput) {
          setShowVoidInput(false);
          sendUserEvent?.('input_cancelled');
        }
        if (showVoiceAgent) {
          setShowVoiceAgent(false);
          setCustomWhisper(null);
        }
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showVoidInput, showVoiceAgent, isAvatarWorld, sendUserEvent]);

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
  
  // Handle voice agent close
  const handleVoiceClose = useCallback(() => {
    setShowVoiceAgent(false);
    setCustomWhisper(null);
  }, []);
  
  // Handle voice transcript for display
  const handleVoiceTranscript = useCallback((data) => {
    if (data.type === 'ai') {
      setCustomWhisper(null);
    } else if (data.type === 'user') {
      setCustomWhisper("THINKING...");
    }
  }, []);

  // Use custom hooks
  const {
    posts,
    friends,
    loading,
    loadingMore,
    hasMore,
    loadMore,
    addPost,
    removePost,
    updatePost
  } = useHomeFeed(worldMode, currentUser);

  // Edit post state
  const [editingPost, setEditingPost] = useState(null);
  const [editedPostText, setEditedPostText] = useState('');

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

  // Handle edit post - opens edit dialog
  const handleEditPost = (post) => {
    setEditingPost(post);
    setEditedPostText(post.content || post.text || '');
  };

  // Handle save edited post
  const handleSaveEditedPost = async () => {
    if (!editingPost || !editedPostText.trim()) return;
    
    try {
      const updatedPost = await postService.updatePost(editingPost.id, {
        text: editedPostText.trim(),
        post_type: worldMode === 'avatar' ? 'avatar' : 'real'
      });
      
      // Update post in local state
      updatePost(editingPost.id, {
        content: editedPostText.trim(),
        text: editedPostText.trim(),
        ...updatedPost
      });
      
      toast.success("Post updated successfully");
      setEditingPost(null);
      setEditedPostText('');
    } catch (error) {
      console.error("Error updating post:", error);
      toast.error("Failed to update post");
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
          {/* Mobile bottom nav padding + responsive container */}
          <div className="max-w-7xl mx-auto px-0 sm:px-4 pt-0 sm:pt-4 pb-20 sm:pb-6 relative z-10 -mt-4 sm:mt-0">
            {/* Desktop: 3-column grid | Mobile: Single column feed only */}
            <div className="lg:grid lg:grid-cols-12 lg:gap-6">
              
              {/* Left Sidebar - DESKTOP ONLY (hidden via CSS media query) */}
              <aside className="lg:col-span-3" data-sidebar="left">
                <div className="lg:sticky lg:top-20">
                  <HomeSidebar 
                    user={currentUser}
                    worldMode={worldMode}
                  />
                </div>
              </aside>

              {/* Main Feed - Always visible, full width on mobile */}
              <main className="w-full lg:col-span-6">
                {/* Sticky Top Section - Stories + Create Post (All screen sizes) */}
                <div 
                  className="sticky z-30 -mx-3 sm:mx-0 pb-3 sm:pb-4 pt-0 sm:pt-1"
                  style={{
                    top: 'calc(3.5rem + env(safe-area-inset-top, 0px))',
                    background: isImmersive 
                      ? 'rgba(10, 15, 30, 0.90)'
                      : 'rgba(245, 247, 250, 0.90)',
                  }}
                >
                  {/* Friends Stories Row - Both worlds, full width on mobile */}
                  <AvatarStoriesRow 
                    currentUser={currentUser}
                    className={`rounded-none sm:rounded-xl mb-2 sm:mb-3 ${isImmersive ? '' : 'bg-white/90 shadow-sm'}`}
                    style={isImmersive ? { 
                      backgroundColor: 'rgba(12, 15, 25, 0.90)',
                      border: '1px solid rgba(255,255,255,0.06)',
                    } : undefined}
                  />
                  
                  {/* Create Post Card - Wider on mobile, 80% opacity in immersive */}
                  <div style={isImmersive ? { 
                    '--card-bg': 'rgba(12, 15, 25, 0.80)',
                  } : undefined}>
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
                      onOrbClick={worldMode === 'avatar' ? () => {
                        // Trigger voice session
                        setShowVoiceAgent(true);
                        setCustomWhisper("CONNECTING...");
                      } : undefined}
                      onSearchClick={() => navigate('/search')}
                      placeholder={worldMode === 'avatar' ? "Share your Maya moments." : "Share your Sense moments."}
                      mood={mood}
                      energyLevel={energy_level}
                      className="w-full !rounded-none sm:!rounded-xl"
                    />
                  </div>
                </div>
                
                {/* Posts Feed with top spacing to prevent overlap */}
                <div className="mt-3 sm:mt-4 space-y-3 sm:space-y-4 px-3 sm:px-0">
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
                  onEdit={handleEditPost}
                  commentsData={commentsData}
                  showingCommentsFor={showingCommentsFor}
                  showingLikesFor={showingLikesFor}
                  hasMore={hasMore}
                  loadingMore={loadingMore}
                  onLoadMore={loadMore}
                />
                </div>
              </main>

              {/* Right Sidebar - DESKTOP ONLY (hidden via CSS media query) */}
              <aside className="lg:col-span-3" data-sidebar="right">
                <div className="lg:sticky lg:top-20">
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
              </aside>
            </div>
          </div>
        </PageContainer>
        
        {/* === VOICE & INPUT OVERLAYS (Avatar World Only) === */}
        {isAvatarWorld && (
          <>
            {/* Voice Agent Overlay - Real-time voice interaction */}
            <VoiceAgent
              isActive={showVoiceAgent}
              onClose={handleVoiceClose}
              colors={colors}
              avatarId={currentUser?.id}
              settingPreset="low_latency"
              onTranscript={handleVoiceTranscript}
            />
            
            {/* Void Input - triggered by T key */}
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
        
        {/* Edit Post Dialog */}
        <Dialog open={editingPost !== null} onOpenChange={(open) => !open && setEditingPost(null)}>
          <DialogContent 
            className="max-w-lg rounded-2xl border"
            style={{ 
              backgroundColor: (isAvatarWorld && isImmersive) ? 'rgba(10, 15, 30, 0.98)' : '#ffffff',
              borderColor: (isAvatarWorld && isImmersive) ? 'rgba(71, 85, 105, 0.4)' : '#e2e8f0',
            }}
          >
            <DialogHeader>
              <DialogTitle style={{ color: (isAvatarWorld && isImmersive) ? '#e2e8f0' : undefined }}>Edit Post</DialogTitle>
            </DialogHeader>
            <div className="py-4">
              <Textarea
                value={editedPostText}
                onChange={(e) => setEditedPostText(e.target.value)}
                placeholder="What's on your mind?"
                className="min-h-[150px] resize-none rounded-xl"
                style={{ 
                  backgroundColor: (isAvatarWorld && isImmersive) ? 'rgba(30, 35, 55, 0.8)' : '#ffffff',
                  borderColor: (isAvatarWorld && isImmersive) ? 'rgba(71, 85, 105, 0.5)' : '#d1d5db',
                  color: (isAvatarWorld && isImmersive) ? '#e2e8f0' : '#1e293b',
                }}
                autoFocus
              />
            </div>
            <DialogFooter className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setEditingPost(null);
                  setEditedPostText('');
                }}
                className={(isAvatarWorld && isImmersive) ? 'border-slate-600 text-slate-300 hover:bg-slate-800' : ''}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSaveEditedPost}
                disabled={!editedPostText.trim()}
                className="bg-blue-500 hover:bg-blue-600 text-white"
              >
                Save Changes
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </>
  );
};

export default FacebookStyleHome;
