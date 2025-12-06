import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { RefreshCw, Zap, Heart, Sparkles, TrendingUp, TrendingDown, Minus } from "lucide-react";
import axios from "axios";
import { useWorldMode } from "@/contexts/WorldModeContext";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
const API = `${BACKEND_URL}/api`;

// Mood color mapping with enhanced palettes
const moods = {
  happy: {
    inner: 'rgba(255, 200, 140, 1)',
    outer: 'rgba(255, 140, 60, 0.9)',
    aura: 'rgba(255, 80, 40, 0.45)',
    particle: '#FFB347',
    glow: '#FF6B35'
  },
  neutral: {
    inner: 'rgba(200, 180, 255, 1)',
    outer: 'rgba(160, 120, 255, 0.85)',
    aura: 'rgba(80, 40, 150, 0.5)',
    particle: '#B8A9FF',
    glow: '#7C5CFF'
  },
  curious: {
    inner: 'rgba(200, 180, 255, 1)',
    outer: 'rgba(160, 120, 255, 0.85)',
    aura: 'rgba(80, 40, 150, 0.5)',
    particle: '#C4B5FF',
    glow: '#9B7DFF'
  },
  bored: {
    inner: 'rgba(150, 150, 180, 1)',
    outer: 'rgba(120, 120, 150, 0.8)',
    aura: 'rgba(60, 60, 100, 0.4)',
    particle: '#9696B4',
    glow: '#6B6B8F'
  },
  excited: {
    inner: 'rgba(255, 200, 140, 1)',
    outer: 'rgba(255, 140, 60, 0.9)',
    aura: 'rgba(255, 80, 40, 0.45)',
    particle: '#FFCC70',
    glow: '#FF9500'
  },
  contemplative: {
    inner: 'rgba(180, 200, 255, 1)',
    outer: 'rgba(140, 160, 255, 0.85)',
    aura: 'rgba(60, 80, 150, 0.5)',
    particle: '#A8C0FF',
    glow: '#6B8CFF'
  },
  social: {
    inner: 'rgba(255, 180, 210, 1)',
    outer: 'rgba(255, 120, 160, 0.9)',
    aura: 'rgba(200, 40, 100, 0.5)',
    particle: '#FFB3D1',
    glow: '#FF6B9D'
  },
  creative: {
    inner: 'rgba(180, 255, 200, 1)',
    outer: 'rgba(100, 230, 170, 0.85)',
    aura: 'rgba(40, 140, 100, 0.5)',
    particle: '#A8FFB8',
    glow: '#4AE68A'
  },
  restless: {
    inner: 'rgba(255, 180, 210, 1)',
    outer: 'rgba(255, 80, 120, 0.9)',
    aura: 'rgba(150, 20, 60, 0.55)',
    particle: '#FF8FAB',
    glow: '#E63B6E'
  },
  calm: {
    inner: 'rgba(150, 210, 255, 1)',
    outer: 'rgba(100, 170, 255, 0.8)',
    aura: 'rgba(40, 80, 160, 0.45)',
    particle: '#96D2FF',
    glow: '#4A9EFF'
  }
};

// Floating memory particle component
const MemoryParticle = ({ word, delay, duration, angle, distance, color }) => {
  const style = {
    position: 'absolute',
    left: '50%',
    top: '50%',
    transform: `translate(-50%, -50%) rotate(${angle}deg) translateY(-${distance}px) rotate(-${angle}deg)`,
    fontSize: '10px',
    color: color || '#3b82f6',
    opacity: 0,
    whiteSpace: 'nowrap',
    textShadow: `0 0 8px rgba(59, 130, 246, 0.3)`,
    animation: `floatParticle ${duration}s ease-in-out ${delay}s infinite`,
    pointerEvents: 'none',
    fontWeight: '400',
    letterSpacing: '0.5px'
  };

  return <span style={style}>{word}</span>;
};

