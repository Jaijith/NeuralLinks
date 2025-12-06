import { useState, useCallback } from 'react';
import { postService } from '@/services/api';
import { toast } from 'sonner';

/**
 * Custom hook for creating posts
 * Supports both Maya (avatar) and Sense (real) worlds
 */
const useCreatePost = (worldMode = 'real', onPostCreated) => {
  const [postText, setPostText] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [showDialog, setShowDialog] = useState(false);

  const postType = worldMode === 'avatar' ? 'avatar' : 'real';
  const isAvatarWorld = worldMode === 'avatar';

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

  const createPost = useCallback(async () => {
    if (!postText.trim() && !selectedImage) {
      toast.error("Please add some text or an image");
      return;
    }

    setUploading(true);
    try {
      let response;
      let newPost;

      if (selectedImage) {
        // Upload image with caption
        response = await postService.uploadPostImage(selectedImage);
        const imageUrl = response.image_url || response.url;
        
        // Create post with image
        newPost = await postService.createPost(postText, postType, imageUrl);
      } else {
        // Create text-only post
        newPost = await postService.createPost(postText, postType);
      }

      // Success
      toast.success(isAvatarWorld ? "✨ Maya post created!" : "🎉 Post created!");
      
      // Reset form
      setPostText('');
      setSelectedImage(null);
      setImagePreview(null);
      setShowDialog(false);

      // Notify parent
      if (onPostCreated) {
        const enrichedPost = {
          ...(newPost.post || newPost),
          user_id: (newPost.post || newPost).user_id || newPost.user_id,
          displayName: isAvatarWorld 
            ? (newPost.avatar_name || newPost.name)
            : newPost.name,
          displayPicture: isAvatarWorld
            ? (newPost.avatar_picture || newPost.picture)
            : newPost.picture,
          likes: (newPost.post || newPost).likes || 0,
          liked_by: (newPost.post || newPost).liked_by || [],
          comments: (newPost.post || newPost).comments || [],
          comment_count: (newPost.post || newPost).comment_count || 0
        };
        onPostCreated(enrichedPost);
      }

      return newPost;
    } catch (error) {
      console.error("Error creating post:", error);
      toast.error("Failed to create post");
      return null;
    } finally {
      setUploading(false);
    }
  }, [postText, selectedImage, postType, isAvatarWorld, onPostCreated]);

  const reset = useCallback(() => {
    setPostText('');
    setSelectedImage(null);
    setImagePreview(null);
    setShowDialog(false);
  }, []);

  return {
    postText,
    setPostText,
    selectedImage,
    imagePreview,
    uploading,
    showDialog,
    setShowDialog,
    handleImageSelect,
    handleRemoveImage,
    createPost,
    reset
  };
};

export default useCreatePost;

