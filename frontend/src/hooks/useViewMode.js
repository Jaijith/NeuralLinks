/**
 * useViewMode - Hook for managing Classic vs Immersive view mode
 * 
 * Uses a shared state via custom event to sync across all components.
 * Persists user preference in localStorage.
 * 
 * Note: Sense (real) world always uses Classic mode.
 * Immersive mode is only available for Maya (avatar) world.
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
    // Check if we're in Sense (real) world - always return classic
    const worldMode = localStorage.getItem('worldMode');
    if (worldMode === 'real') {
      return VIEW_MODES.CLASSIC;
    }
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === VIEW_MODES.IMMERSIVE ? VIEW_MODES.IMMERSIVE : VIEW_MODES.CLASSIC;
  }
  return VIEW_MODES.CLASSIC;
};

// Check if currently in Maya world
const isInMayaWorld = () => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('worldMode') === 'avatar';
  }
  return false;
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

  // Also listen for world mode changes to force classic in Sense world
  useEffect(() => {
    const handleStorageChange = () => {
      const worldMode = localStorage.getItem('worldMode');
      if (worldMode === 'real') {
        // Force classic mode for Sense world
        setViewMode(VIEW_MODES.CLASSIC);
        document.body.classList.remove('view-immersive');
        document.body.classList.add('view-classic');
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  // Update body class when view mode changes
  useEffect(() => {
    document.body.classList.remove('view-classic', 'view-immersive');
    document.body.classList.add(`view-${viewMode}`);
  }, [viewMode]);

  // Persist to localStorage and broadcast when changed
  const updateViewMode = useCallback((newMode) => {
    // Don't allow immersive mode in Sense world
    if (newMode === VIEW_MODES.IMMERSIVE && !isInMayaWorld()) {
      console.warn('Immersive mode is only available in Maya world');
      return;
    }
    
    localStorage.setItem(STORAGE_KEY, newMode);
    setViewMode(newMode);
    
    // Broadcast to other components
    window.dispatchEvent(new CustomEvent(VIEW_MODE_CHANGE_EVENT, {
      detail: { viewMode: newMode }
    }));
  }, []);

  const toggleViewMode = useCallback(() => {
    // Don't toggle if in Sense world - stay in classic
    if (!isInMayaWorld()) {
      return;
    }
    const newMode = viewMode === VIEW_MODES.CLASSIC ? VIEW_MODES.IMMERSIVE : VIEW_MODES.CLASSIC;
    updateViewMode(newMode);
  }, [viewMode, updateViewMode]);

  const setClassic = useCallback(() => updateViewMode(VIEW_MODES.CLASSIC), [updateViewMode]);
  const setImmersive = useCallback(() => {
    // Only allow in Maya world
    if (isInMayaWorld()) {
      updateViewMode(VIEW_MODES.IMMERSIVE);
    }
  }, [updateViewMode]);

  // For Sense world, always return classic regardless of state
  const effectiveViewMode = isInMayaWorld() ? viewMode : VIEW_MODES.CLASSIC;
  const effectiveIsImmersive = isInMayaWorld() && viewMode === VIEW_MODES.IMMERSIVE;

  return {
    viewMode: effectiveViewMode,
    isImmersive: effectiveIsImmersive,
    isClassic: !effectiveIsImmersive,
    toggleViewMode,
    setClassic,
    setImmersive,
    // Expose whether immersive is allowed (only in Maya)
    canUseImmersive: isInMayaWorld()
  };
}

export default useViewMode;
