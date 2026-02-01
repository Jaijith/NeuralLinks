/**
 * ViewModeToggle - Toggle button to switch between Classic and Immersive views
 * 
 * A sleek toggle that fits the ambient aesthetic.
 * Supports compact mode for toolbar placement.
 */

import { motion } from 'framer-motion';
import { Sparkles, Sun } from 'lucide-react';

const ViewModeToggle = ({ isImmersive, onToggle, colors, compact = false }) => {
  // Default colors for header usage (when colors not passed)
  const defaultColors = {
    primary: '#6366f1',
    secondary: '#8b5cf6',
    glow: 'rgba(99, 102, 241, 0.4)'
  };
  
  const c = colors || defaultColors;
  
  // Compact mode for header toolbar
  if (compact) {
    return (
      <motion.button
        onClick={onToggle}
        className="flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium transition-all min-h-[32px]"
        style={{
          background: isImmersive 
            ? 'rgba(99, 102, 241, 0.2)'
            : 'rgba(0, 0, 0, 0.05)',
          border: isImmersive 
            ? '1px solid rgba(99, 102, 241, 0.4)'
            : '1px solid rgba(0, 0, 0, 0.1)',
          color: isImmersive ? '#a5b4fc' : 'rgba(0, 0, 0, 0.6)',
        }}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        title={isImmersive ? 'Switch to Classic' : 'Switch to Immersive'}
      >
        {isImmersive ? (
          <Sparkles className="w-3.5 h-3.5" />
        ) : (
          <Sun className="w-3.5 h-3.5" />
        )}
        <span className="hidden sm:inline">{isImmersive ? 'Immersive' : 'Classic'}</span>
      </motion.button>
    );
  }
  
  // Full mode (original design)
  return (
    <motion.button
      onClick={onToggle}
      className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all"
      style={{
        background: isImmersive 
          ? `linear-gradient(135deg, ${c.primary}30 0%, ${c.secondary}20 100%)`
          : 'rgba(255, 255, 255, 0.9)',
        border: isImmersive 
          ? `1px solid ${c.primary}40`
          : '1px solid rgba(0, 0, 0, 0.1)',
        color: isImmersive ? 'rgba(255, 255, 255, 0.9)' : 'rgba(0, 0, 0, 0.7)',
        boxShadow: isImmersive 
          ? `0 0 15px ${c.glow || 'rgba(100, 150, 255, 0.3)'}`
          : '0 2px 8px rgba(0, 0, 0, 0.1)'
      }}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
    >
      {isImmersive ? (
        <>
          <Sparkles className="w-3.5 h-3.5" />
          <span>Immersive</span>
        </>
      ) : (
        <>
          <Sun className="w-3.5 h-3.5" />
          <span>Classic</span>
        </>
      )}
      
      {/* Toggle indicator */}
      <div 
        className="relative w-8 h-4 rounded-full ml-1"
        style={{
          background: isImmersive 
            ? `linear-gradient(90deg, ${c.primary}50, ${c.secondary}50)`
            : 'rgba(0, 0, 0, 0.15)'
        }}
      >
        <motion.div
          className="absolute top-0.5 w-3 h-3 rounded-full"
          style={{
            background: isImmersive ? c.primary : 'white',
            boxShadow: isImmersive 
              ? `0 0 6px ${c.glow}`
              : '0 1px 3px rgba(0, 0, 0, 0.2)'
          }}
          animate={{
            left: isImmersive ? '18px' : '2px'
          }}
          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        />
      </div>
    </motion.button>
  );
};

export default ViewModeToggle;
