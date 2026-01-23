/**
 * PostContent Component
 * Content section of a post (text and image)
 */

import { memo } from 'react';
import OptimizedImage from '@/components/common/OptimizedImage';

const PostContent = memo(({ post, className = '' }) => {
  const text = post.text || post.content || '';
  const imageUrl = post.image_url;
  const hasImage = imageUrl || post.has_image;

  const handleImageClick = () => {
    if (imageUrl) {
      window.open(imageUrl, '_blank');
    }
  };

  return (
    <div className={`px-3 sm:px-4 pb-3 overflow-hidden ${className}`}>
      {text && (
        <p className="text-sm leading-relaxed whitespace-pre-wrap break-words text-gray-800 mb-3">
          {text}
        </p>
      )}
      {hasImage && imageUrl && (
        <div className="mt-3 rounded-lg overflow-hidden">
          <OptimizedImage
            src={imageUrl}
            alt={text || 'Post image'}
            className="w-full max-h-96 object-cover"
            onClick={handleImageClick}
            loading="lazy"
            placeholder={
              <div className="w-full h-64 bg-gray-200 animate-pulse" />
            }
          />
        </div>
      )}
    </div>
  );
});

PostContent.displayName = 'PostContent';

export default PostContent;

