import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Camera, Image as ImageIcon } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { useWorldMode } from "@/contexts/WorldModeContext";
import AppHeader from "@/components/AppHeader";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const GalleryPage = ({ user, setUser }) => {
  const navigate = useNavigate();
  const { worldMode } = useWorldMode();
  const [galleryPhotos, setGalleryPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showUploadImage, setShowUploadImage] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [imageCaption, setImageCaption] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);

  useEffect(() => {
    fetchGalleryPhotos();
  }, [worldMode]);

  const fetchGalleryPhotos = async () => {
    try {
      const postType = worldMode === 'avatar' ? 'avatar' : 'real';
      const response = await axios.get(`${API}/gallery/photos?post_type=${postType}`, {
        withCredentials: true,
      });
      setGalleryPhotos(response.data.photos || []);
    } catch (error) {
      console.error("Error fetching gallery photos:", error);
      toast.error("Failed to load gallery photos");
    } finally {
      setLoading(false);
    }
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error("Please select an image file");
      return;
    }

    setSelectedImage(file);
    setShowUploadImage(true);
  };

  const uploadImage = async () => {
    if (!selectedImage) return;

    setUploadingImage(true);
    try {
      const postType = worldMode === 'avatar' ? 'avatar' : 'real';
      
      // Step 1: Get presigned URL from backend
      const presignedResponse = await axios.post(`${API}/posts/presigned-upload`, {
        filename: selectedImage.name,
        content_type: selectedImage.type,
        subfolder: 'images',
      }, { withCredentials: true });
      
      const { presigned_url, public_url } = presignedResponse.data;
      
      // Step 2: Upload file directly to S3 using presigned URL
      await fetch(presigned_url, {
        method: 'PUT',
        body: selectedImage,
        headers: {
          'Content-Type': selectedImage.type,
        },
      });
      
      // Step 3: Create the post with the S3 image URL
      await axios.post(`${API}/posts/create-with-s3-image`, {
        image_url: public_url,
        caption: imageCaption,
        post_type: postType,
      }, { withCredentials: true });

      toast.success("Image uploaded successfully!");
      setShowUploadImage(false);
      setSelectedImage(null);
      setImageCaption('');
      fetchGalleryPhotos(); // Refresh gallery
    } catch (error) {
      console.error("Error uploading image:", error);
      toast.error("Failed to upload image");
    } finally {
      setUploadingImage(false);
    }
  };

  const handleImageClick = (photo) => {
    // Navigate to home page and scroll to post
    navigate(`/home`);
    // Scroll to post after navigation (using setTimeout to ensure page loads)
    setTimeout(() => {
      const postElement = document.querySelector(`[data-post-id="${photo.post_id}"]`);
      if (postElement) {
        postElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 1000);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-slate-50">
        <AppHeader user={user} setUser={setUser} currentPage="gallery" />
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-600">Loading gallery...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-slate-50">
      <AppHeader user={user} setUser={setUser} currentPage="gallery" />
      
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold mb-2 text-gray-900">
              Gallery
            </h1>
            <p className="text-gray-600">
              {galleryPhotos.length} {galleryPhotos.length === 1 ? 'photo' : 'photos'}
            </p>
          </div>
          <label className="cursor-pointer">
            <input
              type="file"
              accept="image/*"
              onChange={handleImageUpload}
              className="hidden"
              id="gallery-upload"
            />
            <Button
              onClick={(e) => {
                e.preventDefault();
                document.getElementById('gallery-upload')?.click();
              }}
              className="bg-blue-500 hover:bg-blue-600 text-white"
            >
              <Camera className="w-4 h-4 mr-2" />
              Upload Photo
            </Button>
          </label>
        </div>

        {galleryPhotos.length === 0 ? (
          <Card className="p-12 text-center glass-morphism">
            <ImageIcon className="w-16 h-16 mx-auto mb-4 text-gray-400" />
            <h3 className="text-xl font-semibold mb-2 text-gray-900">
              No photos yet
            </h3>
            <p className="text-gray-600 mb-4">
              Start building your gallery by uploading your first photo!
            </p>
            <label className="cursor-pointer inline-block">
              <input
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
                id="gallery-upload-empty"
              />
              <Button
                onClick={(e) => {
                  e.preventDefault();
                  document.getElementById('gallery-upload-empty')?.click();
                }}
                className="bg-blue-500 hover:bg-blue-600 text-white"
              >
                <Camera className="w-4 h-4 mr-2" />
                Upload Your First Photo
              </Button>
            </label>
          </Card>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {galleryPhotos.map((photo) => (
              <div
                key={photo.id}
                className="relative aspect-square rounded-lg overflow-hidden cursor-pointer hover:opacity-90 transition-opacity border border-gray-200 shadow-sm group"
                onClick={() => handleImageClick(photo)}
              >
                <img
                  src={photo.image_url}
                  alt={photo.caption || 'Gallery photo'}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    console.error("Image load error:", photo.image_url);
                    e.target.style.display = 'none';
                    e.target.parentElement.classList.add('bg-gray-200');
                  }}
                />
                {photo.caption && (
                  <div className="absolute inset-x-0 bottom-0 p-3 bg-gradient-to-t from-black/80 via-black/60 to-transparent">
                    <p className="text-sm text-white font-medium line-clamp-2 break-words">
                      {photo.caption}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Upload Image Dialog */}
      <Dialog open={showUploadImage} onOpenChange={setShowUploadImage}>
        <DialogContent className="max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="text-gray-900 font-bold">
              Upload Photo
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {selectedImage && (
              <div className="w-full">
                <img
                  src={URL.createObjectURL(selectedImage)}
                  alt="Preview"
                  className="w-full h-64 object-cover rounded"
                />
              </div>
            )}
            <Textarea
              placeholder="Add a caption (optional)"
              value={imageCaption}
              onChange={(e) => setImageCaption(e.target.value)}
              rows={3}
              className="resize-none"
            />
            <div className="flex justify-end space-x-2">
              <Button
                variant="ghost"
                onClick={() => {
                  setShowUploadImage(false);
                  setSelectedImage(null);
                  setImageCaption('');
                }}
                disabled={uploadingImage}
              >
                Cancel
              </Button>
              <Button
                onClick={uploadImage}
                disabled={uploadingImage || !selectedImage}
                className="bg-blue-500 hover:bg-blue-600 text-white"
              >
                {uploadingImage ? 'Uploading...' : 'Upload'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default GalleryPage;

