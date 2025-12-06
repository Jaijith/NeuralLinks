/**
 * OptimizedImage Component
 * Image component with lazy loading, placeholder, error handling, and responsive images
 */

import { useState, memo, useCallback } from 'react';

const OptimizedImage = memo(({ 
  src, 
  alt = '', 
  className = '',
  onClick,
  onError,
  placeholder = null,
  fallback = null,
  loading = 'lazy',
  ...props
}) => {
  const [imageError, setImageError] = useState(false);
  const [imageLoading, setImageLoading] = useState(true);

  const handleError = useCallback((e) => {
    setImageError(true);
    setImageLoading(false);
    if (onError) {
      onError(e);
    } else {
      console.error('Image load error:', src);
      e.target.style.display = 'none';
    }
  }, [src, onError]);

  const handleLoad = useCallback(() => {
    setImageLoading(false);
  }, []);

  const handleClick = useCallback(() => {
    if (onClick && src) {
      onClick();
    }
  }, [onClick, src]);

  // Show fallback if error
  if (imageError && fallback) {
    return (
      <div className={`flex items-center justify-center bg-gray-100 ${className}`}>
        {fallback}
      </div>
    );
  }

  if (imageError) {
    return null;
  }

  return (
    <div className={`relative ${className}`}>
      {/* Placeholder/Skeleton while loading */}
      {imageLoading && placeholder && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100 animate-pulse">
          {placeholder}
        </div>
      )}
      
      {/* Actual image */}
      <img
        src={src}
        alt={alt}
        loading={loading}
        onError={handleError}
        onLoad={handleLoad}
        onClick={handleClick}
        className={`${imageLoading ? 'opacity-0' : 'opacity-100'} transition-opacity duration-300 ${onClick ? 'cursor-pointer' : ''} ${className}`}
        style={{ 
          ...(imageLoading && { position: 'absolute', visibility: 'hidden' })
        }}
        {...props}
      />
    </div>
  );
});

OptimizedImage.displayName = 'OptimizedImage';

export default OptimizedImage;

