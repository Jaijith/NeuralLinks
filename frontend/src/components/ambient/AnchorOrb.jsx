/**
 * AnchorOrb - The Living Spirit Anchor
 * 
 * A magical, futuristic orb that represents the avatar's presence.
 * Pulses like a heartbeat, responds to interaction with ethereal effects.
 */

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const AnchorOrb = ({ 
  colors, 
  energy = 0.5, 
  pulseSpeed = 3,
  onActivate,
  presenceIntensity = 0.5 
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const [isCharging, setIsCharging] = useState(false);
  const [chargeProgress, setChargeProgress] = useState(0);
  
  // Handle hover
  const handleMouseEnter = useCallback(() => {
    setIsHovered(true);
  }, []);
  
  const handleMouseLeave = useCallback(() => {
    setIsHovered(false);
    setIsCharging(false);
    setChargeProgress(0);
  }, []);
  
  // Handle click - immediate activation (no hold required)
  const handleClick = useCallback(() => {
    if (onActivate) {
      onActivate();
    }
  }, [onActivate]);
  
  // Handle click and hold (charging) for special effect
  const handleMouseDown = useCallback(() => {
    setIsCharging(true);
    
    // Animate charge progress
    let progress = 0;
    const interval = setInterval(() => {
      progress += 0.03;
      setChargeProgress(Math.min(1, progress));
      
      if (progress >= 1) {
        clearInterval(interval);
        setIsCharging(false);
        setChargeProgress(0);
      }
    }, 20);
    
    // Store interval for cleanup
    const cleanup = () => {
      clearInterval(interval);
      setIsCharging(false);
      setChargeProgress(0);
    };
    
    window.addEventListener('mouseup', cleanup, { once: true });
  }, []);
  
  // Orb size based on state
  const orbSize = isHovered ? 80 : 56;
  const glowIntensity = 0.4 + presenceIntensity * 0.3 + (isCharging ? chargeProgress * 0.3 : 0);
  
  return (
    <div className="fixed bottom-6 right-6 z-[100]">
      {/* Ambient glow halo - always visible */}
      <motion.div
        className="absolute rounded-full"
        style={{
          width: orbSize + 80,
          height: orbSize + 80,
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          background: `radial-gradient(circle, ${colors.primary}20 0%, ${colors.secondary}10 40%, transparent 70%)`,
        }}
        animate={{
          scale: [1, 1.15, 1],
          opacity: [0.6, 0.9, 0.6]
        }}
        transition={{
          duration: pulseSpeed * 1.2,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />
      
      {/* Pulse ring - heartbeat effect */}
      <motion.div
        className="absolute rounded-full"
        style={{
          width: orbSize + 10,
          height: orbSize + 10,
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          border: `1px solid ${colors.primary}`,
          opacity: 0
        }}
        animate={{
          scale: [1, 2.5],
          opacity: [0.6, 0]
        }}
        transition={{
          duration: pulseSpeed,
          repeat: Infinity,
          ease: "easeOut"
        }}
      />
      
      {/* Second pulse ring - offset */}
      <motion.div
        className="absolute rounded-full"
        style={{
          width: orbSize + 10,
          height: orbSize + 10,
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          border: `1px solid ${colors.secondary}`,
          opacity: 0
        }}
        animate={{
          scale: [1, 2],
          opacity: [0.4, 0]
        }}
        transition={{
          duration: pulseSpeed,
          repeat: Infinity,
          ease: "easeOut",
          delay: pulseSpeed / 2
        }}
      />
      
      {/* Main orb */}
      <motion.div
        className="relative cursor-pointer"
        style={{
          width: orbSize,
          height: orbSize,
        }}
        animate={{
          scale: isCharging ? 0.85 : isHovered ? 1.1 : [1, 1.08, 1],
        }}
        transition={isCharging ? {
          scale: { duration: 0.2 }
        } : {
          scale: { duration: pulseSpeed, repeat: Infinity, ease: "easeInOut" }
        }}
        whileHover={{ scale: 1.15 }}
        whileTap={{ scale: 0.95 }}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onClick={handleClick}
        onMouseDown={handleMouseDown}
      >
        {/* Outer ring - futuristic border */}
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{
            border: `2px solid ${colors.primary}60`,
            boxShadow: `
              0 0 15px ${colors.glow},
              0 0 30px ${colors.glow},
              inset 0 0 15px ${colors.primary}20
            `
          }}
          animate={{
            rotate: [0, 360]
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "linear"
          }}
        />
        
        {/* Orb glass effect */}
        <div
          className="absolute inset-[3px] rounded-full overflow-hidden"
          style={{
            background: `
              radial-gradient(circle at 30% 25%, 
                rgba(255,255,255,0.15) 0%, 
                transparent 50%
              ),
              radial-gradient(circle at 70% 80%, 
                ${colors.secondary}30 0%, 
                transparent 50%
              ),
              radial-gradient(circle at 50% 50%, 
                ${colors.primary}25 0%, 
                ${colors.primary}10 50%,
                transparent 100%
              )
            `,
            backdropFilter: 'blur(4px)',
            boxShadow: `inset 0 0 20px ${colors.primary}30`
          }}
        />
        
        {/* Inner core - the "spirit" */}
        <motion.div
          className="absolute rounded-full"
          style={{
            width: '45%',
            height: '45%',
            left: '27.5%',
            top: '27.5%',
            background: `radial-gradient(circle, ${colors.primary} 0%, ${colors.secondary}80 50%, transparent 100%)`,
            boxShadow: `0 0 20px ${colors.glow}`
          }}
          animate={{
            opacity: [0.6, 1, 0.6],
            scale: [0.9, 1.1, 0.9]
          }}
          transition={{
            duration: pulseSpeed * 0.6,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        
        {/* Sparkle particles orbiting */}
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="absolute w-1.5 h-1.5 rounded-full"
            style={{
              background: colors.primary,
              boxShadow: `0 0 6px ${colors.glow}`,
              left: '50%',
              top: '50%',
            }}
            animate={{
              x: [
                Math.cos((i / 3) * Math.PI * 2) * (orbSize * 0.35),
                Math.cos((i / 3) * Math.PI * 2 + Math.PI) * (orbSize * 0.35),
                Math.cos((i / 3) * Math.PI * 2) * (orbSize * 0.35),
              ],
              y: [
                Math.sin((i / 3) * Math.PI * 2) * (orbSize * 0.35),
                Math.sin((i / 3) * Math.PI * 2 + Math.PI) * (orbSize * 0.35),
                Math.sin((i / 3) * Math.PI * 2) * (orbSize * 0.35),
              ],
              opacity: [0.4, 0.8, 0.4]
            }}
            transition={{
              duration: 4,
              repeat: Infinity,
              delay: i * 1.3,
              ease: "easeInOut"
            }}
          />
        ))}
      </motion.div>
      
      {/* Hover tooltip */}
      <AnimatePresence>
        {isHovered && (
          <motion.div
            className="absolute -top-10 left-1/2 -translate-x-1/2 whitespace-nowrap"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.15 }}
          >
            <span 
              className="text-[10px] font-medium tracking-[0.15em] uppercase px-3 py-1.5 rounded-full"
              style={{ 
                color: colors.primary,
                background: `${colors.primary}15`,
                border: `1px solid ${colors.primary}30`,
                boxShadow: `0 0 10px ${colors.glow}`
              }}
            >
              Click to speak
            </span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default AnchorOrb;
