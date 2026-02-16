/**
 * PostContent Component
 * Content section of a post (text, links, and image)
 * - Auto-detects URLs in text and makes them clickable
 * - Shows a link preview card for the first URL found
 */

import { memo, useMemo } from 'react';
import OptimizedImage from '@/components/common/OptimizedImage';
import useViewMode from '@/hooks/useViewMode';

// Regex to detect URLs in text
const URL_REGEX = /(https?:\/\/[^\s<>"{}|\\^`[\]]+)/g;

/**
 * Extract a display-friendly domain from a URL
 * e.g. "https://www.bbc.com/news/article-123" → "bbc.com"
 */
function extractDomain(url) {
  try {
    const hostname = new URL(url).hostname;
    return hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

/**
 * Render post text with clickable links
 * Splits text on URLs and wraps each URL in an <a> tag
 */
function renderTextWithLinks(text, isImmersive) {
  if (!text) return null;

  const parts = text.split(URL_REGEX);
  if (parts.length === 1) return text; // No URLs found

  return parts.map((part, i) => {
    if (URL_REGEX.test(part)) {
      // Reset regex lastIndex (it's stateful with /g flag)
      URL_REGEX.lastIndex = 0;
      return (
        <a
          key={i}
          href={part}
          target="_blank"
          rel="noopener noreferrer"
          className={`underline decoration-1 underline-offset-2 break-all ${
            isImmersive
              ? 'text-blue-400 hover:text-blue-300'
              : 'text-blue-600 hover:text-blue-700'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          {extractDomain(part)}
        </a>
      );
    }
    return part;
  });
}

/**
 * Link preview card — shows domain, source name, and news title
 * from post metadata (if available)
 */
const LinkPreviewCard = memo(({ url, metadata, isImmersive }) => {
  const domain = extractDomain(url);
  const newsTitle = metadata?.news_title || '';
  const newsSource = metadata?.news_source || domain;

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={`block rounded-lg border overflow-hidden transition-colors mb-3 ${
        isImmersive
          ? 'border-slate-600 bg-slate-800/50 hover:bg-slate-700/50'
          : 'border-gray-200 bg-gray-50 hover:bg-gray-100'
      }`}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="px-3 py-2.5">
        <div className="flex items-center gap-1.5 mb-1">
          <svg
            className={`w-3.5 h-3.5 flex-shrink-0 ${isImmersive ? 'text-gray-400' : 'text-gray-500'}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          <span className={`text-xs font-medium truncate ${isImmersive ? 'text-gray-400' : 'text-gray-500'}`}>
            {newsSource}
          </span>
        </div>
        {newsTitle && (
          <p className={`text-sm font-medium leading-snug line-clamp-2 ${isImmersive ? 'text-gray-200' : 'text-gray-800'}`}>
            {newsTitle}
          </p>
        )}
        <p className={`text-xs mt-1 truncate ${isImmersive ? 'text-blue-400' : 'text-blue-600'}`}>
          {domain}
        </p>
      </div>
    </a>
  );
});
LinkPreviewCard.displayName = 'LinkPreviewCard';

const PostContent = memo(({ post, className = '' }) => {
  const { isImmersive } = useViewMode();
  const text = post.text || post.content || '';
  const imageUrl = post.image_url;
  const hasImage = imageUrl || post.has_image;
  const metadata = post.metadata;

  // Extract first URL from text for the link preview card
  const firstUrl = useMemo(() => {
    if (!text) return null;
    // Check metadata first (more reliable)
    if (metadata?.news_url) return metadata.news_url;
    const match = text.match(URL_REGEX);
    URL_REGEX.lastIndex = 0;
    return match ? match[0] : null;
  }, [text, metadata]);

  const handleImageClick = () => {
    if (imageUrl) {
      window.open(imageUrl, '_blank');
    }
  };

  return (
    <div className={`px-3 sm:px-4 pb-3 overflow-hidden ${className}`}>
      {text && (
        <p className={`text-sm leading-relaxed whitespace-pre-wrap break-words mb-3 ${isImmersive ? 'text-gray-200' : 'text-gray-800'}`}>
          {renderTextWithLinks(text, isImmersive)}
        </p>
      )}

      {/* Link preview card for news posts */}
      {firstUrl && (
        <LinkPreviewCard url={firstUrl} metadata={metadata} isImmersive={isImmersive} />
      )}

      {hasImage && imageUrl && (
        <div className="rounded-lg overflow-hidden">
          <OptimizedImage
            src={imageUrl}
            alt={text || 'Post image'}
            className="w-full max-h-96 object-cover"
            onClick={handleImageClick}
            loading="lazy"
            placeholder={
              <div className={`w-full h-64 animate-pulse ${isImmersive ? 'bg-slate-700' : 'bg-gray-200'}`} />
            }
          />
        </div>
      )}
    </div>
  );
});

PostContent.displayName = 'PostContent';

export default PostContent;

