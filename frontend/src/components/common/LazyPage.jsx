/**
 * LazyPage Component
 * Wrapper for lazy-loaded pages with Suspense and error boundary
 */

import { Suspense } from 'react';
import ErrorBoundary from './ErrorBoundary';
import LoadingSpinner from './LoadingSpinner';

const LazyPage = ({ children, fallback = null }) => {
  const defaultFallback = fallback || (
    <LoadingSpinner size="lg" message="Loading page..." fullScreen />
  );

  return (
    <ErrorBoundary>
      <Suspense fallback={defaultFallback}>
        {children}
      </Suspense>
    </ErrorBoundary>
  );
};

export default LazyPage;

