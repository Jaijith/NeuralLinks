/**
 * WhisperText - Truly subliminal presence indicator
 * 
 * Almost invisible text that only becomes apparent when you're looking for it.
 * Like a ghost watermark - the avatar's whisper in the background.
 */

import { motion, AnimatePresence } from 'framer-motion';
import { useState, useEffect } from 'react';

const WhisperText = ({ 
  text, 
  colors, 
  isInputActive = false,
  energy = 0.5 
}) => {
  const [displayText, setDisplayText] = useState(text);
  const [showOverride, setShowOverride] = useState(false);
  
  // Override text when input is active
  useEffect(() => {
    if (isInputActive) {
      setShowOverride(true);
      setDisplayText('...');
    } else {
      const timer = setTimeout(() => {
        setShowOverride(false);
        setDisplayText(text);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [isInputActive, text]);
  
  // Very slow breathing - ethereal
  const breatheDuration = 15 + (1 - energy) * 10; // 15-25 seconds
  
  // Don't show prominent text normally - only during input
  if (!showOverride) {
    // Return a minimal presence indicator instead of large text
    return (
      <div className="fixed inset-0 pointer-events-none z-[1]">
        {/* Subtle center presence - barely visible */}
        <motion.div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
          animate={{
            opacity: [0.02, 0.04, 0.02],
            scale: [1, 1.1, 1]
          }}
          transition={{
            duration: breatheDuration,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        >
          <div 
            className="w-[300px] h-[300px] rounded-full blur-[60px]"
            style={{
              background: `radial-gradient(circle, ${colors.primary}10 0%, transparent 70%)`
            }}
          />
        </motion.div>
      </div>
    );
  }
  
  // Input active - show subtle "listening" indicator
  return (
    <div className="fixed inset-0 flex items-center justify-center pointer-events-none z-[1]">
      <AnimatePresence mode="wait">
        <motion.div
          key="listening"
          className="flex items-center gap-2"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9 }}
          transition={{ duration: 0.3 }}
        >
          {/* Pulsing dots to indicate listening */}
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-2 h-2 rounded-full"
              style={{
                background: colors.primary,
                boxShadow: `0 0 10px ${colors.glow}`
              }}
              animate={{
                scale: [1, 1.5, 1],
                opacity: [0.4, 0.8, 0.4]
              }}
              transition={{
                duration: 1,
                repeat: Infinity,
                delay: i * 0.2,
                ease: "easeInOut"
              }}
            />
          ))}
        </motion.div>
      </AnimatePresence>
    </div>
  );
};

export default WhisperText;
