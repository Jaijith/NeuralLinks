/**
 * AvatarStoriesRow - Horizontal scrollable row of friend avatars with mood rings
 * 
 * Instagram-style stories: shows friends' avatars with colored gradient rings.
 * Clicking a friend opens a popup showing their most recent post.
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { useWorldMode } from '@/contexts/WorldModeContext';
import { friendService, postService } from '@/services/api';
import { Plus, X, Heart, MessageCircle, Globe, Clock, ChevronLeft, ChevronRight } from 'lucide-react';
import useViewMode from '@/hooks/useViewMode';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

// Mood to color mapping - gradient colors for the ring
const MOOD_COLORS = {
  calm: { start: '#4ade80', end: '#22d3ee', name: 'Calm' },
  happy: { start: '#fbbf24', end: '#f97316', name: 'Happy' },
  curious: { start: '#60a5fa', end: '#8b5cf6', name: 'Curious' },
  excited: { start: '#f472b6', end: '#ec4899', name: 'Excited' },
  thoughtful: { start: '#818cf8', end: '#6366f1', name: 'Thoughtful' },
  playful: { start: '#fb923c', end: '#f97316', name: 'Playful' },
  neutral: { start: '#94a3b8', end: '#64748b', name: 'Neutral' },
  focused: { start: '#14b8a6', end: '#0d9488', name: 'Focused' },
  relaxed: { start: '#a78bfa', end: '#8b5cf6', name: 'Relaxed' },
  energetic: { start: '#ef4444', end: '#f97316', name: 'Energetic' },
};

const DEFAULT_MOOD = 'neutral';

/**
 * Helper to get relative time string
 */
const getRelativeTime = (dateStr) => {
  if (!dateStr) return '';
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
};

/**
 * Helper to get image URL
 */
const getImageUrl = (imageUrl) => {
  if (!imageUrl) return null;
  if (imageUrl.startsWith('http')) return imageUrl;
  return `${BACKEND_URL}${imageUrl.startsWith('/') ? '' : '/'}${imageUrl}`;
};

/**
 * Single Avatar Story Item with mood ring - clean circular design
 */
const AvatarStoryItem = ({ friend, onClick, isCurrentUser = false, worldMode, isImmersive = false }) => {
  const isAvatarWorld = worldMode === 'avatar';
  
  const displayName = isAvatarWorld 
    ? (friend.avatar_name || friend.name)
    : friend.name;
  const displayPicture = isAvatarWorld
    ? (friend.avatar_picture || friend.picture)
    : friend.picture;
  
  const mood = friend.avatar_mood || friend.mood || DEFAULT_MOOD;
  const moodColors = MOOD_COLORS[mood] || MOOD_COLORS[DEFAULT_MOOD];
  const gradientId = `mood-ring-${friend.id}-${mood}`;
  
  const avatarUrl = displayPicture ? getImageUrl(displayPicture) : null;
  
  return (
    <button
      onClick={onClick}
      className="flex flex-col items-center flex-shrink-0 group focus:outline-none focus-visible:outline-none active:outline-none"
      style={{ 
        width: '68px', 
        touchAction: 'manipulation', 
        WebkitTapHighlightColor: 'transparent',
        outline: 'none',
        border: 'none',
        background: 'transparent',
        padding: 0,
        WebkitAppearance: 'none',
      }}
    >
      {/* Avatar with gradient mood ring */}
      <div className="relative w-[62px] h-[62px] sm:w-[68px] sm:h-[68px] flex items-center justify-center">
        {/* SVG gradient ring - perfectly circular */}
        <svg 
          className="absolute inset-0 w-full h-full" 
          viewBox="0 0 68 68" 
          fill="none"
        >
          <defs>
            <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={moodColors.start} />
              <stop offset="100%" stopColor={moodColors.end} />
            </linearGradient>
          </defs>
          <circle
            cx="34"
            cy="34"
            r="32"
            fill="none"
            stroke={`url(#${gradientId})`}
            strokeWidth="2.5"
          />
        </svg>
        
        {/* Avatar - perfectly circular, centered inside the ring */}
        <div 
          className="rounded-full overflow-hidden flex items-center justify-center"
          style={{
            width: '52px',
            height: '52px',
            border: isImmersive ? '2.5px solid #0f172a' : '2.5px solid #ffffff',
          }}
        >
          {isCurrentUser ? (
            <div 
              className="w-full h-full flex items-center justify-center"
              style={{ background: isImmersive ? '#1e293b' : '#f1f5f9' }}
            >
              <Plus className="w-5 h-5" style={{ color: isImmersive ? '#60a5fa' : '#3b82f6' }} />
            </div>
          ) : (
            avatarUrl ? (
              <img 
                src={avatarUrl} 
                alt={displayName} 
                className="w-full h-full object-cover"
                onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling && (e.target.nextSibling.style.display = 'flex'); }}
              />
            ) : null
          )}
          {/* Fallback initial */}
          {!isCurrentUser && (
            <div 
              className="w-full h-full items-center justify-center text-white text-sm font-semibold"
              style={{ 
                display: avatarUrl ? 'none' : 'flex',
                background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
              }}
            >
              {displayName?.charAt(0)?.toUpperCase() || '?'}
            </div>
          )}
        </div>
      </div>
      
      {/* Name - clean, truncated */}
      <span 
        className="mt-1 text-center leading-tight truncate w-full px-0.5"
        style={{
          fontSize: '11px',
          color: isImmersive ? 'rgba(255,255,255,0.7)' : '#4b5563',
          fontWeight: 500,
        }}
      >
        {isCurrentUser ? 'Your Story' : (displayName?.split(' ')[0] || 'Friend')}
      </span>
    </button>
  );
};

