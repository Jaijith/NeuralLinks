/**
 * useSwipeNavigation Hook
 * Enables swipe gestures for navigation in PWA
 * 
 * Navigation flow (like pages in a book):
 *   Home ←→ Profile
 * 
 * Swipe right (finger moves left→right): go to previous page
 * Swipe left (finger moves right→left): go to next page
 */

import { useEffect, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const useSwipeNavigation = (options = {}) => {
  const {
    threshold = 80,
    enabled = true,
  } = options;

  const navigate = useNavigate();
  const location = useLocation();
  const touchStartX = useRef(0);
  const touchEndX = useRef(0);
  const touchStartY = useRef(0);
  const touchEndY = useRef(0);
  const isSwiping = useRef(false);
  const isHorizontalSwipe = useRef(false);

  // Simple two-page navigation: Home ↔ Profile
  const navigationMap = {
    '/':          { swipeRight: '/myprofile', swipeLeft: '/myprofile' },
    '/home':      { swipeRight: '/myprofile', swipeLeft: '/myprofile' },
    '/myprofile': { swipeRight: '/home',      swipeLeft: '/home' },
  };

  const handleTouchStart = useCallback((e) => {
    if (!enabled) return;
    
    // Don't swipe if a dialog/popup/overlay is open
    if (document.querySelector('[data-state="open"][role="dialog"]') ||
        document.querySelector('[data-radix-dialog-overlay]') ||
        document.querySelector('[data-story-popup="open"]') ||
        document.querySelector('[data-radix-dropdown-menu-content]')) {
      return;
    }

    const startX = e.touches[0].clientX;
    const screenWidth = window.innerWidth;

    // Don't intercept edge swipes (iOS back/forward gesture zones)
    if (startX < 25 || startX > screenWidth - 25) return;
    
    // Don't intercept swipes on scrollable containers
    const target = e.target;
    if (target.closest('.overflow-x-auto') || target.closest('.scrollbar-hide')) return;

    touchStartX.current = startX;
    touchStartY.current = e.touches[0].clientY;
    touchEndX.current = startX;
    touchEndY.current = e.touches[0].clientY;
    isSwiping.current = true;
    isHorizontalSwipe.current = false;
  }, [enabled]);

  const handleTouchMove = useCallback((e) => {
    if (!isSwiping.current) return;
    
    touchEndX.current = e.touches[0].clientX;
    touchEndY.current = e.touches[0].clientY;

    // Once we detect a clear horizontal swipe, prevent default to stop
    // iOS Safari from consuming the gesture for its own back/forward navigation
    const deltaX = Math.abs(touchEndX.current - touchStartX.current);
    const deltaY = Math.abs(touchEndY.current - touchStartY.current);
    
    if (!isHorizontalSwipe.current && deltaX > 15 && deltaX > deltaY * 1.8) {
      isHorizontalSwipe.current = true;
    }
    
    if (isHorizontalSwipe.current) {
      e.preventDefault();
    }
  }, []);

  const handleTouchEnd = useCallback(() => {
    if (!isSwiping.current || !enabled) return;
    
    const deltaX = touchEndX.current - touchStartX.current;
    const deltaY = touchEndY.current - touchStartY.current;
    
    // Only trigger if horizontal swipe is significantly greater than vertical
    if (Math.abs(deltaX) > Math.abs(deltaY) * 1.5 && Math.abs(deltaX) > threshold) {
      const currentPath = location.pathname;
      const navConfig = navigationMap[currentPath];
      
      if (navConfig) {
        if (deltaX > 0 && navConfig.swipeRight) {
          navigate(navConfig.swipeRight);
        } else if (deltaX < 0 && navConfig.swipeLeft) {
          navigate(navConfig.swipeLeft);
        }
      }
    }
    
    // Reset
    isSwiping.current = false;
    isHorizontalSwipe.current = false;
    touchStartX.current = 0;
    touchEndX.current = 0;
    touchStartY.current = 0;
    touchEndY.current = 0;
  }, [enabled, threshold, navigate, location.pathname]);

  useEffect(() => {
    if (!enabled) return;
    
    // Check for touch support (works on both iOS and Android)
    const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    if (!hasTouch) return;

    // touchstart: passive is fine (we don't preventDefault here)
    document.addEventListener('touchstart', handleTouchStart, { passive: true });
    // touchmove: MUST be { passive: false } so we can preventDefault() on iOS
    // This prevents iOS Safari from consuming horizontal swipes for back/forward
    document.addEventListener('touchmove', handleTouchMove, { passive: false });
    // touchend: passive is fine
    document.addEventListener('touchend', handleTouchEnd, { passive: true });

    return () => {
      document.removeEventListener('touchstart', handleTouchStart);
      document.removeEventListener('touchmove', handleTouchMove);
      document.removeEventListener('touchend', handleTouchEnd);
    };
  }, [enabled, handleTouchStart, handleTouchMove, handleTouchEnd]);

  return {
    isSwipeEnabled: enabled && ('ontouchstart' in window || navigator.maxTouchPoints > 0),
  };
};

export default useSwipeNavigation;
