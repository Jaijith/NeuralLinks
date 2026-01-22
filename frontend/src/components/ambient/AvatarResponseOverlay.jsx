/**
 * AvatarResponseOverlay - Displays avatar's response in an immersive overlay
 * 
 * Shows the avatar's response after user speaks through VoidInput.
 * Features animated cards, mood indicators, and smooth transitions.
 */

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Heart, Sparkles, Brain, MessageCircle, X, TrendingUp } from 'lucide-react';

// Card type to icon mapping
const getCardIcon = (type) => {
  const icons = {
    warm_presence: Heart,
    recap: MessageCircle,
    serendipity: Sparkles,
    reflection: Brain,
    growth: TrendingUp,
    guidance: Sparkles,
    micro_mission: Sparkles,
    celebration: Sparkles,
    acknowledgment: Heart,
    empathy: Heart,
    support: Heart
  };
  return icons[type] || MessageCircle;
};

const AvatarResponseOverlay = ({ 
  isVisible, 
  response, 
  onClose, 
  colors,
  autoCloseDelay = 8000 // Auto close after 8 seconds
}) => {
  const [isClosing, setIsClosing] = useState(false);

  // Auto close after delay
  useEffect(() => {
    if (isVisible && response && autoCloseDelay > 0) {
      const timer = setTimeout(() => {
        handleClose();
      }, autoCloseDelay);
      return () => clearTimeout(timer);
    }
  }, [isVisible, response, autoCloseDelay]);

  const handleClose = useCallback(() => {
    setIsClosing(true);
    setTimeout(() => {
      setIsClosing(false);
      onClose?.();
    }, 300);
  }, [onClose]);

  // Handle keyboard
  useEffect(() => {
    if (!isVisible) return;
    
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' || e.key === ' ') {
        e.preventDefault();
        handleClose();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isVisible, handleClose]);

  if (!isVisible || !response) return null;

  // Extract response data
  const { cards = [], detected_intent, bonding_mode, metrics, mood_changed, new_mood } = response;
  
  // Get primary response text from first card
  const primaryCard = cards[0];
  const primaryText = primaryCard?.content || response.message || "I hear you...";

  return (
    <AnimatePresence>
      {isVisible && !isClosing && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 z-[60]"
            style={{ 
              background: `radial-gradient(ellipse at center, ${colors.glow}20 0%, rgba(0,0,0,0.7) 70%)` 
            }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            onClick={handleClose}
          />

          {/* Response Container */}
          <motion.div
            className="fixed inset-0 z-[61] flex items-center justify-center pointer-events-none"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            {/* Close button */}
            <motion.button
              className="absolute top-6 right-6 p-2 rounded-full pointer-events-auto"
              style={{ 
                background: 'rgba(255,255,255,0.1)',
                color: 'rgba(255,255,255,0.7)'
              }}
              whileHover={{ scale: 1.1, background: 'rgba(255,255,255,0.2)' }}
              whileTap={{ scale: 0.95 }}
              onClick={handleClose}
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <X size={20} />
            </motion.button>

            {/* Main Response Card */}
            <motion.div
              className="relative max-w-lg mx-8 pointer-events-auto"
              initial={{ scale: 0.8, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: -10 }}
              transition={{ 
                type: "spring",
                stiffness: 200,
                damping: 20,
                delay: 0.1
              }}
            >
              {/* Glow effect behind card */}
              <div 
                className="absolute -inset-4 rounded-3xl blur-2xl opacity-30"
                style={{ background: colors.glow }}
              />

              {/* Card */}
              <div 
                className="relative rounded-2xl p-6 backdrop-blur-xl"
                style={{
                  background: 'rgba(12, 15, 25, 0.9)',
                  border: `1px solid ${colors.primary}30`,
                  boxShadow: `0 0 60px ${colors.glow}20, inset 0 1px 0 rgba(255,255,255,0.1)`
                }}
              >
                {/* Avatar indicator */}
                <motion.div 
                  className="flex items-center gap-3 mb-4 pb-4"
                  style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 }}
                >
                  {/* Pulsing avatar orb */}
                  <motion.div
                    className="w-10 h-10 rounded-full flex items-center justify-center"
                    style={{ 
                      background: `linear-gradient(135deg, ${colors.primary}, ${colors.secondary})`,
                      boxShadow: `0 0 20px ${colors.glow}50`
                    }}
                    animate={{
                      boxShadow: [
                        `0 0 20px ${colors.glow}50`,
                        `0 0 30px ${colors.glow}70`,
                        `0 0 20px ${colors.glow}50`
                      ]
                    }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    <Sparkles size={18} className="text-white" />
                  </motion.div>
                  
                  <div>
                    <div className="text-sm font-medium text-white/90">Your Avatar</div>
                    {new_mood && (
                      <div className="text-xs text-white/50">
                        Feeling {new_mood}
                      </div>
                    )}
                  </div>

                  {/* Intent badge */}
                  {detected_intent && (
                    <motion.div
                      className="ml-auto px-3 py-1 rounded-full text-xs"
                      style={{
                        background: `${colors.primary}20`,
                        color: colors.primary,
                        border: `1px solid ${colors.primary}30`
                      }}
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 0.4 }}
                    >
                      {detected_intent.replace(/_/g, ' ')}
                    </motion.div>
                  )}
                </motion.div>

                {/* Primary response text */}
                <motion.div
                  className="text-lg text-white/90 leading-relaxed mb-4"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  {primaryText}
                </motion.div>

                {/* Additional cards (if more than one) */}
                {cards.length > 1 && (
                  <motion.div
                    className="space-y-3 mt-4 pt-4"
                    style={{ borderTop: '1px solid rgba(255,255,255,0.1)' }}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                  >
                    {cards.slice(1).map((card, index) => {
                      const Icon = getCardIcon(card.type);
                      return (
                        <motion.div
                          key={index}
                          className="flex items-start gap-3 p-3 rounded-lg"
                          style={{ background: 'rgba(255,255,255,0.05)' }}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.5 + (index * 0.1) }}
                        >
                          <Icon size={16} className="text-white/60 mt-0.5 flex-shrink-0" />
                          <div className="text-sm text-white/70">{card.content}</div>
                        </motion.div>
                      );
                    })}
                  </motion.div>
                )}

                {/* Question prompt if present */}
                {primaryCard?.question && (
                  <motion.div
                    className="mt-4 p-4 rounded-lg"
                    style={{ 
                      background: `${colors.primary}10`,
                      border: `1px solid ${colors.primary}20`
                    }}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.6 }}
                  >
                    <div className="text-sm text-white/80">{primaryCard.question}</div>
                  </motion.div>
                )}

                {/* Metrics */}
                {metrics && (metrics.bond_delta || metrics.trust_delta) && (
                  <motion.div
                    className="flex items-center justify-center gap-6 mt-4 pt-4"
                    style={{ borderTop: '1px solid rgba(255,255,255,0.1)' }}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.7 }}
                  >
                    {metrics.bond_delta !== undefined && metrics.bond_delta !== 0 && (
                      <div className="flex items-center gap-1 text-xs">
                        <Heart size={12} className="text-pink-400" />
                        <span className="text-pink-400">
                          {metrics.bond_delta > 0 ? '+' : ''}{(metrics.bond_delta * 100).toFixed(1)}% bond
                        </span>
                      </div>
                    )}
                    {metrics.trust_delta !== undefined && metrics.trust_delta !== 0 && (
                      <div className="flex items-center gap-1 text-xs">
                        <TrendingUp size={12} className="text-green-400" />
                        <span className="text-green-400">
                          {metrics.trust_delta > 0 ? '+' : ''}{(metrics.trust_delta * 100).toFixed(1)}% trust
                        </span>
                      </div>
                    )}
                  </motion.div>
                )}

                {/* Dismiss hint */}
                <motion.div
                  className="text-center mt-4 text-xs text-white/30"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.8 }}
                >
                  Press Space or Esc to close
                </motion.div>
              </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default AvatarResponseOverlay;
