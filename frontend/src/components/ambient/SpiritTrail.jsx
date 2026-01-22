/**
 * SpiritTrail - Subtle ethereal cursor enhancement (OPTIMIZED)
 * 
 * Very subtle particles that give a hint of "presence" when moving.
 * Heavily optimized for minimal browser impact.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const TRAIL_LENGTH = 4; // Minimal trail
const TRAIL_DECAY = 0.6;

const SpiritTrail = ({ colors, energy = 0.5 }) => {
  const [trail, setTrail] = useState([]);
  const lastMoveRef = useRef(Date.now());
  const trailIdRef = useRef(0);
  
  // Handle mouse move with heavy throttling
  const handleMouseMove = useCallback((e) => {
    const now = Date.now();
    
    // Very aggressive throttle - only update every 80ms
    if (now - lastMoveRef.current < 80) return;
    lastMoveRef.current = now;
    
    // Add new point to trail
    setTrail(prev => {
      const newPoint = {
        id: trailIdRef.current++,
        x: e.clientX,
        y: e.clientY,
        timestamp: now,
      };
      
      // Keep only recent points
      const filtered = prev.filter(p => now - p.timestamp < 400);
      return [...filtered, newPoint].slice(-TRAIL_LENGTH);
    });
  }, []);
  
  // Add mouse listener
  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [handleMouseMove]);
  
  // Hide on touch devices
  const [isTouchDevice, setIsTouchDevice] = useState(false);
  useEffect(() => {
    setIsTouchDevice('ontouchstart' in window);
  }, []);
  
  if (isTouchDevice) return null;
  
  return (
    <div className="fixed inset-0 pointer-events-none z-[2]">
      <AnimatePresence mode="popLayout">
        {trail.map((point, index) => {
          const age = (Date.now() - point.timestamp) / 400;
          const opacity = Math.max(0, (1 - age) * TRAIL_DECAY * (index / TRAIL_LENGTH) * 0.25);
          
          return (
            <motion.div
              key={point.id}
              className="absolute rounded-full"
              style={{
                left: point.x - 3,
                top: point.y - 3,
                width: 6,
                height: 6,
                background: colors.primary,
                boxShadow: `0 0 4px ${colors.glow}`,
                willChange: 'opacity'
              }}
              initial={{ opacity: 0 }}
              animate={{ opacity }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            />
          );
        })}
      </AnimatePresence>
    </div>
  );
};

export default SpiritTrail;
