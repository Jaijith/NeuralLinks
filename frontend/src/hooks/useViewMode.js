/**
 * useViewMode - Hook for managing Classic vs Immersive view mode
 * 
 * Persists user preference in localStorage.
 */

import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'maya_view_mode';

export const VIEW_MODES = {
  CLASSIC: 'classic',
  IMMERSIVE: 'immersive'
};

export function useViewMode() {
  const [viewMode, setViewMode] = useState(() => {
    // Initialize from localStorage
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored === VIEW_MODES.IMMERSIVE ? VIEW_MODES.IMMERSIVE : VIEW_MODES.CLASSIC;
    }
    return VIEW_MODES.CLASSIC;
  });

  // Persist to localStorage when changed
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, viewMode);
  }, [viewMode]);

  const toggleViewMode = useCallback(() => {
    setViewMode(prev => 
      prev === VIEW_MODES.CLASSIC ? VIEW_MODES.IMMERSIVE : VIEW_MODES.CLASSIC
    );
  }, []);

  const setClassic = useCallback(() => setViewMode(VIEW_MODES.CLASSIC), []);
  const setImmersive = useCallback(() => setViewMode(VIEW_MODES.IMMERSIVE), []);

  return {
    viewMode,
    isImmersive: viewMode === VIEW_MODES.IMMERSIVE,
    isClassic: viewMode === VIEW_MODES.CLASSIC,
    toggleViewMode,
    setClassic,
    setImmersive
  };
}

export default useViewMode;
