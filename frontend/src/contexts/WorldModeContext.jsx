import { createContext, useContext, useState, useEffect } from 'react';

const WorldModeContext = createContext();

// Storage key for view mode (same as useViewMode hook)
const VIEW_MODE_STORAGE_KEY = 'maya_view_mode';
const VIEW_MODE_CHANGE_EVENT = 'maya_view_mode_change';

export const useWorldMode = () => {
  const context = useContext(WorldModeContext);
  if (!context) {
    throw new Error('useWorldMode must be used within WorldModeProvider');
  }
  return context;
};

export const WorldModeProvider = ({ children }) => {
  const [worldMode, setWorldModeState] = useState(() => {
    // Load from localStorage
    return localStorage.getItem('worldMode') || 'real';
  });

  // Custom setter that also handles view mode for Sense world
  const setWorldMode = (newMode) => {
    setWorldModeState(newMode);
    localStorage.setItem('worldMode', newMode);
    
    // Force classic mode when switching to Sense (real) world
    if (newMode === 'real') {
      localStorage.setItem(VIEW_MODE_STORAGE_KEY, 'classic');
      document.body.classList.remove('view-immersive');
      document.body.classList.add('view-classic');
      // Broadcast the view mode change
      window.dispatchEvent(new CustomEvent(VIEW_MODE_CHANGE_EVENT, {
        detail: { viewMode: 'classic' }
      }));
    }
  };

  const toggleWorldMode = () => {
    const newMode = worldMode === 'real' ? 'avatar' : 'real';
    setWorldMode(newMode);
  };

  useEffect(() => {
    // Apply Avatar World styles
    if (worldMode === 'avatar') {
      document.body.classList.add('avatar-world');
    } else {
      document.body.classList.remove('avatar-world');
      // Ensure classic mode is set for Sense world
      document.body.classList.remove('view-immersive');
      document.body.classList.add('view-classic');
    }
  }, [worldMode]);

  return (
    <WorldModeContext.Provider value={{ worldMode, setWorldMode, toggleWorldMode }}>
      {children}
    </WorldModeContext.Provider>
  );
};
