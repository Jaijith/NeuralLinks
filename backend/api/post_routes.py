"""
Post Routes
"""

import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Query, UploadFile, File, Form
from typing import Dict, Any, Optional
from core.auth import require_auth
from services.post_service import PostService
from utils.file_storage import save_file, get_file_url
import logging
import boto3
from botocore.exceptions import ClientError

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
    limit: int = Query(20, description="Number of posts to return"),
    skip: int = Query(0, description="Number of posts to skip"),
    request: Request = None
):
    """Get user's posts (current user or specified user_id) with pagination"""
    current_user = await require_auth(request)
    target_user_id = user_id if user_id else current_user.id
    post_service = get_post_service()
    return await post_service.get_user_posts(target_user_id, post_type, limit=limit, skip=skip)


@router.get("/feed/posts")
async def get_feed_posts(
    post_type: str = Query("real", description="Post type: 'real' or 'avatar'"),
    limit: int = Query(20, description="Number of posts to return"),
    skip: int = Query(0, description="Number of posts to skip"),
    request: Request = None
):
    """Get feed posts (posts from friends and user) with pagination"""
    current_user = await require_auth(request)
    post_service = get_post_service()
    return await post_service.get_feed_posts(current_user.id, post_type, limit=limit, skip=skip)


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


@router.post("/posts/get-upload-url")
async def get_upload_url(request: Request, data: Dict[str, Any]):
    """Get a presigned S3 URL for direct image upload"""
    user = await require_auth(request)
    
    filename = data.get('filename', 'image.jpg')
    content_type = data.get('content_type', 'image/jpeg')
    
    # Validate content type
    if not content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Generate unique S3 key
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_ext = os.path.splitext(filename)[1] or '.jpg'
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in os.path.splitext(filename)[0])
    s3_key = f"images/{timestamp}_{safe_name}{file_ext}"
    
    # Get S3 configuration
    s3_bucket = os.environ.get('AWS_S3_BUCKET', '')
    s3_region = os.environ.get('AWS_S3_REGION', 'us-west-2')
    
    if not s3_bucket:
        raise HTTPException(status_code=500, detail="S3 not configured")
    
    try:
        s3_client = boto3.client('s3', region_name=s3_region)
        
        # Generate presigned URL for upload
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': s3_bucket,
                'Key': s3_key,
                'ContentType': content_type,
            },
            ExpiresIn=300,  # 5 minutes
        )
        
        # Generate the final image URL
        image_url = f"https://{s3_bucket}.s3.{s3_region}.amazonaws.com/{s3_key}"
        
        return {
            "upload_url": presigned_url,
            "image_url": image_url,
            "s3_key": s3_key,
        }
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")


@router.post("/posts/create-with-image")
async def create_post_with_image(request: Request, data: Dict[str, Any]):
    """Create a post after image has been uploaded to S3"""
    user = await require_auth(request)
    
    image_url = data.get('image_url')
    caption = data.get('caption', '')
    post_type = data.get('post_type', 'real')
    
    if not image_url:
        raise HTTPException(status_code=400, detail="image_url is required")
    
    # Create post with image
    post_service = get_post_service()
    post_data = {
        'text': caption,
        'post_type': post_type,
        'image_url': image_url
    }
    
    post = await post_service.create_post(user.id, post_data)
    logger.info(f"Post created with image: {post.get('id')}, image_url: {image_url}")
    
    return {
        "success": True,
        "post": post,
        "image_url": image_url
    }


@router.post("/posts/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    post_type: str = Form("real"),
    request: Request = None
):
    """Upload an image and create a photo post (legacy endpoint - may have issues with large files)"""
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


@router.post("/posts/presigned-upload")
async def get_presigned_upload_url(
    request: Request,
    data: Dict[str, Any]
):
    """
    Get a presigned URL for direct S3 upload.
    This bypasses API Gateway payload limits.
    """
    user = await require_auth(request)
    
    filename = data.get('filename', 'image.jpg')
    content_type = data.get('content_type', 'image/jpeg')
    subfolder = data.get('subfolder', 'images')
    
    # Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_ext = os.path.splitext(filename)[1] or '.jpg'
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in os.path.splitext(filename)[0])
    unique_filename = f"{timestamp}_{safe_name}{file_ext}"
    s3_key = f"{subfolder}/{unique_filename}"
    
    # Get S3 configuration
    s3_bucket = os.environ.get('AWS_S3_BUCKET', '')
    s3_region = os.environ.get('AWS_S3_REGION', 'us-west-2')
    
    if not s3_bucket:
        raise HTTPException(status_code=500, detail="S3 not configured")
    
    try:
        s3_client = boto3.client('s3', region_name=s3_region)
        
        # Generate presigned URL for PUT operation
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': s3_bucket,
                'Key': s3_key,
                'ContentType': content_type,
            },
            ExpiresIn=300  # 5 minutes
        )
        
        # Generate the final public URL for the file
        public_url = f"https://{s3_bucket}.s3.{s3_region}.amazonaws.com/{s3_key}"
        
        logger.info(f"Generated presigned URL for {s3_key}")
        
        return {
            "presigned_url": presigned_url,
            "public_url": public_url,
            "s3_key": s3_key,
            "expires_in": 300
        }
        
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")


@router.post("/posts/create-with-s3-image")
async def create_post_with_s3_image(
    request: Request,
    data: Dict[str, Any]
):
    """
    Create a post with an image that was uploaded directly to S3.
    Called after successful presigned URL upload.
    """
    user = await require_auth(request)
    
    image_url = data.get('image_url')
    caption = data.get('caption', '')
    post_type = data.get('post_type', 'real')
    
    if not image_url:
        raise HTTPException(status_code=400, detail="image_url is required")
    
    # Create post with image
    post_service = get_post_service()
    post_data = {
        'text': caption,
        'post_type': post_type,
        'image_url': image_url
    }
    
    post = await post_service.create_post(user.id, post_data)
    logger.info(f"Post created with S3 image: {post.get('id')}, image_url: {image_url}")
    
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

