import { useState, useEffect, useCallback } from 'react';
import { friendService } from '@/services/api';
import { toast } from 'sonner';

/**
 * Custom hook for managing friend requests
 * Supports both Maya (avatar) and Sense (real) worlds
 */
const useFriendRequests = (worldMode = 'real') => {
  const [friendRequests, setFriendRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [processing, setProcessing] = useState(new Set());

  const fetchFriendRequests = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await friendService.getFriendRequests();
      setFriendRequests(response.requests || response || []);
    } catch (err) {
      console.error("Error fetching friend requests:", err);
      setError(err);
      // Don't show error toast for requests, just log it
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFriendRequests();
  }, [fetchFriendRequests, worldMode]); // Re-fetch when worldMode changes

  const acceptRequest = useCallback(async (friendshipId, requesterId) => {
    if (processing.has(friendshipId)) return;
    
    setProcessing(prev => new Set(prev).add(friendshipId));
    try {
      await friendService.acceptFriendRequest(friendshipId);
      toast.success("Friend request accepted!");
      await fetchFriendRequests();
    } catch (err) {
      console.error("Error accepting friend request:", err);
      toast.error("Failed to accept friend request");
    } finally {
      setProcessing(prev => {
        const next = new Set(prev);
        next.delete(friendshipId);
        return next;
      });
    }
  }, [processing, fetchFriendRequests]);

  const declineRequest = useCallback(async (friendshipId) => {
    if (processing.has(friendshipId)) return;
    
    setProcessing(prev => new Set(prev).add(friendshipId));
    try {
      await friendService.declineFriendRequest(friendshipId);
      toast.success("Friend request declined");
      await fetchFriendRequests();
    } catch (err) {
      console.error("Error declining friend request:", err);
      toast.error("Failed to decline friend request");
    } finally {
      setProcessing(prev => {
        const next = new Set(prev);
        next.delete(friendshipId);
        return next;
      });
    }
  }, [processing, fetchFriendRequests]);

  const refresh = useCallback(() => {
    fetchFriendRequests();
  }, [fetchFriendRequests]);

  return {
    friendRequests,
    loading,
    error,
    processing,
    acceptRequest,
    declineRequest,
    refresh,
    refetch: fetchFriendRequests
  };
};

export default useFriendRequests;

