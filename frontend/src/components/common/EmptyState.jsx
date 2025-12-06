import React from 'react';
import { Button } from '@/components/ui/button';
import { Sparkles, Search, Image, Users, Heart, MessageCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * @typedef {Object} EmptyStateProps
 * @property {React.ComponentType} [icon] - Icon component to display (default: Sparkles)
 * @property {string} title - Title text
 * @property {string} [description] - Description text
 * @property {Object} [action] - Action button configuration
 * @property {string} action.label - Button label
 * @property {function} action.onClick - Button click handler
 * @property {string} [variant] - Visual variant ('default' | 'minimal' | 'centered')
 * @property {string} [className] - Additional CSS classes
 */

/**
 * Reusable Empty State component for displaying empty states consistently across pages.
 * @param {EmptyStateProps} props
 */
const EmptyState = React.memo(({ 
  icon: Icon = Sparkles,
  title,
  description,
  action,
  variant = 'default',
  className
}) => {
  const isCentered = variant === 'centered';
  const isMinimal = variant === 'minimal';

  return (
    <div className={cn(
      "flex flex-col items-center justify-center",
      isCentered ? "min-h-[400px]" : "p-8",
      isMinimal ? "py-4" : "",
      className
    )}>
      {!isMinimal && (
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
          <Icon className="w-8 h-8 text-white" />
        </div>
      )}
      
      <h3 className={cn(
        "font-bold mb-2 text-gray-900",
        isMinimal ? "text-lg" : "text-2xl"
      )}>
        {title}
      </h3>
      
      {description && (
        <p className={cn(
          "text-center mb-6 text-gray-600",
          isMinimal ? "text-sm mb-3" : ""
        )}>
          {description}
        </p>
      )}
      
      {action && (
        <Button
          onClick={action.onClick}
          className={cn(
            "px-6 py-3 rounded-full",
            isMinimal ? "px-4 py-2 text-sm" : "",
            "bg-gradient-to-r from-violet-500 to-fuchsia-500 hover:from-violet-600 hover:to-fuchsia-600 text-white"
          )}
        >
          {action.label}
        </Button>
      )}
    </div>
  );
});

EmptyState.displayName = "EmptyState";

// Pre-configured variants for common use cases
EmptyState.NoPosts = (props) => (
  <EmptyState
    icon={MessageCircle}
    title="No posts yet"
    description="Start by creating your first post"
    {...props}
  />
);

EmptyState.NoFriends = (props) => (
  <EmptyState
    icon={Users}
    title="No friends yet"
    description="Start connecting with others"
    {...props}
  />
);

EmptyState.NoPhotos = (props) => (
  <EmptyState
    icon={Image}
    title="No photos yet"
    description="Upload your first photo"
    {...props}
  />
);

EmptyState.NoMatches = (props) => (
  <EmptyState
    icon={Heart}
    title="No matches yet"
    description="Discover new connections"
    {...props}
  />
);

EmptyState.NoResults = (props) => (
  <EmptyState
    icon={Search}
    title="No results found"
    description="Try adjusting your search"
    {...props}
  />
);

export default EmptyState;

