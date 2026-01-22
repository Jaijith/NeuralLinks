/**
 * Atmosphere - Subtle ambient presence layer
 * 
 * Creates a feeling of a living spirit presence without overwhelming the UI.
 * Uses edge glows, subtle particles, and gentle animations.
 */

import { motion, AnimatePresence } from 'framer-motion';
import { useMemo } from 'react';

const Atmosphere = ({ mood, energy, colors, presenceIntensity }) => {
  // Animation duration inversely proportional to energy
  const animationDuration = useMemo(() => {
    return 12 + (1 - energy) * 8; // 12-20 seconds (slower, more ethereal)
  }, [energy]);
  
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      {/* Edge glow - top */}
      <motion.div
        className="absolute top-0 left-0 right-0 h-[300px]"
        style={{
          background: `linear-gradient(180deg, ${colors.primary}15 0%, transparent 100%)`
        }}
        animate={{
          opacity: [0.3, 0.5, 0.3]
        }}
        transition={{
          duration: animationDuration,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />
      
      {/* Edge glow - bottom */}
      <motion.div
        className="absolute bottom-0 left-0 right-0 h-[200px]"
        style={{
          background: `linear-gradient(0deg, ${colors.secondary}12 0%, transparent 100%)`
        }}
        animate={{
          opacity: [0.2, 0.4, 0.2]
        }}
        transition={{
          duration: animationDuration * 0.8,
          repeat: Infinity,
          ease: "easeInOut",
          delay: 3
        }}
      />
      
      {/* Corner presence - top left */}
      <motion.div
        className="absolute -top-20 -left-20 w-[400px] h-[400px] rounded-full blur-[100px]"
        style={{ 
          background: `radial-gradient(circle, ${colors.primary}18 0%, transparent 70%)`
        }}
        animate={{
          scale: [1, 1.15, 1],
          opacity: [0.4, 0.6, 0.4]
        }}
        transition={{
          duration: animationDuration,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />
      
      {/* Corner presence - bottom right */}
      <motion.div
        className="absolute -bottom-20 -right-20 w-[350px] h-[350px] rounded-full blur-[80px]"
        style={{ 
          background: `radial-gradient(circle, ${colors.secondary}15 0%, transparent 70%)`
        }}
        animate={{
          scale: [1, 1.1, 1],
          opacity: [0.3, 0.5, 0.3]
        }}
        transition={{
          duration: animationDuration * 0.9,
          repeat: Infinity,
          ease: "easeInOut",
          delay: 4
        }}
      />
      
      {/* Floating spirit particles - very sparse and ethereal */}
      {[...Array(8)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full"
          style={{
            width: 2 + (i % 3),
            height: 2 + (i % 3),
            background: `radial-gradient(circle, ${colors.primary} 0%, transparent 70%)`,
            left: `${15 + (i * 11) % 70}%`,
            top: `${20 + (i * 13) % 60}%`,
            boxShadow: `0 0 ${4 + i * 2}px ${colors.glow}`
          }}
          animate={{
            y: [0, -60 - i * 10, 0],
            x: [0, (i % 2 === 0 ? 20 : -20), 0],
            opacity: [0, 0.6, 0],
            scale: [0.5, 1, 0.5]
          }}
          transition={{
            duration: 10 + i * 2,
            repeat: Infinity,
            delay: i * 1.5,
            ease: "easeInOut"
          }}
        />
      ))}
      
      {/* Subtle vignette for depth */}
      <div 
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `radial-gradient(ellipse 80% 60% at 50% 50%, transparent 40%, rgba(0,0,0,0.08) 100%)`
        }}
      />
    </div>
  );
};

export default Atmosphere;
