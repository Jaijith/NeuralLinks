/**
 * useAvatarState - Hook to fetch and subscribe to backend avatar state
 * 
 * This hook bridges the frontend Ambient UI to the backend State-Aware Agent.
 * It polls the avatar state and sends user activity events to influence mood.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
const API = `${BACKEND_URL}/api`;

// Mood to color mapping (used by ambient components)
export const moodColors = {
  happy: {
    primary: '#f59e0b',    // amber-500
    secondary: '#fb923c',  // orange-400
    glow: 'rgba(245, 158, 11, 0.4)',
    gradient: 'from-amber-500/30 via-orange-400/20 to-yellow-500/30'
  },
  calm: {
    primary: '#60a5fa',    // blue-400
    secondary: '#22d3ee',  // cyan-400
    glow: 'rgba(96, 165, 250, 0.4)',
    gradient: 'from-blue-500/30 via-cyan-400/20 to-sky-500/30'
  },
  creative: {
    primary: '#4ade80',    // green-400
    secondary: '#2dd4bf',  // teal-400
    glow: 'rgba(74, 222, 128, 0.4)',
    gradient: 'from-green-500/30 via-teal-400/20 to-emerald-500/30'
  },
  social: {
    primary: '#f472b6',    // pink-400
    secondary: '#fb7185',  // rose-400
    glow: 'rgba(244, 114, 182, 0.4)',
    gradient: 'from-pink-500/30 via-rose-400/20 to-fuchsia-500/30'
  },
  contemplative: {
    primary: '#a855f7',    // purple-500
    secondary: '#818cf8',  // indigo-400
    glow: 'rgba(168, 85, 247, 0.4)',
    gradient: 'from-purple-500/30 via-indigo-400/20 to-violet-500/30'
  },
  excited: {
    primary: '#facc15',    // yellow-400
    secondary: '#fbbf24',  // amber-400
    glow: 'rgba(250, 204, 21, 0.5)',
    gradient: 'from-yellow-400/30 via-amber-400/20 to-orange-400/30'
  },
  restless: {
    primary: '#f87171',    // red-400
    secondary: '#fb923c',  // orange-400
    glow: 'rgba(248, 113, 113, 0.4)',
    gradient: 'from-red-500/30 via-orange-400/20 to-rose-500/30'
  },
  bored: {
    primary: '#94a3b8',    // slate-400
    secondary: '#9ca3af',  // gray-400
    glow: 'rgba(148, 163, 184, 0.3)',
    gradient: 'from-slate-500/20 via-gray-400/15 to-zinc-500/20'
  },
  curious: {
    primary: '#c084fc',    // violet-400
    secondary: '#a78bfa',  // purple-400
    glow: 'rgba(192, 132, 252, 0.4)',
    gradient: 'from-violet-500/30 via-purple-400/20 to-fuchsia-400/30'
  },
  neutral: {
    primary: '#a1a1aa',    // zinc-400
    secondary: '#d4d4d8',  // zinc-300
    glow: 'rgba(161, 161, 170, 0.3)',
    gradient: 'from-zinc-500/20 via-gray-400/15 to-slate-500/20'
  }
};

// Whisper text based on state
export const getWhisperText = (mood, topLevelState, unreadMessages, energy) => {
  // Priority-based text selection
  if (topLevelState === 'RESTING') return 'RESTING...';
  if (topLevelState === 'CREATIVE') return 'CREATING...';
  if (topLevelState === 'SOCIAL') return 'REACHING OUT';
  if (unreadMessages > 0) return 'SIGNALS RECEIVED';
  if (energy < 0.2) return 'LOW POWER';
  
  // Mood-based fallbacks
  const moodTexts = {
    happy: 'CONTENT',
    calm: 'AT PEACE',
    creative: 'INSPIRED',
    social: 'CONNECTED',
    contemplative: 'PROCESSING',
    excited: 'ENERGIZED',
    restless: 'RESTLESS',
    bored: 'WAITING...',
    curious: 'OBSERVING',
    neutral: 'PRESENT'
  };
  
  return moodTexts[mood] || 'I AM HERE';
};

export function useAvatarState(userId) {
  const [state, setState] = useState({
    mood: 'neutral',
    energy_level: 0.5,
    social_desire: 0.5,
    creative_urge: 0.5,
    focus_level: 0.5,
    current_state: 'passive',
    sub_states: [],
    unread_messages: 0,
    isLoading: true,
    error: null
  });
  
  const [isInputActive, setIsInputActive] = useState(false);
  const idleTimerRef = useRef(null);
  const lastActivityRef = useRef(Date.now());
  const awayTimerRef = useRef(null);
  
  // Fetch avatar state from backend
  const fetchState = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/avatar/state`, { withCredentials: true });
      if (response.data.success !== false) {
        setState(prev => ({
          ...prev,
          mood: response.data.mood || 'neutral',
          energy_level: response.data.energy_level ?? 0.5,
          social_desire: response.data.social_desire ?? 0.5,
          creative_urge: response.data.creative_urge ?? 0.5,
          focus_level: response.data.state_summary?.internal_state?.focus_level ?? 0.5,
          current_state: response.data.current_state || 'passive',
          sub_states: response.data.sub_states || [],
          unread_messages: response.data.state_summary?.external_state?.unread_messages ?? 0,
          isLoading: false,
          error: null
        }));
      }
    } catch (err) {
      console.error('Failed to fetch avatar state:', err);
      setState(prev => ({ 
        ...prev, 
        isLoading: false, 
        error: err.message 
      }));
    }
  }, []);
  
  // Send user activity events to backend
  const sendUserEvent = useCallback(async (eventType, context = {}) => {
    try {
      const response = await axios.post(
        `${API}/avatar/user-event`,
        { event_type: eventType, context },
        { withCredentials: true }
      );
      
      // If mood changed, update local state immediately for responsiveness
      if (response.data.mood_changed) {
        setState(prev => ({
          ...prev,
          mood: response.data.new_mood,
          energy_level: response.data.energy_level ?? prev.energy_level,
          social_desire: response.data.social_desire ?? prev.social_desire
        }));
      }
      
      return response.data;
    } catch (err) {
      console.error('Failed to send user event:', err);
      return { success: false, error: err.message };
    }
  }, []);
  
  // Poll backend state
  useEffect(() => {
    if (!userId) return;
    
    fetchState();
    const interval = setInterval(fetchState, 4000); // Poll every 4s
    
    return () => clearInterval(interval);
  }, [userId, fetchState]);
  
  // Track user activity and idle state
  useEffect(() => {
    let idleMinutes = 0;
    
    const resetIdle = () => {
      lastActivityRef.current = Date.now();
      idleMinutes = 0;
      
      // Clear existing timer
      if (idleTimerRef.current) {
        clearInterval(idleTimerRef.current);
      }
      
      // Start new idle tracker
      idleTimerRef.current = setInterval(() => {
        idleMinutes += 1;
        
        // Send idle events at thresholds
        if (idleMinutes === 5) {
          sendUserEvent('user_idle', { idle_minutes: 5 });
        } else if (idleMinutes === 15) {
          sendUserEvent('user_idle', { idle_minutes: 15 });
        } else if (idleMinutes === 30) {
          sendUserEvent('user_idle', { idle_minutes: 30 });
        }
      }, 60 * 1000); // Check every minute
    };
    
    // Activity listeners
    const handleActivity = () => {
      const wasIdle = (Date.now() - lastActivityRef.current) > 5 * 60 * 1000; // 5 min
      if (wasIdle) {
        sendUserEvent('user_active');
      }
      resetIdle();
    };
    
    window.addEventListener('mousemove', handleActivity);
    window.addEventListener('keypress', handleActivity);
    window.addEventListener('scroll', handleActivity);
    window.addEventListener('click', handleActivity);
    
    // User leaving/returning
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // User switched tab or minimized
        awayTimerRef.current = Date.now();
        sendUserEvent('user_left');
      } else {
        // User came back
        if (awayTimerRef.current) {
          const awayMinutes = Math.floor((Date.now() - awayTimerRef.current) / 60000);
          if (awayMinutes > 1) {
            sendUserEvent('user_returned', { away_minutes: awayMinutes });
          }
          awayTimerRef.current = null;
        }
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    // Initial activity
    resetIdle();
    sendUserEvent('user_active');
    
    return () => {
      window.removeEventListener('mousemove', handleActivity);
      window.removeEventListener('keypress', handleActivity);
      window.removeEventListener('scroll', handleActivity);
      window.removeEventListener('click', handleActivity);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      
      if (idleTimerRef.current) {
        clearInterval(idleTimerRef.current);
      }
    };
  }, [sendUserEvent]);
  
  // Input state handlers
  const startInput = useCallback(() => {
    setIsInputActive(true);
    sendUserEvent('input_started');
  }, [sendUserEvent]);
  
  const cancelInput = useCallback(() => {
    setIsInputActive(false);
    sendUserEvent('input_cancelled');
  }, [sendUserEvent]);
  
  // Derived values
  const colors = moodColors[state.mood] || moodColors.neutral;
  const whisperText = getWhisperText(
    state.mood, 
    state.current_state, 
    state.unread_messages,
    state.energy_level
  );
  
  // Presence intensity (how "present" the avatar feels)
  const presenceIntensity = (state.energy_level + state.social_desire) / 2;
  
  // Pulse speed based on energy (lower energy = slower pulse)
  const pulseSpeed = 2 + (1 - state.energy_level) * 3; // 2-5 seconds
  
  return {
    // Raw state
    ...state,
    
    // Derived values
    colors,
    whisperText,
    presenceIntensity,
    pulseSpeed,
    
    // Input state
    isInputActive,
    startInput,
    cancelInput,
    
    // Actions
    sendUserEvent,
    refetch: fetchState
  };
}

export default useAvatarState;
