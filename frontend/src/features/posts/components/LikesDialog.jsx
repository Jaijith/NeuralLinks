import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ThumbsUp } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { postService } from '@/services/api';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

/**
 * @typedef {Object} LikesDialogProps
 * @property {boolean} open - Whether the dialog is open
 * @property {function} onOpenChange - Handler for open state changes
 * @property {string} postId - ID of the post
 * @property {string} [worldMode] - Current world mode ('real' or 'avatar')
 * @property {string} [className] - Additional CSS classes
 */

/**
 * Likes Dialog component for displaying who liked a post.
 * Supports both Maya (avatar) and Sense (real) worlds.
 * @param {LikesDialogProps} props
 */
const LikesDialog = React.memo(({
  open,
  onOpenChange,
  postId,
  worldMode = 'real',
  className
}) => {
  const navigate = useNavigate();
  const [likesData, setLikesData] = useState([]);
  const [likesCount, setLikesCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const isAvatarWorld = worldMode === 'avatar';

  useEffect(() => {
    if (open && postId) {
      fetchLikes();
    } else {
      // Reset when closed
      setLikesData([]);
      setLikesCount(0);
    }
  }, [open, postId]);

  const fetchLikes = async () => {
    if (!postId) return;
    
    setLoading(true);
    try {
      const response = await postService.getPostLikes(postId);
      
      // Handle different response formats
      if (Array.isArray(response)) {
        setLikesData(response);
        setLikesCount(response.length);
      } else if (response.likes) {
        setLikesData(response.likes);
        setLikesCount(response.count || response.likes.length);
      } else if (response.users) {
        setLikesData(response.users);
        setLikesCount(response.count || response.users.length);
      } else {
        setLikesCount(response.count || 0);
      }
    } catch (error) {
      console.error("Error fetching likes:", error);
      toast.error("Failed to load likes");
    } finally {
      setLoading(false);
    }
  };

  const handleUserClick = (userId) => {
    if (userId) {
      onOpenChange(false);
      navigate(`/profile/${userId}`);
    }
  };

  const getDisplayName = (user) => {
    if (isAvatarWorld) {
      return user.avatar_name || user.name || 'Unknown User';
    }
    return user.name || 'Unknown User';
  };

  const getDisplayPicture = (user) => {
    if (isAvatarWorld) {
      return user.avatar_picture || user.picture || '';
    }
    return user.picture || '';
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={cn(
        "max-w-md",
        isAvatarWorld ? "bg-slate-900 border-blue-500/30" : "bg-white",
        className
      )}>
        <DialogHeader>
          <DialogTitle className={isAvatarWorld ? 'text-white' : 'text-gray-900'}>
            People who liked this
          </DialogTitle>
        </DialogHeader>
        
        <div className="max-h-96 overflow-y-auto space-y-2 mt-4">
          {loading ? (
            <div className="text-center py-6">
              <div className="w-8 h-8 border-2 border-gray-400 border-t-transparent rounded-full animate-spin mx-auto"></div>
            </div>
          ) : likesData.length > 0 ? (
            likesData.map((user) => {
              const displayName = getDisplayName(user);
              const displayPicture = getDisplayPicture(user);
              const userId = user.id || user.user_id;

              return (
                <div
                  key={userId || Math.random()}
                  className={cn(
                    "flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-colors",
                    isAvatarWorld 
                      ? "hover:bg-slate-800" 
                      : "hover:bg-gray-50"
                  )}
                  onClick={() => handleUserClick(userId)}
                >
                  <Avatar className="w-10 h-10">
                    <AvatarImage src={displayPicture} alt={displayName} />
                    <AvatarFallback className="bg-blue-500 text-white">
                      {displayName.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <p className={cn(
                    "font-medium flex-1",
                    isAvatarWorld ? "text-white" : "text-gray-900"
                  )}>
                    {displayName}
                  </p>
                </div>
              );
            })
          ) : likesCount > 0 ? (
            <div className="text-center py-6">
              <div className={cn(
                "w-12 h-12 mx-auto mb-3 rounded-full flex items-center justify-center",
                isAvatarWorld ? "bg-blue-500/20" : "bg-blue-100"
              )}>
                <ThumbsUp className={cn(
                  "w-6 h-6",
                  isAvatarWorld ? "text-blue-400" : "text-blue-500"
                )} />
              </div>
              <p className={isAvatarWorld ? 'text-blue-200' : 'text-gray-600'}>
                {likesCount} {likesCount === 1 ? 'person likes' : 'people like'} this
              </p>
            </div>
          ) : (
            <p className={cn(
              "text-center py-6",
              isAvatarWorld ? "text-blue-400" : "text-gray-500"
            )}>
              No likes yet
            </p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
});

LikesDialog.displayName = "LikesDialog";

export default LikesDialog;

