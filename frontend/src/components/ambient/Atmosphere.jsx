/**
 * Atmosphere - Subtle ambient presence layer (ULTRA LIGHTWEIGHT)
 * 
 * Performance optimizations:
 * - NO Framer Motion - pure CSS animations
 * - NO blur filters
 * - NO particles on mobile
 * - Simple gradients only
 */

import { useMemo, useEffect, useState } from 'react';

// Detect mobile/PWA
const isMobile = () => {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
    window.matchMedia('(max-width: 768px)').matches ||
    window.matchMedia('(display-mode: standalone)').matches;
};

const Atmosphere = ({ mood, energy, colors, presenceIntensity }) => {
  const [isLowPowerMode, setIsLowPowerMode] = useState(true);
  
  useEffect(() => {
    setIsLowPowerMode(isMobile());
  }, []);
  
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      {/* CSS animations for desktop only */}
      {!isLowPowerMode && (
        <style>{`
          @keyframes atmospherePulse { 0%, 100% { opacity: 0.3; } 50% { opacity: 0.5; } }
          .atmo-pulse { animation: atmospherePulse 15s ease-in-out infinite; }
        `}</style>
      )}
      
      {/* Edge glow - top (static on mobile) */}
      <div
        className={`absolute top-0 left-0 right-0 h-[200px] ${!isLowPowerMode ? 'atmo-pulse' : ''}`}
        style={{
          background: `linear-gradient(180deg, ${colors.primary}12 0%, transparent 100%)`,
          opacity: 0.4
        }}
      />
      
      {/* Edge glow - bottom */}
      <div
        className="absolute bottom-0 left-0 right-0 h-[150px]"
        style={{
          background: `linear-gradient(0deg, ${colors.secondary}10 0%, transparent 100%)`,
          opacity: 0.3
        }}
      />
      
      {/* Corner presence - top left (NO blur) */}
      <div
        className={`absolute -top-10 -left-10 w-[300px] h-[300px] rounded-full ${!isLowPowerMode ? 'atmo-pulse' : ''}`}
        style={{ 
          background: `radial-gradient(circle, ${colors.primary}15 0%, transparent 70%)`,
          opacity: 0.5
        }}
      />
      
      {/* Corner presence - bottom right (NO blur) */}
      <div
        className="absolute -bottom-10 -right-10 w-[250px] h-[250px] rounded-full"
        style={{ 
          background: `radial-gradient(circle, ${colors.secondary}12 0%, transparent 70%)`,
          opacity: 0.4
        }}
      />
      
      {/* Subtle vignette - static */}
      <div 
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse 80% 60% at 50% 50%, transparent 50%, rgba(0,0,0,0.05) 100%)'
        }}
      />
    </div>
  );
};

export default Atmosphere;
