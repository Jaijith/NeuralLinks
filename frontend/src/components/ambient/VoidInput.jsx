/**
 * VoidInput - Minimalist spacebar-triggered input
 * 
 * A borderless, centered input that appears when user presses spacebar.
 * Text explodes into particles on submit.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const VoidInput = ({ 
  isActive, 
  onSubmit, 
  onClose, 
  colors,
  placeholder = "Speak your mind..."
}) => {
  const [value, setValue] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [particles, setParticles] = useState([]);
  const inputRef = useRef(null);
  
  // Focus input when active
  useEffect(() => {
    if (isActive && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isActive]);
  
  // Handle keyboard
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!isActive) return;
      
      // Escape to close
      if (e.key === 'Escape') {
        onClose?.();
        setValue('');
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isActive, onClose]);
  
  // Create explosion particles from text
  const createParticles = useCallback((text) => {
    const chars = text.split('');
    const newParticles = chars.map((char, i) => ({
      id: i,
      char,
      x: (i - chars.length / 2) * 20,
      y: 0,
      vx: (Math.random() - 0.5) * 300,
      vy: (Math.random() - 0.8) * 400,
      rotation: Math.random() * 360
    }));
    setParticles(newParticles);
    
    // Clear particles after animation
    setTimeout(() => setParticles([]), 1500);
  }, []);
  
  // Handle submit
  const handleSubmit = useCallback(async (e) => {
    e?.preventDefault();
    
    if (!value.trim()) return;
    
    setIsSubmitting(true);
    
    // Create explosion effect
    createParticles(value);
    
    // Send to backend
    try {
      await onSubmit?.(value.trim());
    } catch (err) {
      console.error('Submit error:', err);
    }
    
    // Clear and close after animation
    setTimeout(() => {
      setValue('');
      setIsSubmitting(false);
      onClose?.();
    }, 800);
  }, [value, onSubmit, onClose, createParticles]);
  
  return (
    <AnimatePresence>
      {isActive && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 z-[50]"
            style={{ background: 'rgba(0, 0, 0, 0.5)' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            onClick={() => {
              if (!isSubmitting) {
                onClose?.();
                setValue('');
              }
            }}
          />
          
          {/* Input container */}
          <motion.div
            className="fixed inset-0 flex items-center justify-center z-[51] pointer-events-none"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            {/* Input form */}
            <motion.form
              onSubmit={handleSubmit}
              className="relative pointer-events-auto"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              {/* The input itself - minimalist */}
              <motion.input
                ref={inputRef}
                type="text"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder={placeholder}
                disabled={isSubmitting}
                className="bg-transparent border-none outline-none text-center"
                style={{
                  fontSize: '2rem',
                  fontWeight: 300,
                  letterSpacing: '0.05em',
                  color: 'rgba(255, 255, 255, 0.9)',
                  caretColor: colors.primary,
                  width: '80vw',
                  maxWidth: '600px',
                  textShadow: `0 0 20px ${colors.glow}`
                }}
                animate={isSubmitting ? { opacity: 0, scale: 1.1 } : {}}
              />
              
              {/* Subtle underline */}
              <motion.div
                className="absolute bottom-0 left-1/2 -translate-x-1/2 h-px"
                style={{ 
                  background: `linear-gradient(90deg, transparent, ${colors.primary}40, transparent)`,
                  width: value.length > 0 ? '100%' : '60%'
                }}
                animate={{
                  opacity: [0.3, 0.6, 0.3],
                  scaleX: value.length > 0 ? 1 : 0.6
                }}
                transition={{
                  opacity: { duration: 2, repeat: Infinity },
                  scaleX: { duration: 0.3 }
                }}
              />
              
              {/* Hint text */}
              <motion.p
                className="absolute -bottom-10 left-1/2 -translate-x-1/2 text-xs tracking-widest uppercase whitespace-nowrap"
                style={{ color: 'rgba(255, 255, 255, 0.3)' }}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                Enter to send • Esc to close
              </motion.p>
            </motion.form>
            
            {/* Explosion particles */}
            {particles.map((particle) => (
              <motion.span
                key={particle.id}
                className="absolute text-2xl font-light pointer-events-none"
                style={{
                  color: colors.primary,
                  textShadow: `0 0 10px ${colors.glow}`,
                  left: '50%',
                  top: '50%'
                }}
                initial={{
                  x: particle.x,
                  y: particle.y,
                  opacity: 1,
                  rotate: 0,
                  scale: 1
                }}
                animate={{
                  x: particle.x + particle.vx,
                  y: particle.y + particle.vy,
                  opacity: 0,
                  rotate: particle.rotation,
                  scale: 0.5
                }}
                transition={{
                  duration: 1.2,
                  ease: "easeOut"
                }}
              >
                {particle.char}
              </motion.span>
            ))}
          </motion.div>
          
          {/* Flash effect on submit */}
          <AnimatePresence>
            {isSubmitting && (
              <motion.div
                className="fixed inset-0 z-[49] pointer-events-none"
                style={{ background: colors.glow }}
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.15 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.1 }}
              />
            )}
          </AnimatePresence>
        </>
      )}
    </AnimatePresence>
  );
};

export default VoidInput;
