import { createContext, useContext, useState, useEffect } from 'react';

const WorldModeContext = createContext();

export const useWorldMode = () => {
  const context = useContext(WorldModeContext);
  if (!context) {
    throw new Error('useWorldMode must be used within WorldModeProvider');
  }
  return context;
};

export const WorldModeProvider = ({ children }) => {
  const [worldMode, setWorldMode] = useState(() => {
    // Load from localStorage
    return localStorage.getItem('worldMode') || 'real';
  });

  const toggleWorldMode = () => {
    const newMode = worldMode === 'real' ? 'avatar' : 'real';
    setWorldMode(newMode);
    localStorage.setItem('worldMode', newMode);
  };

  useEffect(() => {
    // Apply Avatar World styles
    if (worldMode === 'avatar') {
      document.body.classList.add('avatar-world');
    } else {
      document.body.classList.remove('avatar-world');
    }
  }, [worldMode]);

  return (
    <WorldModeContext.Provider value={{ worldMode, setWorldMode, toggleWorldMode }}>
      {children}
    </WorldModeContext.Provider>
  );
};
