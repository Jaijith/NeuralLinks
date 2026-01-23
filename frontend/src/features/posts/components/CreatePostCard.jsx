import React from 'react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card } from '@/components/ui/card';
import { Video, Image, Smile } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

/**
 * @typedef {Object} CreatePostCardProps
 * @property {Object} user - Current user object
 * @property {string} [worldMode] - Current world mode ('real' or 'avatar')
 * @property {function} onCreateClick - Handler when create post is clicked
 * @property {function} [onPhotoClick] - Handler when photo button is clicked
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
  className
}) => {
  const isAvatarWorld = worldMode === 'avatar';
  
  const displayName = isAvatarWorld 
    ? (user.avatar_name || user.name)
    : user.name;
  const displayPicture = isAvatarWorld
    ? (user.avatar_picture || user.picture)
    : user.picture;

  const placeholder = isAvatarWorld 
    ? "Share a thought in Maya..."
    : "What's on your mind?";

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

  return (
    <Card className={cn("rounded-xl p-3 sm:p-4 glass-card overflow-hidden", className)}>
      <div className="flex items-center gap-2 sm:gap-3">
        <Avatar className="w-9 h-9 sm:w-10 sm:h-10 flex-shrink-0">
          <AvatarImage src={displayPicture} alt={displayName} />
          <AvatarFallback className="bg-blue-500 text-white text-sm">
            {displayName?.charAt(0) || '?'}
          </AvatarFallback>
        </Avatar>
        <button
          onClick={onCreateClick}
          className="flex-1 text-left px-3 sm:px-4 py-2 sm:py-2.5 rounded-full transition-all bg-gray-100 hover:bg-gray-200 text-gray-600 text-sm sm:text-base truncate min-h-[44px]"
        >
          {placeholder}
        </button>
      </div>
      
      <div className="flex items-center justify-around mt-3 pt-3 border-t border-gray-200">
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
              className="flex items-center gap-1 sm:gap-2 px-2 sm:px-4 py-2 rounded-lg transition-all hover:bg-gray-100 min-h-[44px]"
            >
              <Icon className="w-4 h-4 sm:w-5 sm:h-5 flex-shrink-0" style={{ color: item.iconColor }} />
              <span className="font-medium text-xs sm:text-sm text-gray-700">{item.label}</span>
            </button>
          );
        })}
      </div>
    </Card>
  );
});

CreatePostCard.displayName = "CreatePostCard";

export default CreatePostCard;

