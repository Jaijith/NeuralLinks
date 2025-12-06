import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Camera, MapPin, Briefcase, MessageCircle, UserPlus, Bot, Edit2 } from 'lucide-react';
import { userService, friendService } from '@/services/api';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

/**
 * @typedef {Object} ProfileInfoProps
 * @property {Object} profileUser - Profile user object
 * @property {boolean} isOwnProfile - Whether this is the current user's profile
 * @property {string} [worldMode] - Current world mode ('real' or 'avatar')
 * @property {string} [friendshipStatus] - Friendship status ('none' | 'pending' | 'friends')
 * @property {function} onProfileUpdated - Callback when profile is updated
 * @property {function} [onMessage] - Handler for message action
 * @property {function} [onSendFriendRequest] - Handler for sending friend request
 * @property {boolean} [uploadingPicture] - Whether profile picture is uploading
 */

/**
 * Profile Info component displaying user information and actions.
 * Supports both Maya (avatar) and Sense (real) worlds.
 */
const ProfileInfo = React.memo(({
  profileUser,
  isOwnProfile,
  worldMode = 'real',
  friendshipStatus = 'none',
  onProfileUpdated,
  onMessage,
  onSendFriendRequest,
  uploadingPicture = false
}) => {
  const navigate = useNavigate();
  const isAvatarWorld = worldMode === 'avatar';

  const displayName = isAvatarWorld
    ? (profileUser.avatar_name || profileUser.name || 'Set Avatar Nickname')
    : profileUser.name;
  const displayPicture = isAvatarWorld
    ? (profileUser.avatar_picture || profileUser.picture)
    : profileUser.picture;
  const displayBio = isAvatarWorld
    ? (profileUser.avatar_bio || profileUser.bio || 'Configure your maya profile!')
    : profileUser.bio;
  const displayJobTitle = isAvatarWorld
    ? (profileUser.avatar_job_title || profileUser.job_title)
    : profileUser.job_title;
  const displayLocation = isAvatarWorld
    ? (profileUser.avatar_location || profileUser.location)
    : profileUser.location;

  const handleProfilePictureUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error("Please select an image file");
      return;
    }

    try {
      await userService.uploadProfilePicture(file, worldMode);
      toast.success(isAvatarWorld ? "Maya profile picture updated!" : "Profile picture updated!");
      if (onProfileUpdated) {
        onProfileUpdated();
      }
    } catch (error) {
      console.error("Error uploading profile picture:", error);
      toast.error("Failed to upload profile picture");
    }
  };

  const handleMessage = () => {
    if (onMessage) {
      onMessage(profileUser);
    } else {
      navigate(`/chat/${profileUser.id}`);
    }
  };

  const handleSendFriendRequest = async () => {
    if (onSendFriendRequest) {
      onSendFriendRequest(profileUser.id);
    } else {
      try {
        await friendService.sendFriendRequest(profileUser.id);
        toast.success("Friend request sent!");
        if (onProfileUpdated) {
          onProfileUpdated();
        }
      } catch (error) {
        console.error("Error sending friend request:", error);
        const errorMessage = error.response?.data?.detail || error.message || "Failed to send friend request";
        toast.error(errorMessage);
      }
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-6">
      <div className="flex flex-col md:flex-row items-start md:items-end gap-6 -mt-20 relative z-10">
        {/* Profile Picture */}
        <div className="relative">
          <Avatar className="w-32 h-32 border-4 border-white shadow-lg">
            <AvatarImage src={displayPicture} className="object-cover" />
            <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white text-3xl">
              {displayName?.charAt(0) || '?'}
            </AvatarFallback>
          </Avatar>
          {isOwnProfile && (
            <label className="absolute bottom-0 right-0 cursor-pointer">
              <input
                type="file"
                accept="image/*"
                onChange={handleProfilePictureUpload}
                className="hidden"
                id="profile-picture-upload"
                disabled={uploadingPicture}
              />
              <Button
                size="sm"
                className="rounded-full bg-blue-500 hover:bg-blue-600 text-white p-2"
                disabled={uploadingPicture}
                onClick={(e) => {
                  e.preventDefault();
                  document.getElementById('profile-picture-upload')?.click();
                }}
              >
                <Camera className="w-4 h-4" />
              </Button>
            </label>
          )}
        </div>

        {/* Profile Details */}
        <div className="flex-1 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <h1 className="text-3xl font-bold text-gray-900">{displayName}</h1>
              {profileUser.is_bot && (
                <Badge className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700">
                  <Bot className="w-3 h-3 mr-1" />
                  AI
                </Badge>
              )}
            </div>
            {displayBio && (
              <p className="text-gray-700 mb-2">{displayBio}</p>
            )}
            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
              {displayJobTitle && (
                <div className="flex items-center gap-1">
                  <Briefcase className="w-4 h-4" />
                  <span>{displayJobTitle}</span>
                </div>
              )}
              {displayLocation && (
                <div className="flex items-center gap-1">
                  <MapPin className="w-4 h-4" />
                  <span>{displayLocation}</span>
                </div>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            {isOwnProfile ? (
              <Button
                variant="outline"
                onClick={() => navigate('/settings')}
                className="border-purple-400 text-purple-700 hover:bg-purple-50"
              >
                <Edit2 className="w-4 h-4 mr-2" />
                Edit Profile
              </Button>
            ) : (
              <>
                {friendshipStatus === 'friends' ? (
                  <Button
                    onClick={handleMessage}
                    className="bg-blue-500 hover:bg-blue-600 text-white"
                  >
                    <MessageCircle className="w-4 h-4 mr-2" />
                    Message
                  </Button>
                ) : friendshipStatus === 'pending' ? (
                  <Button
                    variant="outline"
                    disabled
                    className="border-gray-300 text-gray-500"
                  >
                    Request Pending
                  </Button>
                ) : (
                  <Button
                    onClick={handleSendFriendRequest}
                    className="bg-purple-500 hover:bg-purple-600 text-white"
                  >
                    <UserPlus className="w-4 h-4 mr-2" />
                    Add Friend
                  </Button>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
});

ProfileInfo.displayName = "ProfileInfo";

export default ProfileInfo;

