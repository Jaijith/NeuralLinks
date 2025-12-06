import { useState, useEffect, useCallback } from 'react';
import { userService, friendService } from '@/services/api';
import { toast } from 'sonner';

/**
 * Custom hook for managing user profile data
 * Supports both Maya (avatar) and Sense (real) worlds
 */
const useProfile = (userId, worldMode = 'real', currentUser) => {
  const [profileUser, setProfileUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isOwnProfile, setIsOwnProfile] = useState(false);
  const [friendshipStatus, setFriendshipStatus] = useState('none'); // 'none', 'friends', 'pending', 'requested'

  const fetchProfile = useCallback(async () => {
    if (!userId) return;

    setLoading(true);
    setError(null);
    try {
      const response = await userService.getUserProfile(userId, worldMode);
      const userData = response.user || response;
      
      setProfileUser(userData);
      setIsOwnProfile(userId === currentUser?.id || userData.id === currentUser?.id);

      // Check friendship status if not own profile
      if (!isOwnProfile && currentUser) {
        try {
          const friendsRes = await friendService.getFriends();
          const friends = Array.isArray(friendsRes) ? friendsRes : (friendsRes.friends || []);
          const isFriend = friends.some(f => f.id === userId || f.id === userData.id);
          
          if (isFriend) {
            setFriendshipStatus('friends');
          } else {
            // Could check for pending requests here if needed
            setFriendshipStatus('none');
          }
        } catch (err) {
          console.error("Error checking friendship:", err);
        }
      }
    } catch (err) {
      console.error("Error fetching profile:", err);
      setError(err);
      toast.error("Failed to load profile");
    } finally {
      setLoading(false);
    }
  }, [userId, worldMode, currentUser?.id]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const refresh = useCallback(() => {
    fetchProfile();
  }, [fetchProfile]);

  return {
    profileUser,
    loading,
    error,
    isOwnProfile,
    friendshipStatus,
    setFriendshipStatus,
    refresh
  };
};

export default useProfile;
