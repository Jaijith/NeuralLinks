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
  ViewModeToggle,
  AvatarResponseOverlay,
  VoiceAgent,
  VoiceSettings
} from "@/components/ambient";
import useAvatarState from "@/hooks/useAvatarState";
import useViewMode from "@/hooks/useViewMode";
import { chatService } from "@/services/api/workflowService";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

// Generate aggressive CSS for the mode - using unique page container ID
const getGlobalStyles = (isImmersive, containerId) => {
  const id = containerId || 'maya-page-container';
  
  if (isImmersive) {
    return `
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
      
      /* IMMERSIVE MODE - Override CSS variables */
      #${id} {
        --card: 12 15 25;
        --card-foreground: 255 255 255;
        --background: transparent;
        --foreground: 255 255 255;
        --muted: 30 35 50;
        --muted-foreground: 200 200 220;
        --border: 255 255 255;
      }
      
      #${id} * {
        font-family: 'Inter', sans-serif !important;
      }
      
      /* Target Card component and all card-like elements */
      #${id} .bg-card,
      #${id} [class*="bg-card"],
      #${id} .glass-card,
      #${id} .rounded-lg,
      #${id} .rounded-xl,
      #${id} .rounded-2xl,
      #${id} .rounded-md,
      #${id} .shadow,
      #${id} .shadow-sm,
      #${id} .shadow-md,
      #${id} .shadow-lg,
      #${id} .border,
      #${id} [class*="shadow"],
      #${id} .bg-white,
      #${id} [class*="bg-white"] {
        background: rgba(12, 15, 25, 0.88) !important;
        backdrop-filter: blur(16px) saturate(1.3) !important;
        -webkit-backdrop-filter: blur(16px) saturate(1.3) !important;
        border-color: rgba(255, 255, 255, 0.1) !important;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.5) !important;
      }
      
      /* Text white - but EXCLUDE colored backgrounds and special components */
      #${id},
      #${id} div:not([class*="bg-yellow"]):not([class*="bg-green"]):not([class*="bg-red"]):not([class*="bg-blue"]):not([class*="bg-purple"]):not([class*="bg-pink"]):not([class*="bg-orange"]):not([class*="bg-gradient"]):not([class*="from-"]):not(.memory-orb-page):not(.memory-orb-page *),
      #${id} p:not([class*="text-white"]):not(.memory-orb-page *),
      #${id} span:not([class*="bg-"]):not([class*="text-white"]):not(.memory-orb-page *),
      #${id} h1:not(.memory-orb-page *), #${id} h2:not(.memory-orb-page *), #${id} h3:not(.memory-orb-page *),
      #${id} h4:not(.memory-orb-page *), #${id} h5:not(.memory-orb-page *), #${id} h6:not(.memory-orb-page *),
      #${id} a:not([class*="bg-"]):not(.memory-orb-page *),
      #${id} label:not(.memory-orb-page *),
      #${id} li:not(.memory-orb-page *) {
        color: rgba(255, 255, 255, 0.9) !important;
      }
      
      /* PRESERVE MemoryOrb component's own styling */
      #${id} .memory-orb-page,
      #${id} .memory-orb-page * {
        color: inherit !important;
      }
      
      #${id} .memory-orb-page .stat-bars,
      #${id} .memory-orb-page .memory-panel {
        background: rgba(255, 255, 255, 0.95) !important;
      }
      
      #${id} .memory-orb-page .stat-label {
        color: #1f2937 !important;
      }
      
      #${id} .memory-orb-page svg {
        color: inherit !important;
      }
      
      /* Buttons - only apply to non-colored buttons */
      #${id} button:not([class*="bg-"]):not([class*="btn-"]) {
        color: rgba(255, 255, 255, 0.85) !important;
      }
      
      /* PRESERVE original colors on badges and colored elements */
      #${id} [class*="bg-yellow"] *,
      #${id} [class*="bg-green"] *,
      #${id} [class*="bg-red"]:not(.bg-red-50) *,
      #${id} [class*="bg-blue"]:not(.bg-blue-50) *,
      #${id} [class*="bg-purple"]:not(.bg-purple-50) *,
      #${id} [class*="bg-pink"] *,
      #${id} [class*="bg-orange"] *,
      #${id} [class*="bg-gradient"] *,
      #${id} [class*="from-pink"] *,
      #${id} [class*="from-purple"] *,
      #${id} [class*="from-blue"] *,
      #${id} [class*="from-green"] * {
        color: inherit !important;
      }
      
      /* Badges with colored backgrounds - keep dark text */
      #${id} [class*="bg-yellow-100"],
      #${id} [class*="bg-purple-100"],
      #${id} [class*="bg-green-100"],
      #${id} [class*="bg-blue-100"],
      #${id} [class*="bg-pink-100"],
      #${id} [class*="bg-red-100"],
      #${id} [class*="bg-orange-100"] {
        background-color: inherit !important;
      }
      
      #${id} [class*="bg-yellow-100"] *,
      #${id} [class*="bg-purple-100"] *,
      #${id} [class*="bg-green-100"] *,
      #${id} [class*="bg-blue-100"] *,
      #${id} [class*="bg-red-100"] *,
      #${id} .text-purple-700,
      #${id} .text-yellow-700,
      #${id} .text-green-700,
      #${id} .text-blue-700,
      #${id} .text-red-700 {
        color: inherit !important;
      }
      
      /* Muted text - only for non-colored elements */
      #${id} .text-muted-foreground:not([class*="bg-"]),
      #${id} .text-gray-400:not([class*="bg-"]),
      #${id} .text-gray-500:not([class*="bg-"]),
      #${id} .text-gray-600:not([class*="bg-"]) {
        color: rgba(255, 255, 255, 0.65) !important;
      }
      
      /* Inputs */
      #${id} input,
      #${id} textarea,
      #${id} select {
        background: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: rgba(255, 255, 255, 0.9) !important;
      }
      
      #${id} input::placeholder,
      #${id} textarea::placeholder {
        color: rgba(255, 255, 255, 0.4) !important;
      }
      
      /* Borders */
      #${id} .border,
      #${id} [class*="border-gray"],
      #${id} [class*="divide-gray"] > * {
        border-color: rgba(255, 255, 255, 0.1) !important;
      }
      
      /* Background utilities */
      #${id} .bg-gray-50,
      #${id} .bg-gray-100,
      #${id} [class*="bg-gray-"],
      #${id} .bg-muted,
      #${id} [class*="bg-muted"] {
        background: rgba(255, 255, 255, 0.05) !important;
      }
      
      /* SVG/Icons */
      #${id} svg {
        color: rgba(255, 255, 255, 0.7) !important;
      }
      
      /* Tabs styling */
      #${id} [role="tablist"] {
        background: rgba(255, 255, 255, 0.05) !important;
      }
      
      #${id} [role="tab"] {
        color: rgba(255, 255, 255, 0.6) !important;
      }
      
      #${id} [role="tab"][data-state="active"] {
        background: rgba(255, 255, 255, 0.1) !important;
        color: rgba(255, 255, 255, 0.95) !important;
      }
      
      /* Dialog/Modal styling */
      #${id} [role="dialog"] {
        background: rgba(12, 15, 25, 0.95) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
      }
      
      /* Animation */
      .page-content-card {
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
      #${id} * {
        font-family: 'Inter', sans-serif !important;
      }
      
      /* Light glass cards */
      #${id} .bg-card,
      #${id} .glass-card,
      #${id} .rounded-lg,
      #${id} .rounded-xl,
      #${id} .rounded-2xl,
      #${id} .rounded-md,
      #${id} .shadow,
      #${id} [class*="shadow"],
      #${id} .bg-white,
      #${id} [class*="bg-white"] {
        background: rgba(255, 255, 255, 0.95) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border-color: rgba(0, 0, 0, 0.08) !important;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08) !important;
      }
      
      /* Dark text */
      #${id},
      #${id} div,
      #${id} p,
      #${id} span,
      #${id} h1, #${id} h2, #${id} h3,
      #${id} h4, #${id} h5, #${id} h6,
      #${id} a,
      #${id} label,
      #${id} li,
      #${id} button,
      #${id} .text-card-foreground,
      #${id} .text-foreground {
        color: rgba(0, 0, 0, 0.85) !important;
      }
      
      /* Muted text */
      #${id} .text-muted-foreground,
      #${id} .text-gray-400,
      #${id} .text-gray-500,
      #${id} .text-gray-600 {
        color: rgba(0, 0, 0, 0.55) !important;
      }
      
      /* SVG/Icons */
      #${id} svg {
        color: rgba(0, 0, 0, 0.6) !important;
      }
      
      /* Animation */
      .page-content-card {
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
  
  // Void input state
  const [showVoidInput, setShowVoidInput] = useState(false);
  const [customWhisper, setCustomWhisper] = useState(null);
  const [avatarResponse, setAvatarResponse] = useState(null);
  const [showResponse, setShowResponse] = useState(false);
  const [chatSessionId, setChatSessionId] = useState(null);
  
  // Voice mode state - voice is the PRIMARY interaction method
  const [showVoiceAgent, setShowVoiceAgent] = useState(false);
  const [showVoiceSettings, setShowVoiceSettings] = useState(false);
  
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
  
  // Open text input (alternative to voice)
  const openTextInput = useCallback(() => {
    setShowVoidInput(true);
    setCustomWhisper("TYPE...");
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
  
  // Spacebar to start voice session, T for text input
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
      // T key - open text input instead
      if (e.code === 'KeyT' && !showVoidInput && !showVoiceAgent &&
          !['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) {
        e.preventDefault();
        openTextInput();
      }
      // S key to open voice settings
      if (e.code === 'KeyS' && e.shiftKey && !showVoidInput && !showVoiceAgent &&
          !['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) {
        e.preventDefault();
        setShowVoiceSettings(true);
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isAvatarWorld, showVoidInput, showVoiceAgent, openTextInput]);
  
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
          className={`min-h-screen min-h-[100dvh] ${backgroundClass} overflow-x-hidden`}
          style={{
            // Add top padding to account for fixed header (56px + safe area)
            paddingTop: 'calc(56px + env(safe-area-inset-top, 0px))',
          }}
        >
          {/* View Mode Toggle - sticky, scrolls with content on mobile */}
          {isAvatarWorld && showToggle && (
            <div className="sticky top-[60px] sm:top-[64px] right-0 z-40 flex justify-end px-3 sm:px-6 py-2">
              <ViewModeToggle 
                isImmersive={isImmersive}
                onToggle={toggleViewMode}
                colors={colors}
              />
            </div>
          )}
          
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
            />
            
            {/* Voice Controls - small buttons above orb */}
            <div 
              className="fixed z-[99] bottom-[130px] sm:bottom-[110px] right-4 sm:right-6 flex flex-col items-center gap-2"
              style={{ 
                bottom: typeof window !== 'undefined' && window.innerWidth < 640 
                  ? 'calc(130px + env(safe-area-inset-bottom, 0px))' 
                  : undefined
              }}
            >
              {/* Settings button */}
              <button
                onClick={() => setShowVoiceSettings(true)}
                className="w-8 h-8 rounded-full flex items-center justify-center transition-all hover:scale-110"
                style={{
                  background: `${colors.primary}20`,
                  border: `1px solid ${colors.primary}40`
                }}
                title="Voice Settings (Shift+S)"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke={colors.primary}>
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>
              
              {/* Text input button (press T) */}
              <button
                onClick={openTextInput}
                className="w-8 h-8 rounded-full flex items-center justify-center transition-all hover:scale-110"
                style={{
                  background: 'rgba(255,255,255,0.1)',
                  border: '1px solid rgba(255,255,255,0.2)'
                }}
                title="Text Input (T)"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" style={{ color: 'rgba(255,255,255,0.6)' }}>
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
            </div>
            
            {/* Voice Agent Overlay - Real-time voice interaction */}
            <VoiceAgent
              isActive={showVoiceAgent}
              onClose={handleVoiceClose}
              colors={colors}
              avatarId={user?.id}
              settingPreset="low_latency"
              onTranscript={handleVoiceTranscript}
            />
            
            {/* Voice Settings Panel */}
            <VoiceSettings
              isOpen={showVoiceSettings}
              onClose={() => setShowVoiceSettings(false)}
              colors={colors}
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
