/**
 * ImmersivePageWrapper - Shared wrapper for immersive mode across all pages
 * 
 * Provides:
 * - Automatic avatar state integration
 * - View mode toggle (Classic/Immersive)
 * - Background effects (ImmersiveBackground or Atmosphere)
 * - Spirit trail, whisper text, anchor orb
 * - Consistent styling across all pages
 */

import { useState, useCallback, useEffect } from "react";
import { useWorldMode } from "@/contexts/WorldModeContext";
import { 
  Atmosphere, 
  ImmersiveBackground,
  WhisperText, 
  SpiritTrail, 
  AnchorOrb, 
  VoidInput,
  AvatarResponseOverlay,
  VoiceAgent
} from "@/components/ambient";
import useAvatarState from "@/hooks/useAvatarState";
import useViewMode from "@/hooks/useViewMode";
import useSwipeNavigation from "@/hooks/useSwipeNavigation";
import { chatService } from "@/services/api/workflowService";
import { prewarmContext } from "@/services/api/voiceService";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

// Simplified CSS for the mode - PERFORMANCE OPTIMIZED
// Removed: backdrop-filter (expensive), wildcard selectors, complex :not() chains
const getGlobalStyles = (isImmersive, containerId) => {
  const id = containerId || 'maya-page-container';
  
  if (isImmersive) {
    return `
      /* IMMERSIVE MODE - Comprehensive overrides for all pages */
      #${id} {
        --card-bg: rgba(12, 15, 25, 0.70);
        --text-primary: rgba(255, 255, 255, 0.9);
        --text-muted: rgba(255, 255, 255, 0.6);
        --border-color: rgba(255, 255, 255, 0.1);
      }
      
      /* Card/panel backgrounds - target common patterns but avoid colored cards */
      #${id} .immersive-card,
      #${id} .glass-morphism:not([class*="bg-blue"]):not([class*="bg-purple"]):not([class*="bg-pink"]):not([class*="bg-green"]):not([class*="bg-red"]):not([class*="bg-yellow"]) {
        background: var(--card-bg) !important;
        border-color: var(--border-color) !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;
      }
      
      /* White backgrounds to dark (including opacity variants like bg-white/70) */
      #${id} [class*="bg-white"] {
        background: var(--card-bg) !important;
      }
      
      /* Generic card backgrounds */
      #${id} [class*="bg-card"] {
        background: var(--card-bg) !important;
      }
      
      /* Text colors - override common gray text classes */
      #${id} .immersive-text,
      #${id} h1:not([style]),
      #${id} h2:not([style]),
      #${id} h3:not([style]),
      #${id} h4:not([style]) {
        color: var(--text-primary) !important;
      }
      
      #${id} .immersive-muted {
        color: rgba(255, 255, 255, 0.6) !important;
      }
      
      /* Muted text specifically */
      #${id} [class*="text-gray-500"],
      #${id} [class*="text-gray-400"],
      #${id} [class*="text-slate-500"],
      #${id} [class*="text-slate-400"] {
        color: rgba(255, 255, 255, 0.5) !important;
      }
      
      #${id} [class*="text-gray-600"],
      #${id} [class*="text-gray-700"],
      #${id} [class*="text-gray-800"],
      #${id} [class*="text-gray-900"],
      #${id} [class*="text-slate-600"],
      #${id} [class*="text-slate-700"],
      #${id} [class*="text-slate-800"],
      #${id} [class*="text-slate-900"] {
        color: rgba(255, 255, 255, 0.85) !important;
      }
      
      /* Border colors */
      #${id} [class*="border-gray"],
      #${id} [class*="border-slate"],
      #${id} [class*="border-purple-100"],
      #${id} [class*="border-purple-200"] {
        border-color: rgba(255, 255, 255, 0.1) !important;
      }
      
      /* Background overrides for subtle bg classes */
      #${id} [class*="bg-gray-50"],
      #${id} [class*="bg-gray-100"],
      #${id} [class*="bg-slate-50"],
      #${id} [class*="bg-slate-100"] {
        background: rgba(255, 255, 255, 0.05) !important;
      }
      
      /* Inputs in immersive mode */
      #${id} input,
      #${id} textarea,
      #${id} select {
        background: rgba(255, 255, 255, 0.08) !important;
        border-color: var(--border-color) !important;
        color: var(--text-primary) !important;
      }
      
      #${id} input::placeholder,
      #${id} textarea::placeholder {
        color: rgba(255, 255, 255, 0.4) !important;
      }
      
      /* Darken pastel backgrounds for readability in immersive mode */
      #${id} [class*="bg-yellow-50"],
      #${id} [class*="bg-yellow-100"] {
        background: rgba(234, 179, 8, 0.15) !important;
      }
      #${id} [class*="bg-purple-50"],
      #${id} [class*="bg-purple-100"] {
        background: rgba(139, 92, 246, 0.15) !important;
      }
      #${id} [class*="bg-green-50"],
      #${id} [class*="bg-green-100"],
      #${id} [class*="bg-emerald-50"],
      #${id} [class*="bg-emerald-100"] {
        background: rgba(16, 185, 129, 0.15) !important;
      }
      #${id} [class*="bg-red-50"],
      #${id} [class*="bg-red-100"] {
        background: rgba(239, 68, 68, 0.15) !important;
      }
      #${id} [class*="bg-blue-50"],
      #${id} [class*="bg-blue-100"] {
        background: rgba(59, 130, 246, 0.15) !important;
      }
      
      /* Preserve actual colored solid backgrounds (500-level and gradients) */
      #${id} [class*="bg-gradient"],
      #${id} [class*="bg-blue-500"],
      #${id} [class*="bg-blue-600"],
      #${id} [class*="bg-purple-500"],
      #${id} [class*="bg-purple-600"],
      #${id} [class*="bg-green-500"],
      #${id} [class*="bg-green-600"],
      #${id} [class*="bg-red-500"],
      #${id} [class*="bg-red-600"],
      #${id} [class*="bg-yellow-400"],
      #${id} [class*="bg-yellow-500"] {
        /* Keep vivid colored backgrounds as-is */
      }
      
      /* Buttons with colored backgrounds keep white text */
      #${id} button[class*="bg-blue-5"],
      #${id} button[class*="bg-green-5"],
      #${id} button[class*="bg-purple-5"],
      #${id} button[class*="bg-red-5"],
      #${id} button[class*="bg-yellow-5"],
      #${id} .btn-primary,
      #${id} button[class*="bg-gradient"] {
        color: rgb(255, 255, 255) !important;
      }
      
      /* Hover states */
      #${id} [class*="hover\\:bg-gray"]:hover,
      #${id} [class*="hover\\:bg-slate"]:hover,
      #${id} [class*="hover\\:bg-purple-50"]:hover,
      #${id} [class*="hover\\:bg-violet-50"]:hover {
        background: rgba(255, 255, 255, 0.08) !important;
      }
      
      #${id} [class*="hover\\:bg-red-50"]:hover {
        background: rgba(239, 68, 68, 0.2) !important;
      }
      
      #${id} [class*="hover\\:bg-green"]:hover {
        background: rgba(16, 185, 129, 0.2) !important;
      }
    `;
  } else {
    // Classic mode - use defaults, minimal CSS
    return `
      /* CLASSIC MODE - Minimal overrides */
      #${id} {
        --card-bg: rgba(255, 255, 255, 0.98);
        --text-primary: rgba(0, 0, 0, 0.85);
        --text-muted: rgba(0, 0, 0, 0.55);
      }
    `;
  }
};

