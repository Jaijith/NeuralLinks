/**
 * usePerformance Hook
 * Hook for tracking component render performance
 */

import { useEffect, useRef } from 'react';
import { logger } from '@/utils';

const usePerformance = (componentName) => {
  const renderCount = useRef(0);
  const lastRenderTime = useRef(performance.now());

  useEffect(() => {
    renderCount.current += 1;
    const now = performance.now();
    const renderTime = now - lastRenderTime.current;
    lastRenderTime.current = now;

    if (renderTime > 16) { // More than one frame (60fps = 16.67ms per frame)
      logger.warn(`${componentName} render #${renderCount.current} took ${renderTime.toFixed(2)}ms`);
    }

    return () => {
      // Cleanup
    };
  });

  return {
    renderCount: renderCount.current,
  };
};

export default usePerformance;

