import { useState, useEffect, useCallback } from 'react';
import { friendService } from '@/services/api';
import { toast } from 'sonner';

/**
 * Custom hook for managing friends list
 * Supports both Maya (avatar) and Sense (real) worlds
 */
const useFriends = (worldMode = 'real') => {
  const [friends, setFriends] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchFriends = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await friendService.getFriends();
      // Handle different response formats
      setFriends(Array.isArray(response) ? response : (response.friends || []));
    } catch (err) {
      console.error("Error fetching friends:", err);
      setError(err);
      toast.error("Failed to load friends");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFriends();
  }, [fetchFriends, worldMode]); // Re-fetch when worldMode changes

  const refresh = useCallback(() => {
    fetchFriends();
  }, [fetchFriends]);

  return {
    friends,
    loading,
    error,
    refresh,
    refetch: fetchFriends
  };
};

export default useFriends;

