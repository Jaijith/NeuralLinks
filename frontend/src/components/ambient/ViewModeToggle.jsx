/**
 * ViewModeToggle - Toggle button to switch between Classic and Immersive views
 * 
 * A sleek toggle that fits the ambient aesthetic.
 */

import { motion } from 'framer-motion';
import { Sparkles, Sun } from 'lucide-react';

const ViewModeToggle = ({ isImmersive, onToggle, colors }) => {
  return (
    <motion.button
      onClick={onToggle}
      className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all"
      style={{
        background: isImmersive 
          ? `linear-gradient(135deg, ${colors?.primary}30 0%, ${colors?.secondary}20 100%)`
          : 'rgba(255, 255, 255, 0.9)',
        border: isImmersive 
          ? `1px solid ${colors?.primary}40`
          : '1px solid rgba(0, 0, 0, 0.1)',
        color: isImmersive ? 'rgba(255, 255, 255, 0.9)' : 'rgba(0, 0, 0, 0.7)',
        boxShadow: isImmersive 
          ? `0 0 15px ${colors?.glow || 'rgba(100, 150, 255, 0.3)'}`
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
            ? `linear-gradient(90deg, ${colors?.primary}50, ${colors?.secondary}50)`
            : 'rgba(0, 0, 0, 0.15)'
        }}
      >
        <motion.div
          className="absolute top-0.5 w-3 h-3 rounded-full"
          style={{
            background: isImmersive ? colors?.primary : 'white',
            boxShadow: isImmersive 
              ? `0 0 6px ${colors?.glow}`
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
