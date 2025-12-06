import React from 'react';
import { FriendRequestCard } from '@/components/common';
import { EmptyState } from '@/components/common';
import { cn } from '@/lib/utils';

/**
 * @typedef {Object} FriendRequestsListProps
 * @property {Array} requests - Array of friend request objects
 * @property {string} [worldMode] - Current world mode ('real' or 'avatar')
 * @property {function} onAccept - Handler for accept action
 * @property {function} onDecline - Handler for decline action
 * @property {Set} [processing] - Set of request IDs currently being processed
 * @property {boolean} [loading] - Whether the list is loading
 * @property {string} [className] - Additional CSS classes
 */

/**
 * Friend Requests List component for displaying friend requests consistently.
 * Supports both Maya (avatar) and Sense (real) worlds.
 * @param {FriendRequestsListProps} props
 */
const FriendRequestsList = React.memo(({ 
  requests = [],
  worldMode = 'real',
  onAccept,
  onDecline,
  processing = new Set(),
  loading = false,
  className
}) => {
  if (loading) {
    return (
      <div className={cn("space-y-3", className)}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-20 bg-gray-200 animate-pulse rounded-lg" />
        ))}
      </div>
    );
  }

  if (requests.length === 0) {
    return (
      <EmptyState
        title="No friend requests"
        description="You don't have any pending friend requests"
        variant="minimal"
      />
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      {requests.map((request) => {
        const requestId = request.id || request._id;
        const isProcessing = processing.has(requestId);
        
        return (
          <FriendRequestCard
            key={requestId}
            request={request}
            worldMode={worldMode}
            onAccept={onAccept}
            onDecline={onDecline}
            loading={isProcessing}
          />
        );
      })}
    </div>
  );
});

FriendRequestsList.displayName = "FriendRequestsList";

export default FriendRequestsList;

