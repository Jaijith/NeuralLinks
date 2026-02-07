/**
 * MiniMemoryOrb - Miniature version of the MemoryOrb with voice activation
 * 
 * A small, interactive orb that shows:
 * - Current mood/state through colors
 * - Cycling knowledge words
 * - Click to activate voice session
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';
import useViewMode from '@/hooks/useViewMode';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
const API = `${BACKEND_URL}/api`;

// Mood color mapping for immersive (dark) mode
const moods = {
  happy: {
    inner: 'rgba(255, 200, 140, 1)',
    outer: 'rgba(255, 140, 60, 0.9)',
    glow: '#FF6B35',
    text: '#d97706'
  },
  neutral: {
    inner: 'rgba(200, 180, 255, 1)',
    outer: 'rgba(160, 120, 255, 0.85)',
    glow: '#7C5CFF',
    text: '#7c3aed'
  },
  curious: {
    inner: 'rgba(200, 180, 255, 1)',
    outer: 'rgba(160, 120, 255, 0.85)',
    glow: '#9B7DFF',
    text: '#8b5cf6'
  },
  bored: {
    inner: 'rgba(150, 150, 180, 1)',
    outer: 'rgba(120, 120, 150, 0.8)',
    glow: '#6B6B8F',
    text: '#64748b'
  },
  excited: {
    inner: 'rgba(255, 200, 140, 1)',
    outer: 'rgba(255, 140, 60, 0.9)',
    glow: '#FF9500',
    text: '#ea580c'
  },
  contemplative: {
    inner: 'rgba(180, 200, 255, 1)',
    outer: 'rgba(140, 160, 255, 0.85)',
    glow: '#6B8CFF',
    text: '#2563eb'
  },
  social: {
    inner: 'rgba(255, 180, 210, 1)',
    outer: 'rgba(255, 120, 160, 0.9)',
    glow: '#FF6B9D',
    text: '#db2777'
  },
  creative: {
    inner: 'rgba(180, 255, 200, 1)',
    outer: 'rgba(100, 230, 170, 0.85)',
    glow: '#4AE68A',
    text: '#059669'
  },
  restless: {
    inner: 'rgba(255, 180, 210, 1)',
    outer: 'rgba(255, 80, 120, 0.9)',
    glow: '#E63B6E',
    text: '#dc2626'
  },
  calm: {
    inner: 'rgba(150, 210, 255, 1)',
    outer: 'rgba(100, 170, 255, 0.8)',
    glow: '#4A9EFF',
    text: '#0284c7'
  }
};

const MiniMemoryOrb = ({ 
  onClick, 
  size = 'default', // 'small' | 'default' | 'large'
  showState = true,
  mood: parentMood,         // When provided, uses parent's mood (single source of truth)
  energyLevel: parentEnergy, // When provided, uses parent's energy level
  className = '' 
}) => {
  const { isImmersive } = useViewMode();
  const [avatarState, setAvatarState] = useState(null);
  const [knowledgeWords, setKnowledgeWords] = useState([]);
  const [currentWord, setCurrentWord] = useState('');
  const [wordIndex, setWordIndex] = useState(0);
  const [isHovered, setIsHovered] = useState(false);
  const [isPressed, setIsPressed] = useState(false);

  // Only fetch avatar state independently if parent doesn't provide mood
  const shouldFetchState = parentMood === undefined;

  useEffect(() => {
    const fetchAvatarState = async () => {
      try {
        const response = await axios.get(`${API}/avatar/state`, { withCredentials: true });
        setAvatarState(response.data);
      } catch (error) {
        console.error('Error fetching avatar state:', error);
        setAvatarState({ mood: 'calm', current_state: 'passive', energy_level: 0.5 });
      }
    };

    const fetchMemory = async () => {
      try {
        const response = await axios.get(`${API}/avatar/full-memory`, { withCredentials: true });
        if (response.data.success) {
          const semantic = response.data.semantic_memory || {};
          const words = [
            ...(semantic.interests || []).slice(0, 4),
            ...(semantic.traits || []).slice(0, 2),
            ...(semantic.values || []).slice(0, 2)
          ].map(w => w.charAt(0).toUpperCase() + w.slice(1).replace(/_/g, ' '));
          
          setKnowledgeWords(words);
          if (words.length > 0) {
            setCurrentWord(words[0]);
          }
        }
      } catch (error) {
        console.error('Error fetching memory:', error);
      }
    };

    // Only fetch state if parent doesn't provide it
    if (shouldFetchState) {
      fetchAvatarState();
    }
    fetchMemory();

    const stateInterval = shouldFetchState ? setInterval(fetchAvatarState, 10000) : null;
    const memoryInterval = setInterval(fetchMemory, 30000);

    return () => {
      if (stateInterval) clearInterval(stateInterval);
      clearInterval(memoryInterval);
    };
  }, [shouldFetchState]);

  // Cycle through words
  useEffect(() => {
    if (knowledgeWords.length === 0) return;

    const interval = setInterval(() => {
      setWordIndex(prev => {
        const next = (prev + 1) % knowledgeWords.length;
        setCurrentWord(knowledgeWords[next] || '');
        return next;
      });
    }, 2000);

    return () => clearInterval(interval);
  }, [knowledgeWords]);

  // Use parent-provided mood/energy if available, otherwise use independent fetch
  const mood = parentMood || avatarState?.mood || 'calm';
  const currentState = avatarState?.current_state || 'passive';
  const energy = parentEnergy ?? avatarState?.energy_level ?? 0.5;
  const moodColors = moods[mood] || moods.calm;

  // Size configurations - smaller on mobile
  const sizeConfig = useMemo(() => {
    const isMobile = typeof window !== 'undefined' && window.innerWidth < 640;
    switch (size) {
      case 'small':
        return { orb: isMobile ? 48 : 56, container: isMobile ? 60 : 72, fontSize: 7, stateSize: 6 };
      case 'large':
        return { orb: isMobile ? 68 : 80, container: isMobile ? 84 : 100, fontSize: 10, stateSize: 9 };
      default:
        return { orb: isMobile ? 56 : 68, container: isMobile ? 72 : 88, fontSize: 8, stateSize: 7 };
    }
  }, [size]);

  const handleClick = useCallback(() => {
    onClick?.();
  }, [onClick]);

  return (
    <button
      onClick={handleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => { setIsHovered(false); setIsPressed(false); }}
      onMouseDown={() => setIsPressed(true)}
      onMouseUp={() => setIsPressed(false)}
      className={`relative flex-shrink-0 group ${className}`}
      style={{
        width: sizeConfig.container + 20,
        height: sizeConfig.container + 10,
      }}
      title="Click to speak with your avatar"
    >
      <style>{`
        @keyframes miniOrbBreathe {
          0%, 100% {
            transform: scale(1);
            box-shadow:
              0 0 20px 8px var(--outer-glow),
              0 0 40px 16px var(--aura-color);
          }
          50% {
            transform: scale(1.05);
            box-shadow:
              0 0 30px 12px var(--outer-glow),
              0 0 60px 24px var(--aura-color);
          }
        }

        @keyframes miniRingRotate {
          0% { transform: translate(-50%, -50%) rotate(0deg); }
          100% { transform: translate(-50%, -50%) rotate(360deg); }
        }

        @keyframes floatingWord {
          0%, 100% { 
            opacity: 0; 
            transform: translateY(0px);
          }
          10%, 90% { 
            opacity: 0.8; 
          }
          50% { 
            opacity: 1; 
            transform: translateY(-3px);
          }
        }

        @keyframes pulseRing {
          0% { transform: translate(-50%, -50%) scale(1); opacity: 0.6; }
          100% { transform: translate(-50%, -50%) scale(1.8); opacity: 0; }
        }
      `}</style>

      {/* Container with padding for glow and floating words */}
      <div 
        className="absolute inset-0 flex items-center justify-center"
        style={{
          '--inner-glow': moodColors.inner,
          '--outer-glow': moodColors.outer,
          '--aura-color': `${moodColors.glow}40`,
        }}
      >
        {/* Floating words around the orb */}
        {knowledgeWords.slice(0, 6).map((word, i) => {
          const positions = [
            { top: '5%', left: '10%' },
            { top: '5%', right: '10%' },
            { top: '45%', left: '0%' },
            { top: '45%', right: '0%' },
            { bottom: '10%', left: '15%' },
            { bottom: '10%', right: '15%' },
          ];
          const pos = positions[i] || positions[0];
          const delay = i * 0.8;
          const duration = 4 + (i % 3);
          
          return (
            <span
              key={i}
              style={{
                position: 'absolute',
                ...pos,
                whiteSpace: 'nowrap',
                fontSize: '8px',
                fontWeight: 600,
                letterSpacing: '0.3px',
                pointerEvents: 'none',
                color: isImmersive ? `${moodColors.glow}` : moodColors.text,
                textShadow: isImmersive 
                  ? `0 0 4px ${moodColors.glow}60` 
                  : `0 1px 2px rgba(255,255,255,0.8)`,
                animation: `floatingWord ${duration}s ease-in-out ${delay}s infinite`,
              }}
            >
              {word.length > 10 ? word.slice(0, 9) + '…' : word}
            </span>
          );
        })}

        {/* Pulse ring on hover */}
        {isHovered && (
          <div 
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              width: sizeConfig.orb,
              height: sizeConfig.orb,
              borderRadius: '50%',
              border: `1px solid ${moodColors.outer}`,
              animation: 'pulseRing 2s ease-out infinite',
            }}
          />
        )}

        {/* Main orb - different styles for immersive vs classical */}
        <div 
          style={{
            position: 'relative',
            width: sizeConfig.orb,
            height: sizeConfig.orb,
            borderRadius: '50%',
            background: isImmersive 
              ? `radial-gradient(
                  circle at 50% 50%,
                  rgba(10, 15, 30, 0.95) 0%,
                  rgba(10, 15, 30, 0.9) 45%,
                  ${moodColors.inner} 55%,
                  ${moodColors.outer} 70%,
                  transparent 85%
                )`
              : `radial-gradient(
                  circle at 50% 50%,
                  transparent 0%,
                  transparent 35%,
                  ${moodColors.inner} 42%,
                  ${moodColors.outer} 58%,
                  transparent 75%
                )`,
            boxShadow: `
              0 0 20px 8px ${moodColors.outer},
              0 0 40px 16px ${moodColors.glow}40
            `,
            animation: 'miniOrbBreathe 3s ease-in-out infinite',
            transform: isPressed ? 'scale(0.95)' : isHovered ? 'scale(1.1)' : 'scale(1)',
            transition: 'transform 0.15s ease',
            cursor: 'pointer',
          }}
        >
          {/* Inner ring */}
          <div 
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              width: '70%',
              height: '70%',
              borderRadius: '50%',
              border: `2px solid ${isImmersive ? moodColors.outer : 'rgba(255,255,255,0.9)'}`,
              boxShadow: `
                0 0 10px ${moodColors.outer},
                inset 0 0 10px ${moodColors.glow}30
              `,
              transform: 'translate(-50%, -50%)',
              animation: 'miniRingRotate 12s linear infinite',
            }}
          />
          
          {/* Center state text - static, transparent spirit feeling */}
          <div 
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              whiteSpace: 'nowrap',
              zIndex: 5,
              fontWeight: 600,
              letterSpacing: '0.5px',
              maxWidth: '90%',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              fontSize: sizeConfig.fontSize - 2,
              color: isImmersive ? 'rgba(255, 255, 255, 0.35)' : 'rgba(31, 41, 55, 0.6)',
              textShadow: isImmersive 
                ? `0 0 8px ${moodColors.glow}50` 
                : `0 0 8px rgba(255,255,255,0.8)`,
            }}
          >
            {mood.charAt(0).toUpperCase() + mood.slice(1)}
          </div>
        </div>
      </div>

      {/* Tooltip on hover */}
      {isHovered && (
        <div 
          className="absolute -top-8 left-1/2 transform -translate-x-1/2 whitespace-nowrap px-2 py-1 rounded-full text-[10px] font-medium tracking-wide uppercase"
          style={{
            background: isImmersive ? `${moodColors.glow}20` : 'rgba(255,255,255,0.95)',
            color: moodColors.text,
            border: `1px solid ${moodColors.glow}40`,
            boxShadow: isImmersive ? `0 0 8px ${moodColors.glow}30` : '0 2px 8px rgba(0,0,0,0.1)',
          }}
        >
          Click to speak
        </div>
      )}
    </button>
  );
};

export default MiniMemoryOrb;
