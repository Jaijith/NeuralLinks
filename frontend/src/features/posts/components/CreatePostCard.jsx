import React from 'react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card } from '@/components/ui/card';
import { Video, Image, Smile, Search } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import MiniMemoryOrb from '@/components/MiniMemoryOrb';
import useViewMode from '@/hooks/useViewMode';

/**
 * @typedef {Object} CreatePostCardProps
 * @property {Object} user - Current user object
 * @property {string} [worldMode] - Current world mode ('real' or 'avatar')
 * @property {function} onCreateClick - Handler when create post is clicked
 * @property {function} [onPhotoClick] - Handler when photo button is clicked
 * @property {function} [onOrbClick] - Handler when voice orb is clicked (Maya world only)
 * @property {function} [onSearchClick] - Handler when search is clicked
 * @property {string} [placeholder] - Custom placeholder text
 * @property {string} [className] - Additional CSS classes
 */

/**
 * Create Post Card component - Input card that triggers post creation.
 * Supports both Maya (avatar) and Sense (real) worlds.
 * @param {CreatePostCardProps} props
 */
const CreatePostCard = React.memo(({ 
  user, 
  worldMode = 'real',
  onCreateClick,
  onPhotoClick,
  onOrbClick,
  onSearchClick,
  placeholder: customPlaceholder,
  mood,
  energyLevel,
  className
}) => {
  const { isImmersive } = useViewMode();
  const isAvatarWorld = worldMode === 'avatar';
  
  const displayName = isAvatarWorld 
    ? (user.avatar_name || user.name)
    : user.name;
  const displayPicture = isAvatarWorld
    ? (user.avatar_picture || user.picture)
    : user.picture;

  const placeholder = customPlaceholder || (isAvatarWorld 
    ? "Share your Maya moments."
    : "What's on your mind?");

  const handlePhotoClick = () => {
    if (onPhotoClick) {
      onPhotoClick();
    } else {
      onCreateClick();
      // Small delay to ensure dialog is open before triggering file input
      setTimeout(() => {
        document.getElementById('post-image-upload')?.click();
      }, 100);
    }
  };

  const handleFeatureClick = (feature) => {
    if (feature === 'Photo') {
      handlePhotoClick();
    } else {
      toast.info(`${feature} feature coming soon!`);
    }
  };

  // Maya world: Card + separate Orb side by side
  if (isAvatarWorld) {
    return (
      <div className={cn("flex items-center gap-2 sm:gap-4", className)}>
        {/* Input Card - Takes most of the space */}
        <Card 
          className="flex-1 min-w-0 rounded-xl p-2.5 sm:p-4 overflow-hidden"
          style={{
            backgroundColor: isImmersive ? 'rgba(15, 23, 42, 0.8)' : 'rgba(255, 255, 255, 0.95)',
            borderColor: isImmersive ? 'rgba(51, 65, 85, 0.5)' : '#e5e7eb',
            boxShadow: isImmersive ? undefined : '0 1px 3px 0 rgb(0 0 0 / 0.1)'
          }}
        >
          <div className="flex items-center gap-2 sm:gap-3">
            <Avatar className="w-8 h-8 sm:w-10 sm:h-10 flex-shrink-0">
              <AvatarImage src={displayPicture} alt={displayName} />
              <AvatarFallback className="bg-purple-600 text-white text-sm">
                {displayName?.charAt(0) || '?'}
              </AvatarFallback>
            </Avatar>
            <button
              onClick={onCreateClick}
              className={cn(
                "flex-1 min-w-0 text-left px-3 sm:px-4 py-2 sm:py-2.5 rounded-full transition-all text-sm sm:text-base min-h-[40px] sm:min-h-[44px] truncate",
                isImmersive 
                  ? "bg-slate-800/60 hover:bg-slate-700/60 text-gray-300" 
                  : "bg-gray-100 hover:bg-gray-200 text-gray-600"
              )}
            >
              {placeholder}
            </button>
            
            {/* Search icon */}
            {onSearchClick && (
              <button
                onClick={onSearchClick}
                className={cn(
                  "w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-colors",
                  isImmersive 
                    ? "bg-slate-800/60 hover:bg-slate-700/60 text-gray-400" 
                    : "bg-gray-100 hover:bg-gray-200 text-gray-500"
                )}
              >
                <Search className="w-4 h-4 sm:w-5 sm:h-5" />
              </button>
            )}
          </div>
        </Card>
        
        {/* Separate Mini Memory Orb - Compact on mobile */}
        {onOrbClick && (
          <div className="flex-shrink-0">
            <MiniMemoryOrb onClick={onOrbClick} size="default" showState={false} mood={mood} energyLevel={energyLevel} />
          </div>
        )}
      </div>
    );
  }

  // Sense world: Regular card layout - also respects immersive mode
  return (
    <Card 
      className={cn("rounded-xl p-3 sm:p-4 overflow-hidden", className)}
      style={{
        backgroundColor: isImmersive ? 'rgba(15, 23, 42, 0.8)' : 'white',
        borderColor: isImmersive ? 'rgba(51, 65, 85, 0.5)' : undefined,
        boxShadow: isImmersive ? undefined : '0 1px 3px 0 rgb(0 0 0 / 0.1)'
      }}
    >
      <div className="flex items-center gap-2 sm:gap-3">
        <Avatar className="w-9 h-9 sm:w-10 sm:h-10 flex-shrink-0">
          <AvatarImage src={displayPicture} alt={displayName} />
          <AvatarFallback className="bg-blue-500 text-white text-sm">
            {displayName?.charAt(0) || '?'}
          </AvatarFallback>
        </Avatar>
        <button
          onClick={onCreateClick}
          className={cn(
            "flex-1 text-left px-3 sm:px-4 py-2 sm:py-2.5 rounded-full transition-all text-sm sm:text-base truncate min-h-[44px]",
            isImmersive 
              ? "bg-slate-800/60 hover:bg-slate-700/60 text-gray-300" 
              : "bg-gray-100 hover:bg-gray-200 text-gray-600"
          )}
        >
          {placeholder}
        </button>
        
        {/* Search icon */}
        {onSearchClick && (
          <button
            onClick={onSearchClick}
            className={cn(
              "w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-colors",
              isImmersive 
                ? "bg-slate-800/60 hover:bg-slate-700/60 text-gray-400" 
                : "bg-gray-100 hover:bg-gray-200 text-gray-500"
            )}
          >
            <Search className="w-5 h-5" />
          </button>
        )}
      </div>
      
      {/* Action buttons row */}
      <div className={cn(
        "flex items-center justify-around mt-3 pt-3 border-t",
        isImmersive ? "border-slate-700" : "border-gray-200"
      )}>
        {[
          { icon: Video, label: 'Live', iconColor: '#fb7185' },
          { icon: Image, label: 'Photo', iconColor: '#34d399' },
          { icon: Smile, label: 'Feeling', iconColor: '#fbbf24' },
        ].map((item, idx) => {
          const Icon = item.icon;
          return (
            <button
              key={idx}
              onClick={() => handleFeatureClick(item.label)}
              className={cn(
                "flex items-center gap-1 sm:gap-2 px-2 sm:px-4 py-2 rounded-lg transition-all min-h-[44px]",
                isImmersive ? "hover:bg-slate-800" : "hover:bg-gray-100"
              )}
            >
              <Icon className="w-4 h-4 sm:w-5 sm:h-5 flex-shrink-0" style={{ color: item.iconColor }} />
              <span className={cn(
                "font-medium text-xs sm:text-sm",
                isImmersive ? "text-gray-300" : "text-gray-700"
              )}>{item.label}</span>
            </button>
          );
        })}
      </div>
    </Card>
  );
});

CreatePostCard.displayName = "CreatePostCard";

export default CreatePostCard;

