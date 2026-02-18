import React from 'react';
import AppHeader from '@/components/AppHeader';
import { cn } from '@/lib/utils';

/**
 * @typedef {Object} PageContainerProps
 * @property {React.ReactNode} children - Page content
 * @property {Object} user - Current user object
 * @property {function} setUser - User setter function
 * @property {string} [currentPage] - Current page identifier
 * @property {string} [className] - Additional CSS classes for container
 * @property {boolean} [showHeader] - Whether to show header (default: true)
 * @property {string} [backgroundClass] - Background class (default: gradient, auto-adapts to immersive)
 * @property {boolean} [hasBottomNav] - Whether page has bottom navigation (for mobile padding)
 * @property {boolean} [fullWidth] - Whether to use full width (no max-width container)
 */

/**
 * Reusable Page Container component for consistent page layout across the app.
 * Includes responsive padding, safe area support, and mobile bottom nav handling.
 * Auto-adapts background to immersive mode via body class detection.
 * @param {PageContainerProps} props
 */
const PageContainer = React.memo(({ 
  children, 
  user, 
  setUser, 
  currentPage,
  className,
  showHeader = true,
  backgroundClass,
  hasBottomNav = true,
  fullWidth = false
}) => {
  // Auto-detect immersive mode for background
  const isImmersive = typeof document !== 'undefined' && document.body.classList.contains('view-immersive');
  const defaultBg = isImmersive ? 'bg-transparent' : 'bg-gradient-to-br from-blue-50 via-white to-slate-50';
  const effectiveBgClass = backgroundClass !== undefined ? backgroundClass : defaultBg;
  return (
    <div 
      className={cn(
        // Use dynamic viewport height for mobile
        "min-h-screen-safe min-h-[100dvh]",
        effectiveBgClass, 
        className
      )}
      style={{
        // Add top padding to account for fixed header (56px + safe area)
        paddingTop: showHeader ? 'calc(56px + env(safe-area-inset-top, 0px))' : undefined,
      }}
    >
      {showHeader && (
        <AppHeader user={user} setUser={setUser} currentPage={currentPage} />
      )}
      <main 
        id="main-content"
        className={cn(
          // Responsive horizontal padding
          "px-3 sm:px-4 md:px-6",
          // Responsive vertical padding
          "py-4 sm:py-6",
          // Max width container (unless fullWidth)
          !fullWidth && "max-w-7xl mx-auto",
          // Add bottom padding for mobile bottom navigation
          hasBottomNav && "pb-20 sm:pb-6"
        )}
      >
        {children}
      </main>
    </div>
  );
});

PageContainer.displayName = "PageContainer";

export default PageContainer;

