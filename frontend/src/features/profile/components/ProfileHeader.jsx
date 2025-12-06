import React from 'react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Camera, MessageCircle, UserPlus, UserCheck, Briefcase, MapPin } from 'lucide-react';
import { friendService } from '@/services/api';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

/**
 * @typedef {Object} ProfileHeaderProps
 * @property {Object} profileUser - Profile user object
 * @property {Object} currentUser - Current logged-in user
 * @property {boolean} isOwnProfile - Whether this is the current user's own profile
 * @property {string} [worldMode] - Current world mode ('real' or 'avatar')
 * @property {string} [friendshipStatus] - Friendship status ('none', 'friends', 'pending', 'requested')
 * @property {function} [onFriendshipStatusChange] - Callback when friendship status changes
 * @property {boolean} [uploadingProfilePicture] - Whether profile picture is uploading
 * @property {boolean} [uploadingCoverPhoto] - Whether cover photo is uploading
 * @property {function} [onProfilePictureUpload] - Handler for profile picture upload
 * @property {function} [onCoverPhotoUpload] - Handler for cover photo upload
 */

/**
 * Profile Header component with cover photo, profile picture, and basic info.
 * Supports both Maya (avatar) and Sense (real) worlds.
 */
const ProfileHeader = React.memo(({
  profileUser,
  currentUser,
  isOwnProfile,
  worldMode = 'real',
  friendshipStatus = 'none',
  onFriendshipStatusChange,
  uploadingProfilePicture = false,
  uploadingCoverPhoto = false,
  onProfilePictureUpload,
  onCoverPhotoUpload
}) => {
  const navigate = useNavigate();
  const isAvatarWorld = worldMode === 'avatar';

  const displayName = isAvatarWorld
    ? (profileUser.avatar_name || profileUser.name)
    : profileUser.name;
  const displayPicture = isAvatarWorld
    ? (profileUser.avatar_picture || profileUser.picture)
    : profileUser.picture;
  const displayBio = isAvatarWorld
    ? (profileUser.avatar_bio || profileUser.bio)
    : profileUser.bio;
  const displayJobTitle = isAvatarWorld
    ? (profileUser.avatar_job_title || profileUser.job_title)
    : profileUser.job_title;
  const displayLocation = isAvatarWorld
    ? (profileUser.avatar_location || profileUser.location)
    : profileUser.location;
  const coverPhoto = isAvatarWorld
    ? profileUser.avatar_cover_photo
    : profileUser.cover_photo;

  const handleSendFriendRequest = async () => {
    if (!profileUser?.id) {
      toast.error("Invalid user ID");
      return;
    }

    try {
      await friendService.sendFriendRequest(profileUser.id);
      toast.success("Friend request sent!");
      if (onFriendshipStatusChange) {
        onFriendshipStatusChange('pending');
      }
    } catch (error) {
      console.error("Error sending friend request:", error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || "Failed to send friend request";
      toast.error(errorMessage);
    }
  };

  const handleMessage = () => {
    navigate(`/chat/${profileUser.id}`);
  };

  return (
    <>
      {/* Cover Photo */}
      <div className="relative h-96 bg-gradient-to-br from-pink-400 via-purple-500 to-indigo-600 profile-cover overflow-hidden">
        {coverPhoto && (
          <img
            src={coverPhoto}
            alt="Cover photo"
            className="w-full h-full object-cover"
          />
        )}
        <div className="absolute inset-0 bg-black/20"></div>
        {isOwnProfile && (
          <div className="absolute bottom-4 right-4 z-10">
            <label className="cursor-pointer">
              <input
                type="file"
                accept="image/*"
                onChange={onCoverPhotoUpload}
                className="hidden"
                id="cover-photo-upload"
                disabled={uploadingCoverPhoto}
              />
              <Button
                variant="secondary"
                className="bg-white/90 hover:bg-white shadow-lg"
                disabled={uploadingCoverPhoto}
                onClick={(e) => {
                  e.preventDefault();
                  document.getElementById('cover-photo-upload')?.click();
                }}
              >
                <Camera className="w-4 h-4 mr-2" />
                {uploadingCoverPhoto ? 'Uploading...' : 'Edit Cover Photo'}
              </Button>
            </label>
          </div>
        )}
      </div>

      {/* Profile Info */}
      <div className="max-w-6xl mx-auto px-6">
        <div className="relative">
          <div className="absolute -top-32 left-8">
            <Avatar className="w-44 h-44 border-8 border-white shadow-xl">
              <AvatarImage src={displayPicture} className="object-cover" />
              <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white text-4xl">
                {displayName?.charAt(0)}
              </AvatarFallback>
            </Avatar>
            {isOwnProfile && (
              <label className="cursor-pointer">
                <input
                  type="file"
                  accept="image/*"
                  onChange={onProfilePictureUpload}
                  className="hidden"
                  id="profile-picture-upload"
                  disabled={uploadingProfilePicture}
                />
                <Button
                  size="sm"
                  className="absolute bottom-2 right-2 rounded-full w-10 h-10 p-0 bg-white hover:bg-gray-100"
                  disabled={uploadingProfilePicture}
                  onClick={(e) => {
                    e.preventDefault();
                    document.getElementById('profile-picture-upload')?.click();
                  }}
                >
                  <Camera className="w-5 h-5 text-gray-700" />
                </Button>
              </label>
            )}
          </div>

          <div className="pt-20 pb-6 flex items-end justify-between">
            <div>
              <h1 className="text-4xl font-bold text-gray-900 mb-2">{displayName}</h1>
              {displayBio && (
                <p className="text-lg text-gray-700 mb-2">{displayBio}</p>
              )}
              <div className="flex items-center gap-4 text-sm text-gray-600">
                {displayJobTitle && (
                  <span className="flex items-center gap-1">
                    <Briefcase className="w-4 h-4" />
                    {displayJobTitle}
                  </span>
                )}
                {displayLocation && (
                  <span className="flex items-center gap-1">
                    <MapPin className="w-4 h-4" />
                    {displayLocation}
                  </span>
                )}
              </div>
            </div>

            {!isOwnProfile && (
              <div className="flex gap-3">
                {friendshipStatus === 'friends' ? (
                  <>
                    <Button
                      onClick={handleMessage}
                      className="bg-blue-500 hover:bg-blue-600 text-white"
                    >
                      <MessageCircle className="w-4 h-4 mr-2" />
                      Message
                    </Button>
                    <Button variant="outline" className="border-gray-300">
                      <UserCheck className="w-4 h-4 mr-2" />
                      Friends
                    </Button>
                  </>
                ) : friendshipStatus === 'pending' ? (
                  <Button variant="outline" disabled className="border-gray-300">
                    Friend Request Sent
                  </Button>
                ) : (
                  <Button
                    onClick={handleSendFriendRequest}
                    className="bg-blue-500 hover:bg-blue-600 text-white"
                  >
                    <UserPlus className="w-4 h-4 mr-2" />
                    Add Friend
                  </Button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
});

ProfileHeader.displayName = "ProfileHeader";

export default ProfileHeader;
