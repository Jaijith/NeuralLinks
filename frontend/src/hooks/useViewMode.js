/**
 * useViewMode - Hook for managing Classic vs Immersive view mode
 * 
 * Uses a shared state via custom event to sync across all components.
 * Persists user preference in localStorage.
 */

import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'maya_view_mode';
const VIEW_MODE_CHANGE_EVENT = 'maya_view_mode_change';

export const VIEW_MODES = {
  CLASSIC: 'classic',
  IMMERSIVE: 'immersive'
};

// Get initial value from localStorage
const getInitialMode = () => {
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === VIEW_MODES.IMMERSIVE ? VIEW_MODES.IMMERSIVE : VIEW_MODES.CLASSIC;
  }
  return VIEW_MODES.CLASSIC;
};

export function useViewMode() {
  const [viewMode, setViewMode] = useState(getInitialMode);

  // Listen for changes from other components
  useEffect(() => {
    const handleViewModeChange = (event) => {
      setViewMode(event.detail.viewMode);
    };
    
    window.addEventListener(VIEW_MODE_CHANGE_EVENT, handleViewModeChange);
    return () => window.removeEventListener(VIEW_MODE_CHANGE_EVENT, handleViewModeChange);
  }, []);

  // Persist to localStorage and broadcast when changed
  const updateViewMode = useCallback((newMode) => {
    localStorage.setItem(STORAGE_KEY, newMode);
    setViewMode(newMode);
    
    // Broadcast to other components
    window.dispatchEvent(new CustomEvent(VIEW_MODE_CHANGE_EVENT, {
      detail: { viewMode: newMode }
    }));
  }, []);

  const toggleViewMode = useCallback(() => {
    const newMode = viewMode === VIEW_MODES.CLASSIC ? VIEW_MODES.IMMERSIVE : VIEW_MODES.CLASSIC;
    updateViewMode(newMode);
  }, [viewMode, updateViewMode]);

  const setClassic = useCallback(() => updateViewMode(VIEW_MODES.CLASSIC), [updateViewMode]);
  const setImmersive = useCallback(() => updateViewMode(VIEW_MODES.IMMERSIVE), [updateViewMode]);

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