/**
 * Story Popup - Shows the friend's latest post (Instagram-style overlay)
 * Adapts to all 4 mode combos: Sense/Classic, Sense/Immersive, Maya/Classic, Maya/Immersive
 */
const StoryPopup = ({ friend, worldMode, isImmersive, onClose }) => {
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const navigate = useNavigate();
  
  const isAvatarWorld = worldMode === 'avatar';
  const displayName = isAvatarWorld 
    ? (friend.avatar_name || friend.name) 
    : friend.name;
  const displayPicture = isAvatarWorld
    ? (friend.avatar_picture || friend.picture)
    : friend.picture;
  const avatarUrl = displayPicture ? getImageUrl(displayPicture) : null;

  // Theme based on mode combination
  const isDark = isAvatarWorld || isImmersive;
  const theme = {
    cardBg: isDark 
      ? (isImmersive ? 'linear-gradient(180deg, rgba(12,15,25,0.97) 0%, rgba(20,25,40,0.97) 100%)' : 'linear-gradient(180deg, #1a1f2e 0%, #111827 100%)')
      : '#ffffff',
    headerBorder: isDark ? '1px solid rgba(255,255,255,0.06)' : '1px solid #f3f4f6',
    textPrimary: isDark ? '#f1f5f9' : '#111827',
    textSecondary: isDark ? 'rgba(255,255,255,0.55)' : '#6b7280',
    textBody: isDark ? 'rgba(255,255,255,0.85)' : '#374151',
    avatarBorder: isDark ? '2px solid rgba(96,165,250,0.35)' : '2px solid #e5e7eb',
    closeBg: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.04)',
    closeColor: isDark ? '#cbd5e1' : '#6b7280',
    divider: isDark ? '1px solid rgba(255,255,255,0.06)' : '1px solid #f3f4f6',
    accentBg: isDark ? 'rgba(96,165,250,0.12)' : '#eff6ff',
    accentColor: isDark ? '#60a5fa' : '#2563eb',
    progressBar: isAvatarWorld 
      ? 'linear-gradient(90deg, #8b5cf6, #6366f1, #3b82f6)' 
      : 'linear-gradient(90deg, #3b82f6, #06b6d4, #10b981)',
    spinnerColor: isDark ? 'rgba(96,165,250,0.4)' : '#d1d5db',
    emptyIcon: isDark ? 'rgba(255,255,255,0.15)' : '#d1d5db',
    emptyText: isDark ? 'rgba(255,255,255,0.35)' : '#9ca3af',
    imageBg: isDark ? 'rgba(0,0,0,0.3)' : 'rgba(0,0,0,0.05)',
  };

  // Fetch latest post for this friend
  useEffect(() => {
    const fetchLatestPost = async () => {
      try {
        setLoading(true);
        const postType = isAvatarWorld ? 'avatar' : 'real';
        const response = await postService.getUserPosts(friend.id, postType, 1, 0);
        // Backend returns { posts: [...], total, has_more } - extract the posts array
        const posts = response?.posts || (Array.isArray(response) ? response : []);
        if (posts.length > 0) {
          setPost(posts[0]);
        } else {
          // Try fallback type
          const fallbackType = isAvatarWorld ? 'real' : 'avatar';
          const fallbackResponse = await postService.getUserPosts(friend.id, fallbackType, 1, 0);
          const fallbackPosts = fallbackResponse?.posts || (Array.isArray(fallbackResponse) ? fallbackResponse : []);
          if (fallbackPosts.length > 0) {
            setPost(fallbackPosts[0]);
          } else {
            setError(true);
          }
        }
      } catch (err) {
        console.error('Error fetching latest post:', err);
        setError(true);
      } finally {
        setLoading(false);
      }
    };
    fetchLatestPost();
  }, [friend.id, isAvatarWorld]);

  useEffect(() => {
    const handleKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  const postContent = post?.content || post?.text || '';
  const postImage = post?.image_url ? getImageUrl(post.image_url) : null;
  const postTime = getRelativeTime(post?.created_at);
  const likesCount = post?.likes_count || post?.liked_by?.length || 0;
  const commentsCount = post?.comments_count || 0;

  const safeClose = useCallback((e) => {
    if (e) { e.preventDefault(); e.stopPropagation(); }
    setTimeout(() => onClose(), 50);
  }, [onClose]);

  return (
    <div 
      className="fixed inset-0 z-[9999] flex items-center justify-center"
      data-story-popup="open"
      onClick={safeClose}
      onTouchEnd={(e) => { e.preventDefault(); e.stopPropagation(); safeClose(e); }}
      style={{ touchAction: 'none', WebkitTapHighlightColor: 'transparent' }}
    >
      {/* Backdrop */}
      <div 
        className="absolute inset-0"
        style={{ background: isDark ? 'rgba(0,0,0,0.85)' : 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
        onTouchStart={(e) => e.stopPropagation()}
        onTouchMove={(e) => e.stopPropagation()}
      />
      
      {/* Story Card */}
      <div 
        className="relative w-full max-w-[380px] mx-4 rounded-2xl overflow-hidden"
        style={{
          maxHeight: '82vh',
          background: theme.cardBg,
          boxShadow: isDark ? '0 25px 60px rgba(0,0,0,0.7)' : '0 25px 60px rgba(0,0,0,0.2)',
          touchAction: 'manipulation',
        }}
        onClick={(e) => e.stopPropagation()}
        onTouchEnd={(e) => e.stopPropagation()}
      >
        {/* Top accent bar */}
        <div className="h-[3px]" style={{ background: theme.progressBar }} />
        
        {/* Header */}
        <div 
          className="flex items-center justify-between px-4 py-3"
          style={{ borderBottom: theme.headerBorder }}
        >
          <div 
            className="flex items-center gap-3 cursor-pointer min-w-0 flex-1"
            onClick={() => { onClose(); navigate(`/profile/${friend.id}`); }}
          >
            <div 
              className="w-10 h-10 rounded-full overflow-hidden flex-shrink-0"
              style={{ border: theme.avatarBorder }}
            >
              {avatarUrl ? (
                <img src={avatarUrl} alt={displayName} className="w-full h-full object-cover" />
              ) : (
                <div 
                  className="w-full h-full flex items-center justify-center text-white text-sm font-bold"
                  style={{ background: isAvatarWorld ? 'linear-gradient(135deg, #8b5cf6, #6366f1)' : 'linear-gradient(135deg, #3b82f6, #06b6d4)' }}
                >
                  {displayName?.charAt(0)?.toUpperCase() || '?'}
                </div>
              )}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold leading-tight truncate" style={{ color: theme.textPrimary }}>
                {displayName}
              </p>
              <div className="flex items-center gap-1.5 mt-0.5">
                {postTime && (
                  <span className="text-[10px] flex items-center gap-1" style={{ color: theme.textSecondary }}>
                    <Clock className="w-2.5 h-2.5" />
                    {postTime}
                  </span>
                )}
                <span 
                  className="text-[9px] px-1.5 py-0.5 rounded-full font-medium"
                  style={{ 
                    background: isAvatarWorld ? 'rgba(139,92,246,0.15)' : 'rgba(59,130,246,0.1)',
                    color: isAvatarWorld ? '#a78bfa' : '#60a5fa',
                  }}
                >
                  {isAvatarWorld ? 'Maya' : 'Sense'}
                </span>
              </div>
            </div>
          </div>
          
          <button
            onClick={safeClose}
            onTouchEnd={(e) => { e.preventDefault(); e.stopPropagation(); safeClose(e); }}
            className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 focus:outline-none"
            style={{
              background: theme.closeBg,
              color: theme.closeColor,
              touchAction: 'manipulation',
              WebkitTapHighlightColor: 'transparent',
              outline: 'none',
            }}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        
        {/* Content */}
        <div className="px-4 pb-4 pt-3" style={{ maxHeight: 'calc(82vh - 130px)', overflowY: 'auto' }}>
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <div 
                className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin"
                style={{ borderColor: theme.spinnerColor, borderTopColor: 'transparent' }}
              />
            </div>
          ) : error || !post ? (
            <div className="text-center py-14">
              <Globe className="w-12 h-12 mx-auto mb-3" style={{ color: theme.emptyIcon }} />
              <p className="text-sm font-medium mb-1" style={{ color: theme.textSecondary }}>No recent updates</p>
              <p className="text-xs mb-4" style={{ color: theme.emptyText }}>
                {displayName} hasn't shared anything recently
              </p>
              <button 
                className="text-xs font-semibold px-5 py-2 rounded-full transition-colors"
                style={{ background: theme.accentBg, color: theme.accentColor }}
                onClick={() => { onClose(); navigate(`/profile/${friend.id}`); }}
              >
                View Profile
              </button>
            </div>
          ) : (
            <>
              {/* Post Image */}
              {postImage && (
                <div className="rounded-xl overflow-hidden mb-3" style={{ background: theme.imageBg }}>
                  <img 
                    src={postImage} 
                    alt="Post" 
                    className="w-full object-cover"
                    style={{ maxHeight: '42vh' }}
                  />
                </div>
              )}
              
              {/* Post Text */}
              {postContent && (
                <p 
                  className="text-[13px] leading-relaxed mb-3"
                  style={{
                    color: theme.textBody,
                    display: '-webkit-box',
                    WebkitLineClamp: postImage ? 5 : 12,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }}
                >
                  {postContent}
                </p>
              )}
              
              {/* Engagement bar */}
              <div 
                className="flex items-center gap-4 pt-3 mt-1"
                style={{ borderTop: theme.divider }}
              >
                <span className="flex items-center gap-1.5 text-xs" style={{ color: theme.textSecondary }}>
                  <Heart className="w-3.5 h-3.5" />
                  {likesCount}
                </span>
                <span className="flex items-center gap-1.5 text-xs" style={{ color: theme.textSecondary }}>
                  <MessageCircle className="w-3.5 h-3.5" />
                  {commentsCount}
                </span>
                <button 
                  className="ml-auto text-xs font-semibold px-4 py-1.5 rounded-full transition-colors focus:outline-none"
                  style={{ background: theme.accentBg, color: theme.accentColor, outline: 'none' }}
                  onClick={() => { onClose(); navigate(`/profile/${friend.id}`); }}
                >
                  View Profile
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * Main Avatar Stories Row Component
 */
const AvatarStoriesRow = ({ currentUser, className = '', style = {} }) => {
  const navigate = useNavigate();
  const { worldMode } = useWorldMode();
  const { isImmersive } = useViewMode();
  const [friends, setFriends] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedFriend, setSelectedFriend] = useState(null);
  
  const isAvatarWorld = worldMode === 'avatar';
  
  // Fetch friends and sort by most recent post
  useEffect(() => {
    const fetchFriends = async () => {
      try {
        const data = await friendService.getFriends();
        
        // Fetch latest post for ALL friends to determine ordering by recency
        // (don't pre-slice — we need recency info from all friends first)
        const postType = isAvatarWorld ? 'avatar' : 'real';
        const friendsWithLatest = await Promise.all(
          data.map(async (friend) => {
            try {
              const response = await postService.getUserPosts(friend.id, postType, 1, 0);
              const posts = response?.posts || (Array.isArray(response) ? response : []);
              const latestPost = posts[0];
              return {
                ...friend,
                _latestPostTime: latestPost?.created_at ? new Date(latestPost.created_at).getTime() : 0,
              };
            } catch {
              return { ...friend, _latestPostTime: 0 };
            }
          })
        );
        
        // Sort by most recent post first, then take top 15 for display
        friendsWithLatest.sort((a, b) => b._latestPostTime - a._latestPostTime);
        setFriends(friendsWithLatest.slice(0, 15));
      } catch (error) {
        console.error('Error fetching friends for stories:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchFriends();
  }, [isAvatarWorld]);
  
  // Assign moods for display
  const friendsWithMoods = useMemo(() => {
    const moods = Object.keys(MOOD_COLORS);
    return friends.map((friend, idx) => ({
      ...friend,
      avatar_mood: friend.avatar_mood || moods[idx % moods.length]
    }));
  }, [friends]);
  
  const handleFriendClick = useCallback((friend) => {
    setSelectedFriend(friend);
  }, []);
  
  const handleCurrentUserClick = useCallback(() => {
    navigate('/myprofile');
  }, [navigate]);

  const handleClosePopup = useCallback(() => {
    setSelectedFriend(null);
  }, []);
  
  if (loading) {
    return (
      <div className={`flex gap-3 px-3 py-3 overflow-x-auto scrollbar-hide ${className}`} style={style}>
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex flex-col items-center gap-1.5 animate-pulse" style={{ width: '68px' }}>
            <div 
              className="w-[62px] h-[62px] rounded-full" 
              style={{ background: isImmersive ? 'rgba(51,65,85,0.4)' : '#e5e7eb' }} 
            />
            <div 
              className="w-10 h-2 rounded-full" 
              style={{ background: isImmersive ? 'rgba(51,65,85,0.4)' : '#e5e7eb' }} 
            />
          </div>
        ))}
      </div>
    );
  }
  
  return (
    <>
      <div className={`relative ${className}`} style={style}>
        {/* Horizontal scrollable container */}
        <div className="flex gap-1 sm:gap-1.5 px-2 py-2.5 overflow-x-auto scrollbar-hide">
          {/* Current user - first position */}
          <AvatarStoryItem
            friend={{
              ...currentUser,
              id: 'current-user',
              avatar_mood: currentUser?.avatar_mood || 'curious'
            }}
            onClick={handleCurrentUserClick}
            isCurrentUser={true}
            worldMode={worldMode}
            isImmersive={isImmersive}
          />
          
          {/* Friends */}
          {friendsWithMoods.map((friend) => (
            <AvatarStoryItem
              key={friend.id}
              friend={friend}
              onClick={() => handleFriendClick(friend)}
              worldMode={worldMode}
              isImmersive={isImmersive}
            />
          ))}
          
          {/* Empty state */}
          {friends.length === 0 && (
            <div 
              className="flex items-center justify-center px-6 text-sm"
              style={{ color: isImmersive ? 'rgba(255,255,255,0.35)' : '#9ca3af' }}
            >
              Add friends to see their stories
            </div>
          )}
        </div>
        
        {/* Right edge fade */}
        {friends.length > 3 && (
          <div 
            className="absolute right-0 top-0 bottom-0 w-6 pointer-events-none rounded-r-xl"
            style={{
              background: isImmersive 
                ? 'linear-gradient(to left, rgba(15, 23, 42, 0.9), transparent)'
                : 'linear-gradient(to left, rgba(255, 255, 255, 0.95), transparent)'
            }}
          />
        )}
        
        <style>{`
          .scrollbar-hide::-webkit-scrollbar { display: none; }
          .scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
          /* Remove all focus/tap outlines from story buttons */
          .scrollbar-hide button { outline: none !important; -webkit-tap-highlight-color: transparent !important; }
          .scrollbar-hide button:focus, .scrollbar-hide button:active, .scrollbar-hide button:focus-visible { outline: none !important; box-shadow: none !important; }
        `}</style>
      </div>
      
      {/* Story Popup */}
      {selectedFriend && (
        <StoryPopup
          friend={selectedFriend}
          worldMode={worldMode}
          isImmersive={isImmersive}
          onClose={handleClosePopup}
        />
      )}
    </>
  );
};

export default AvatarStoriesRow;
