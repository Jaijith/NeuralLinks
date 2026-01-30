/**
 * VoiceAgent - Real-time voice communication component
 * 
 * Provides an immersive voice interaction interface with the avatar.
 * Uses WebRTC for low-latency speech-to-speech communication.
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useVoiceSession, VoiceSessionState } from '../../hooks/useVoiceSession';

// CSS for smooth animations
const orbStyles = `
  @keyframes orbPulse {
    0%, 100% { transform: scale(1); opacity: 0.6; }
    50% { transform: scale(1.05); opacity: 0.8; }
  }
  @keyframes orbGlow {
    0%, 100% { box-shadow: 0 0 20px var(--glow-color), 0 0 40px var(--glow-color); }
    50% { box-shadow: 0 0 40px var(--glow-color), 0 0 80px var(--glow-color); }
  }
  @keyframes ringExpand {
    0% { transform: scale(1); opacity: 0.4; }
    100% { transform: scale(1.5); opacity: 0; }
  }
  @keyframes speakingPulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.15); }
  }
  .orb-idle { animation: orbPulse 3s ease-in-out infinite; }
  .orb-listening { animation: orbPulse 1.5s ease-in-out infinite; }
  .orb-speaking { animation: speakingPulse 0.3s ease-in-out infinite; }
  .ring-expand { animation: ringExpand 2s ease-out infinite; }
`;

const VoiceAgent = ({
  isActive,
  onClose,
  colors,
  avatarId,
  settingPreset = 'low_latency', // Use low_latency preset by default
  onTranscript
}) => {
  const [showTranscript, setShowTranscript] = useState(false);
  const [transcriptHistory, setTranscriptHistory] = useState([]);
  const transcriptEndRef = useRef(null);
  
  const {
    sessionState,
    isConnected,
    isSpeaking,
    isListening,
    transcript,
    aiTranscript,
    error,
    audioLevel,
    startSession,
    stopSession,
    interrupt
  } = useVoiceSession({
    avatarId,
    settingPreset,
    onTranscript: (data) => {
      setTranscriptHistory(prev => [...prev.slice(-20), data]);
      onTranscript?.(data);
    },
    onStateChange: (state) => {
      console.log('Voice state:', state);
    },
    onError: (err) => {
      console.error('Voice error:', err);
    }
  });
  
  // Auto-start session when activated
  useEffect(() => {
    if (isActive && sessionState === VoiceSessionState.IDLE) {
      startSession();
    }
  }, [isActive, sessionState, startSession]);
  
  // Handle close
  const handleClose = useCallback(() => {
    stopSession();
    onClose?.();
  }, [stopSession, onClose]);
  
  // Scroll transcript to bottom
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcriptHistory]);
  
  // Get status text
  const getStatusText = () => {
    switch (sessionState) {
      case VoiceSessionState.CONNECTING:
        return 'Connecting...';
      case VoiceSessionState.CONNECTED:
        return 'Ready to listen';
      case VoiceSessionState.LISTENING:
        return 'Listening...';
      case VoiceSessionState.SPEAKING:
        return 'Speaking...';
      case VoiceSessionState.ERROR:
        return error || 'Connection error';
      case VoiceSessionState.DISCONNECTED:
        return 'Disconnected';
      default:
        return 'Starting...';
    }
  };
  
  // Compute orb class based on state
  const orbClass = useMemo(() => {
    if (isSpeaking) return 'orb-speaking';
    if (isListening) return 'orb-listening';
    return 'orb-idle';
  }, [isSpeaking, isListening]);
  
  // Dynamic scale based on audio level (smooth CSS transform)
  const audioScale = useMemo(() => {
    return 1 + (audioLevel * 0.25);
  }, [audioLevel]);
  
  return (
    <AnimatePresence>
      {isActive && (
        <>
          <style>{orbStyles}</style>
          
          {/* Full-screen backdrop */}
          <motion.div
            className="fixed inset-0 z-[200] bg-black/80 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={handleClose}
          />
          
          {/* Voice UI container */}
          <motion.div
            className="fixed inset-0 z-[201] flex flex-col items-center justify-center pointer-events-none"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {/* Central orb visualization */}
            <motion.div
              className="relative w-40 h-40 sm:w-56 sm:h-56 pointer-events-auto"
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.5, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 200, damping: 20 }}
            >
              {/* Expanding rings (CSS animated) */}
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="absolute inset-0 rounded-full ring-expand"
                  style={{
                    border: `1px solid ${colors.primary}40`,
                    animationDelay: `${i * 0.6}s`,
                    opacity: isListening || isSpeaking ? 0.6 : 0.3
                  }}
                />
              ))}
              
              {/* Audio reactive ring */}
              <div
                className="absolute inset-0 rounded-full transition-transform duration-75"
                style={{
                  border: `2px solid ${colors.primary}`,
                  transform: `scale(${audioScale})`,
                  opacity: (isListening || isSpeaking) ? 0.8 : 0.3,
                  transition: 'transform 75ms ease-out, opacity 150ms ease'
                }}
              />
              
              {/* Main orb - CSS animated for smooth performance */}
              <div
                className={`absolute inset-4 rounded-full ${orbClass}`}
                style={{
                  '--glow-color': colors.glow,
                  background: `radial-gradient(circle at 30% 30%, 
                    ${colors.primary}50, 
                    ${colors.secondary}30 50%, 
                    ${colors.primary}10 80%)`,
                  backdropFilter: 'blur(10px)',
                  border: `1px solid ${colors.primary}60`,
                  boxShadow: `0 0 30px ${colors.glow}, 0 0 60px ${colors.glow}40`,
                  transform: `scale(${isSpeaking ? audioScale : 1})`,
                  transition: 'transform 100ms ease-out'
                }}
              >
                {/* Inner core - also CSS animated */}
                <div
                  className="absolute inset-6 sm:inset-10 rounded-full"
                  style={{
                    background: `radial-gradient(circle, 
                      ${colors.primary} 0%, 
                      ${colors.secondary}90 40%, 
                      transparent 100%)`,
                    boxShadow: `0 0 40px ${colors.glow}`,
                    transform: `scale(${isSpeaking ? 1 + audioLevel * 0.3 : 1})`,
                    opacity: isSpeaking ? 1 : 0.7,
                    transition: 'transform 100ms ease-out, opacity 150ms ease'
                  }}
                />
              </div>
              
              {/* Listening indicator dot */}
              {isListening && (
                <motion.div
                  className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-10"
                  initial={{ opacity: 0, scale: 0 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0 }}
                >
                  <div 
                    className="w-3 h-3 rounded-full"
                    style={{
                      background: colors.primary,
                      boxShadow: `0 0 15px ${colors.glow}`,
                      animation: 'orbPulse 1s ease-in-out infinite'
                    }}
                  />
                </motion.div>
              )}
            </motion.div>
            
            {/* Status text */}
            <motion.div
              className="mt-8 text-center pointer-events-auto"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <p 
                className="text-lg sm:text-xl font-light tracking-wide"
                style={{ color: colors.primary }}
              >
                {getStatusText()}
              </p>
              
              {/* Current AI transcript */}
              {aiTranscript && (
                <motion.p
                  className="mt-4 max-w-md px-4 text-sm sm:text-base text-white/80 italic"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  "{aiTranscript}"
                </motion.p>
              )}
              
              {/* Error message */}
              {error && (
                <motion.p
                  className="mt-4 text-red-400 text-sm"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  {error}
                </motion.p>
              )}
            </motion.div>
            
            {/* Control buttons */}
            <motion.div
              className="mt-8 flex items-center gap-4 pointer-events-auto"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              {/* Toggle transcript */}
              <button
                onClick={() => setShowTranscript(!showTranscript)}
                className="px-4 py-2 rounded-full text-sm transition-all min-h-[44px]"
                style={{
                  background: showTranscript ? `${colors.primary}30` : 'rgba(255,255,255,0.1)',
                  border: `1px solid ${showTranscript ? colors.primary : 'rgba(255,255,255,0.2)'}`,
                  color: showTranscript ? colors.primary : 'rgba(255,255,255,0.7)'
                }}
              >
                {showTranscript ? 'Hide' : 'Show'} Transcript
              </button>
              
              {/* Interrupt button (when AI is speaking) */}
              {isSpeaking && (
                <motion.button
                  onClick={interrupt}
                  className="px-4 py-2 rounded-full text-sm text-white/70 hover:text-white transition-all min-h-[44px]"
                  style={{
                    background: 'rgba(255,255,255,0.1)',
                    border: '1px solid rgba(255,255,255,0.2)'
                  }}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                >
                  Interrupt
                </motion.button>
              )}
              
              {/* End call button */}
              <button
                onClick={handleClose}
                className="px-6 py-2 rounded-full text-sm bg-red-500/20 border border-red-500/50 text-red-400 hover:bg-red-500/30 transition-all min-h-[44px]"
              >
                End
              </button>
            </motion.div>
            
            {/* Transcript panel */}
            <AnimatePresence>
              {showTranscript && (
                <motion.div
                  className="fixed bottom-24 left-4 right-4 sm:left-auto sm:right-8 sm:w-96 max-h-60 overflow-y-auto rounded-xl pointer-events-auto"
                  style={{
                    background: 'rgba(0,0,0,0.8)',
                    border: `1px solid ${colors.primary}30`,
                    backdropFilter: 'blur(10px)'
                  }}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 20 }}
                >
                  <div className="p-4 space-y-3">
                    {transcriptHistory.length === 0 ? (
                      <p className="text-white/40 text-sm text-center">
                        Conversation will appear here...
                      </p>
                    ) : (
                      transcriptHistory.map((item, i) => (
                        <div
                          key={i}
                          className={`text-sm ${item.type === 'user' ? 'text-right' : 'text-left'}`}
                        >
                          <span
                            className="inline-block px-3 py-2 rounded-lg max-w-[85%]"
                            style={{
                              background: item.type === 'user' 
                                ? `${colors.primary}20` 
                                : 'rgba(255,255,255,0.1)',
                              color: item.type === 'user' ? colors.primary : 'rgba(255,255,255,0.8)'
                            }}
                          >
                            {item.text}
                          </span>
                        </div>
                      ))
                    )}
                    <div ref={transcriptEndRef} />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            
            {/* Instructions */}
            <motion.p
              className="fixed bottom-8 left-1/2 -translate-x-1/2 text-white/30 text-xs sm:text-sm text-center pointer-events-none"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              Just speak naturally • Tap anywhere to close
            </motion.p>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default VoiceAgent;
