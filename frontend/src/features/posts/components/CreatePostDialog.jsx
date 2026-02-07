import React, { useState, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Globe, Image as ImageIcon, X } from 'lucide-react';
import { postService } from '@/services/api';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import useViewMode from '@/hooks/useViewMode';

/**
 * @typedef {Object} CreatePostDialogProps
 * @property {boolean} open - Whether the dialog is open
 * @property {function} onOpenChange - Handler for open state changes
 * @property {Object} user - Current user object
 * @property {string} [worldMode] - Current world mode ('real' or 'avatar')
 * @property {function} onPostCreated - Callback when post is successfully created
 * @property {string} [className] - Additional CSS classes
 */

/**
 * Create Post Dialog component for creating posts with text and image upload.
 * Supports both Maya (avatar) and Sense (real) worlds.
 * @param {CreatePostDialogProps} props
 */
const CreatePostDialog = React.memo(({
  open,
  onOpenChange,
  user,
  worldMode = 'real',
  onPostCreated,
  className
}) => {
  const { isImmersive } = useViewMode();
  const [postText, setPostText] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [uploading, setUploading] = useState(false);

  const isAvatarWorld = worldMode === 'avatar';
  const postType = isAvatarWorld ? 'avatar' : 'real';
  // Use dark theme for immersive mode in any world
  const useDarkTheme = isImmersive || isAvatarWorld;
  
  const displayName = isAvatarWorld 
    ? (user.avatar_name || user.name)
    : user.name;
  const displayPicture = isAvatarWorld
    ? (user.avatar_picture || user.picture)
    : user.picture;

  const handleImageSelect = useCallback((e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error("Please select an image file");
      return;
    }

    setSelectedImage(file);
    const reader = new FileReader();
    reader.onloadend = () => {
      setImagePreview(reader.result);
    };
    reader.readAsDataURL(file);
  }, []);

  const handleRemoveImage = useCallback(() => {
    setSelectedImage(null);
    setImagePreview(null);
    // Reset file input
    const fileInput = document.getElementById('post-image-upload');
    if (fileInput) {
      fileInput.value = '';
    }
  }, []);

  const handleCreatePost = useCallback(async () => {
    if (!postText.trim() && !selectedImage) {
      toast.error("Please add some text or an image");
      return;
    }

    setUploading(true);
    try {
      let newPost;

      if (selectedImage) {
        // Upload image with caption using FormData
        const formData = new FormData();
        formData.append('file', selectedImage);
        formData.append('caption', postText);
        formData.append('post_type', postType);
        
        const response = await postService.createPostWithImage(formData);
        newPost = response.post || response;
      } else {
        // Create text-only post
        const postData = {
          text: postText,
          post_type: postType
        };
        const response = await postService.createPost(postData);
        newPost = response.post || response;
      }

      // Success
      toast.success(isAvatarWorld ? "✨ Maya post created!" : "🎉 Post created!");
      
      // Reset form
      setPostText('');
      setSelectedImage(null);
      setImagePreview(null);
      onOpenChange(false);

      // Notify parent
      if (onPostCreated) {
        onPostCreated(newPost);
      }
    } catch (error) {
      console.error("Error creating post:", error);
      const errorMessage = error.response?.data?.detail || error.message || "Failed to create post";
      toast.error(errorMessage);
    } finally {
      setUploading(false);
    }
  }, [postText, selectedImage, postType, isAvatarWorld, onPostCreated, onOpenChange]);

  const handleClose = useCallback(() => {
    if (!uploading) {
      setPostText('');
      setSelectedImage(null);
      setImagePreview(null);
      onOpenChange(false);
    }
  }, [uploading, onOpenChange]);

  const dialogTitle = isAvatarWorld ? '✨ Create Maya Post' : '📝 Create Post';
  const placeholder = isAvatarWorld 
    ? "What's your avatar thinking?"
    : "What's on your mind?";

  // Accent color - purple for Maya, blue for Sense
  const accentColor = isAvatarWorld ? 'purple' : 'blue';
  
  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent 
        className={cn(
          "w-[95vw] max-w-lg mx-auto p-4 sm:p-6 rounded-2xl",
          useDarkTheme 
            ? "bg-slate-900 border border-slate-700/50" 
            : "bg-white border border-gray-200",
          className
        )}
        style={{
          maxHeight: '90vh',
          overflowY: 'auto',
        }}
      >
        <DialogHeader className="pb-2">
          <DialogTitle className={cn(
            "text-lg sm:text-xl font-bold text-center",
            useDarkTheme ? "text-white" : "text-gray-900"
          )}>
            {dialogTitle}
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* User Info */}
          <div className="flex items-center gap-3">
            <Avatar className={cn(
              "w-10 h-10 sm:w-12 sm:h-12 ring-2",
              isAvatarWorld ? "ring-purple-500/30" : "ring-blue-500/20"
            )}>
              <AvatarImage src={displayPicture} alt={displayName} />
              <AvatarFallback className={isAvatarWorld ? "bg-purple-600 text-white" : "bg-blue-500 text-white"}>
                {displayName?.charAt(0) || '?'}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className={cn(
                "font-semibold truncate",
                useDarkTheme ? "text-white" : "text-gray-900"
              )}>
                {displayName}
              </p>
              <div className={cn(
                "flex items-center gap-1 text-xs",
                useDarkTheme ? "text-gray-400" : "text-gray-500"
              )}>
                <Globe className="w-3 h-3" />
                <span>Public</span>
              </div>
            </div>
          </div>

          {/* Text Input */}
          <Textarea
            placeholder={placeholder}
            value={postText}
            onChange={(e) => setPostText(e.target.value)}
            rows={4}
            className={cn(
              "w-full resize-none rounded-xl text-base",
              useDarkTheme 
                ? `bg-slate-800 border-slate-700 text-white placeholder:text-gray-500 focus:ring-${accentColor}-500/50 focus:border-${accentColor}-500` 
                : "bg-gray-50 border-gray-200 text-gray-900 placeholder:text-gray-400 focus:ring-blue-500/50"
            )}
          />

          {/* Hidden file input */}
          <input
            type="file"
            accept="image/*"
            onChange={handleImageSelect}
            className="hidden"
            id="post-image-upload"
          />

          {/* Image Preview */}
          {imagePreview && (
            <div className="relative rounded-xl overflow-hidden">
              <img
                src={imagePreview}
                alt="Preview"
                className="w-full h-48 sm:h-64 object-cover"
              />
              <button
                onClick={handleRemoveImage}
                className="absolute top-2 right-2 bg-red-500 hover:bg-red-600 text-white rounded-full p-1.5 transition-colors"
                aria-label="Remove image"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
            <label
              htmlFor="post-image-upload"
              className={cn(
                "cursor-pointer flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl transition-all",
                useDarkTheme 
                  ? "bg-slate-800 hover:bg-slate-700 text-gray-300" 
                  : "bg-gray-100 hover:bg-gray-200 text-gray-700"
              )}
            >
              <ImageIcon className="w-5 h-5" style={{ color: '#34d399' }} />
              <span className="font-medium text-sm">Add Photo</span>
            </label>
            
            <div className="flex gap-2">
              <Button
                variant="ghost"
                onClick={handleClose}
                disabled={uploading}
                className={cn(
                  "flex-1 sm:flex-none px-4",
                  useDarkTheme 
                    ? "text-gray-400 hover:bg-slate-800 hover:text-white" 
                    : "text-gray-600 hover:bg-gray-100"
                )}
              >
                Cancel
              </Button>
              <Button
                onClick={handleCreatePost}
                disabled={(!postText.trim() && !selectedImage) || uploading}
                className={cn(
                  "flex-1 sm:flex-none px-6",
                  isAvatarWorld 
                    ? "bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white border-0" 
                    : "bg-blue-500 hover:bg-blue-600 text-white"
                )}
              >
                {uploading ? 'Posting...' : 'Post'}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
});

CreatePostDialog.displayName = "CreatePostDialog";

export default CreatePostDialog;