/**
 * ImmersivePageWrapper component
 * 
 * @param {Object} props
 * @param {React.ReactNode} props.children - Page content
 * @param {string} props.pageId - Unique page identifier for CSS targeting
 * @param {boolean} props.showToggle - Whether to show view mode toggle (default: true)
 * @param {boolean} props.showOrb - Whether to show anchor orb (default: true)
 * @param {string} props.className - Additional classes for the wrapper
 * @param {Object} props.user - User object (needed for avatar state)
 */
const ImmersivePageWrapper = ({ 
  children, 
  pageId = 'maya-page',
  showToggle = true,
  showOrb = true,
  className = '',
  user = null
}) => {
  const { worldMode } = useWorldMode();
  const isAvatarWorld = worldMode === 'avatar';
  
  // Avatar state for ambient effects (pass userId when in avatar world)
  const { 
    mood, 
    energy_level, 
    colors, 
    whisperText, 
    presenceIntensity,
    interests,
    pulseSpeed
  } = useAvatarState(isAvatarWorld ? user?.id : null);
  
  // View mode (classic vs immersive)
  const { isImmersive, toggleViewMode } = useViewMode();
  
  // Swipe navigation for PWA (enabled on mobile)
  useSwipeNavigation({
    enabled: true,
    threshold: 80,
  });
  
  // Void input state
  const [showVoidInput, setShowVoidInput] = useState(false);
  const [customWhisper, setCustomWhisper] = useState(null);
  const [avatarResponse, setAvatarResponse] = useState(null);
  const [showResponse, setShowResponse] = useState(false);
  const [chatSessionId, setChatSessionId] = useState(null);
  
  // Voice mode state - voice is the PRIMARY interaction method
  const [showVoiceAgent, setShowVoiceAgent] = useState(false);
  
  // Initialize chat session when user is available
  useEffect(() => {
    if (isAvatarWorld && user?.id && !chatSessionId) {
      chatService.createSession(user.id)
        .then(session => {
          setChatSessionId(session.session_id);
        })
        .catch(err => {
          console.error('Failed to create chat session:', err);
        });
    }
  }, [isAvatarWorld, user?.id, chatSessionId]);
  
  // Handle orb activation - always starts voice session
  const handleOrbActivate = useCallback(() => {
    setShowVoiceAgent(true);
    setCustomWhisper("CONNECTING...");
  }, []);
  
  // Pre-warm voice context on orb hover (reduces latency when session starts)
  const handleOrbHover = useCallback(() => {
    if (user?.id) {
      prewarmContext(user.id);
    }
  }, [user?.id]);
  
  // Handle voice agent close
  const handleVoiceClose = useCallback(() => {
    setShowVoiceAgent(false);
    setCustomWhisper(null);
  }, []);
  
  // Handle voice transcript for display
  const handleVoiceTranscript = useCallback((data) => {
    if (data.type === 'ai') {
      // AI finished speaking
      setCustomWhisper(null);
    } else if (data.type === 'user') {
      // User spoke
      setCustomWhisper("THINKING...");
    }
  }, []);
  
  // Handle void input submission - use chatService for proper AI responses
  const handleVoidSubmit = useCallback(async (message) => {
    setCustomWhisper("THINKING...");
    
    try {
      // Ensure we have a chat session
      let sessionId = chatSessionId;
      if (!sessionId && user?.id) {
        const session = await chatService.createSession(user.id);
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
    } catch (error) {
      console.error('Failed to send message:', error);
      setCustomWhisper("...");
      setTimeout(() => setCustomWhisper(null), 2000);
    }
  }, [user?.id, chatSessionId]);
  
  // Handle void input close
  const handleVoidClose = useCallback(() => {
    setShowVoidInput(false);
    setCustomWhisper(null);
  }, []);
  
  // Handle response overlay close
  const handleResponseClose = useCallback(() => {
    setShowResponse(false);
    setAvatarResponse(null);
  }, []);
  
  // Spacebar to start voice session
  useEffect(() => {
    if (!isAvatarWorld) return;
    
    const handleKeyDown = (e) => {
      // Spacebar - start voice session
      if (e.code === 'Space' && !showVoidInput && !showVoiceAgent &&
          !['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) {
        e.preventDefault();
        setShowVoiceAgent(true);
        setCustomWhisper("CONNECTING...");
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isAvatarWorld, showVoidInput, showVoiceAgent]);
  
  const containerId = `${pageId}-container`;
  const modeClass = isAvatarWorld 
    ? (isImmersive ? 'immersive-mode' : 'classic-mode')
    : '';
  
  // Determine background class for page container
  const backgroundClass = isAvatarWorld && isImmersive 
    ? "bg-transparent" 
    : "bg-gradient-to-br from-blue-50 via-white to-slate-50";
  
  return (
    <>
      <style>{getGlobalStyles(isAvatarWorld && isImmersive, containerId)}</style>
      <div id={containerId} className={`min-h-screen ${modeClass} ${className}`}>
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
        
        {/* === PAGE CONTENT === */}
        <div 
          className={`min-h-screen min-h-[100dvh] ${backgroundClass}`}
          style={{
            // Add top padding to account for fixed header (56px + safe area)
            paddingTop: 'calc(56px + env(safe-area-inset-top, 0px))',
            // NOTE: Do NOT add overflow-x:hidden here — it breaks position:sticky
            // for child elements. Horizontal overflow is handled by html/body in index.css.
          }}
        >
          {/* View Mode Toggle moved to AppHeader toolbar - no longer needed here */}
          {children}
        </div>
        
        {/* === LIVING SPIRIT ORB (Avatar World Only) === */}
        {isAvatarWorld && showOrb && (
          <>
            <AnchorOrb 
              colors={colors}
              energy={energy_level}
              pulseSpeed={pulseSpeed}
              presenceIntensity={presenceIntensity}
              onActivate={handleOrbActivate}
              onHoverStart={handleOrbHover}
            />
            
            {/* Voice Agent Overlay - Real-time voice interaction */}
            <VoiceAgent
              isActive={showVoiceAgent}
              onClose={handleVoiceClose}
              colors={colors}
              avatarId={user?.id}
              settingPreset="low_latency"
              onTranscript={handleVoiceTranscript}
            />
            
            {/* Void Input Overlay - Text input */}
            <VoidInput 
              isActive={showVoidInput}
              onClose={handleVoidClose}
              onSubmit={handleVoidSubmit}
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

export default ImmersivePageWrapper;
