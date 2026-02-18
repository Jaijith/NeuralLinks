/**
 * LoadingSpinner Component
 * Centralized loading spinner with customizable size and message
 * Mode-aware: adapts to immersive/classic view
 */

import { memo } from 'react';

const LoadingSpinner = memo(({ 
  size = 'md', 
  message = 'Loading...',
  fullScreen = false,
  className = ''
}) => {
  const sizeClasses = {
    sm: 'w-8 h-8 border-2',
    md: 'w-12 h-12 border-3',
    lg: 'w-16 h-16 border-4',
  };

  // Check if immersive mode is active via body classes (avoids hook dependency)
  const isImmersive = typeof document !== 'undefined' && document.body.classList.contains('view-immersive');

  const spinner = (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <div 
        className={`${sizeClasses[size]} ${isImmersive ? 'border-violet-400' : 'border-purple-400'} border-t-transparent rounded-full animate-spin mb-4`}
      />
      {message && (
        <p className={isImmersive ? 'text-slate-300' : 'text-gray-600'}>{message}</p>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${
        isImmersive ? 'bg-transparent' : 'bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50'
      }`}>
        {spinner}
      </div>
    );
  }

  return spinner;
});

LoadingSpinner.displayName = 'LoadingSpinner';

export default LoadingSpinner;