// Experience pulse component
const ExperiencePulse = ({ type, valence, delay }) => {
  const getColor = () => {
    if (valence > 0.3) return 'rgba(100, 255, 150, 0.6)';
    if (valence < -0.3) return 'rgba(255, 100, 100, 0.6)';
    return 'rgba(200, 200, 255, 0.6)';
  };

  return (
    <div
      style={{
        position: 'absolute',
        left: '50%',
        top: '50%',
        transform: 'translate(-50%, -50%)',
        width: '100%',
        height: '100%',
        borderRadius: '50%',
        border: `2px solid ${getColor()}`,
        opacity: 0,
        animation: `experiencePulse 3s ease-out ${delay}s infinite`
      }}
    />
  );
};

const MemoryOrb = ({ user, hideHeader = false }) => {
  const [avatarState, setAvatarState] = useState(null);
  const [fullMemory, setFullMemory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedMood, setSelectedMood] = useState(null);
  const [currentWord, setCurrentWord] = useState("");
  const [wordIndex, setWordIndex] = useState(0);
  const [knowledgeWords, setKnowledgeWords] = useState([]);
  const { worldMode } = useWorldMode();
  const isAvatarWorld = worldMode === 'avatar';
  const orbRef = useRef(null);

  useEffect(() => {
    fetchAvatarState();
    fetchFullMemory();
    
    const stateInterval = setInterval(fetchAvatarState, 5000);
    const memoryInterval = setInterval(fetchFullMemory, 15000);
    
    return () => {
      clearInterval(stateInterval);
      clearInterval(memoryInterval);
    };
  }, []);

  const fetchAvatarState = async () => {
    try {
      const response = await axios.get(`${API}/avatar/state`, { withCredentials: true });
      setAvatarState(response.data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching avatar state:", error);
      setAvatarState({ mood: "calm", current_state: "passive", energy_level: 0.5 });
      setLoading(false);
    }
  };

  const fetchFullMemory = async () => {
    try {
      const response = await axios.get(`${API}/avatar/full-memory`, { withCredentials: true });
      if (response.data.success) {
        setFullMemory(response.data);
        
        // Extract words for floating particles
        const semantic = response.data.semantic_memory || {};
        const words = [
          ...(semantic.interests || []).slice(0, 8),
          ...(semantic.traits || []).slice(0, 4),
          ...(semantic.values || []).slice(0, 4)
        ].map(w => w.charAt(0).toUpperCase() + w.slice(1).replace(/_/g, ' '));
        
        setKnowledgeWords(words);
        if (words.length > 0 && !currentWord) {
          setCurrentWord(words[0]);
        }
      }
    } catch (error) {
      console.error("Error fetching full memory:", error);
    }
  };

  // Cycle through words in center
  useEffect(() => {
    if (knowledgeWords.length === 0) return;

    const interval = setInterval(() => {
      setWordIndex(prev => {
        const next = (prev + 1) % knowledgeWords.length;
        setCurrentWord(knowledgeWords[next] || "");
        return next;
      });
    }, 2500);

    return () => clearInterval(interval);
  }, [knowledgeWords]);

  const mood = selectedMood || avatarState?.mood || "calm";
  const currentState = avatarState?.current_state || "passive";
  const energy = avatarState?.energy_level || 0.5;
  const socialDesire = avatarState?.social_desire || 0.5;
  const creativeUrge = avatarState?.creative_urge || 0.5;
  const moodColors = moods[mood] || moods.calm;

  // Get emotional trend icon
  const getTrendIcon = (trend) => {
    switch (trend) {
      case 'improving': return <TrendingUp className="w-4 h-4 text-green-400" />;
      case 'declining': return <TrendingDown className="w-4 h-4 text-red-400" />;
      default: return <Minus className="w-4 h-4 text-gray-400" />;
    }
  };

  // Dark color mapping for particles on light background
  const darkParticleColors = {
    happy: '#d97706',      // Darker orange
    neutral: '#7c3aed',    // Darker purple
    curious: '#8b5cf6',    // Darker purple-blue
    bored: '#64748b',       // Darker gray-blue
    excited: '#ea580c',    // Darker orange-red
    contemplative: '#2563eb', // Darker blue
    social: '#db2777',     // Darker pink
    creative: '#059669',   // Darker green
    restless: '#dc2626',   // Darker red
    calm: '#0284c7'        // Darker blue
  };

  // Generate floating particles with darker colors
  const particles = knowledgeWords.slice(0, 12).map((word, i) => ({
    word,
    delay: i * 0.5,
    duration: 8 + Math.random() * 4,
    angle: (360 / Math.min(knowledgeWords.length, 12)) * i,
    distance: 220 + Math.random() * 80, // Increased distance for bigger orb
    color: moodColors.particle,
    darkColor: darkParticleColors[mood] || '#1f2937' // Fallback to dark gray
  }));

  // Get recent experiences for pulses
  const recentExperiences = fullMemory?.episodic_memory?.recent_highlights || [];

  return (
    <div 
      className="memory-orb-page"
      style={{
        margin: '0 auto',
        minHeight: hideHeader ? 'auto' : '100vh',
        background: 'transparent',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#1f2937',
        fontFamily: '"SF Pro Display", -apple-system, BlinkMacSystemFont, sans-serif',
        overflow: 'visible',
        position: 'relative',
        padding: hideHeader ? '2rem' : '2rem',
        maxWidth: '900px',
        width: '100%'
      }}
    >
      <style>{`
        @keyframes floatParticle {
          0%, 100% {
            opacity: 0;
            transform: translate(-50%, -50%) rotate(var(--angle)) translateY(calc(-1 * var(--distance))) rotate(calc(-1 * var(--angle))) scale(0.8);
          }
          20%, 80% {
            opacity: 0.85;
          }
          50% {
            opacity: 1;
            transform: translate(-50%, -50%) rotate(var(--angle)) translateY(calc(-1 * var(--distance) - 20px)) rotate(calc(-1 * var(--angle))) scale(1);
          }
        }

        @keyframes experiencePulse {
          0% {
            transform: translate(-50%, -50%) scale(0.8);
            opacity: 0.8;
          }
          100% {
            transform: translate(-50%, -50%) scale(2);
            opacity: 0;
          }
        }

        @keyframes breathe {
          0%, 100% {
            transform: scale(1);
            box-shadow:
              0 0 30px 10px var(--outer-glow),
              0 0 80px 35px var(--aura-color);
          }
          50% {
            transform: scale(1.08);
            box-shadow:
              0 0 50px 20px var(--outer-glow),
              0 0 130px 60px var(--aura-color);
          }
        }

        @keyframes flicker {
          0%, 100% { opacity: 0.92; }
          25% { opacity: 1; }
          50% { opacity: 0.88; }
          75% { opacity: 0.98; }
        }

        @keyframes ringRotate {
          0% {
            transform: translate(-50%, -50%) rotate(0deg);
          }
          100% {
            transform: translate(-50%, -50%) rotate(360deg);
          }
        }

        @keyframes swirl {
          0% { transform: rotate(0deg) scale(1.05); }
          50% { transform: rotate(-180deg) scale(1.15); }
          100% { transform: rotate(-360deg) scale(1.05); }
        }

        @keyframes wordFade {
          0%, 100% { opacity: 0; transform: translate(-50%, -50%) scale(0.9); }
          15%, 85% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
        }

        @keyframes energyPulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.8; }
        }

        .memory-orb-page .orb-container {
          position: relative;
          width: 400px;
          height: 400px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .memory-orb-page .orb {
          position: relative;
          width: 300px;
          height: 300px;
          border-radius: 50%;
          background: radial-gradient(
            circle at 50% 50%,
            transparent 0%,
            transparent 35%,
            var(--inner-glow) 42%,
            var(--outer-glow) 58%,
            transparent 75%
          );
          filter: blur(1px);
          box-shadow:
            0 0 30px 10px var(--outer-glow),
            0 0 80px 35px var(--aura-color);
          animation:
            breathe 5s ease-in-out infinite,
            flicker 1.8s ease-in-out infinite;
        }

        .memory-orb-page .orb::before {
          content: "";
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          width: 200px;
          height: 200px;
          border-radius: 50%;
          border: 2px solid rgba(255, 255, 255, 0.9);
          box-shadow:
            0 0 20px rgba(255, 255, 255, 0.7),
            0 0 40px var(--inner-glow),
            inset 0 0 15px rgba(255, 255, 255, 0.4);
          animation: ringRotate 12s linear infinite;
        }

        .memory-orb-page .orb::after {
          content: "";
          position: absolute;
          inset: -20%;
          border-radius: 50%;
          background:
            radial-gradient(circle at 30% 20%, rgba(255,255,255,0.2), transparent 50%),
            radial-gradient(circle at 70% 30%, rgba(255,255,255,0.15), transparent 55%),
            radial-gradient(circle at 25% 70%, rgba(255,255,255,0.12), transparent 55%),
            radial-gradient(circle at 80% 75%, rgba(255,255,255,0.1), transparent 60%);
          opacity: 0.7;
          mix-blend-mode: screen;
          filter: blur(8px);
          animation: swirl 25s linear infinite;
        }

        .memory-orb-page .center-word {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          font-size: 15px;
          color: rgba(31, 41, 55, 0.9);
          white-space: nowrap;
          z-index: 15;
          font-weight: 600;
          letter-spacing: 1px;
          text-shadow: 0 0 10px rgba(255, 255, 255, 0.8);
          animation: wordFade 2.5s ease-in-out infinite;
          }

        .memory-orb-page .energy-ring {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          width: 360px;
          height: 360px;
          border-radius: 50%;
          border: 1px solid transparent;
          background: conic-gradient(
            from 0deg,
            transparent 0%,
            var(--outer-glow) calc(var(--energy) * 100%),
            transparent calc(var(--energy) * 100%)
          );
          mask: radial-gradient(transparent 90%, black 91%);
          -webkit-mask: radial-gradient(transparent 90%, black 91%);
          opacity: 0.6;
          animation: energyPulse 3s ease-in-out infinite;
        }

        .memory-orb-page .stat-bars {
          display: flex;
          gap: 1.5rem;
          margin-top: 3rem;
          padding: 1rem 1.5rem;
          background: rgba(255, 255, 255, 0.95);
          border-radius: 16px;
          border: 1px solid rgba(0, 0, 0, 0.08);
          backdrop-filter: blur(10px);
          box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08), 0 4px 24px rgba(0, 0, 0, 0.04);
        }

        .memory-orb-page .stat-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.5rem;
        }

        .memory-orb-page .stat-label {
          font-size: 10px;
          text-transform: uppercase;
          letter-spacing: 1px;
          opacity: 1;
          color: #1f2937;
          font-weight: 600;
        }

        .memory-orb-page .stat-bar {
          width: 60px;
          height: 4px;
          background: rgba(0, 0, 0, 0.1);
          border-radius: 2px;
          overflow: hidden;
        }

        .memory-orb-page .stat-fill {
          height: 100%;
          border-radius: 2px;
          transition: width 0.5s ease-out;
        }

        .memory-orb-page .memory-panel {
          position: relative;
          margin-top: 2rem;
          margin-bottom: 2rem;
          width: 100%;
          max-width: 600px;
          background: rgba(255, 255, 255, 0.95);
          border-radius: 20px;
          border: 1px solid rgba(0, 0, 0, 0.08);
          backdrop-filter: blur(20px);
          overflow: hidden;
          transition: all 0.3s ease;
          box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08), 0 4px 24px rgba(0, 0, 0, 0.04);
        }

        .memory-orb-page .memory-panel.collapsed {
          height: 50px;
        }

        .memory-orb-page .memory-panel.expanded {
          height: 300px;
        }

        .memory-orb-page .panel-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0.75rem 1.25rem;
          cursor: pointer;
          border-bottom: 1px solid rgba(0, 0, 0, 0.08);
          color: #1f2937;
        }

        .memory-orb-page .panel-tabs {
          display: flex;
          gap: 0.5rem;
          padding: 0.5rem 1rem;
          border-bottom: 1px solid rgba(0, 0, 0, 0.08);
        }

        .memory-orb-page .panel-tab {
          padding: 0.4rem 0.8rem;
          font-size: 11px;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s;
          background: transparent;
          border: 1px solid rgba(0, 0, 0, 0.1);
          color: #6b7280;
        }

        .memory-orb-page .panel-tab.active {
          background: rgba(59, 130, 246, 0.1);
          color: #3b82f6;
          border-color: rgba(59, 130, 246, 0.3);
        }

        .memory-orb-page .panel-content {
          padding: 1rem 1.25rem;
          height: calc(100% - 100px);
          overflow-y: auto;
        }

        .memory-orb-page .memory-item {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.5rem 0;
          border-bottom: 1px solid rgba(0, 0, 0, 0.05);
          color: #374151;
        }

        .memory-orb-page .memory-tag {
          display: inline-block;
          padding: 0.25rem 0.6rem;
          font-size: 11px;
          border-radius: 12px;
          background: rgba(59, 130, 246, 0.1);
          margin: 0.15rem;
          color: #3b82f6;
        }

        .memory-orb-page .action-stat {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.4rem 0;
          font-size: 12px;
        }

        .memory-orb-page .success-bar {
          width: 80px;
          height: 6px;
          background: rgba(0, 0, 0, 0.1);
          border-radius: 3px;
          overflow: hidden;
        }

        .memory-orb-page .success-fill {
          height: 100%;
          background: linear-gradient(90deg, #4ade80, #22c55e);
          border-radius: 3px;
        }

        .memory-orb-page .mood-selector {
          display: flex;
          flex-direction: row;
          justify-content: center;
          align-items: center;
          gap: 12px;
          z-index: 20;
        }

        .memory-orb-page .mood-btn {
          width: 44px;
          height: 44px;
          border-radius: 50%;
          border: none;
          background: #ffffff !important;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 18px;
          transition: all 0.2s;
          border: 2px solid rgba(0, 0, 0, 0.3) !important;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25), 0 2px 4px rgba(0, 0, 0, 0.15) !important;
        }

        .memory-orb-page .mood-btn:hover {
          transform: scale(1.15);
          background: #ffffff !important;
          box-shadow: 0 6px 18px rgba(0, 0, 0, 0.3), 0 3px 6px rgba(0, 0, 0, 0.2) !important;
          border-color: rgba(0, 0, 0, 0.4) !important;
        }

        .memory-orb-page .mood-btn.active {
          border: 3px solid #2563eb !important;
          box-shadow: 0 0 25px rgba(37, 99, 235, 0.6), 0 4px 12px rgba(0, 0, 0, 0.25) !important;
          background: #ffffff !important;
        }
      `}</style>

      {/* Header with refresh */}
      {!hideHeader && (
        <div style={{ 
          position: 'absolute', 
          top: '1rem', 
          right: '1rem',
          display: 'flex',
          gap: '0.5rem'
        }}>
        <Button
            onClick={() => { fetchAvatarState(); fetchFullMemory(); }}
          variant="outline"
          size="sm"
            style={{
              background: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid rgba(0, 0, 0, 0.1)',
              color: '#374151'
            }}
        >
          <RefreshCw className="w-4 h-4" />
        </Button>
        </div>
      )}

      {/* Main Orb Scene */}
      <div style={{ 
        position: 'relative', 
        flex: 1, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        width: '100%',
        maxHeight: '500px',
        marginTop: hideHeader ? '4rem' : '5rem',
        marginBottom: '2rem'
      }}>
        <div 
          className="orb-container"
          style={{
            '--inner-glow': moodColors.inner,
            '--outer-glow': moodColors.outer,
            '--aura-color': moodColors.aura,
            '--energy': energy
          }}
        >
          {/* Energy ring */}
          <div className="energy-ring" />
          
          {/* Experience pulses */}
          {recentExperiences.slice(0, 3).map((exp, i) => (
            <ExperiencePulse 
              key={i}
              type={exp.type}
              valence={exp.valence || 0}
              delay={i * 1.5}
            />
          ))}
          
          {/* Main orb */}
          <div className="orb" ref={orbRef}>
          {currentWord && (
              <div className="center-word">{currentWord}</div>
          )}
        </div>
        
          {/* Floating memory particles */}
          {particles.map((p, i) => (
            <span
              key={i}
              style={{
                position: 'absolute',
                left: '50%',
                top: '50%',
                '--angle': `${p.angle}deg`,
                '--distance': `${p.distance}px`,
                transform: `translate(-50%, -50%) rotate(${p.angle}deg) translateY(-${p.distance}px) rotate(-${p.angle}deg)`,
                fontSize: '12px',
                color: p.darkColor || '#1f2937',
                opacity: 0,
                whiteSpace: 'nowrap',
                textShadow: '0 1px 2px rgba(255, 255, 255, 0.8), 0 0 4px rgba(0, 0, 0, 0.1)',
                animation: `floatParticle ${p.duration}s ease-in-out ${p.delay}s infinite`,
                pointerEvents: 'none',
                fontWeight: '600',
                letterSpacing: '0.5px'
              }}
            >
              {p.word}
            </span>
          ))}
        </div>

      </div>

      {/* State info */}
      <div style={{ textAlign: 'center', marginTop: '2.5rem' }}>
        <div style={{ 
          fontSize: '24px', 
          fontWeight: '700',
          color: '#d97706',
          textTransform: 'capitalize',
          letterSpacing: '1px'
        }}>
          {mood}
          {selectedMood && <span style={{ fontSize: '10px', opacity: 0.5, marginLeft: '8px' }}>(manual)</span>}
        </div>
        <div style={{ fontSize: '14px', opacity: 1, marginTop: '0.5rem', color: '#1f2937', fontWeight: '600' }}>
          State: {currentState}
        </div>
      </div>

      {/* Stat bars */}
      <div className="stat-bars">
        <div className="stat-item">
          <Zap className="w-4 h-4" style={{ color: '#d97706' }} />
          <div className="stat-bar">
            <div className="stat-fill" style={{ width: `${energy * 100}%`, background: 'linear-gradient(90deg, #d97706, #ea580c)' }} />
          </div>
          <span className="stat-label">Energy</span>
        </div>
        <div className="stat-item">
          <Heart className="w-4 h-4" style={{ color: '#db2777' }} />
          <div className="stat-bar">
            <div className="stat-fill" style={{ width: `${socialDesire * 100}%`, background: 'linear-gradient(90deg, #db2777, #be185d)' }} />
          </div>
          <span className="stat-label">Social</span>
        </div>
        <div className="stat-item">
          <Sparkles className="w-4 h-4" style={{ color: '#0891b2' }} />
          <div className="stat-bar">
            <div className="stat-fill" style={{ width: `${creativeUrge * 100}%`, background: 'linear-gradient(90deg, #0891b2, #0e7490)' }} />
          </div>
          <span className="stat-label">Creative</span>
        </div>
      </div>

      {/* Mood selector - Horizontal below stat bars */}
      <div className="mood-selector" style={{ display: 'flex', justifyContent: 'center', gap: '12px', marginTop: '2rem', marginBottom: '1.5rem' }}>
        {Object.entries(moods).slice(0, 6).map(([moodName, _]) => (
          <button 
            key={moodName}
            className={`mood-btn ${mood === moodName ? 'active' : ''}`}
            onClick={() => setSelectedMood(moodName)}
            title={moodName}
          >
            {moodName === 'happy' && '😊'}
            {moodName === 'neutral' && '😐'}
            {moodName === 'curious' && '🤔'}
            {moodName === 'bored' && '😑'}
            {moodName === 'excited' && '🤩'}
            {moodName === 'contemplative' && '🧘'}
          </button>
        ))}
      </div>

    </div>
  );
};

export default MemoryOrb;
