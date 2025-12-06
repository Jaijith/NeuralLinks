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
  const [postText, setPostText] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [uploading, setUploading] = useState(false);

  const isAvatarWorld = worldMode === 'avatar';
  const postType = isAvatarWorld ? 'avatar' : 'real';
  
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

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className={cn("max-w-lg bg-white", className)}>
        <DialogHeader>
          <DialogTitle className="text-xl font-bold text-gray-900">
            {dialogTitle}
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4 mt-4">
          {/* User Info */}
          <div className="flex items-start gap-3">
            <Avatar className="w-10 h-10">
              <AvatarImage src={displayPicture} alt={displayName} />
              <AvatarFallback>{displayName?.charAt(0) || '?'}</AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <p className="font-semibold text-gray-900">
                {displayName}
              </p>
              <div className="flex items-center gap-1 text-xs text-gray-500">
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
            rows={5}
            className="resize-none border-none text-lg bg-gray-50 focus:ring-blue-500/50"
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
            <div className="relative">
              <img
                src={imagePreview}
                alt="Preview"
                className="w-full h-64 object-cover rounded-lg"
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
          <div className="flex items-center justify-between">
            <label
              htmlFor="post-image-upload"
              className="cursor-pointer flex items-center gap-2 px-4 py-2 rounded-lg transition-all hover:bg-gray-100 text-gray-700"
            >
              <ImageIcon className="w-5 h-5" style={{ color: '#34d399' }} />
              <span className="font-medium text-sm">Add Photo</span>
            </label>
            <div className="flex gap-2">
              <Button
                variant="ghost"
                onClick={handleClose}
                disabled={uploading}
                className="text-gray-600 hover:bg-gray-100"
              >
                Cancel
              </Button>
              <Button
                onClick={handleCreatePost}
                disabled={(!postText.trim() && !selectedImage) || uploading}
                className="px-6 bg-blue-500 hover:bg-blue-600 text-white"
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

