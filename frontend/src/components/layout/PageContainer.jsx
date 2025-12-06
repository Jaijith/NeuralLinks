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
 * @property {string} [backgroundClass] - Background class (default: gradient)
 */

/**
 * Reusable Page Container component for consistent page layout across the app.
 * @param {PageContainerProps} props
 */
const PageContainer = React.memo(({ 
  children, 
  user, 
  setUser, 
  currentPage,
  className,
  showHeader = true,
  backgroundClass = "bg-gradient-to-br from-blue-50 via-white to-slate-50"
}) => {
  return (
    <div className={cn("min-h-screen", backgroundClass, className)}>
      {showHeader && (
        <AppHeader user={user} setUser={setUser} currentPage={currentPage} />
      )}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {children}
      </div>
    </div>
  );
});

PageContainer.displayName = "PageContainer";

export default PageContainer;

