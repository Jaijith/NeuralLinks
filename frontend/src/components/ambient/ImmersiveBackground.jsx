/**
 * ImmersiveBackground - Cosmic space-themed background (OPTIMIZED)
 * 
 * Performance optimizations:
 * - Reduced star count (60 instead of 180)
 * - CSS animations for stars instead of Framer Motion
 * - Fewer particles (8 instead of 15)
 * - will-change hints for GPU acceleration
 * - Simplified gradients
 */

import { useMemo } from 'react';
import { motion } from 'framer-motion';

// Pre-generate stars once (not on every render)
const generateStars = () => {
  const stars = [];
  // Reduced to 60 stars total
  for (let i = 0; i < 50; i++) {
    stars.push({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 1.5 + 0.5,
      opacity: Math.random() * 0.4 + 0.2,
      delay: Math.random() * 4
    });
  }
  // Medium stars (fewer)
  for (let i = 50; i < 60; i++) {
    stars.push({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 2 + 1.5,
      opacity: Math.random() * 0.3 + 0.3,
      delay: Math.random() * 4
    });
  }
  return stars;
};

// Static stars - generated once
const STARS = generateStars();

const ImmersiveBackground = ({ colors, energy = 0.5, presenceIntensity = 0.5 }) => {
  // Animation speed based on energy (memoized)
  const animationDuration = useMemo(() => {
    return 25 + (1 - energy) * 15; // 25-40 seconds (slower = less CPU)
  }, [energy]);
  
  // Nebula opacity based on presence (memoized)
  const nebulaOpacity = useMemo(() => {
    return 0.25 + presenceIntensity * 0.2;
  }, [presenceIntensity]);

  const primaryHex = useMemo(() => 
    Math.round(nebulaOpacity * 255).toString(16).padStart(2, '0'),
    [nebulaOpacity]
  );

  const secondaryHex = useMemo(() => 
    Math.round(nebulaOpacity * 0.8 * 255).toString(16).padStart(2, '0'),
    [nebulaOpacity]
  );

  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      {/* Deep space base gradient - static, no animation */}
      <div 
        className="absolute inset-0"
        style={{
          background: `
            radial-gradient(ellipse 120% 80% at 50% 0%, #0d1117 0%, #010409 50%),
            linear-gradient(180deg, #0d1117 0%, #010409 100%)
          `
        }}
      />
      
      {/* Star field layer - using CSS animations */}
      <div className="absolute inset-0">
        <style>{`
          @keyframes twinkle {
            0%, 100% { opacity: 0.2; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(1.1); }
          }
        `}</style>
        {STARS.map((star) => (
          <div
            key={star.id}
            className="absolute rounded-full bg-white"
            style={{
              left: `${star.x}%`,
              top: `${star.y}%`,
              width: star.size,
              height: star.size,
              opacity: star.opacity,
              animation: `twinkle ${3 + star.delay}s ease-in-out infinite`,
              animationDelay: `${star.delay}s`,
              willChange: 'opacity, transform'
            }}
          />
        ))}
      </div>
      
      {/* Primary nebula cloud - mood radiance */}
      <motion.div
        className="absolute -top-[15%] -left-[5%] w-[70%] h-[60%]"
        style={{
          background: `radial-gradient(ellipse at center, ${colors.primary}${primaryHex} 0%, transparent 60%)`,
          filter: 'blur(80px)',
          willChange: 'transform, opacity'
        }}
        animate={{
          scale: [1, 1.1, 1],
          opacity: [nebulaOpacity * 0.8, nebulaOpacity, nebulaOpacity * 0.8]
        }}
        transition={{
          duration: animationDuration,
          repeat: Infinity,
          ease: "linear"
        }}
      />
      
      {/* Secondary nebula cloud - bottom */}
      <motion.div
        className="absolute -bottom-[10%] -right-[10%] w-[60%] h-[50%]"
        style={{
          background: `radial-gradient(ellipse at center, ${colors.secondary}${secondaryHex} 0%, transparent 60%)`,
          filter: 'blur(90px)',
          willChange: 'transform, opacity'
        }}
        animate={{
          scale: [1, 1.15, 1],
          opacity: [nebulaOpacity * 0.6, nebulaOpacity * 0.9, nebulaOpacity * 0.6]
        }}
        transition={{
          duration: animationDuration * 0.9,
          repeat: Infinity,
          ease: "linear",
          delay: 3
        }}
      />
      
      {/* Center mood glow - simplified */}
      <div
        className="absolute top-[30%] left-[40%] w-[40%] h-[40%]"
        style={{
          background: `radial-gradient(ellipse at center, ${colors.primary}18 0%, transparent 60%)`,
          filter: 'blur(60px)',
        }}
      />
      
      {/* Edge glow - top (static gradient, subtle animation) */}
      <motion.div 
        className="absolute top-0 left-0 right-0 h-[200px]"
        style={{
          background: `linear-gradient(180deg, ${colors.primary}25 0%, transparent 100%)`,
          willChange: 'opacity'
        }}
        animate={{ opacity: [0.7, 1, 0.7] }}
        transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
      />
      
      {/* Edge glow - bottom */}
      <div 
        className="absolute bottom-0 left-0 right-0 h-[150px]"
        style={{
          background: `linear-gradient(0deg, ${colors.secondary}20 0%, transparent 100%)`
        }}
      />
      
      {/* Floating spirit particles - reduced to 8 */}
      {[...Array(8)].map((_, i) => (
        <motion.div
          key={`particle-${i}`}
          className="absolute rounded-full"
          style={{
            width: 2 + (i % 3),
            height: 2 + (i % 3),
            left: `${10 + (i * 10) % 80}%`,
            top: `${15 + (i * 12) % 70}%`,
            background: colors.primary,
            boxShadow: `0 0 ${6 + i}px ${colors.glow}`,
            willChange: 'transform, opacity'
          }}
          animate={{
            y: [0, -80 - i * 5, 0],
            opacity: [0, 0.7, 0],
          }}
          transition={{
            duration: 12 + i * 2,
            repeat: Infinity,
            delay: i * 1.5,
            ease: "linear"
          }}
        />
      ))}
      
      {/* Vignette for depth - static */}
      <div 
        className="absolute inset-0"
        style={{
          background: `radial-gradient(ellipse 70% 50% at 50% 50%, transparent 30%, rgba(0,0,0,0.35) 100%)`
        }}
      />
    </div>
  );
};

export default ImmersiveBackground;
