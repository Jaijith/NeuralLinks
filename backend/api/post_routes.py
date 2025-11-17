"""
Post Routes
"""

from fastapi import APIRouter, Request, HTTPException, Query, UploadFile, File, Form
from typing import Dict, Any, Optional
from core.auth import require_auth
from services.post_service import PostService
from utils.file_storage import save_file, get_file_url
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["posts"])


def get_post_service() -> PostService:
    """Get post service instance"""
    from app.globals import post_service
    return post_service


@router.post("/profile/posts")
async def create_post(post_data: Dict[str, str], request: Request):
    """Create a new post on user's profile"""
    user = await require_auth(request)
    post_service = get_post_service()
    return await post_service.create_post(user.id, post_data)


@router.get("/profile/posts")
async def get_user_posts(
    post_type: str = Query("real", description="Post type: 'real' or 'avatar'"),
    user_id: Optional[str] = Query(None, description="User ID (defaults to current user)"),
    request: Request = None
):
    """Get user's posts (current user or specified user_id)"""
    current_user = await require_auth(request)
    target_user_id = user_id if user_id else current_user.id
    post_service = get_post_service()
    return await post_service.get_user_posts(target_user_id, post_type)


@router.get("/feed/posts")
async def get_feed_posts(
    post_type: str = Query("real", description="Post type: 'real' or 'avatar'"),
    request: Request = None
):
    """Get feed posts (posts from friends and user)"""
    current_user = await require_auth(request)
    post_service = get_post_service()
    return await post_service.get_feed_posts(current_user.id, post_type)


@router.delete("/profile/posts/{post_id}")
async def delete_post(post_id: str, request: Request):
    """Delete a post"""
    user = await require_auth(request)
    post_service = get_post_service()
    deleted = await post_service.delete_post(post_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"message": "Post deleted"}


@router.post("/posts/{post_id}/like")
async def like_post(post_id: str, request: Request):
    """Like or unlike a post (toggle behavior)"""
    user = await require_auth(request)
    post_service = get_post_service()
    result = await post_service.like_post(post_id, user.id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Post not found"))
    return {"message": "Post liked" if result.get("liked") else "Post unliked", "liked": result.get("liked"), "likes": result.get("likes")}


@router.post("/posts/{post_id}/comment")
async def comment_on_post(post_id: str, comment_data: Dict[str, str], request: Request):
    """Add a comment to a post"""
    user = await require_auth(request)
    comment_text = comment_data.get('text', '')
    if not comment_text:
        raise HTTPException(status_code=400, detail="Comment text is required")
    
    post_service = get_post_service()
    result = await post_service.comment_on_post(post_id, user.id, comment_text, user.name, user.picture or "")
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Post not found"))
    return {"message": "Comment added", "comment": result.get("comment")}


@router.get("/posts/{post_id}/comments")
async def get_post_comments(post_id: str, request: Request):
    """Get all comments for a post"""
    _ = await require_auth(request)
    
    post_service = get_post_service()
    result = await post_service.get_post_comments(post_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Post not found"))
    return {"comments": result.get("comments", []), "count": result.get("count", 0)}


@router.get("/posts/{post_id}/likes")
async def get_post_likes(post_id: str, request: Request):
    """Get list of users who liked a post"""
    _ = await require_auth(request)
    
    post_service = get_post_service()
    result = await post_service.get_post_likes(post_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Post not found"))
    return {"users": result.get("users", []), "count": result.get("count", 0)}


@router.put("/profile/posts/{post_id}")
async def update_post(post_id: str, post_data: Dict[str, str], request: Request):
    """Update a post"""
    user = await require_auth(request)
    post_service = get_post_service()
    result = await post_service.update_post(post_id, user.id, post_data)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Post not found"))
    return {"message": "Post updated"}


@router.post("/posts/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    post_type: str = Form("real"),
    request: Request = None
):
    """Upload an image and create a photo post"""
    user = await require_auth(request)
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read file content
    file_content = await file.read()
    
    # Save file
    try:
        file_path = await save_file(file_content, file.filename, 'images')
        image_url = get_file_url(file_path)
        logger.info(f"File saved: {file_path}, URL: {image_url}")
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save image")
    
    # Create post with image
    post_service = get_post_service()
    post_data = {
        'text': caption or '',
        'post_type': post_type,
        'image_url': image_url
    }
    
    post = await post_service.create_post(user.id, post_data)
    logger.info(f"Post created with image: {post.get('id')}, image_url: {post.get('image_url')}")
    
    return {
        "success": True,
        "post": post,
        "image_url": image_url
    }


@router.get("/gallery/photos")
async def get_gallery_photos(
    post_type: str = Query("real", description="Post type: 'real' or 'avatar'"),
    limit: int = Query(50, description="Number of photos to return"),
    request: Request = None
):
    """Get gallery photos (posts with images)"""
    user = await require_auth(request)
    post_service = get_post_service()
    photos = await post_service.get_gallery_photos(user.id, post_type, limit)
    return {"photos": photos, "count": len(photos)}

