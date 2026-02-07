/**
 * ImmersiveBackground - Mood-driven cosmic background (LIGHTWEIGHT)
 * 
 * Makes the avatar's mood dramatically visible through smooth color washes.
 * Uses wide, overlapping gradients for an aurora-like effect without visible blobs.
 * Performance: pure CSS gradients only, no JS animations, no blur filters.
 * Mobile: reduced star count, no twinkle animation.
 */

import { useMemo, useEffect, useState } from 'react';

const isMobile = () => {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
    window.matchMedia('(max-width: 768px)').matches ||
    window.matchMedia('(display-mode: standalone)').matches;
};

const generateStars = (count) => {
  const stars = [];
  for (let i = 0; i < count; i++) {
    stars.push({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 1.6 + 0.4,
      opacity: Math.random() * 0.5 + 0.15
    });
  }
  return stars;
};

const ImmersiveBackground = ({ colors, energy = 0.5, presenceIntensity = 0.5 }) => {
  const [isLowPower, setIsLowPower] = useState(true);
  
  useEffect(() => {
    setIsLowPower(isMobile());
  }, []);
  
  const stars = useMemo(() => {
    return generateStars(isLowPower ? 15 : 30);
  }, [isLowPower]);
  
  // Intensity drives the overall vibrancy
  const intensity = useMemo(() => {
    return 0.30 + presenceIntensity * 0.30; // 0.30 - 0.60
  }, [presenceIntensity]);

  // Generate hex opacity helpers
  const op = useMemo(() => {
    const toHex = (fraction) => Math.round(fraction * 255).toString(16).padStart(2, '0');
    return {
      high: toHex(intensity),           // ~30-60%
      med: toHex(intensity * 0.55),     // ~16-33%
      low: toHex(intensity * 0.30),     // ~9-18%
      faint: toHex(intensity * 0.15),   // ~4-9%
    };
  }, [intensity]);

  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      
      {/* Layer 1: Deep base with very subtle mood tinting at the edges */}
      <div 
        className="absolute inset-0"
        style={{
          background: `
            linear-gradient(170deg,
              ${colors.primary}${op.faint} 0%,
              #060a12 15%,
              #050810 45%,
              #060a12 80%,
              ${colors.secondary}${op.faint} 100%
            )
          `
        }}
      />

      {/* Layer 2: Full-viewport primary color wash — wide & soft, top-biased */}
      <div
        className="absolute inset-0"
        style={{
          background: `radial-gradient(
            ellipse 130% 80% at 25% 15%,
            ${colors.primary}${op.med} 0%,
            ${colors.primary}${op.low} 20%,
            ${colors.primary}${op.faint} 45%,
            transparent 75%
          )`,
        }}
      />

      {/* Layer 3: Full-viewport secondary color wash — wide & soft, bottom-biased */}
      <div
        className="absolute inset-0"
        style={{
          background: `radial-gradient(
            ellipse 120% 90% at 75% 85%,
            ${colors.secondary}${op.med} 0%,
            ${colors.secondary}${op.low} 20%,
            ${colors.secondary}${op.faint} 45%,
            transparent 75%
          )`,
        }}
      />

      {/* Layer 4: Diagonal band — blends both colors across center like aurora */}
      <div
        className="absolute inset-0"
        style={{
          background: `linear-gradient(
            135deg,
            ${colors.primary}${op.low} 0%,
            transparent 25%,
            ${colors.secondary}${op.faint} 40%,
            ${colors.primary}${op.faint} 60%,
            transparent 75%,
            ${colors.secondary}${op.low} 100%
          )`,
        }}
      />

      {/* Layer 5: Very wide center blend — prevents harsh boundary between primary/secondary */}
      <div
        className="absolute inset-0"
        style={{
          background: `radial-gradient(
            ellipse 100% 70% at 50% 45%,
            ${colors.primary}${op.faint} 0%,
            ${colors.secondary}${op.faint} 35%,
            transparent 70%
          )`,
        }}
      />

      {/* Layer 6: Top edge glow — soft mood wash along the header area */}
      <div 
        className="absolute top-0 left-0 right-0"
        style={{
          height: '40%',
          background: `linear-gradient(180deg,
            ${colors.primary}${op.low} 0%,
            ${colors.primary}${op.faint} 30%,
            transparent 100%
          )`
        }}
      />

      {/* Layer 7: Bottom edge glow */}
      <div 
        className="absolute bottom-0 left-0 right-0"
        style={{
          height: '35%',
          background: `linear-gradient(0deg,
            ${colors.secondary}${op.low} 0%,
            ${colors.secondary}${op.faint} 30%,
            transparent 100%
          )`
        }}
      />

      {/* Stars — tiny dots for depth */}
      <div className="absolute inset-0">
        {!isLowPower && (
          <style>{`
            @keyframes twinkle { 0%, 100% { opacity: 0.15; } 50% { opacity: 0.8; } }
            .star-twinkle { animation: twinkle 5s ease-in-out infinite; }
          `}</style>
        )}
        {stars.map((star) => (
          <div
            key={star.id}
            className={`absolute rounded-full bg-white ${!isLowPower ? 'star-twinkle' : ''}`}
            style={{
              left: `${star.x}%`,
              top: `${star.y}%`,
              width: star.size,
              height: star.size,
              opacity: star.opacity,
              animationDelay: !isLowPower ? `${star.id * 0.4}s` : undefined,
            }}
          />
        ))}
      </div>
      
      {/* Slow nebula drift on primary wash — desktop only, pure CSS */}
      {!isLowPower && (
        <style>{`
          @keyframes nebulaDrift { 
            0%, 100% { opacity: 0.9; transform: translate(0, 0) scale(1); } 
            50% { opacity: 1; transform: translate(0.5%, 0.5%) scale(1.01); } 
          }
          .nebula-drift { animation: nebulaDrift 30s ease-in-out infinite; }
        `}</style>
      )}
      
      {/* Gentle vignette — frames content without darkening the mood colors */}
      <div 
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse 90% 70% at 50% 50%, transparent 40%, rgba(0,0,0,0.25) 100%)'
        }}
      />
    </div>
  );
};

export default ImmersiveBackground;
